from google.appengine.ext import ndb
import datetime

class Cheever(ndb.Model):
    username = ndb.StringProperty(default="Choose a Username")
    bio = ndb.TextProperty(default="Enter your bio here")
    notifyEmail = ndb.StringProperty(default="me@email.com")
    followers = ndb.KeyProperty(repeated=True)
    following = ndb.KeyProperty(repeated=True)
    liked = ndb.KeyProperty(repeated=True)
    cheeved = ndb.KeyProperty(repeated=True)
    numScore = ndb.IntegerProperty(default=0)
    numFollowers = ndb.IntegerProperty(default=0)
    numFollowing = ndb.IntegerProperty(default=0)
    numContribs = ndb.IntegerProperty(default=0)
    created = ndb.DateTimeProperty(default=datetime.datetime.now())


class Achievement(ndb.Model):
    title = ndb.StringProperty()
    category = ndb.StringProperty()
    description = ndb.TextProperty()
    score = ndb.IntegerProperty()
    contributor = ndb.StringProperty()
    numLiked = ndb.IntegerProperty(default=0)
    numCheeved = ndb.IntegerProperty(default=0)
    created = ndb.DateTimeProperty(default=datetime.datetime.now())
    verified = ndb.BooleanProperty(default=False)


class LeaderboardStats(ndb.Model):
    username = ndb.StringProperty()
    statType = ndb.StringProperty('type')
    value = ndb.IntegerProperty(default=0)


class SystemStats(ndb.Model):
    numUsers = ndb.IntegerProperty(default=0)
    numContributors = ndb.IntegerProperty(default=0)
    numAchievements = ndb.IntegerProperty(default=0)
    maxScore = ndb.IntegerProperty(default=0)
    created = ndb.DateTimeProperty(default=datetime.datetime.now())
