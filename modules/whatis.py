import re
import urllib2

qurl = "http://www.google.com/search?q=%s&hl=en"

def whatis(self, input):
    """Performs a "what is <argument>" query to Google and displays the result"""

    msg = lambda message: self.say(message)
    
    query = input.groups()[1].strip()

    showurl = False
    if "-u " in query:
        showurl = True
    query = "what is " + query.replace("-u ","")
    
    query = query.encode('utf-8')
    url = qurl % urllib.quote(query)
    
    if showurl:
        msg(chr(2) + "URL: " + chr(2) + url)

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor)
    headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.2) Gecko/2008091620 Firefox/3.0.2',
               'Connection':'Keep-Alive', 'Content-Type':'application/x-www-form-urlencoded'}
    
    page = opener.open(urllib2.Request(url,None,headers)).read()
    gsays = chr(2) + "Google says: " + chr(2)

    match = re.search(r"<td nowrap[^>]*><h2 class=r [^>]+><b>(.+?)</b>", page,re.IGNORECASE)
    print match
    if match:
        result = match.group(1).strip().replace("&quot;","\"")
        result = re.sub(r"<[^>]+?>","",result)
        msg(gsays+result)
        return
    del match
    
    match = re.search(r"Web definitions for <b>.+?<td valign=top>([^<]+)<br>", page)
    if match:
        msg(gsays+match.group(1).strip().replace("&quot;","\""))
        return
    del match
    
    match = re.search(r'alt="Clock"></td><td valign=[^>]+><b>([^<]+)</b>([^\-]+)- <b>',page)
    if match:
        time = match.group(1).strip()
        zone = match.group(2).strip()
        result = time + ", " + zone

        msg(gsays + result)
        return

    msg("Google knows not!")

whatis.rule = (["whatis", "w"], "(.+)")
whatis.usage = [("Use Google Calculator to convert between currencies", "$pcmd <amount> <currency> in <amount> <currency>"),
                ("Show the URL to the result page together with the result", "$pcmd -u <query>")]
whatis.example = [("Convert 100 USD to EUR", "$pcmd 100 usd in eur"),
                  ("Convert miles per hour to meters per second", "$pcmd 1 mph in meters per second")]
whatis.priority = 'high'

if __name__ == '__main__': 
   print __doc__.strip()
