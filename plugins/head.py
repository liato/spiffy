import re
import urllib2

from utils import tounicode, decodehtml

def head(self, input):
    """Fetches the headers of a web page"""
    url = input.args.strip()
    
    if not url: 
        try:
            url = self.lasturl[input.sender.lower()]
        except KeyError:
            self.reply("No URLs posted previously and none given, nothing I can do.")
            return
    
    m = re.search(r"^https?://", url, re.I)
    if not m:
        url = "http://" + url
       
    self.lasturl[input.sender.lower()] = url
    
    try:
        headers = urllib2.urlopen(url).headers
    except urllib2.URLError:
        self.say("Error: Invalid url.")
        return
    
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
    url = input.args.strip()
    
    if not url: 
        try:
            url = self.lasturl[input.sender.lower()]
        except KeyError:
            self.reply("No URLs posted previously and none given, nothing I can do.")
            return
    
    m = re.search(r"^https?://", url, re.I)
    if not m:
        url = "http://" + url
       
    self.lasturl[input.sender.lower()] = url       

       
    try:
        page = tounicode(urllib2.urlopen(url).read())
        title = re.search('<title>(.*?)</title>', page, re.I | re.MULTILINE | re.DOTALL)
        if not title:
            self.say("Page has no title tag!")
            return
        self.say("\x02Title:\x02 %s" % decodehtml(title.group(1).replace("\n","")))
    except urllib2.URLError, e:
        self.say('Error: Invalid url.')
        
title.rule = ["title"]
title.usage = [("Fetch the title of a web page", "$pcmd <URL>"),
   ("Fetch the title of the last seen URL in the current channel", "$pcmd")]
title.example = [("Fetch the title of Reddit's main page", "$pcmd www.reddit.com")]

def noteurl(self, input):
    m = re.search(r"(https?://[^ ]+|www\.[^ ]+)", input.args, re.I)
    if not m:
       return
       
    input.sender = input.sender.lower()
    url = m.group(1).encode('utf-8')
    if not input.sender in self.bot.urls:
       self.bot.urls[input.sender] = {}
    
    if url in self.bot.urls[input.sender] and not (input.nick == self.bot.urls[input.sender][url][1]):
        self.say("OLD!")
        self.say("[%s] <%s> %s" % (self.bot.urls[input.sender][url][0].strftime("%y%m%d %H:%M:%S"), self.bot.urls[input.sender][url][1], self.bot.urls[input.sender][url][2]))
    else:
        self.bot.urls[input.sender][url] = (self.localtime(), input.nick, input.args)
    self.bot.lasturl[input.sender] = url   
noteurl.rule = r'.*'


def setup(self, input):
    self.bot.urls = {}
    self.bot.lasturl = {}
    
noteurl.setup = setup
