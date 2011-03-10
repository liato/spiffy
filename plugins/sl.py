# -*- coding: utf-8 -*-
import datetime
import re
import time
import urllib
import urllib2

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print "No json module found, unable to load sl plugin."
        raise

from utils import humantime


def sl(self, input):
    """Queries sl.se for train/bus times"""
    
    cmd = input.args
    if input.command.lower() == "slf":
        cmd = "-f "+cmd
    
    m = re.search(r'(?P<fl>-fl)|-fa (?P<fafrom>[^,]+),\s*?(?P<fato>[^,]+),\s*?(?P<faname>.+)|-fr (?P<frmatch>.+)|-f (?P<favorite>[^,]+)(?:,\s*?(?P<ftime>[01-2]?[0-9][.:]?[0-5][0-9]))?|(?P<later>sen|tidig)(?:are)?|(?P<start>[^,]+),\s*(?P<stop>[^,]+)(?:,\s*?(?:(?P<date>\d{4}-\d{2}-\d{2} [012]?[0-9][.:]?[0-5][0-9])|(?P<time>[01-2]?[0-9][.:]?[0-5][0-9])))?', cmd, re.I)
    if not m:
        raise self.BadInputError()
        return
        
    sl_api_key = self.config.get('sl_api_key', '')
    sl_api_url = self.config.get('sl_api_url', '')


    start = stop = sdate = stime = None
    
    stime = m.group("time") if m.group("time") else stime
    sdate = m.group("date") if m.group("date") else sdate
    user = input.nick.lower()
    if not user in self.storage:
        self.storage[user] = {}
    db = self.storage[user]
    
    
    if m.group("later"):
        self.say('Not implemented yet')
        pass

        
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
        isDepartureTime = True
        if sdate or stime:
            isDepartureTime = False

        if sdate:
            sdate = sdate[:16]
        elif stime:
            if len(stime) is 1:
              stime = '0%s:00' % stime
            elif len(stime) is 2:
                stime = stime+':00'
            elif len(stime) is 4:
                stime = stime[:2]+':'+stime[2:]
                
            sdate = str(self.localtime())[:11]+stime
        else:
            sdate = str(self.localtime())[:16]

        
  
        r = urllib2.urlopen("%sjourneyplanner/?key=%s" % (sl_api_url, sl_api_key),
                            data=json.dumps({"origin":
                                                {"id": 0,
                                                 "longitude": 0,
                                                 "latitude": 0,
                                                 "name": start
                                                 },
                                             "isTimeDeparture": isDepartureTime,
                                             "time": sdate,
                                             "destination":
                                                {"id": 0,
                                                 "longitude": 0,
                                                 "latitude": 0,
                                                 "name": stop
                                                 }
                                            }))

        data = r.read()
        d = json.loads(data)
        if d.get('numberOfTrips',0) == 0:
            self.say('Couldn\'t find anything.')
            return
        else:
            trips = d["trips"]
            trip = None

            if not isDepartureTime: # user specified a desired time of arrival
                desiredTime = datetime.datetime.strptime(sdate,"%Y-%m-%d %H:%M")

                bestTrip = None

                for t in trips:
                    arrivalString = t["arrivalDate"] + " " + t["arrivalTime"]
                    arrivalTime = datetime.datetime.strptime(arrivalString, "%d.%m.%y %H:%M")
                    delta = desiredTime-arrivalTime
                    if delta.total_seconds() >= 0:
                        bestTrip = t
                    else:
                        break
                    
                trip = bestTrip
            else: # user wants to go as soon as possible
                bestTrip = None
                
                for t in trips:
                    departureString = t["departureDate"] + " " + t["departureTime"]
                    departureTime = datetime.datetime.strptime(departureString, "%d.%m.%y %H:%M")
                    delta = datetime.datetime.now()-departureTime
                    self.say(delta.total_seconds())
                    if delta.total_seconds() <= 0:
                        bestTrip = t
                        break
                trip = bestTrip

            if not trip:
                self.say('Couldn\'t find anything.')
                return
                
            
            duration = trip['duration'].split(':')
            duration = humantime(int(duration[0])*60*60 + int(duration[1])*60)
            readableDate = datetime.datetime.strptime(trip["departureDate"], "%d.%m.%y").strftime("%Y-%m-%d")
            self.say(u'Från \x02%s\x02 till \x02%s\x02, %s %s - %s (%s), %s %s:' % (trip['origin']['name'], trip['destination']['name'], readableDate, trip['departureTime'], trip['arrivalTime'], duration, (trip['changes'] if trip['changes'] is not 0 else 'inga'), ('byte' if trip['changes'] is 1 else 'byten')))
            for subtrip in trip['subTrips']:
                self.say(u'[%s] %s - %s \x02%s\x02 från \x02%s\x02 mot \x02%s\x02. Kliv av vid \x02%s' % (subtrip['transport']['type'], subtrip['departureTime'], subtrip['arrivalTime'],
                                                                                                          subtrip['transport']['name'], subtrip['origin']['name'], subtrip['transport']['towards'], subtrip['destination']['name']))
        

    
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
