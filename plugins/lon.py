# -*- coding: utf-8 -*-

import calendar
import datetime
import urllib2

from utils import humantime

icsurl = 'http://www.google.com/calendar/ical/en.swedish%23holiday@group.v.calendar.google.com/public/basic.ics'


def lon(self, input):
    """How long till the next pay day in Sweden?"""
    
    month = None
    if input.args:
        try:
            month = int(input.args)
        except ValueError:
            pass
        else:
            if month > 12 or month < 1:
                month = None
    
    date = datetime.date.today()
    date = datetime.date(date.year, month or date.month, 25)

    if str(date.year) in self.storage:
        holidays = self.storage[str(date.year)]
    else:
        try:
            data = urllib2.urlopen(icsurl).read()
        except (urllib2.HTTPError, urllib2.URLError):
            holidays = {}
        else:
            holidays = {}            
            lastdate = None
            for line in data.split('\n'):
                line = line.strip('\r').strip('\n')
                if line.startswith('DTSTART;VALUE=DATE:'):
                    lastdate = line.split(':')[1]
                    holidays[lastdate] = None
                elif line.startswith('SUMMARY:'):
                    holidays[lastdate] = line.split(':')[1]
            self.storage[str(date.year)] = holidays
            self.storage.save()

    payday = None
    while date >= datetime.date(date.year, date.month, 1):
        if date.weekday() in (5, 6) or str(date) in holidays:
            date = date - datetime.timedelta(days = 1)
        else:
            payday = date
            break
        
    if payday is not None:
        datedif = datetime.datetime(*payday.timetuple()[:3]) - self.localtime()
        datedif = datedif.days * 24 * 3600 + datedif.seconds
        if datedif < 0:
            self.say(u"Lönen kom %s sedan (%s)" % (humantime(abs(datedif)), payday))
        elif datedif == 0:
            self.say(u"Lönen kommer nu!")
        else:
            self.say(u"Lönen kommer om %s (%s)" % (humantime(abs(datedif)), payday))
            
    else:
        self.say(u'Error: Ingen lön den här månaden?')


lon.rule = ['lon', 'loen', 'payday']
lon.usage = [(u'När kommer lönen?', '$pcmd'),
    (u'När kommer lönen månad nummer <i>?', '$pcmd <i>')]