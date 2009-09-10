import re
import urllib

from utils import removehtml

def isitdown(self, input):
    """Check if a website is down using downforeveryoneorjustme.com"""
    if not input.args:
        raise self.BadInputError()

    site = urllib.quote(input.args.encode('utf-8'))

    try:
        data = urllib.urlopen('http://downforeveryoneorjustme.com/%s' % site).read()
    except IOError: 
        self.say('Error: Unable to establish a connection to downforeveryoneorjustme.com.')
        return

    data = data.replace('\r','').replace('\n','')
    m = re.search(r'<div id="container">(?P<resp>.*?)(?:Check another|Try again)',data,re.IGNORECASE)
    if not m:
        self.say('Error: Could not parse data. Has the site layout changed?')
        return

    m = re.sub(r'(?:<a href[^>]*>|</a>)','\x02', m.group("resp"))
    m = removehtml(m).strip()
    self.say(m)

isitdown.rule = ['isitdown', 'id']
isitdown.usage = [('Check if the website at url is accessable', '$pcmd <url>')]
isitdown.example = [('Check if google.com is up or down', '$pcmd google.com')]
