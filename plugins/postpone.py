import datetime
import re
from threading import Timer

from utils import humantime

import parsedatetime.parsedatetime as pdt
from twisted.words.protocols.irc import numeric_to_symbolic, symbolic_to_numeric

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

