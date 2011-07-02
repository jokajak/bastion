import ldap
import getpass
import tg
from bastion.model import DBSession, metadata
from bastion.lib.scheduler.scheduler import get_task, scheduler
from datetime import datetime, timedelta
from paste.deploy.converters import asbool
import logging
log = logging.getLogger(__name__)

nisNetgroupTriple = "( %s , %s , %s )"
def format_add_entry(hostname, user, timestamp):
    return (ldap.MOD_ADD, 'nisNetgroupTriple', str(nisNetgroupTriple % (hostname, user, timestamp )))

def format_mod_entry(hostname, user, timestamp):
    return (ldap.MOD_REPLACE, 'nisNetgroupTriple', str(nisNetgroupTriple % (hostname, user, timestamp )))

def format_remove_entry(hostname, user, timestamp):
    return (ldap.MOD_DELETE, 'nisNetgroupTriple', str(nisNetgroupTriple % (hostname, user, timestamp )))

def get_current_entries(con, netgroup_dn, netgroup):
    log.debug("Getting entries for %s" % netgroup)
    res = con.search(netgroup_dn, ldap.SCOPE_SUBTREE, netgroup)
    res, entries = con.result(res)
    # returns something like this:
    #(101, [('cn=home_hosts,ou=Groups,dc=example,dc=com', {'objectClass': ['top', 'nisnetgroup'], 'cn': ['home_hosts']})])
    if len(entries) == 1:
        dn, entry = entries[0]
    else:
        # multiple results, what do we do?  raise an error eventually
        pass
    res = []
    if 'nisNetgroupTriple' in entry:
        log.debug(len(entry['nisNetgroupTriple']))
        log.debug(entry['nisNetgroupTriple'])
        for triple_str in entry['nisNetgroupTriple']:
            # each value in the array is a string, need to parse it out in to a tuple
            triple_str = triple_str.strip('(').strip(')')
            triple_str = triple_str.replace(' ', '')
            host, user, time = triple_str.split(',')
            new_entry=(host, user, time)
            res.append(new_entry)
    return dn, res

def get_connection():
    ldap_server = tg.config.get('ldap.server')
    bind_dn = tg.config.get('ldap.bind_dn')
    pw = tg.config.get('ldap.bind_password')
    con = ldap.initialize(ldap_server)
    res = con.simple_bind(bind_dn, pw)
    return con

def prune_expired_entries(entries, timeout):
    """
    Given a list of netgroup triple entries and a timeout this function removes
    entries from the list whose timeout has passed
    """
    today = datetime.today()
    valid_entries = []
    invalid_entries = []
    offset = timedelta(int(timeout))
    log.debug("prune_expired_entries start")
    log.debug(entries)
    for entry in entries:
        log.debug("prune_expired_entries: checking an entry")
        log.debug(entry)
        timestamp = datetime.strptime(entry[2], "%Y%m%d%H%M")
        if (timestamp + offset > today):
            valid_entries.append(entry)
    return valid_entries, invalid_entries

def sync_entries():
    log.debug("sync_entries: Starting")
    from bastion.model.auth import User
    users = DBSession.query(User)

    db_home_entries = []
    db_travel_entries = []
    ldap_home_entries = []
    ldap_travel_entries = []

    use_ip = asbool(tg.config.get('netgroups.store_ip'))
    log.debug(use_ip)

    domain = tg.config.get('netgroups.domain', 'travel.addrs')
    home_netgroup = tg.config.get('netgroups.home', 'home')
    travel_netgroup = tg.config.get('netgroups.travel', 'travel')
    netgroup_dn = tg.config.get('netgroups.base_dn')

    netgroups = [ home_netgroup, travel_netgroup ]
    log.debug("sync_entries: Getting db entries")
    for user in users:
        if user.home_addr:
            timeout = tg.config.get('netgroups.timeout.%s' % home_netgroup)
            if use_ip:
                hostname = user.home_addr
            else:
                hostname = "%s.%s.%s" % (user.user_name, home_netgroup, domain)
            entry = (hostname, user.user_name, user.home_updated.strftime("%Y%m%d%H%M"))
            db_home_entries.append(entry)
        if user.travel_addr:
            timeout = tg.config.get('netgroups.timeout.%s' % travel_netgroup)
            if use_ip:
                hostname = user.travel_addr
            else:
                hostname = "%s.%s.%s" % (user.user_name, travel_netgroup, domain)
            entry = (hostname, user.user_name, user.travel_updated.strftime("%Y%m%d%H%M"))
            db_travel_entries.append(entry)

    log.debug("sync_entries: Getting ldap entries")
    con = get_connection()
    netgroup = tg.config.get('netgroups.search.format', "(cn=%s)") % home_netgroup
    timeout = tg.config.get('netgroups.timeout.%s' % home_netgroup)
    netgroup, ldap_home_entries = get_current_entries(con, netgroup_dn, netgroup)
    db_home_entries, to_prune = prune_expired_entries(db_home_entries, timeout)
    ldap_home_entries, to_prune = prune_expired_entries(ldap_home_entries, timeout)
    # now we only have valid entries in both db_*_entries and ldap_*_entries
    log.debug(db_home_entries)
    db_home_lookup = dict([(entry[1], entry) for entry in db_home_entries])

    to_modify = []
    for entry in ldap_home_entries:
        if ( entry[1] not in db_home_lookup ):
            to_prune.append(entry)
            continue
        db_entry = db_home_lookup[entry[1]]
        if ( db_entry != entry ):
            to_modify.append(db_entry)
        del db_home_lookup[entry[1]]
    actions = [format_remove_entry(entry[0], entry[1], entry[2]) for entry in to_prune]
    [actions.append(format_mod_entry(entry[0], entry[1], entry[2])) for entry in to_modify]
    [actions.append(format_add_entry(entry[0], entry[1], entry[2])) for username, entry in db_home_lookup.iteritems()]
    if len(actions) > 0:
        log.debug("Synchronizing home hosts")
        log.debug(netgroup)
        log.debug(actions)
        res = con.modify(netgroup, actions)
        res, result = con.result(res)
    else:
        log.debug("No entries to change for home hosts")

    netgroup = tg.config.get('netgroups.search.format', "(cn=%s)") % travel_netgroup
    timeout = tg.config.get('netgroups.timeout.%s' % travel_netgroup)
    netgroup, ldap_travel_entries = get_current_entries(con, netgroup_dn, netgroup)
    db_travel_entries, to_prune = prune_expired_entries(db_travel_entries, timeout)
    ldap_travel_entries, to_prune = prune_expired_entries(ldap_travel_entries, timeout)
    # now we only have valid entries in both db_*_entries and ldap_*_entries
    db_user_lookup = dict([(entry[1], entry) for entry in db_travel_entries])
    log.debug(db_user_lookup)
    log.debug(db_travel_entries)
    log.debug(format_add_entry(db_travel_entries[0][0], db_travel_entries[0][1], db_travel_entries[0][2]))

    to_modify = []
    for entry in ldap_travel_entries:
        if ( entry[1] not in db_user_lookup ):
            to_prune.append(entry)
            continue
        db_entry = db_user_lookup[entry[1]]
        if ( db_entry != entry ):
            to_modify.append(db_entry)
        del db_user_lookup[entry[1]]
    actions = [format_add_entry(entry[0], entry[1], entry[2]) for username, entry in db_user_lookup.iteritems()]
    [actions.append(format_mod_entry(entry[0], entry[1], entry[2])) for entry in to_modify]
    [actions.append(format_remove_entry(entry[0], entry[1], entry[2])) for entry in to_prune]
    if len(actions) > 0:
        log.debug("Synchronizing travel hosts")
        log.debug(netgroup)
        log.debug(actions)
        res = con.modify(netgroup, actions)
        res, result = con.result(res)
    else:
        log.debug("No entries to change for travel hosts")

    # determine common entries
    con.unbind()
    # rename the task after it completes so we can run it again
    scheduler.rename_task("sync", "sync-completed")
