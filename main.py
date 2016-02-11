#!/usr/bin/env python

import webapp2
import jinja2
import datetime
import os
import logging

# import sys
# sys.path.append(os.path.join(sys.path[0], 'lib'))

from google.appengine.api import users
from apiclient.discovery import build
from oauth2client.appengine import OAuth2Decorator

from models import Cheever, Achievement, LeaderboardStats, SystemStats
from google.appengine.ext import ndb

from google.appengine.api import memcache

from google.appengine.api import taskqueue, mail

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

        results = memcache.get('popular')

        if results is None:
            results = Achievement.query().order(
                -Achievement.numLiked,
                -Achievement.score).fetch(10)
            memcache.add('popular', results, time=60)

        self.template_values['achievements'] = results

        contribStats = memcache.get('contribStats')
        if contribStats is None:
            query = LeaderboardStats.query()
            query = query.filter(LeaderboardStats.statType == 'contribution')
            query = query.order(-LeaderboardStats.value)
            contribStats = query.fetch()

            memcache.add('contribStats', contribStats)

        self.template_values['contribStats'] = contribStats

        scoreStats = memcache.get('scoreStats')
        if scoreStats is None:
            query = LeaderboardStats.query()
            query = query.filter(LeaderboardStats.statType == 'score')
            query = query.order(-LeaderboardStats.value)
            scoreStats = query.fetch()

            memcache.add('scoreStats', scoreStats)

        self.template_values['scoreStats'] = scoreStats

        systemStats = memcache.get('systemStats')
        self.template_values['systemStats'] = systemStats

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
            verified=False
        )

        cheever.numContribs += 1

        # Commit our updates to the datastore
        @ndb.transactional(xg=True)
        def commit():
            achievement.put()
            cheever.put()

        commit()

        self.redirect('/profile')


class CheeversPage(_BaseHandler):

    def get(self):
        logging.info('CheeversPage class requested')
        template = jinja.get_template('cheevers.html')
        self.response.out.write(
            template.render(self.template_values))

    def post(self):
        logging.info('CheeversPage posted')

        query = Cheever.query()

        if self.request.get('username') != '':
            query = query.filter(Cheever.username ==
                                 self.request.get('username'))

        try:
            beginScore = int(self.request.get('beginScore'))
            query = query.filter(Cheever.numScore >= beginScore)
        except:
            pass

        try:
            endScore = int(self.request.get('endScore'))
            query = query.filter(Cheever.numScore <= endScore)
        except:
            pass

        logging.info(self.request.get('beginScore'))
        logging.info(self.request.get('endScore'))

        query = query.order(Cheever.numScore, Cheever.username)

        logging.info(query)

        results = query.fetch()

        current_key = ndb.Key(Cheever, self.user.email())
        for c in results:
            c.followText = 'Follow'
            if current_key in c.followers:
                c.followText = 'Unfollow'

        self.template_values['cheevers'] = results
        template = jinja.get_template('cheevers.html')

        self.response.out.write(
            template.render(self.template_values))


class AchievementsPage(_BaseHandler):

    def get(self):
        logging.info('AchievementsPage class requested')
        template = jinja.get_template('achievements.html')
        self.response.out.write(
            template.render(self.template_values))

    def post(self):
        logging.info('AchievementsPage posted')

        query = Achievement.query()

        if self.request.get('title') != '':
            query = query.filter(Achievement.title ==
                                 self.request.get('title'))

        if self.request.get('contributor') != '':
            query = query.filter(
                Achievement.contributor == self.request.get('contributor'))

        try:
            beginDate = datetime.datetime.strptime(
                self.request.get('beginDate'), '%Y-%m-%d')
            query = query.filter(Achievement.created >= beginDate)
        except:
            beginDate = datetime.datetime(1900, 1, 1)

        try:
            endDate = datetime.datetime.strptime(
                self.request.get('endDate'), '%Y-%m-%d')
            query = query.filter(Achievement.created <= endDate)
        except:
            endDate = datetime.datetime.now()

        query = query.filter(Achievement.verified == True)

        query = query.order(ndb.GenericProperty(self.request.get('sort')))

        logging.info(self.request.get('sort'))
        logging.info(query)

        results = query.fetch()

        self.template_values['achievements'] = results
        template = jinja.get_template('achievements.html')

        self.response.out.write(
            template.render(self.template_values))


class followCheever(_BaseHandler):

    def get(self):
        logging.info('followCheever requested')

        cheever_key = ndb.Key(urlsafe=self.request.get('key'))
        cheever = cheever_key.get()

        current_key = ndb.Key(Cheever, self.user.email())
        current = current_key.get()

        if current_key in cheever.followers:
            cheever.followers.remove(cheever_key)
            cheever.numFollowers -= 1

            current.following.remove(cheever_key)
            current.numFollowing -= 1

        else:
            cheever.followers.append(current_key)
            cheever.numFollowers += 1

            current.following.append(cheever_key)
            current.numFollowing += 1

        @ndb.transactional(xg=True)
        def commit():
            cheever.put()
            current.put()

        commit()

        self.redirect('/cheevers')


class likeAchievement(_BaseHandler):

    def get(self):
        logging.info('likeAchievement requested')

        achievement_key = ndb.Key(urlsafe=self.request.get('key'))
        achievement = achievement_key.get()

        current_key = ndb.Key(Cheever, self.user.email())
        current = current_key.get()

        if achievement_key in current.liked:
            current.liked.remove(achievement_key)
            achievement.numLiked -= 1
        else:
            current.liked.append(achievement_key)
            achievement.numLiked += 1

        @ndb.transactional(xg=True)
        def commit():
            achievement.put()
            current.put()

        commit()

        self.redirect('/')


class completeAchievement(_BaseHandler):

    def get(self):
        logging.info('completeAchievement requested')

        achievement_key = ndb.Key(urlsafe=self.request.get('key'))
        achievement = achievement_key.get()

        current_key = ndb.Key(Cheever, self.user.email())
        current = current_key.get()

        if achievement_key in current.cheeved:
            current.cheeved.remove(achievement_key)
            current.numScore -= achievement.score
            achievement.numCheeved -= 1
        else:
            current.cheeved.append(achievement_key)
            current.numScore += achievement.score
            achievement.numCheeved += 1

        @ndb.transactional(xg=True)
        def commit():
            achievement.put()
            current.put()

        commit()

        self.redirect('/')


class GenerateSystemStats(_BaseHandler):

    def get(self):
        logging.info('Generating SystemStats')

        achievements = Achievement.query().filter(Achievement.verified == True).fetch()
        cheevers = Cheever.query().fetch()
        contributors = Achievement.query(
            projection=[Achievement.contributor], distinct=True).fetch()

        maxScore = 0
        for a in achievements:
            maxScore += a.score

        systemStats = SystemStats(
            numUsers=cheevers.__len__(),
            numContributors=contributors.__len__(),
            numAchievements=achievements.__len__(),
            maxScore=maxScore,
            created=datetime.datetime.now()
        )

        systemStats.put()
        memcache.set('systemStats', systemStats)


class GenerateLeaderboardStats(_BaseHandler):

    def get(self):
        logging.info('Generate LeaderboardStats')

        cheevers = Cheever.query().order(-Cheever.numScore).fetch(10)
        for pos in range(0, cheevers.__len__()):
            leaderboardPos_key = ndb.Key('LeaderboardStats', str(pos) + 's')
            leaderboardPos = leaderboardPos_key.get()
            if not leaderboardPos:
                leaderboardPos = LeaderboardStats(key=leaderboardPos_key)

            leaderboardPos.populate(
                username=cheevers[pos].username,
                statType='score',
                value=cheevers[pos].numScore
            )
            leaderboardPos.put()

        cheevers = Cheever.query().order(-Cheever.numContribs).fetch(10)
        for pos in range(0, cheevers.__len__()):
            leaderboardPos_key = ndb.Key('LeaderboardStats', str(pos) + 'st')
            leaderboardPos = leaderboardPos_key.get()
            if not leaderboardPos:
                leaderboardPos = LeaderboardStats(key=leaderboardPos_key)

            leaderboardPos.populate(
                username=cheevers[pos].username,
                statType='contribution',
                value=cheevers[pos].numContribs
            )

            leaderboardPos.put()

        memcache.delete('contribStats')
        memcache.delete('scoreStats')


class AdminPage(_BaseHandler):

    def get(self):
        logging.info('AdminPage requested')

        achievements = Achievement.query().filter(
            Achievement.verified == False).fetch()

        self.template_values['achievements'] = achievements

        template = jinja.get_template('admin.html')
        self.response.out.write(template.render(self.template_values))

    def post(self):
        logging.info('AdminPage Posted')

        if self.request.get('action') == "accept":
            achievement = ndb.Key(urlsafe=self.request.get('key')).get()
            achievement.verified = True
            achievement.put()

            cheever = Cheever.query().filter(
                Cheever.username == achievement.contributor).get()
            import pdb; pdb.set_trace()
            for f in cheever.followers:
                follower = f.get()
                if follower:
                    logging.info('Adding Notify Task for ' +
                                 follower.username)
                    t = taskqueue.Task(
                        url='/notifyTask',
                        params={
                            'username': follower.username,
                            'email': follower.notifyEmail,
                            'title': achievement.title,
                            'description': achievement.description,
                            'category': achievement.category,
                            'score': achievement.score
                        }
                    )
                    t.add(queue_name='cheevedit-push-queue')


class NotifyTask(_BaseHandler):

    def post(self):
        logging.info('NotifyTask Posted')
        subject = 'Cheeved IT! - User {} created a new achievement!'.format(self.request.get('username'))
        body = 'Username: {} \n Achievement Title: {} \n Category: {} \n Description: {} \n Score: {} '. \
            format(self.request.get('username'),
                   self.request.get('title'),
                   self.request.get('category'),
                   self.request.get('description'),
                   self.request.get('score'))

        mail.send_mail(sender="CheevedIT! Admin <gcp@cbtnuggets.com>",
                       to='{} <{}>'.format(self.request.get('username'),
                                           self.request.get('email')),
                       subject=subject,
                       body=body)

        self.redirect('/')

app = webapp2.WSGIApplication([
    ('/achievements', AchievementsPage),
    ('/cheevers', CheeversPage),
    ('/followCheever', followCheever),
    ('/likeAchievement', likeAchievement),
    ('/completeAchievement', completeAchievement),
    ('/profile', ProfilePage),
    ('/newAchievement', NewAchievement),
    ('/calendar', CalendarPage),
    ('/admin', AdminPage),
    ('/generateSystemStats', GenerateSystemStats),
    ('/generateLeaderboardStats', GenerateLeaderboardStats),
    ('/notifyTask', NotifyTask),

    (calendarauthdecorator.callback_path, calendarauthdecorator.callback_handler()),
    ('/', HomePage),
], debug=True)
