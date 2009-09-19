import re
import urllib2

from utils import tounicode

def head(self, input):
   """Fetches the headers of a web page"""
   url = input.args
   
   if not url.strip() and hasattr(self, 'last_seen_url'): 
      try:
         url = self.last_seen_url[input.sender]
      except KeyError:
         self.reply("No URLs posted previously and none given, nothing I can do.")
         return
   elif not url.strip() and not hasattr(self, "last_seen_url"):
      self.reply("No URLs posted previously and none given, nothing I can do.")
      return
   
   if not "http://" in url:
      url = "http://" + url
      
   if hasattr(self, "last_seen_url"):
      self.last_seen_url[input.sender] = url
   
   headers = urllib2.urlopen(url).headers
   
   if not headers:
      self.say("Could not fetch page headers, perhaps the site is down?")
      return
   
   for key, val in headers.dict.iteritems():
      self.say("\x02%s\x02: %s" % (key.capitalize(), val))
   
head.rule = ['head']
head.usage = [("Fetch the headers of a web page", "$pcmd <URL>"),
   ("Fetch the headers of the last seen URL in the current channel", "$pcmd")]
head.example = [("Fetch the headers of Reddit's main page", "$pcmd www.reddit.com")]

def title(self, input):
   """Fetches the contents of the <title> tag of a web page"""
   url = input.args
   
   if not url.strip() and hasattr(self, 'last_seen_url'): 
      try:
         url = self.last_seen_url[input.sender]
      except KeyError:
         self.reply("No URLs posted previously and none given, nothing I can do.")
         return
   elif not url.strip() and not hasattr(self, "last_seen_url"):
      self.reply("No URLs posted previously and none given, nothing I can do.")
      return
   
   if not "http://" in url:
      url = "http://" + url
      
   if hasattr(self, "last_seen_url"):
      self.last_seen_url[input.sender] = url
      
   page = tounicode(urllib2.urlopen(url).read())
   
   title = re.search('<title>(.*?)</title>', page, re.I | re.MULTILINE | re.DOTALL)
   
   if not title:
      self.say("Page has no title tag!")
      return
   self.say("\x02Title:\x02 %s" % title.group(1).replace("\n",""))
   
title.rule = ["title"]
title.usage = [("Fetch the title a web page", "$pcmd <URL>"),
   ("Fetch the title of the last seen URL in the current channel", "$pcmd")]
title.example = [("Fetch the title of Reddit's main page", "$pcmd www.reddit.com")]

def noteurl(self, input):
   m = re.search(r"(http://[^ ]+|www\.[^ ]+)", input.args, re.I)
   if not m:
      return
      
   url = m.group(1).encode('utf-8')
   if not hasattr(self.bot, 'last_seen_url'): 
      self.bot.last_seen_url = {}
   self.bot.last_seen_url[input.sender] = url
   
noteurl.rule = r'.*'
