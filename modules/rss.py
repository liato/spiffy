# -*- coding: utf-8 -*-
from optparse import OptionParser
import datetime
import hashlib
import os
import pickle
import re
import threading
import urllib2
import feedparser

class RSS:
    def __init__(self, url=None, added_by=None, chan=None):
        self.url = url
        self.added_by = added_by
        self.added_on = datetime.datetime.utcnow()
        self.chan = chan
        self.nomatchwarned = False
        self.lastvalue = None

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
        if self.lastvalue:
            for entry in entries:
                if hashlib.sha224(str(entry)).hexdigest() == self.lastvalue:
                    break
                newentries.append(entry)

        self.lastvalue = hashlib.sha224(str(entries[0])).hexdigest()
        return newentries


def setup(self): 
    self.rss_filename = os.path.join("data", 'rss.db')
    self.rss_db = None
    if os.path.exists(self.rss_filename):
        f = open(self.rss_filename, 'rb')
        try:
            fc = f.read()
            self.rss_db = pickle.loads(fc)
        except EOFError:
            pass
        f.close()
    if not self.rss_db:
        self.rss_db = []

    t = threading.Timer(300, checksites, args=(self, None))
    t.start()
   
    
def savedb(fn, data):
    if data:
        try:
            f = open(fn, "wb")
            pickle.dump(data, f, 2)
            f.close()
            return True
        except:
            return False
    return False

def rh(s):
    #remove html and other crap
    #s = htmldecode(s)
    s = re.sub("<[^>]+>","",s)
    s = re.sub(" +"," ",s)
    return s

def checksites(self, pattern=None):
    for site in self.rss_db:
        if (pattern or "") in site.url:
            try:
                res = site.check()
                if res:
                    res.reverse()
                    for entry in res:
                        self.sendLine("PRIVMSG " + site.chan + " :[RSS] \x02%s\x02 - \x1f%s" % (entry.get('title', ''), entry.get('link', '')))
                        msg = entry.get('description', '')
                        msg = re.sub("<br\s?/?>", "\n", msg)
                        msg = rh(msg).split("\n")
                        for line in msg:
                            self.sendLine("PRIVMSG %s :%s" % (site.chan, line))
                        
            except Exception, e:
                self.sendLine("PRIVMSG " + site.chan + " :\x02RSS:\x02 Error while checking %s. (%s)!" % (site.url, e))
            
    savedb(self.rss_filename, self.rss_db)
    if not pattern:
        t = threading.Timer(900, checksites, args=(self,None))
        t.start()
    

def rss(self, input):
    """Checks RSS feeds periodically and notifies the channel when a new post is added."""
    
    if not input.sender.startswith('#'): return
    cmd = input.group(2) or ""

    parser = OptionParserMod() # defined at the end of the file
    parser.add_option("-r", "--remove", dest="remove")
    parser.add_option("-c", "--check", dest="check")
    parser.add_option("-l", "--list", dest="list", action="store_true")
    parser.add_option("-d", "--display", dest="display")

    try:
        options, args = parser.parse_args(cmd.split())
    except ValueError:
        raise self.BadInputError()
        return

    if options.remove:
        for site in self.rss_db:
            if options.remove in site.url:
                self.say("Removing: %s" % site.url)
                self.rss_db.remove(site)
        savedb(self.rss_filename, self.rss_db)
        
    elif options.display:
        for site in self.rss_db:
            if m.group("display_this") in site.url:
                if not site.diff:
                    self.say("No diff!")
                else:
                    self.say("\x02Diff:")
                    for line in site.diff.split("\n")[3:]:
                        if line.startswith("-"):
                            prefix = "\x034"
                        elif line.startswith("+"):
                            prefix = "\x033"
                        else:
                            prefix = ""
                        self.say(prefix+line)
                break

    elif options.check:
        checksites(self, options.check)

    elif options.list:
        for site in self.rss_db:
            if ("".join(args) or "") in site.url:
                self.say("Added by \x02%s\x02 on \x02%s\x02:" % (site.added_by, site.added_on))
                self.say(  "\x02Url:  \x02 %s" % site.url)

        if not self.rss_db:
            self.say("No feeds added yet!")

    elif args:
        url = " ".join(args)
        try:
            site = RSS(url, input.nick, input.sender)
        except Exception, e:
            self.say("Error: %s" % e)
            return
        
        try:
            if site.check() == None:
                self.say("\x02Error:\x02 Unable to parse the feed at %s." % m.group("url"))
                return
        except Exception, e:
            self.say("Error: %s" % e)
            return

        self.rss_db.append(site)
        savedb(self.rss_filename, self.rss_db)
        self.say("Added!")


rss.rule = (["rss"], r"(.*)")
rss.usage = [("Add a new feed","$pcmd <url>"),
             ("Remove feeds whose URLs contain pattern", "$pcmd -r <pattern"),
             ("Check feeds whose URLs contain patter", "$pcmd -c <pattern>"),
             ("List all feeds", "$pcmd -l"),
             ("List all feeds whose URLs contain pattern", "$pcmd -l <pattern>")]
rss.example = [("Check all added Reddit feeds, if any exist", "$pcmd -c reddit")]
rss.thread = True

class OptionParserMod(OptionParser):
    
    # This method allows us to handle the error in our own way, in this
    # case to aid us in determining when faulty input was provided and
    # showing usage information to the user.
    def error(self, description):
        raise ValueError, description


