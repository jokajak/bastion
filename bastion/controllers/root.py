# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _, lazy_ugettext as l_
from repoze.what import predicates
from datetime import datetime
from tw.forms import DataGrid
from tg.decorators import paginate
import tg
import genshi

from bastion.lib.base import BaseController
from bastion.model import DBSession, metadata
from bastion.controllers.error import ErrorController
from bastion import model
from bastion.controllers.secure import SecureController
from bastion.model.auth import User
from bastion.lib.scheduler.scheduler import add_single_task
from bastion.lib.netgroups import sync_entries
from bastion.lib.ipaddr import IPNetwork, IPAddress

__all__ = ['RootController']
import logging
log = logging.getLogger(__name__)

user_grid = DataGrid(fields=[
    ('Username', 'user_name'),
    ('Home IP', 'home_addr'),
    ('Home Last Updated', 'home_updated'),
    ('Travel IP', 'travel_addr'),
    ('Travel Last Updated', 'travel_updated'),
    ('Action', lambda obj:genshi.Markup('<a href="%s">Remove Home IP</a>' % url('/delHome', params=dict(user_id=obj.user_id)))),
    ('Action', lambda obj:genshi.Markup('<a href="%s">Remove Travel IP</a>' % url('/delTravel', params=dict(user_id=obj.user_id))))
])

private_networks = tg.config.get('netgroups.excluded_networks')
if private_networks:
    private_networks = private_networks.split(" ")
    excluded_networks = []
    for network in private_networks:
        try:
            net = IPNetwork(network)
            excluded_networks.append(net)
        except ValueError:
            log.warn("Network %s does not appear valid, skipping" % network)
    log.debug(excluded_networks)
else:
    log.info("No excluded networks configured")

class RootController(BaseController):
    """
    The root controller for the bastion application.

    All the other controllers and WSGI applications should be mounted on this
    controller. For example::

        panel = ControlPanelController()
        another_app = AnotherWSGIApplication()

    Keep in mind that WSGI applications shouldn't be mounted directly: They
    must be wrapped around with :class:`tg.controllers.WSGIAppController`.

    """
    error = ErrorController()

    @expose('bastion.templates.index')
    @require(predicates.not_anonymous(msg="Only logged in users can access this site"))
    def index(self):
        """Handle the front-page."""
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')
        try:
            ip = IPAddress(remote_addr)
        except:
            ip = None
            pass
        userid = request.identity['repoze.who.userid']
        user = User.by_user_name(userid)
        for network in excluded_networks:
            if ip in network:
                return dict(page='index',
                            remote_addr=remote_addr,
                            isExcluded=true)
        if (remote_addr != user.home_addr):
            user.travel_addr = remote_addr
            user.travel_updated = datetime.now()
            try:
                # if the task is already running just piggy back on the next
                # run
                add_single_task(action=sync_entries, taskname="sync", initialdelay=5)
            except ValueError:
                pass
        return dict(page='index',
                    remote_addr=remote_addr,
                    isHome=remote_addr==user.home_addr)

    @expose()
    @expose('json')
    @require(predicates.not_anonymous(msg='Only logged in users can access this site'))
    def sethome(self, came_from=url('/')):
        """Handle homeip requests"""
        msg = _("%s has been set as your home IP" % remote_addr)
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')
        userid = request.identity['repoze.who.userid']
        user = User.by_user_name(userid)
        user.home_addr = remote_addr
        user.home_updated = datetime.now()
        try:
            # if the task is already running just piggy back on the next run
            add_single_task(action=sync_entries, taskname="sync", initialdelay=5)
        except ValueError:
            pass
        for network in excluded_networks:
            if remote_addr in network:
                msg = _("%s has NOT been set as your home IP.  It is on an excluded network" % remote_addr)
                redirect(came_from)
        flash(msg)
        redirect(came_from)

    @expose('bastion.templates.about')
    def about(self):
        """Handle the 'about' page."""
        return dict(page='about')

    @expose('bastion.templates.admin')
    @paginate("users", items_per_page=25)
    @require(predicates.has_permission('manage', msg=l_('Only for managers')))
    def admin(self, **kw):
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')

        users = DBSession.query(User)
        """Illustrate how a page for managers only works."""
        return dict(page='managers stuff',
                    grid=user_grid,
                    users=users)

    @expose('bastion.templates.login')
    def login(self, came_from=url('/')):
        """Start the user login."""
        login_counter = request.environ['repoze.who.logins']
        if login_counter > 0:
            flash(_('Wrong credentials'), 'warning')
        return dict(page='login', login_counter=str(login_counter),
                    came_from=came_from)

    @expose()
    def post_login(self, came_from=url('/')):
        """
        Redirect the user to the initially requested page on successful
        authentication or redirect her back to the login page if login failed.

        """
        if not request.identity:
            login_counter = request.environ['repoze.who.logins'] + 1
            redirect(url('/login', came_from=came_from, __logins=login_counter))
        userid = request.identity['repoze.who.userid']
        flash(_('Welcome back, %s!') % userid)
        redirect(came_from)

    @expose()
    def post_logout(self, came_from=url('/')):
        """
        Redirect the user to the initially requested page on logout and say
        goodbye as well.

        """
        flash(_('We hope to see you soon!'))
        redirect(came_from)

    @expose()
    def delHome(self, user_id=None, came_from=url('/admin')):
        """
        Redirect the user to the initially requested page when home is removed
        and inform the user the action was performed
        """
        if (not user_id):
            user_name = request.identity['repoze.who.userid']
            user = User.by_user_name(user_name)
        else:
            user = User.by_user_id(user_id)
        user.home_addr = None

        try:
            # if the task is already running just piggy back on the next run
            add_single_task(action=sync_entries, taskname="sync", initialdelay=5)
        except ValueError:
            pass
        flash(_("The home IP has been removed"))
        redirect(came_from)

    @expose()
    def delTravel(self, user_id, came_from=url('/admin')):
        """
        Redirect the user to the initially requested page when home is removed
        and inform the user the action was performed
        """
        user = User.by_user_id(user_id)
        user.travel_addr = None

        try:
            # if the task is already running just piggy back on the next run
            add_single_task(action=sync_entries, taskname="sync", initialdelay=5)
        except ValueError:
            pass
        flash(_("The travel IP has been removed"))
        redirect(came_from)

    @expose('json')
    def export_dns(self, types=None):
        domain = tg.config.get('netgroups.domain', 'travel.addrs')
        home_netgroup = tg.config.get('netgroups.home', 'home')
        travel_netgroup = tg.config.get('netgroups.travel', 'travel')
        home_timeout = tg.config.get('netgroups.timeout.%s' % home_netgroup)
        travel_timeout = tg.config.get('netgroups.timeout.%s' % travel_netgroup)
        res = []
        if not types:
            users = DBSession.query(User)
            for user in users:
                if user.home_addr:
                    hostname = "%s.%s.%s" % (user.user_name, home_netgroup, domain)
                    res.append("+%s:%s:15" % (hostname, user.home_addr))
                if user.travel_addr:
                    hostname = "%s.%s.%s" % (user.user_name, travel_netgroup, domain)
                    res.append("+%s:%s:15" % (hostname, user.travel_addr))

        else:
            pass
        return dict(data=res)
