# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _, lazy_ugettext as l_
from repoze.what import predicates
from datetime import datetime
from tw.forms import DataGrid
from tg.decorators import paginate
import genshi

from bastion.lib.base import BaseController
from bastion.model import DBSession, metadata
from bastion.controllers.error import ErrorController
from bastion import model
from bastion.controllers.secure import SecureController

__all__ = ['RootController']

user_grid = DataGrid(fields=[
    ('Username', 'user_name'),
    ('Home IP', 'home_addr'),
    ('Home Last Updated', 'home_updated'),
    ('Travel IP', 'travel_addr'),
    ('Travel Last Updated', 'travel_updated'),
    ('Action', lambda obj:genshi.Markup('<a href="%s">Remove Home IP</a>' % url('/delHome', params=dict(user_id=obj.user_id)))),
    ('Action', lambda obj:genshi.Markup('<a href="%s">Remove Travel IP</a>' % url('/delTravel', params=dict(user_id=obj.user_id))))
])

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
    secc = SecureController()

    error = ErrorController()

    @expose('bastion.templates.index')
    @require(predicates.not_anonymous(msg="Only logged in users can access this site"))
    def index(self):
        """Handle the front-page."""
        from bastion.model.auth import User
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')
        userid = request.identity['repoze.who.userid']
        user = User.by_user_name(userid)
        if (remote_addr != user.home_addr):
            user.travel_addr = remote_addr
            user.travel_updated = datetime.now()
        return dict(page='index',
                    remote_addr=remote_addr,
                    isHome=remote_addr==user.home_addr)

    @expose('bastion.templates.homeip')
    @expose('json')
    @require(predicates.not_anonymous(msg='Only logged in users can access this site'))
    def sethome(self, came_from=url('/')):
        """Handle homeip requests"""
        from bastion.model.auth import User
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')
        userid = request.identity['repoze.who.userid']
        user = User.by_user_name(userid)
        user.home_addr = remote_addr
        user.home_updated = datetime.now()
        return dict(came_from=came_from, remote_addr=remote_addr)

    @expose('bastion.templates.about')
    def about(self):
        """Handle the 'about' page."""
        return dict(page='about')

    @expose('bastion.templates.admin')
    @paginate("users", items_per_page=25)
    @require(predicates.has_permission('manage', msg=l_('Only for managers')))
    def admin(self, **kw):
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')
        from bastion.model.auth import User

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
