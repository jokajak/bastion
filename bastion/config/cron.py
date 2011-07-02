from bastion.lib.scheduler import start_scheduler
from bastion.lib.scheduler.scheduler import add_interval_task, add_single_task
from bastion.lib.netgroups import prune_expired_entries, sync_entries
import sys
import logging
log = logging.getLogger(__name__)

def testTask(email=None):
    log.debug("testTask called")

def schedule():
    """ start scheduler and setup recurring tasks """

    if "shell" in sys.argv: # disable cron in paster shell mode
        return

    log.info("Starting Scheduler Manager")
    start_scheduler()

    # ================ #
    # Add cron tasks here

    # run at intervals (once an hour)
    add_interval_task(action=sync_entries, taskname="prune", interval=60*60, initialdelay=5)

    # ================= #
