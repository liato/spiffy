#!/usr/bin/env python
"""
head.py - self HTTP Metadata Utilities
Copyright 2008, Sean B. Palmer, inamidst.com
Licensed under the Eiffel Forum License 2.

http://inamidst.com/self/
"""

import re
import urllib
import urllib2
import httplib
import urlparse
import time

from utils import tounicode

from htmlentitydefs import name2codepoint

def head(self, input):
   "Fetches the headers of a web page"
   url = input.args
   
   if not url.strip() and hasattr(self, 'last_seen_url'): 
      try:
         url = self.last_seen_url[input.sender]
      except KeyError:
         self.reply("Failed spectacularly, try again later!")
         return
   elif not url.strip() and not hasattr(self, "last_seen_url"):
      self.reply("No URLs posted previously and none given, nothing I can do.")
      return
   
   if not "http://" in url:
      url = "http://" + url
      
   if hasattr(self, "last_seen_url"):
      self.last_seen_url[input.sender] = url
   
   headers = urllib2.urlopen(url).headers
   
   for key, val in headers.dict.iteritems():
      self.say("\x02%s\x02: %s" % (key.capitalize(), val))
   
head.rule = ['head']
head.usage = [("Fetch the headers of a web page", "$pcmd <URL>"),
   ("Fetch the headers of the last seen URL in the current channel", "$pcmd")]
head.example = [("Fetch the headers of Reddit's main page", "$pcmd www.reddit.com")]

r_title = re.compile(r'(?ims)<title[^>]*>(.*?)</title\s*>')
r_entity = re.compile(r'&[A-Za-z0-9#]+;')


def title(self, input):
   "Fetches the contents of the <title> tag of a web page"
   url = input.args
   
   if not url.strip() and hasattr(self, 'last_seen_url'): 
      try:
         url = self.last_seen_url[input.sender]
      except KeyError:
         self.reply("Failed spectacularly, try again later!")
         return
   elif not url.strip() and not hasattr(self, "last_seen_url"):
      self.reply("No URLs posted previously and none given, nothing I can do.")
      return
   
   if not "http://" in url:
      url = "http://" + url
      
   if hasattr(self, "last_seen_url"):
      self.last_seen_url[input.sender] = url
      
   page = tounicode(urllib2.urlopen(url).read())
   
   title = re.search('<title>(.*?)</title>', page, re.I).group(1)
   self.say("\x02Title:\x02 %s" % title)
   
title.rule = ["title"]
title.usage = [("Fetch the title a web page", "$pcmd <URL>"),
   ("Fetch the title of the last seen URL in the current channel", "$pcmd")]
title.example = [("Fetch the title of Reddit's main page", "$pcmd www.reddit.com")]

def noteurl(self, input):
   m = re.search(r"(http://[^ ]+)", input.args, re.I)
   if not m:
      return
      
   url = m.group(1).encode('utf-8')
   if not hasattr(self.bot, 'last_seen_url'): 
      self.bot.last_seen_url = {}
   self.bot.last_seen_url[input.sender] = url
   
noteurl.rule = r'.*'
