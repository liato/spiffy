import re
import urllib
import urllib2

from utils import decodehtml, removehtml
qurl = "http://www.google.com/search?q=%s&hl=en"

def whatis(self, input):
    """Performs a "what is <argument>" query to Google and displays the result"""

    if not input.args:
        raise self.BadInputError()

    query = input.args.strip()

    showurl = False
    if query.startswith("-u "):
        showurl = True
        query = query[3:]
    query = "what is " + query
    
    query = query.encode('utf-8')
    url = qurl % urllib.quote(query)
    
    if showurl:
        self.say(chr(2) + "URL: " + chr(2) + url)

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.2) Gecko/2008091620 Firefox/3.0.2',
               'Connection':'Keep-Alive', 'Content-Type':'application/x-www-form-urlencoded'}
    
    page = opener.open(urllib2.Request(url,None,headers)).read()
    
    regexes = [r"<h[23]\sclass=r[^>]*><b>(.+?)</b></h[23]>",
             r"onebox/[^>]*>(.*?)<(?:/table|br)"]
    
    for regex in regexes:
        match = re.search(regex, page,re.IGNORECASE)
        if match:
            self.say(decodehtml(removehtml(match.group(1).strip())))
            return

    self.say("Dunno :S")

whatis.rule = ["whatis", "w"]
whatis.usage = [("Use Google Calculator to convert between currencies", "$pcmd <amount> <currency> in <amount> <currency>"),
                ("Show the URL to the result page together with the result", "$pcmd -u <query>")]
whatis.example = [("Convert 100 USD to EUR", "$pcmd 100 usd in eur"),
                  ("Convert miles per hour to meters per second", "$pcmd 1 mph in meters per second")]
