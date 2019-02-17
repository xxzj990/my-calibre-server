#!/usr/bin/python
#-*- coding: UTF-8 -*-

import datetime
import logging
from tornado import web
from models import Reader
from base_handlers import BaseHandler
import json

class Done(BaseHandler):
    def get_sa(self, user):
        social = user.social_auth.all()
        if not social: return ""
        return dict(social[0].extra_data)

    def get(self):
        user = self.get_current_user()
        sa = self.get_sa(user)
        if sa:
            user.username = sa['username']
            user.save()
        logging.info("LOGIN: %d - %s - %s" % ( user.id, user.username, sa))

        if user and not user.extra:
            socials = user.social_auth.all()
            if socials:
                logging.info("init new user %s, info=%s" % (user.username, socials))
                user.init(socials[0])
                user.save()

        url = self.get_secure_cookie('login_redirect')
        if not url: url = "/"
        self.redirect( url )

class Login(BaseHandler):
    def auto_login(self):
        auto = int(self.settings.get('auto_login', 0))
        if not auto: return False

        logging.info("Auto login as user %s" % auto)
        self.set_secure_cookie("user_id", str(auto))
        user = self.session.query(Reader).get(auto)
        if not user:
            logging.info("Init default auto login user")
            user = Reader(id=auto)
            user.init_default_user()
            user.save()
        self.add_msg("success", _("自动登录成功。"))
        return True

    def get(self):
        url = self.get_argument("next", "/")
        self.set_secure_cookie("login_redirect", url)
        if self.auto_login():
            return self.redirect( url )
        return self.html_page('login.html', vars())

class Logout(BaseHandler):
    def get(self):
        self.set_secure_cookie("user_id", "")
        self.set_secure_cookie("admin_id", "")
        self.redirect('/')

class SettingView(BaseHandler):
    def get(self, **kwrags):
        user = self.current_user
        return self.html_page('setting/view.html', vars())

class SettingSave(BaseHandler):
    @web.authenticated
    def post(self):
        user = self.current_user
        modify = user.extra
        for key in ['kindle_email']:
            if key in self.request.arguments:
                modify[key] = self.get_argument(key)
                user.email = self.get_argument(key)
        if modify:
            logging.debug(modify)
            user.extra.update(modify)
            user.update_time = datetime.datetime.now()
            user.save()
            self.add_msg("success", _("Settings saved."))
        else:
            self.add_msg("info", _("Nothing changed."))
        self.redirect('/setting', 302)

class UserView(BaseHandler):
    @web.authenticated
    def get(self):
        nav = "user"
        user = self.current_user
        output = {}
        for key in ['read_history', 'visit_history']:
            ids = [ b['id'] for b in user.extra[key]][:24]
            books = self.db.get_data_as_dict(ids=ids)
            orders = dict( zip(ids, range(100)) )
            books.sort(lambda x,y: cmp(orders.get(x['id']), orders.get(y['id'])))
            output[key] = books[:12]

        return self.html_page('user/view.html', vars())

class AdminView(BaseHandler):
    @web.authenticated
    def get(self):
        if not self.is_admin():
            self.redirect('/', 302)
        items = self.session.query(Reader).order_by(Reader.access_time.desc())
        count = items.count()
        delta = 20
        start = self.get_argument_start()
        page_max = count / delta
        page_now = start / delta
        pages = []
        for p in range(page_now-4, page_now+4):
            if 0 <= p and p <= page_max:
                pages.append(p)
        users = items.limit(delta).offset(start).all()
        return self.html_page('admin/view.html', vars())

class AdminSet(BaseHandler):
    @web.authenticated
    def get(self):
        user_id = self.get_argument("user_id", None)
        if user_id and self.is_admin():
            self.set_secure_cookie("admin_id", self.user_id())
            self.set_secure_cookie("user_id", user_id)
        self.redirect('/', 302)


def routes():
    return                     [
            (r'/done/',        Done),
            (r"/login",        Login),
            (r'/logout',       Logout),
            (r'/setting',      SettingView),
            (r'/setting/save', SettingSave),
            (r'/user',         UserView),
            (r'/admin',        AdminView),
            (r'/admin/set',    AdminSet),
    ]


