import os,logging,email
import oauth,functions
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.api import urlfetch
from django.utils import simplejson as json
from appengine_utilities import sessions
from model import User,Post,Tweetc
from view import MainView

class MainHandler(webapp.RequestHandler):
  #Twitter Application Keys
  application_key = "" 
  application_secret = "" 

  def get(self, code = "", format = ""):
    
    # Set Up Twitter Client
    callback_url = "%s/verify" % self.request.host_url

    #Show Front Page
    if (code is None):
        try:
            self.session = sessions.Session()
            user = User.get_by_key_name(str(self.session["twitter_id"]))
            s = self.session
        except :
            user = None
            s = None
        values = {
          'user': user,
          'session': s,
        }
        path = os.path.join(os.path.dirname(__file__), 'templates/front.html')
        self.response.out.write(template.render(path, values))
        return
        
    if (code == 'login'):
        client = oauth.TwitterClient(MainHandler.application_key, MainHandler.application_secret, callback_url)
        return self.redirect(client.get_authorization_url())
        
    if (code == 'logout'):
        self.session = sessions.Session()
        self.session.delete()
        return self.redirect("/")
        
    if (code == "verify"):

        auth_token = self.request.get("oauth_token")
        auth_verifier = self.request.get("oauth_verifier")
        client = oauth.TwitterClient(MainHandler.application_key, MainHandler.application_secret, callback_url)
        user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)

        #Set Session
        self.session = sessions.Session()
        self.session["twitter_id"] = user_info['id']

        #Put or Update User
        User.create_or_update_user(user_info)

        #Redirect
        return self.redirect("/user/"+user_info['screen_name'])
        
    if (code == "settings"):
        try:
            self.session = sessions.Session()
            user = User.get_by_key_name(str(self.session["twitter_id"]))
            s = self.session
        except :
            user = None
            s = None
            
        if(user is None):
            self.redirect('/')
        notify = self.request.get('p')
        values = {
          'user': user,
          'session': s,
          'notify': notify
        }
        path = os.path.join(os.path.dirname(__file__), 'templates/settings.html')
        self.response.out.write(template.render(path, values))
        return
        
    if (code == 'user')  and (format is not None):
        user_passed_in = format.lower()
        user_passed_in = User.find_by_screen_name(str(user_passed_in))
        try:
            self.session = sessions.Session()
            user = User.get_by_key_name(str(self.session["twitter_id"]))
            s = self.session
            screen_name = user.screen_name
        except :
            user = None
            s =None
            screen_name = None
            
        try:
            timeline = Tweetc.all()
            timeline.filter("user =", user_passed_in.key())
            timeline.order('-created_on')
            timeline.fetch(10)
            notify = self.request.get('p')
            values = {
              'user_logged_in': user,
              'user': user_passed_in,
              'screen_name': screen_name,
              'timeline': timeline,
              'session': s,
              'notify': notify
            }
            path = os.path.join(os.path.dirname(__file__), 'templates/user.html')
            self.response.out.write(template.render(path, values))
            return
        except:
            values = {
              'msg':'Oops - looks like something went wrong... we\'ll have it fixed soon.'
            }
            logging.info(code)
            logging.info(format)
            path = os.path.join(os.path.dirname(__file__), 'templates/error.html')
            self.response.out.write(template.render(path, values))
    else:
        t = Tweetc.find_by_code(str(code))
        self.session = sessions.Session()
        try:
            tweet = functions.word_wrap(t.post.content,110,prefix ="||")
            tweet = tweet.split("||")
            title = tweet[1]
        except:
            t = None
        if t is not None:
            values = {
              'user': t.user,
              'session': self.session,
              'post': functions.linkify(t.post.content),
              'dt': t.created_on,
              'title':title
            }
            path = os.path.join(os.path.dirname(__file__), 'templates/post.html')
            self.response.out.write(template.render(path, values))
        else:
            values = {
              'msg':'Oops - we couldn\'t find that Tweetc'
            }
            logging.info(code)
            logging.info(format)
            path = os.path.join(os.path.dirname(__file__), 'templates/error.html')
            self.response.out.write(template.render(path, values))
            
  def post(self, action):
    #Start Session 
    self.session = sessions.Session()
    if (action == "settings"):
        key =self.request.get('email_key')
        if(len(key) is 0):
            return self.redirect('/settings' )

        user_info = {}
        user_info['id'] = str(self.session["twitter_id"])
        user_info['email_key'] = key
        User.update_settings(user_info)
        return self.redirect('/settings' + '?p=1' )
        
    if (action == "post"):
        # Set Up Twitter Client
        callback_url = "%s/verify" % self.request.host_url
        client = oauth.TwitterClient(MainHandler.application_key, MainHandler.application_secret, callback_url)
        #Get Post
        content = self.request.get('content')
        contet = functions.strip_tags(content)
        #Save Post
        post_info = {}
        post_info['content'] = content
        post_key = Post.save_post(post_info)
    
        #Save Tweetc
        user = User.get_by_key_name(str(self.session["twitter_id"]))
        tweetc_info = {}
        tweetc_info['tweet_id'] = None
        tweetc_info['tweet'] = None
        tweetc_info['user'] = user.key()
        tweetc_info['post'] = post_key
        tweetc_info['client'] = 'web'
        tweetc_key = Tweetc.save_tweetc(tweetc_info)

        #Send Tweet
        tweetc = Tweetc.get(tweetc_key)
        tweet = functions.word_wrap(content,108,prefix ="||")
        tweet = tweet.split("||")
 
        tweetc_code = tweetc.code()
        del tweet[0]
        if len(tweet) == 1:
            i = 1
        elif len(tweet) == 2:
            i = 2
        else:
            i = 3
        count = 0
        tweet_list = []
        while (count < i):
           last = i - 1
           if count == last:
               tweetout = tweet[count] + ' ' + str(count + 1) + '/' + str(i)
               if len(tweet) > 3:
                   tweetout += '...'
               tweetout += ' http://tweetc.com/' + tweetc_code
           else:
               tweetout = tweet[count] + ' ' + str(count + 1) + '/' + str(i)
           self.response.out.write(tweetout)
           tweet_list.append(tweetout)
           count = count + 1
        first_tweet = tweet_list[0] + ' http://tweetc.com/' + tweetc_code
        tweet_list.reverse()
        count = 0
        while (count < i):
           self.response.out.write(tweet_list[count] + '<br>')
           additional_params={"status":tweet_list[count]}
           url = "http://twitter.com/statuses/update.json"
           result = client.make_request(url=url, token=user.token,secret=user.secret, additional_params=additional_params, method=urlfetch.POST)
           rsp = json.loads(result.content)
           if count == 0:
               status_id = rsp['id']
           count = count + 1

    
        #Update Tweetc with Tweet ID
        tweetc = Tweetc.get(tweetc_key)
        tweetc.tweet_id = status_id
        tweetc.tweet = first_tweet
        tweetc.put()
        
        return self.redirect('/user/' + user.screen_name + '?p=1' )

class PageHandler(webapp.RequestHandler):
  def get(self,page):
    try:
        self.session = sessions.Session()
        user = User.get_by_key_name(str(self.session["twitter_id"]))
        s = self.session
    except :
        user = None
        s = None
        
    values = {
      'user': user,
      'session': s,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/' + page + '.html')
    self.response.out.write(template.render(path, values))
    return

class IncomingEmailHandler(InboundMailHandler):
    
    def receive(self, mail_message):
        try:
            email = mail_message.to.split('@')
        except:
            email = None
        email_prefix = email[0].split('.')
        screen_name_temp = email_prefix[0].split('<')
        try:
            screen_name = screen_name_temp[1]
        except:
            screen_name = screen_name_temp[0]
            
        email_key = email_prefix[1]
        email_user = User.find_by_screen_name(screen_name.lower());
        try:
            if(email_key == email_user.email_key):
                # Set Up Twitter Client
                callback_url = "%s/verify" % self.request.host_url
                client = oauth.TwitterClient(MainHandler.application_key, MainHandler.application_secret, callback_url)
                #Get Post
                plaintext_bodies = mail_message.bodies('text/plain')
                for content_type, body in plaintext_bodies:
                        decoded_text = body.decode()
                        content = decoded_text
            
                try:
                    subject = mail_message.subject + "\n\r"
                except:
                    subject = ''

                if content is not None:
                    body = functions.strip_tags(content)
                else:
                    body = ''

                #Save Post
                post_info = {}
                post_info['content'] = subject + body
                post_key = Post.save_post(post_info)

                #Save Tweetc
                user = User.get_by_key_name(str(email_user.twitter_id))
                tweetc_info = {}
                tweetc_info['tweet_id'] = None
                tweetc_info['tweet'] = None
                tweetc_info['user'] = user.key()
                tweetc_info['post'] = post_key
                tweetc_info['client'] = 'email'
                tweetc_key = Tweetc.save_tweetc(tweetc_info)

                #Send Tweet
                tweetc = Tweetc.get(tweetc_key)
                tweet = functions.word_wrap(content,108,prefix ="||")
                tweet = tweet.split("||")
                
                
                tweetc_code = tweetc.code()
                del tweet[0]
                if len(tweet) == 1:
                    i = 1
                elif len(tweet) == 2:
                    i = 2
                else:
                    i = 3
                count = 0
                tweet_list = []
                while (count < i):
                   last = i - 1
                   if count == last:
                       tweetout = tweet[count] + ' ' + str(count + 1) + '/' + str(i)
                       if len(tweet) > 3:
                           tweetout += '...'
                       tweetout += ' http://tweetc.com/' + tweetc_code
                   else:
                       tweetout = tweet[count] + ' ' + str(count + 1) + '/' + str(i)
                   self.response.out.write(tweetout)
                   tweet_list.append(tweetout)
                   count = count + 1
                first_tweet = tweet_list[0] + ' http://tweetc.com/' + tweetc_code
                tweet_list.reverse()
                count = 0
                while (count < i):
                   self.response.out.write(tweet_list[count] + '<br>')
                   additional_params={"status":tweet_list[count]}
                   url = "http://twitter.com/statuses/update.json"
                   result = client.make_request(url=url, token=user.token,secret=user.secret, additional_params=additional_params, method=urlfetch.POST)
                   rsp = json.loads(result.content)
                   if count == 0:
                       status_id = rsp['id']
                   count = count + 1

                #Update Tweetc with Tweet ID
                tweetc = Tweetc.get(tweetc_key)
                tweetc.tweet_id = status_id
                tweetc.tweet = first_tweet
                tweetc.put()
        except:
            logging.info(screen_name)
            logging.info(email_key)
            logging.info("Sending Email Error")
            
DEBUG = os.environ['SERVER_SOFTWARE'].startswith('Dev')
        
application = webapp.WSGIApplication([#('/api/post', ApiHandler),
                                      ('/(api|terms|privacy)', PageHandler),
                                      ('/(post)', MainHandler),
                                      ('/(settings)', MainHandler),
                                      ('/(user)/([a-zA-Z0-9]+)', MainHandler),
                                      ('/([a-zA-Z0-9]{1,6})?(.xml|.json|.html)?', MainHandler),
                                      IncomingEmailHandler.mapping(),
									 ],
                                     debug=DEBUG
                                     )

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()