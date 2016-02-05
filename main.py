#!/usr/bin/env python

import webapp2
import jinja2
import datetime
import os
import logging

from google.appengine.api import users

jinja = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class _BaseHandler(webapp2.RequestHandler):
    """docstring for _BaseHandler"""
    def initialize(self, request, response):
        super(_BaseHandler, self).initialize(request,response)
        self.user = users.get_current_user()
        if self.user:
            self.context = {
                'user': self.user,
                'is_admin': users.is_current_user_admin(),
                'logout_url': users.create_logout_url('/'),
                'versionid': os.environ['CURRENT_VERSION_ID']}
        else:
            self.context = {'login_url': users.create_login_url(self.request.url)}


class HomePage(_BaseHandler):
    def get(self):
        logging.info('Home page requested')
        template = jinja.get_template('home.html')
        self.response.out.write(template.render(self.context))

app = webapp2.WSGIApplication([
    ('/achievements', HomePage),
    ('/cheevers', HomePage),
    ('/profile', HomePage),
    ('/calendar', HomePage),
    ('/admin', HomePage),
    ('/', HomePage),
], debug=True)
