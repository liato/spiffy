import re
import urllib
try:
    import json
except ImportError:
    import simplejson as json
    
def domain(self, input):
    "Domain availability"
    if not input.args:
        raise self.BadInputError()

    hosts = input.args
    hosts = re.sub(r'[\s,]+', ' ', hosts)
    hosts = hosts.split()
    hosts = [urllib.quote(h.encode('utf-8')) for h in hosts]

    response =  []
    for host in hosts:
        try:
            data = urllib.urlopen('http://domai.nr/api/json/search?q=%s' % host).read()
        except IOError: 
            self.say("Error: Unable to establish connection to domai.nr.")
            return
        
        data = json.loads(data)
        if 'error' not in data:
            result = data['results'][0]
            #response.append('\x02%s\x02 [%s]' % (result['domain'], result['availability'][0].upper()))
            response.append('\x02%s\x02 [%s]' % (result['domain'], result['availability']))
            
    if response:
        self.say(', '.join(response))
    else:
        self.say('Sorry, no results.')
    
domain.rule = ["domain", "d"]
domain.usage = [("Check domain availability", "$pcmd <domain>[ <domain>...]")]
domain.example = [("Check if google.com is available for registration", "$pcmd google.com")]
