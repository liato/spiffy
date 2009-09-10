import datetime

try:
    from parsedatetime import parsedatetime as pdt
except ImportError:
    pdt = None
    

Weekdays      = [ u'monday', u'tuesday', u'wednesday',
                  u'thursday', u'friday', u'saturday', u'sunday',
                ]

Months        = [ u'january', u'february', u'march',
                  u'april',   u'may',      u'june',
                  u'july',    u'august',   u'september',
                  u'october', u'november', u'december',
                ]

def parsedatetime(self, input):
    """Parse a date or datetime string. Uses the parsedatetime lib if available."""
    if not input.args:
        raise self.BadInputError()
    dt = None
    
    try:
        dt = datetime.datetime.strptime(input.args, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            dt = datetime.datetime.strptime(input.args, '%Y-%m-%d')
        except ValueError:
            if pdt:
                p = pdt.Calendar()
                dt = datetime.datetime(*p.parse(input.args)[0][:7])
    
    if not dt:
        self.say('Error: Couldn\'t parse the date.')
        return

    self.say('\x02%s\x02 is a %s in week %s in %s' % (str(dt)[:19], Weekdays[dt.weekday()].capitalize(), dt.isocalendar()[1], Months[dt.month-1].capitalize()))
 
parsedatetime.rule = ['pdt', 'parsedatetime']
parsedatetime.usage = [('Parse and return a string representation of the given date', '$pcmd <date>')]
parsedatetime.example = [('Return a string representation of fridays date', '$pcmd friday'),
                        ('Parse the date \'Oct 27 2009\'', '$pcmd Oct 27 2009')]
