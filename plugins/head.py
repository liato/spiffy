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


def atsetup(self, input):
    if not hasattr(self.bot, "pluginstorage_at"):
        self.bot.pluginstorage_at = Storage("data/%s.%s.db" % (self.bot.config['network'], "at"))

def at(self, input):

    if not "autotitle" in self.storage:
        self.storage["autotitle"] = []
    
    cmd = input.args or ""
    
    parser = self.OptionParser()
    parser.add_option("-a", "--add", dest="add")
    parser.add_option("-r", "--remove", dest="remove")
    parser.add_option("-l", "--list", dest="list", action="store_true")

    options, args = parser.parse_args(cmd.split())

    if options.add:
        if not options.add in self.storage["autotitle"]:
            self.say("Added '%s'" % options.add)
            self.storage["autotitle"].append(options.add)
            self.storage.save()
            
    elif options.remove:
        l = [p for p in self.storage["autotitle"] if re.search(options.remove, p, re.I)]

        for p in l:
            self.say("Removing '%s'" % p)
            self.storage["autotitle"].remove(p)
        self.storage.save()
            
    elif options.list:
        if not self.storage["autotitle"]:
            self.say("No patterns added yet")
            return
        
        if not args: # print all patterns
            self.say("\x02Autotitle patterns:\x02 ")
            for i,p in enumerate(self.storage["autotitle"]):
                self.say("%d. %s" % (i+1,p))
        else:
            arg = args[0]
            self.say("\x02Autotitle patterns matching '%s':\x02" % arg)

            matches = [p for p in self.storage["autotitle"] if re.search(arg, p, re.I)]
            
            for i,p in enumerate(matches):
                self.say("%d. %s" % (i+1,p))
    else:
        self.say(self.bot.doc["at"][1])

at.rule = ["at"]
at.usage = [("Add a new pattern","$pcmd -a <pattern>"),
            ("List all patterns","$pcmd -l"),
            ("List only certain patterns","$pcmd -l <pattern>"),
            ("Remove a pattern","$pcmd -r <pattern>")]
at.example = [("Add a pattern for 'reddit'", "$pcmd -a reddit")]
at.setup = atsetup


def autotitle(self, input):
    """Automatically shows the title for specified sites"""

    if hasattr(self.bot,"pluginstorage_at"):
        self.storage = self.bot.pluginstorage_at
    else:
        self.say("Patterns not loaded, hopefully this should never happen")

    matches = re.findall(r"(https?://[^ ]+|www\.[^ ]+)", input.args, re.I)
    if not matches:
       return

    for m in matches:
        url = m.encode('utf-8')
        if not url.startswith("http"):
            url = "http://" + url

        for p in self.storage["autotitle"]:
            if re.search(p, url, re.I):
                try:
                    page = tounicode(urllib2.urlopen(url).read())
                    title = re.search('<title>(.*?)</title>', page, re.I | re.MULTILINE | re.DOTALL)
                    if not title:
                        self.say("Page has no title tag!")
                        return
                    title = decodehtml(title.group(1).replace("\n","")).strip()
                    title = re.sub(r"\s+", " ", title)
                    self.say("\x02Title:\x02 %s" % title)
                except urllib2.URLError, e:
                    self.say('Error: Invalid url.')

autotitle.rule = r".*"




