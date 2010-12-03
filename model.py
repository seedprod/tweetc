import logging
import functions
from google.appengine.ext import db
from google.appengine.api import memcache

class User(db.Model):
  twitter_id = db.IntegerProperty()
  name = db.StringProperty()
  screen_name = db.StringProperty()
  location = db.StringProperty()
  description = db.StringProperty()
  profile_image_url = db.StringProperty()
  url = db.StringProperty()
  token = db.StringProperty()
  secret = db.StringProperty()
  followers_count = db.IntegerProperty()
  friends_count = db.IntegerProperty()
  utc_offset = db.IntegerProperty()
  banned = db.BooleanProperty(default=False)
  last_modified = db.DateTimeProperty(auto_now=True)
  created_on = db.DateTimeProperty(auto_now_add=True)
  email_key = db.StringProperty(default=functions.randomkey(),required=True)
  
  @staticmethod
  def create_or_update_user(user_info):
      user =  User.get_or_insert(key_name = str(user_info['id']))
      user.twitter_id = user_info['id']
      user.name = user_info['name']
      user.screen_name = user_info['screen_name'].lower()
      user.location = user_info['location']
      user.description = user_info['description']
      user.profile_image_url = user_info['profile_image_url']
      user.url = user_info['url']
      user.token = user_info['token']
      user.secret = user_info['secret']
      user.followers_count  = user_info['followers_count']
      user.friends_count = user_info['friends_count']
      user.utc_offset = user_info['utc_offset']
      user.put()

  @staticmethod
  def update_settings(user_info):
      user =  User.get_by_key_name(str(user_info['id']))
      user.email_key= user_info['email_key']
      user.put()
      
  @staticmethod
  def find_by_screen_name(screen_name):
      q = db.Query(User).filter('screen_name =', screen_name)
      user = q.get()
      return user

class Post(db.Model):
  content = db.TextProperty()
  last_modified = db.DateTimeProperty(auto_now=True)
  created_on = db.DateTimeProperty(auto_now_add=True)
  
  @staticmethod
  def save_post(post_info):
      post = Post()
      post.content =  post_info['content']
      return post.put()
  
class Tweetc(db.Model):
  tweet_id = db.IntegerProperty()
  tweet = db.StringProperty(multiline=True)
  client = db.StringProperty()
  post = db.ReferenceProperty(Post, collection_name='post_tweetc')
  user = db.ReferenceProperty(User, collection_name='user_tweetc')
  created_on = db.DateTimeProperty(auto_now_add=True)
  
  KEY_BASE = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
  BASE = 62
  
  def code(self):
      """Return our code, our base-62 encoded id"""
      if not self.is_saved():
          return None
      nid = self.key().id()
      s = []
      while nid:
          nid, c = divmod(nid, Tweetc.BASE)
          s.append(Tweetc.KEY_BASE[c])
      s.reverse()
      return "".join(s)
      
  def save_in_cache(self):
      """We don't really care if this fails"""
      memcache.set(self.code(), self)
      
  @staticmethod
  def save_tweetc(tweetc_info):
      tweetc = Tweetc()
      tweetc.tweet_id =  tweetc_info['tweet_id']
      tweetc.tweet =  tweetc_info['tweet']
      tweetc.user =  tweetc_info['user']
      tweetc.post =  tweetc_info['post']
      tweetc.client =  tweetc_info['client']
      return tweetc.put()

  @staticmethod
  def code_to_id(code):
      aid = 0L
      for c in code:
          aid *= Tweetc.BASE 
          aid += Tweetc.KEY_BASE.index(c)
      return aid

  @staticmethod
  def find_by_code(code):
      try:
          t = memcache.get(code)
      except:
          # http://code.google.com/p/googleappengine/issues/detail?id=417
          logging.error("Tweetc.find_by_code() memcached error")
          t = None

      if t is not None:
          logging.info("Tweetc.find_by_code() cache HIT: %s", str(code))
          return t        

      logging.info("Tweetc.find_by_code() cache MISS: %s", str(code))
      aid = Tweetc.code_to_id(code)
      try:
          t = Tweetc.get_by_id(int(aid))
          if t is not None:
              t.save_in_cache()
          return t
      except db.BadValueError:
          return None


