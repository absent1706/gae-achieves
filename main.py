#!/usr/bin/env python

import webapp2
import jinja2
import datetime
import os
import logging

# import sys
# sys.path.append(os.path.join(sys.path[0], 'lib'))
# import pdb; pdb.set_trace()

from google.appengine.api import users
from apiclient.discovery import build
from oauth2client.appengine import OAuth2Decorator

calendarauthdecorator = OAuth2Decorator(
    client_id='970235710504-3l5ka4kem2lg68eb7tkb10mjr2ghtrif.apps.googleusercontent.com',
    client_secret='Nsj0qTDutY9P8VYQsGXDIla0',
    scope='https://www.googleapis.com/auth/calendar.readonly')

jinja = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

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

class CalendarPage(_BaseHandler):
    @calendarauthdecorator.oauth_required
    def get(self):
        logging.info('CalendarPage requested')

        auth_http = calendarauthdecorator.http()
        service = build('calendar', 'v3', http = auth_http)
        events = service.events().list(
            calendarId='primary',
            timeMin='2013-01-01T00:00:00-00:00',
            maxResults=20).execute()

        self.context['events'] = [event for event in events['items']]

        template = jinja.get_template('calendar.html')
        self.response.out.write(template.render(self.context))

app = webapp2.WSGIApplication([
    ('/achievements', HomePage),
    ('/cheevers', HomePage),
    ('/profile', HomePage),
    ('/calendar', CalendarPage),
    ('/admin', HomePage),
    (calendarauthdecorator.callback_path, calendarauthdecorator.callback_handler()),
    ('/', HomePage),
], debug=True)
