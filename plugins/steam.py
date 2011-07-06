import os
import pickle
import re
import urllib2

from BeautifulSoup import BeautifulSoup as bs

try:
    from hlquery import HLserver
except ImportError:
    HLserver = None

numericprog = re.compile('^[0-9]+$')
def isnumeric(str):
    return numericprog.match(str) is not None


import os
import pickle
import re
import urllib2

from BeautifulSoup import BeautifulSoup as bs

try:
    from hlquery import HLserver
except ImportError:
    HLserver = None

numericprog = re.compile('^[0-9]+$')
def isnumeric(str):
    return numericprog.match(str) is not None


class SteamStatus:

    def __init__(self, id=None, steamalias=False, search=None):
        id = str(id)
        self.userid = id
        self.username = None
        self.status = None # 0=Offline, 1=Online, 2=Playing, 3=Private
        self.game = None
        self.lastseen = None
        self.server = None
        self.steamalias = steamalias
        if search:
            self.userid = self._search(search)

    def update(self):
        if self.steamalias:
            data = urllib2.urlopen('http://steamcommunity.com/id/%s' % self.userid).read()
        else:
            data = urllib2.urlopen('http://steamcommunity.com/profiles/%s' % self.userid).read()
            
            
        data = bs(data, convertEntities=bs.HTML_ENTITIES)
        try:
            self.username = data.find(id="mainContents").h1.contents[0].strip()
        except Exception:
            return
        try:
            self.status = data.find(id='statusOnlineText').string
            self.status = 1
        except Exception:
            pass
        if not self.status:
            try:
                self.game = data.find(id='statusInGameText').string.strip()
                self.status = 2
            except Exception:
                pass
        if not self.status:
            try:
                if data.find('p', 'errorPrivate'):
                    self.status = 3
            except Exception:
                pass
        if not self.status:
            try:
                self.lastseen = data.find(id='statusOfflineText').string.replace('Last Online: ',"")
                self.status = 0
            except Exception:
                pass

        if self.status == 2: # The user is in-game, retrieve the ip if possible
            try:
                friendurl = data.find(id='friendBlocks').div.div.div.a['href']
            except Exception:
                return
            
            friendurl = friendurl +'/friends'
            data = data = urllib2.urlopen(friendurl).read()
            data = bs(data, convertEntities=bs.HTML_ENTITIES)
            try:
                self.server = data.find('a', text=self.username).parent.parent.span.find('a')['href'][16:]
            except Exception:
                pass
        
    def _search(self, user):
        data = urllib2.urlopen('http://steamcommunity.com/actions/Search?T=Account&K=%s' % urllib2.quote(user.encode('utf-8'))).read()
        data = bs(data, convertEntities=bs.HTML_ENTITIES)
        url = data.find('div', 'resultItem')
        if url: url = url.find('a', 'linkTitle')
        if not url:
            return None
        url = dict(url.attrs).get('href', '').strip('/').split('/')
        if url[-2] == 'id':
            self.steamalias = True
        else:
            self.steamalias = False
        return url[-1]
        
        


def setup(self, input): 
    fn = self.config['network'] + '.steamids.db'
    self.bot.steam_filename = os.path.join('data', fn)
    if not os.path.exists(self.bot.steam_filename): 
        try:
            f = open(self.bot.steam_filename, 'w')
        except OSError:
            pass
        else: 
            pickle.dump(dict(abc='123'), f)
            f.close()
    f = open(self.bot.steam_filename, 'r')
    self.bot.steamids = pickle.load(f)
    f.close()
    
def savealiases(fn, data):
    try:
        f = open(fn, 'w')
        pickle.dump(data, f)
        f.close()
        return True
    except:
        return False
    
def steam(self, input):
    """Are your friends playing without you? Probably."""

    if not input.args:
        raise self.BadInputError()
    
    parser = self.OptionParser()
    parser.add_option('-r', '--remove', dest='remove', default=None)
    parser.add_option('-a', '--add', dest='add', nargs=2)
    parser.add_option('-e', '--extended', dest='extended', action='store_true', default=False)
    parser.add_option('-l', '--list', dest='list', action='store_true')
    options, args = parser.parse_args((input.args or '').split())
    
    if options.remove and options.add:
        parser.error('Options -r and -a are mutually exclusive.')

    if options.list:
        if len(self.bot.steamids) == 0:
            self.say("No aliases added yet.")
            return
        
        self.say(chr(2) + u"Alias -> Steam community ID:" + chr(2))
        for k,v in self.bot.steamids.iteritems():
            self.say("   %s -> %s" % (k,v))
        return
    
    if not options.remove and not options.add:
        steamids = ' '.join(args).split(',')
            
        for steamid in steamids:
            steamid = steamid.strip()
            if steamid.lower() in self.bot.steamids:
                id = self.bot.steamids[steamid.lower()]
                if isnumeric(id):
                    status = SteamStatus(id)
                else:
                    status = SteamStatus(id, True)
            else:
                id = steamid
                if isnumeric(id):                
                    status = SteamStatus(id)
                else:
                    status = SteamStatus(search=id)

            status.update()
        
            if status.username:
                if status.status == 0:
                    self.say(u'%s is offline, last seen: %s.' % (status.username, status.lastseen))
                elif status.status == 1:
                    self.say(u'%s is online.' % status.username)
                elif status.status == 2:
                    self.say(u'%s is playing %s%s.' % (status.username, status.game, status.server and ' on steam://connect/'+ status.server or ''))
                    if options.extended:
                        if not status.server:
                            self.say(u'No extra info could be found on %s' % status.username)
                        else:
                            if HLserver:
                                server, port = status.server.split(':')
                                arr = HLserver(server,int(port))
                                info = arr.info()
                                players = arr.players()
                                if not info or not players:
                                    self.say(u'No extra info could be found on %s' % status.username)
                                else:
                                    self.say('\x02Name\x02: %s' % info.get('hostname', 'Unknown'))
                                    self.say('\x02Map\x02: %s' %  info.get('map', 'Unknown'))
                                    self.say('\x02Players\x02: %s/%s' % (info.get('clientcount', '0'), info.get('clientmax', '0')))
                                    for player in players:
                                        if status.username.encode('utf-8') == players[player]['name']:
                                            self.say('\x02%s\x02 has \x02%s\x02 frags and has been playing for \x02%s\x02.' % (status.username, players[player]['frags'], players[player]['stime']))
                            else:
                                self.say('Error: Could not retrieve any extra info on %s. The HLQuery module is missing.' % status.username)
                elif status.status == 3:
                    self.say(u'%s has a private profile.' % status.username)
            else:
                self.say(u'The user \'%s\' could not be found.' % steamid)
    elif options.add:
        if options.add[0].lower() in self.bot.steamids:
            self.say('Updated the alias with new id.')
        else:
            self.say('Alias %s added.' % options.add[0])
        self.bot.steamids[options.add[0].lower()] = options.add[1]
        if not savealiases(self.bot.steam_filename, self.bot.steamids):
            self.say('Error: Could not write database to disk.')
    elif options.remove:
        if options.remove.lower() in self.bot.steamids:
            self.say('Removed the alias.')
            del self.bot.steamids[options.remove.lower()]
        else:
            self.say('No such alias.')
        if not savealiases(self.bot.steam_filename, self.bot.steamids):
            self.say('Error: Could not write database to disk.')


steam.rule = ['steam']
steam.setup = setup
steam.usage = [('Look upp the status for the given userid/useralias', '$pcmd <userid/useralias>'),
               ('Add a new useralias', '$pcmd -a <alias> <steamcommunityid>'),
               ('Remove a useralias', '$pcmd -r <alias>')]
steam.example = [('Look upp the status for the user \'hunter\'', '$pcmd hunter'),
                 ('Look upp the status for the userid 76561197993374432', '$pcmd 76561197993374432'),
                 ('Bind the userid 76561197993374432 to the alias \'hunter\'', '$pcmd -a hunter 76561197993374432'),
                 ('Remove hunter\'s useralias', '$pcmd -r hunter')]
