# -*- coding: latin-1 -*-
import datetime
import re
import time
import urllib
import urllib2

from utils import decodehtml


def sl(self, input):
    """Queries sl.se for train/bus times"""
    
    cmd = input.args
    
    m = re.search(r'(?P<later>sen|tidig)(?:are)?|(?P<start>[^,]+),\s*(?P<stop>[^,]+)(?:,\s*?(?:(?P<date>\d{4}-\d{2}-\d{2} [012]?[0-9][.:]?[0-5][0-9])|(?P<time>[01-2]?[0-9][.:]?[0-5][0-9])))?', cmd, re.I)
    if not m:
        raise self.BadInputError()
        return
        
    baseurl = """http://reseplanerare.sl.se/bin/query.exe/sn?REQ0JourneyStopsS0A=255&S=%s&REQ0JourneyStopsZ0A=255&Z=%s&start=yes&REQ0JourneyTime%3D%s&REQ0HafasSearchForw=%s"""
    nick = input.nick
    
    if m.group("later"):
        if not hasattr(self.bot, "sl_posttarget"):
            self.say("Sorry, didn't work!")
            return
        
        if "sen" in m.group("later"):
            earlat = {self.bot.sl_later:"&#197;k senare"}
        else:
            earlat = {self.bot.sl_earlier:"&#197;k tidigare"}
    
        earlat = urllib.urlencode(earlat)
        req = urllib2.Request(self.bot.sl_posttarget, earlat)
        data = urllib2.urlopen(req).read()
        data = decodehtml(data)
    
    if m.group("start"):
        start = m.group("start")
        stop = m.group("stop")
        tid = None
        date = None
        if m.group("time"):
            tid = m.group("time")
        if m.group("date"):
            date = m.group("date")[11:]
            tid = m.group("date")[0:10]
            

        if tid:
            tpar = 0
        else:
            tpar = 1
    
            tid = str(self.localtime())[11:16]
    
        datestring = ""
        if date:
            then = date.split("-")
            then = datetime.date(int(then[0]),int(then[1]),int(then[2]))
            datestring = str(then.day) + "." + str(then.month) + "." + str(then.year)[-2:]
    
        baseurl = baseurl.encode('utf-8')
        baseurl = urllib.unquote(baseurl)
        start = start.encode('latin_1')
        stop = stop.encode('latin_1')
    
        queryurl = baseurl % (urllib.quote(start),urllib.quote(stop),tid,tpar)
        if date:
            queryurl += "&REQ0JourneyDate=" + datestring


        req = urllib2.Request(queryurl)
        data = urllib2.urlopen(req).read().replace("&nbsp;"," ")
        data = decodehtml(data)

        # if we get a choice for the "from"-field
        recheck = False
        if re.search(r'<label for="from" class="ErrorText">Vilken', data, re.IGNORECASE):
            recheck = True
            match = re.search(r'<option value="S-0N1">([^[]+)\[', data, re.IGNORECASE)
            if match:
                start = match.group(1).strip()
    
            else:
                self.say("error1, i sorry")
    
        if re.search(r'<label for="to" class="ErrorText">Vilken', data, re.IGNORECASE):
            recheck = True
            match = re.search(r'<option value="S-1N1">([^[]+)\[', data, re.IGNORECASE)
            if match:
                stop = match.group(1).strip()
    
            else:
                self.say("error2 i sorry")
    
        if recheck:
            if date:
                queryurl += "&REQ0JourneyDate=" + datestring
                
            queryurl = baseurl % (urllib.quote(start),urllib.quote(stop),tid,tpar)
    
            #req = urllib2.Request(queryurl)
            data = urllib.urlopen(queryurl).read().replace("&nbsp;"," ")
            data = decodehtml(data)
    

    #Find earlier/next post data
    m = re.search(r'tidigare resor."\s*name="(?P<earlier>[^"]+)"', data, re.I | re.DOTALL)
    if m:
        self.bot.sl_earlier = m.group("earlier")

    m = re.search(r'senare resor."\s*name="(?P<later>[^"]+)"', data, re.I | re.DOTALL)
    if m:
        self.bot.sl_later = m.group("later")
        
    m = re.search(r'tp_results_form"\s*action="(?P<posttarget>[^"]+)"', data, re.I | re.DOTALL)
    if m:
        self.bot.sl_posttarget = m.group("posttarget")



    #Parse the page
    match = re.search(r'<div class="FormAreaLight">.+<h3>([^<]+)</h3>.*-bottom:..?px;">.+?<p>(.*)</p><p>'
                      ,data, re.DOTALL | re.IGNORECASE)
    if match:
            head = match.group(1)
            body = match.group(2)
    else:
            head = body = None
            self.say("machine no work")
            return
    
    
    body = re.sub("</?[a-z]{1,2} ?/?>"," ",body)
    body = re.sub("</?[a-z]{3,10}>",chr(2),body)

    foot = body[body.index("Restid"):]
    body = body[:body.index("Restid")].replace("  "," ")
    b2 = body[body.index("Du är framme"):]
    b1 = body[:body.index("Du är framme")]
    
    self.say("\x02%s\x02" % head)# "från xx till xx den blabla"
    self.say(b1)# "tag ... från ..."
    self.say(b2)# "du är framme...."
    self.say(foot) # "restid xx minuter"
    
sl.rule = ["sl"]
sl.usage = [("Find out when and how to travel between two stations", "$pcmd <from>, <to>"),
            ("Perform a query and specify when you want to arrive", "$pcmd <from>, <to>, [YYYY-MM-DD] HH:MM"),
            ("After having performed a query, find out when the next departure is", "$pcmd sen")]
sl.example = [("Find out how to go from T-Centralen to Medborgarplatsen", "$pcmd T-Centralen, Medborgarplatsen"),
              ("Find out when your train leaves tomorrow morning, if you want to arrive at 08:00", "$pcmd T-Centralen, Slussen, 08:00")]
