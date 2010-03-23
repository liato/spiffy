import datetime
import re
import time

from utils import humantime

days = ['Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday']

def week(self, input):
    """Displays the week and weekday for today or for a given date or a date and weekday given a week."""
    
    date = datetime.date(*self.localtime().timetuple()[:3])
    if input.args:
        try:
            date = datetime.date(*time.strptime(input.args, '%Y-%m-%d')[:3])
        except ValueError:
            try:
                isoweek = int(input.args)
                firstweek = datetime.date(date.year, 1, 4)
                thisweek = firstweek + datetime.timedelta(days=(isoweek-1)*7)
                thisweek = thisweek - datetime.timedelta(days=thisweek.isoweekday()-1)
                timedif = datetime.datetime(*thisweek.timetuple()[:3]) - self.localtime()
                timedif = timedif.days*24*3600 + timedif.seconds
                if not thisweek.year == date.year:
                    raise self.BadInputError('Year %d does not have a week %d.' % (date.year, isoweek))
                self.say('The first date of week \x02%d\x02 is \x02%s\x02 (%s %s)' % (thisweek.isocalendar()[1],
                                                                                      thisweek,
                                                                                      humantime(abs(timedif)),
                                                                                      ('left' if timedif > 0 else 'ago')))
                return
            except (ValueError, OverflowError):
                raise self.BadInputError('Invalid date or week.')
                
    self.say("\x02%s\x02 is a \x02%s\x02 in week \x02%d\x02" % (date,
                                       days[date.isoweekday()-1],
                                       date.isocalendar()[1]))


week.rule = ["vecka", "week"]
week.usage = [("Display the current week", "$pcmd"),
              ("Display the week for a given date", "$pcmd <YYYY-MM-DD>"),
              ("Display the first date for a given week", "$pcmd <W>")]
week.example = [("Display the week Halloween was in in 1999", "$pcmd 1999-10-31"),
                ("Display the first date in the 8th week", "$pcmd 8")]
