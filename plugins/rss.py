import datetime
import hashlib
import os
import pickle
import re
import threading
import urllib2

from utils import decodehtml, removehtml

import feedparser
from twisted.internet import reactor


class RSS:
    def __init__(self, url=None, added_by=None, chan=None, limit=0):
        self.url = url
        self.added_by = added_by
        self.added_on = datetime.datetime.utcnow()
        self.chan = chan
        self.limit = limit
        self.visited = []

    def check(self):
        data = None
        try:
            data = feedparser.parse(self.url)
        except Exception, e:
            return None

        if not data:
            return None
        
        entries = data['entries']
        if not entries:
            return None
        
        newentries = []
        if len(self.visited) == 0:
            for entry in entries:
                guid = entry.get('guid') or entry.get('link')
                self.visited.append(guid)    
        else:
            for entry in entries:
                guid = entry.get('guid') or entry.get('link')
                if not guid in self.visited:
                    if len(self.visited) >= 150:
                        self.visited.pop(0)
                    self.visited.append(guid)    
                    newentries.append(entry)

        return newentries

    def getentries(self, num):
        "Get the num last entries"
        
        data = None
        try:
            data = feedparser.parse(self.url)
        except Exception, e:
            return None

        if not data:
            return None
        
        entries = data['entries']
        if not entries:
            return None

        return entries[:num]


def setup(self, input):
    if not 'sites' in self.storage:
        self.storage['sites'] = []
        self.storage.save()
    if hasattr(self, 'rsscheck_thread'):
        try:
            self.rsscheck_thread.cancel()
            del self.rsscheck_thread
        except (RuntimeError, AttributeError):
            pass
    
    self.rsscheck_thread = threading.Timer(60, checksites, args=(self,))
    self.rsscheck_thread.start()

def checksites(self, pattern=None):
    for site in self.storage['sites']:
        if (pattern or "") in site.url:
            try:
                if pattern:
                    reactor.callFromThread(self.msg, site.chan, "Checking %s..." % site.url)
                res = site.check()
                if res:
                    if pattern:
                        reactor.callFromThread(self.msg, site.chan, "Found %d new entries:" % len(res))
                    res.reverse()
                    for entry in res:
                        reactor.callFromThread(self.msg, site.chan, "[RSS] \x02%s\x02 - \x1f%s" % (decodehtml(entry.get('title', '')), entry.get('link', '')))
                        msg = entry.get('description', '')
                        msg = re.sub("<br\s?/?>", "\n", msg)
                        msg = decodehtml(removehtml(msg))
                        if site.limit:
                            msg = "\n".join(msg.split("\n")[:site.limit])
                        reactor.callFromThread(self.msg, site.chan, msg)
                else:
                    if pattern:
                        reactor.callFromThread(self.msg, site.chan, "No new entries found.")
                        
            except Exception, e:
                reactor.callFromThread(self.msg, site.chan, "\x02RSS:\x02 Error while checking %s. (%s)!" % (site.url, e))
    
    self.storage.save()
    if not pattern:
        try:
            self.rsscheck_thread.cancel()
            del self.rsscheck_thread
        except (RuntimeError, AttributeError):
            pass

        self.rsscheck_thread = threading.Timer(300, checksites, args=(self,))
        self.rsscheck_thread.start()
    

def rss(self, input):
    """Checks RSS feeds periodically and notifies the channel when a new post is added."""
    
    if not input.sender.startswith('#'): return
    cmd = input.args or ""

    parser = self.OptionParser()
    parser.add_option("-r", "--remove", dest="remove")
    parser.add_option("-c", "--check", dest="check")
    parser.add_option("-l", "--list", dest="list", action="store_true")
    parser.add_option("-d", "--display", dest="display", type="int")
    parser.add_option("-n", "--limit", dest="limit", type="int", default=0)

    options, args = parser.parse_args(cmd.split())

    if options.remove:
        for site in self.storage['sites']:
            if options.remove in site.url:
                self.say("Removing: %s" % site.url)
                self.storage['sites'].remove(site)
        self.storage.save()
        
    elif options.display:
        if not args:
            self.say("\x02Error:\x02 A pattern must be provided when using switch -d")
            return
        
        for site in self.storage['sites']:
            if "".join(args) in site.url:
                entries = site.getentries(options.display)

                for entry in entries:
                    self.say("[RSS] \x02%s\x02 - \x1f%s" % (entry.get('title', ''), entry.get('link', '')))
                    msg = entry.get('description', '')
                    msg = re.sub("<br\s?/?>", "\n", msg)
                    msg = removehtml(msg).split("\n")[:3] # print max 3 lines of description
                    self.say("\n".join(msg))

    elif options.check:
        checksites(self, options.check)

    elif options.list:
        for site in self.storage['sites']:
            if ("".join(args) or "") in site.url:
                self.say("Added by \x02%s\x02 on \x02%s\x02:" % (site.added_by, site.added_on))
                self.say(  "\x02Url:  \x02 %s" % site.url)
                if site.limit:
                    self.say("Limited to max %d lines" % site.limit)

        if not self.storage['sites']:
            self.say("No feeds added yet!")

    elif args:
        url = " ".join(args)

        for site in self.storage['sites']:
            if url == site.url:
                self.say("Feed already exists, try using the -l switch to check for it.")
                return
            
        try:
            site = RSS(url, input.nick, input.sender, options.limit)
        except Exception, e:
            self.say("Error: %s" % e)
            return
        
        try:
            if site.check() == None:
                self.say("\x02Error:\x02 Unable to parse the feed at %s." % url)
                return
        except Exception, e:
            self.say("Error: %s" % e)
            return

        self.storage['sites'].append(site)
        self.storage.save()
        self.say("Added!")


rss.rule = ["rss"]
rss.setup = setup
rss.usage = [("Add a new feed","$pcmd <url>"),
             ("Add a new feed, print max 3 lines per item","$pcmd -n 3 <url>"),
             ("Remove feeds whose URLs contain pattern", "$pcmd -r <pattern"),
             ("Check feeds whose URLs contain patter", "$pcmd -c <pattern>"),
             ("List all feeds", "$pcmd -l"),
             ("List all feeds whose URLs contain pattern", "$pcmd -l <pattern>"),
             ("Check the last num entries from a particular feed", "$pcmd -d<num> <pattern>")]
rss.example = [("Check all added Reddit feeds, if any exist", "$pcmd -c reddit"),
               ("View the last 3 entries from Reddit", "$pcmd -d3 reddit")]


