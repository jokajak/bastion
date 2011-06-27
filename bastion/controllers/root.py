# -*- coding: utf-8 -*-
"""Main Controller"""

from tg import expose, flash, require, url, request, redirect
from pylons.i18n import ugettext as _, lazy_ugettext as l_
from repoze.what import predicates

from bastion.lib.base import BaseController
from bastion.model import DBSession, metadata
from bastion.controllers.error import ErrorController
from bastion import model
from bastion.controllers.secure import SecureController

__all__ = ['RootController']


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
        remote_addr = request.environ.get('REMOTE_ADDR', 'unknown addr')
        return dict(page='index',
                    remote_addr=remote_addr)

    @expose('bastion.templates.about')
    def about(self):
        """Handle the 'about' page."""
        return dict(page='about')

    @expose('bastion.templates.authentication')
    def auth(self):
        """Display some information about auth* on this application."""
        return dict(page='auth')

    @expose('bastion.templates.index')
    @require(predicates.has_permission('manage', msg=l_('Only for managers')))
    def manage(self, **kw):
        from bastion.model.auth import User

        users = DBSession.query(User).get_all()
        """Illustrate how a page for managers only works."""
        return dict(page='managers stuff')

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
