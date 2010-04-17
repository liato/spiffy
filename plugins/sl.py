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
    if input.command.lower() == "slf":
        cmd = "-f "+cmd
    
    m = re.search(r'(?P<fl>-fl)|-fa (?P<fafrom>[^,]+),\s*?(?P<fato>[^,]+),\s*?(?P<faname>.+)|-fr (?P<frmatch>.+)|-f (?P<favorite>[^,]+)(?:,\s*?(?P<ftime>[01-2]?[0-9][.:]?[0-5][0-9]))?|(?P<later>sen|tidig)(?:are)?|(?P<start>[^,]+),\s*(?P<stop>[^,]+)(?:,\s*?(?:(?P<date>\d{4}-\d{2}-\d{2} [012]?[0-9][.:]?[0-5][0-9])|(?P<time>[01-2]?[0-9][.:]?[0-5][0-9])))?', cmd, re.I)
    if not m:
        raise self.BadInputError()
        return
        
    baseurl = """http://reseplanerare.sl.se/bin/query.exe/sn?REQ0JourneyStopsS0A=255&S=%s&REQ0JourneyStopsZ0A=255&Z=%s&start=yes&REQ0JourneyTime%3D%s&REQ0HafasSearchForw=%s"""
    start = stop = sdate = stime = None
    
    stime = m.group("time") if m.group("time") else stime
    sdate = m.group("date") if m.group("date") else sdate
    user = input.nick.lower()
    if not user in self.storage:
        self.storage[user] = {}
    db = self.storage[user]
    
    
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
        
    if m.group("favorite"):
        if m.group("favorite").lower() in db:
            start, stop = db[m.group("favorite").lower().strip()]
            stime = m.group("ftime") if m.group("ftime") else stime
        else:
            self.say("No such favorite, .sl -fl to list your favorites  or .sl -fa <from>, <to>, <name> to add a new.")
            return

    if m.group("fl"):
        if len(db) > 0:
            self.notice(input.nick, "\x02Your favorites:")
            for name, dest in db.iteritems():
                self.notice(input.nick, " %s: %s -> %s" % (name, dest[0], dest[1]))
        else:
            self.notice(input.nick, "No favorites added yet, use .sl -fa <from>, <to>, <name> to add a new favorite.")
        return

    elif m.group("fafrom"):
        db[m.group("faname").strip()] = (m.group("fafrom").strip(), m.group("fato").strip())
        self.storage.save()
        self.notice(input.nick, "Favorite added!")
        return
    
    elif m.group("frmatch"):
        frmatch = m.group("frmatch").lower()
        for name, dest in db.items():
            if frmatch in name.lower() or frmatch in dest[0].lower() or frmatch in dest[1].lower():
                self.notice(input.nick, "Removing: %s: %s -> %s" % (name, dest[0], dest[1]))
                del db[name]
        self.storage.save()
        return
    
    start = start or m.group("start")
    stop = stop or m.group("stop")
    if start:
        if sdate:
            stime = sdate[0:10]
            sdate = sdate[11:]
            

        if stime:
            tpar = 0
        else:
            tpar = 1
            stime = str(self.localtime())[11:16]
    
        datestring = ""
        if sdate:
            then = sdate.split("-")
            then = datetime.date(int(then[0]),int(then[1]),int(then[2]))
            datestring = str(then.day) + "." + str(then.month) + "." + str(then.year)[-2:]
    
        baseurl = baseurl.encode('utf-8')
        baseurl = urllib.unquote(baseurl)
        start = start.encode('latin_1')
        stop = stop.encode('latin_1')
    
        queryurl = baseurl % (urllib.quote(start),urllib.quote(stop),stime,tpar)
        if sdate:
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
            if sdate:
                queryurl += "&REQ0JourneyDate=" + datestring
                
            queryurl = baseurl % (urllib.quote(start),urllib.quote(stop),stime,tpar)
    
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
    
sl.rule = ["sl", "slf"]
sl.usage = [("Find out when and how to travel between two stations", "$pcmd <from>, <to>"),
            ("Perform a query and specify when you want to arrive", "$pcmd <from>, <to>, [YYYY-MM-DD] HH:MM"),
            ("After having performed a query, find out when the next or previous departure is", "$pcmd sen|tidigare"),
            ("Add a trip to favorites", "$pcmd -fa <from>, <to>, <name>"),
            ("Remove a trip from favorites", "$pcmd -fr <text to match>"),
            ("List all your favorites", "$pcmd -fl"),
            ("Find out when and how to travel using favorites", "$pcmd -f <name>[, <HH:MM>]")]
sl.example = [("Find out how to go from T-Centralen to Medborgarplatsen", "$pcmd T-Centralen, Medborgarplatsen"),
              ("Find out when your train leaves tomorrow morning, if you want to arrive at 08:00", "$pcmd T-Centralen, Slussen, 08:00")]
