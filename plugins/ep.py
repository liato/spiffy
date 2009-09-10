import datetime
import re
import time
import urllib


class TVRage(object):
    def __init__(self, show, episode=None):
        self.rshow = show #Requested show
        self.repisode = episode #Requested episode

        self.show = None #Name of the show
        self.showurl = None #Url to the show
        self.episode = None #Episode info
        self.episodeurl = None #Episode url
        self.premiered = None #Year of the show premiere 
        self.latest = None #Information about the latest episode
        self.next = None #Information about the next episide
        self.country = None #Country of origin
        self.status = None #Current show status (Returning Series|Canceled/Ended)
        self.classification = None #Scriptet, reality...
        self.genres = None #Genres of the show
        self.network = None #Airing network
        self.airtime = None #Day and time
        self.runtime = None #Runtime in minutes

        self.mappings = {
            'show name': ['show'],
            'show url': ['showurl'],
            'premiered': ['premiered', int],
            'episode url': ['episodeurl'],
            'episode info': ['episode', self._parseepisode],
            'latest episode': ['latest', self._parseepisode],
            'next episode': ['next', self._parseepisode],
            'country': ['country'],
            'status': ['status'],
            'classification': ['classification'],
            'genres': ['genres', lambda s: [x.strip() for x in s.split('|')]],
            'network': ['network'],
            'airtime': ['airtime'],
            'runtime': ['runtime', int]
        }
        
        self.update()
    
    def update(self):
        if self.repisode:
            data = urllib.urlopen('http://www.tvrage.com/quickinfo.php?show=%s&ep=%s' % (urllib.quote(self.rshow.encode('utf-8')), urllib.quote(self.repisode.encode('utf-8')))).read()
        else:
            data = urllib.urlopen('http://www.tvrage.com/quickinfo.php?show=%s' % urllib.quote(self.rshow.encode('utf-8'))).read()
        data = data.replace('\r','').split('\n')
        for e in data:
            if '@' in e:
                f, v = e.split('@', 1)
                f = f.lower()
                if f in self.mappings:
                    if len(self.mappings[f]) == 2:
                        setattr(self, self.mappings[f][0], self.mappings[f][1] and self.mappings[f][1](v) or v)
                    else:
                        setattr(self, self.mappings[f][0], v)
    
    def _parseepisode(self, s):
        num, name, air = s.split('^', 3)
        aird = datetime.datetime.utcnow()
        for strf in ['%b/%d/%Y', '%d/%b/%Y', '%d/%Y', '%Y']:
            try:
                aird = datetime.datetime.strptime(air, strf)
                break
            except ValueError:
                pass

        return [num, name, aird]

def ep(self, input):
    """Air dates and other info for tv shows and episodes"""

    m = re.search(r'([^,]+)(?:, ?(\d{1,3}x\d{1,3}))?',input.args)

    if not m:
        raise self.BadInputError()

    showname = m.group(1)
    episode = m.group(2)
    extended = False
    now = datetime.datetime.utcnow()
    now = now - datetime.timedelta(hours=5) #Assume EST. TODO: Add support for mote timezones.
    now = datetime.datetime(*now.timetuple()[:3])
    
    def daysago(then):
        m = {'0': 'today',
             '1': 'tomorrow',
             '-1': 'yesterday'}
        
        datedif = then-now
        datedif = datedif.days
        if then > now:
            return 'Airs %s' % (m.get(str(datedif)) and ('\x02'+m.get(str(datedif))+'\x02') or ('in \x02'+str(datedif)+'\x02 days'))
        else:
            return 'Aired %s' % (m.get(str(datedif)) and ('\x02'+m.get(str(datedif))+'\x02') or ('\x02'+str(-datedif)+'\x02 days ago'))
            
    if showname[0:2] == '-i' or showname[0:2] == '-e':
        showname = showname[3:]
        extended = True

    try:
        show = TVRage(showname, episode)
    except IOError: 
        self.say('Error: A connection to tvrage.com could not be established.')
        return

    if not show.show:
        self.say('The show could not be found.')
        return
    
    self.say('\x02%s\x02 - \x1f%s\x1f%s' % (show.show, show.showurl, ((show.status == 'Canceled/Ended') and '\x034(Canceled/Ended)\x03' or '')))
    if not episode:
        if show.latest:
            self.say('Latest: \x02%s\x02 - %s [ %s | %s ]' % (show.latest[0], show.latest[1], show.latest[2].isoformat()[:10], daysago(show.latest[2])))
        else:
             self.say('Latest: No episodes aired yet')
        if show.next:
            self.say('Next:   \x02%s\x02 - %s [ %s | %s ]' % (show.next[0], show.next[1], show.next[2].isoformat()[:10], daysago(show.next[2])))
        else:
            self.say('Next:   No upcoming episodes')
    else:
        if not show.episode:
            self.say('Error:  No information about the specified episode could be found')
        else:
            self.say('\x02%s\x02 - %s [ %s | %s ] - %s' % (show.episode[0], show.episode[1], show.episode[2].isoformat()[:10], daysago(show.episode[2]), show.episodeurl))
        
    if extended:
        self.say('\x02Info:\x02   The first episode of this %s show aired%s%s%s' % (show.classification.lower(),
                                                                                     show.premiered and ' year ' + str(show.premiered) or '',
                                                                                     show.network and ' on ' + show.network or '',
                                                                                     show.country and ' in ' + show.country or ''))
        if show.airtime:
            self.say('\x02     \x02   The show airs/aired on %ss at %s' % (show.airtime.split(' at')[0], show.airtime.split(' at')[1].strip()))
        if show.status:
            self.say('\x02     \x02   The current status of the show is %s%s' % (show.status.lower(),
                                                                                 show.genres and ' and the genre(s) are '+', '.join(show.genres)))


ep.rule = ["ep"]
ep.usage = [("Fetch information about a show and display airdates", "$pcmd <show>"),
    ("Fetch information about a show and display all details", "$pcmd -i <show>"),
    ("Fetch information about an episode", "$pcmd <show>, <season>x<episode>")]
ep.example = [("Find out when the next episode of Lost airs","$pcmd lost"),
    ("Find out airdates. network, genres and more for the show Lost","$pcmd -i lost"),
    ("Find out when the first episode of Lost aired","$pcmd lost, 01x01")]