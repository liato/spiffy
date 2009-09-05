import datetime
import re
from threading import Timer

import parsedatetime.parsedatetime as pdt
from twisted.words.protocols.irc import numeric_to_symbolic, symbolic_to_numeric

def humantime(seconds, string=True):
    m,s = divmod(seconds, 60)
    h,m = divmod(m, 60)
    d,h = divmod(h, 24)
    w,d = divmod(d, 7)
    if string:
        return ((w and str(w)+'w ' or '')+(d and str(d)+'d ' or '')+(h and str(h)+'h ' or '')+(m and str(m)+'m ' or '')+(s and str(s)+'s' or '')).strip()
    else:
        return (w, d, h, m, s)

def postpone(self, input):
    """Postpones the given command for a given amount of time."""
    m = re.search(r'([^,]+),\s?(.+)', input.args or "", re.I)
    if not m:
        raise self.BadInputError()

    c = pdt.Calendar()
    now = datetime.datetime.utcnow()
    delta = datetime.datetime(*c.parse(m.group(1), now)[0][:-2]) - now
    seconds = delta.days*24*60*60 + delta.seconds + 1
    time = humantime(seconds)
    cmd = m.group(2)
    line = input.line.split(' :', 1)[0]+' :'+cmd
    
    if seconds <= 0:
        raise self.BadInputError('The time entered is invalid.')
    
    def send():
        self.say('\x02[PP]\x02[%s ago] <%s> %s' % (time, input.nick, cmd))
        prefix, command, params, text = self.parsemsg(line)
        if numeric_to_symbolic.has_key(command):
            command = numeric_to_symbolic[command]
        self.bot.handleCommand(command, prefix, params, text, line)
        
    self.say('Postponing the command for %s' % time)
    t = Timer(seconds, send)
    t.start()

postpone.rule = ['postpone', 'pp']
postpone.usage = [('Execute <command> after <time> amount of time','$pcmd <time>, <command>')]
postpone.example = [('Execute the !imdb command after 2 minutes and 13 seconds','$pcmd 2m13s, !imdb terminator salvation')]

