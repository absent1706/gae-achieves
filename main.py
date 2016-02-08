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

from models import Cheever, Achievement, LeaderboardStats, SystemStats
from google.appengine.ext import ndb

calendarauthdecorator = OAuth2Decorator(
    client_id='970235710504-3l5ka4kem2lg68eb7tkb10mjr2ghtrif.apps.googleusercontent.com',
    client_secret='Nsj0qTDutY9P8VYQsGXDIla0',
    scope='https://www.googleapis.com/auth/calendar.readonly')

jinja = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))


class _BaseHandler(webapp2.RequestHandler):
    """docstring for _BaseHandler"""

    def initialize(self, request, response):
        super(_BaseHandler, self).initialize(request, response)
        self.user = users.get_current_user()
        if self.user:
            self.template_values = {
                'user': self.user,
                'is_admin': users.is_current_user_admin(),
                'logout_url': users.create_logout_url('/'),
                'versionid': os.environ['CURRENT_VERSION_ID']}
        else:
            self.template_values = {
                'login_url': users.create_login_url(self.request.url)}


class HomePage(_BaseHandler):

    def get(self):
        logging.info('Home page requested')

        results = Achievement.query().order(
            -Achievement.numLiked,
            -Achievement.score).fetch()

        self.template_values['achievements'] = results

        template = jinja.get_template('home.html')
        self.response.out.write(template.render(self.template_values))


class CalendarPage(_BaseHandler):

    @calendarauthdecorator.oauth_required
    def get(self):
        logging.info('CalendarPage requested')

        auth_http = calendarauthdecorator.http()
        service = build('calendar', 'v3', http=auth_http)
        events = service.events().list(
            calendarId='primary',
            timeMin='2013-01-01T00:00:00-00:00',
            maxResults=20).execute()

        self.template_values['events'] = [event for event in events['items']]

        template = jinja.get_template('calendar.html')
        self.response.out.write(template.render(self.template_values))


class ProfilePage(_BaseHandler):

    def get(self):
        logging.info('ProfilePage class requested')

        # Look for existing profile based on User's email
        cheever_key = ndb.Key('Cheever', self.user.email())
        cheever = cheever_key.get()

        if not cheever:
            # Profile doesn't yet exist, create a new Cheever with default
            # values
            cheever = Cheever(key=ndb.Key("Cheever", self.user.email()))

        # Add the cheever model to our template values for rendering
        self.template_values['cheever'] = cheever

        template = jinja.get_template('profile.html')
        self.response.out.write(template.render(self.template_values))

    def post(self):
        logging.info('ProfilePage posted')

        # Look for existing profile based on Users' email
        cheever_key = ndb.Key('Cheever', self.user.email())
        cheever = cheever_key.get()

        if not cheever:
            # Profile doesn't yet exist, create a new Cheever with default
            # values
            cheever = Cheever(key=ndb.Key("Cheever", self.user.email()))

        # Update the user controlled values
        cheever.username = self.request.get('username')
        cheever.notifyEmail = self.request.get('notifyEmail')
        cheever.bio = self.request.get('bio')

        # Commit our updates to the datastore
        cheever.put()

        self.redirect('/profile')


class NewAchievement(_BaseHandler):

    def post(self):
        logging.info('newAchievement posted')

        # Get the current Cheever's profile so we can update their numContribs
        cheever_key = ndb.Key('Cheever', self.user.email())
        cheever = cheever_key.get()

        # Create new achievement with auto - generated key
        achievement = Achievement()

        achievement.populate(
            title=self.request.get('title'),
            description=self.request.get('description'),
            category=self.request.get('category'),
            score=int(self.request.get('score')),
            contributor=cheever.username,
            verified=True
        )

        cheever.numContribs += 1

        # Commit our updates to the datastore
        achievement.put()
        cheever.put()

        self.redirect('/profile')

app = webapp2.WSGIApplication([
    ('/achievements', HomePage),
    ('/cheevers', HomePage),
    ('/profile', ProfilePage),
    ('/newAchievement', NewAchievement),
    ('/calendar', CalendarPage),
    ('/admin', HomePage),
    (calendarauthdecorator.callback_path, calendarauthdecorator.callback_handler()),
    ('/', HomePage),
], debug=True)
