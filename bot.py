# this will probably raise an exception in Python >= 2.6
from __future__ import with_statement

import codecs
import datetime
import hashlib
import imp
import optparse
import os
import re
import sqlite3
import sys
import threading
import time
import traceback
import warnings

from twisted.words.protocols import irc
from twisted.words.protocols.irc import lowDequote, numeric_to_symbolic, symbolic_to_numeric, split
from twisted.internet import reactor, protocol

try:
    import cjson as json # Try loading the fastest lib first.
    json.dumps = json.encode
    json.loads = json.decode
except ImportError:
    try:
        import json # Available in python >= 2.6.
    except ImportError:
        try:
            import simplejson as json # If no json library is found logging to sqlite and mysql will be disabled.
        except ImportError:
            json = None
            
try:
    import MySQLdb
except ImportError:
    MySQLdb = None
    
try:
    from pytz import timezone
except ImportError:
    timezone = None


    
config_defaults = {'nick': 'spiffy', 'prefix': r'!', 'chandebug': True,
                    'channels': [],
                    'logevents': ['PRIVMSG', 'JOIN', 'PART',
                                    'MODE', 'TOPIC', 'KICK', 'QUIT',
                                    'NOTICE', 'NICK', '332', '333'],
                    'verbose': True, 'reconnect': 10,
                    'logpath': 'logs', 'plugins_exclude': [],
                    'plugins_include': False, 'timezone': None}

def sourcesplit(source):
    """Split nick!user@host and return a 3-value tuple."""
    r = re.compile(r'([^!]*)!?([^@]*)@?(.*)')
    m = r.match(source)
    return m.groups()

class Bot(irc.IRCClient):
    
    class BadInputError(Exception):
        def __init__(self, value=None):
            self.value = value
        def __str__(self):
            return repr(self.value)

    def connectionMade(self):
        self._print = self.factory._print
        self.config = self.factory.config
        self.connections = self.factory.connections
        self.connections[self.config['network']] = self
        if isinstance(self.config['nick'], (list, tuple)):
            self.nickname = self.config['nick'][0]
            self.nickbucket = self.config['nick'][1:]
        else:
            self.nickname = self.config['nick']
            self.nickbucket = []
        self.username = self.config.get('user', self.nickname)
        self.realname = self.config.get('name', self.nickname)
        self.me = '%s!%s@unknown' % (self.nickname, self.username)
        self.config['logevents'] = [s.upper() for s in self.config['logevents']]
        self.logger = IRCLogger(self, self.config.get('logpath'))
        self.chanlist = ChanList(self)
        self.encoding = 'utf-8'
        self.split = split #Make the split function accessible to plugins
        self.sourceURL = None #Disable source reply.
        self.lastmsg = time.mktime(time.gmtime())
        t = threading.Thread(target=self.connectionWatcher)
        t.start()
        
        if not os.path.exists("data"):
            os.mkdir("data")
        
        self.loadPlugins()
        irc.IRCClient.connectionMade(self)
        self._print("Connected to %s:%s at %s" % (self.transport.connector.host, self.transport.connector.port, time.asctime(time.localtime(time.time()))))

    def parsemsg(self, s):
        """Breaks a message from an IRC server into its prefix, command, arguments and text.
        """
        prefix = None
        text = None
        if not s:
            raise irc.IRCBadMessage("Empty line.")
        if s[0] == ':':
            prefix, s = s[1:].split(' ', 1)
        if s.find(' :') != -1:
            s, text = s.split(' :', 1)
    
        args = s.split()
        command = args.pop(0)
        return prefix, command, args, text

    def connectionWatcher(self):
        """Make sure that we are still connected by PINGing the server."""
        while True:
            #Send PING to the server If no data has been received for 200 seconds.
            if (self.lastmsg+200) < time.mktime(time.gmtime()):
                self.lastmsg = time.mktime(time.gmtime())
                self.sendLine("PING YO!")
            time.sleep(200)

    def loadPlugins(self):
        self._print("Loading plugins...")
        self.plugins = {} # Plugins loaded from the plugins directory.
        self.plugins_nicktriggered = {} # plugins that have a <nick> trigger
        self.doc = {} # Documentation for plugins.
        self.plugin_aliases = {} # Aliases for plugin commands.
        self.plugins_regex = {} # Plugins that use a regex for matching
        
        plugins = []
        if os.path.exists(os.path.join(sys.path[0], "plugins")):
            filenames = []

            if isinstance(self.config['plugins_include'], (list, tuple)):
                for fn in self.config['plugins_include']:
                    if not "." in fn:
                        fn = fn + ".py"
                    filenames.append(os.path.join(sys.path[0], "plugins", fn))
            else:
                for fn in os.listdir(os.path.join(sys.path[0], "plugins")): 
                    if fn.endswith('.py') and not fn.startswith('_'):
                        if not fn[:-3] in self.config['plugins_exclude']:
                            filenames.append(os.path.join(sys.path[0], "plugins", fn))

            for filename in filenames:
                name = os.path.basename(filename)[:-3]
                try:
                    self.loadPlugin(filename)
                    plugins.append(name)
                except Exception, e:
                    self._print("Error loading %s: %s (in bot.py)" % (name, e), 'err')


        if plugins: 
           self._print('Registered plugins: %s' % ', '.join(plugins))
        else:
            if not self.config['plugins_include'] == []:
                self._print("Warning: Couldn't find any plugins. Does /plugins exist?", 'err')

    def loadPlugin(self, filename, function = None):

        def createdoc(self, func, commands = None):
            pcmd = self.config["prefix"] + func.name # pcmd = prefixed command
            
            if commands:
                commands = commands[:]

            if func.__doc__:
                doc = func.__doc__
            else:
                doc = None

            if hasattr(func, "usage"):
                usage = "\x02Usage:\x02\n  "
                usage += "\n  ".join(cmd + " - " + text
                                     for text,cmd in func.usage)
                
                usage = usage.replace("$pcmd", pcmd)
                usage = usage.replace("$cmd", func.name)
                usage = usage.replace("$nick", self.nickname)
            else:
                usage = None
            
            if hasattr(func, 'example'): 
                example = "\x02Example:\x02\n  "
                example += "\n  ".join("\n    ".join(e for e in f)
                                       for f in func.example)

                example = example.replace("$pcmd", pcmd)
                example = example.replace("$cmd", func.name)                    
                example = example.replace('$nick', self.nickname)
            else:
                example = None

            for command in commands or []:
                self.plugin_aliases[command.lower()] = func.name
            if func.name in (commands or []):
                commands.remove(func.name)
            if commands:
                aliases = "\x02Aliases for the %s command:\x02\n  " % func.name
                aliases += ", ".join(commands)
            else:
                aliases = None
            
            self.doc[func.name] = (doc, usage, example, aliases)            

        def handlefunc(func):
            if hasattr(func, 'rule'):
                if not hasattr(func, 'name'): 
                    func.name = func.__name__
                func.name = func.name.lower()
                
                if not hasattr(func, 'event'):
                    func.event = 'PRIVMSG'
                else:
                    func.event = func.event.upper()
       
                self.plugins[func.name] = func
                
                if isinstance(func.rule, str):
                    if '$nick' in func.rule:
                        self.plugins_nicktriggered[func.name] = func
                    pattern = func.rule.replace('$nickname', self.nickname).replace('$nick', self.nickname)
                    regexp = re.compile(pattern)

                    createdoc(self, func)
                    
                    self.plugins_regex[func.name] = regexp
    
                elif isinstance(func.rule, (tuple, list)):
                    commands = func.rule
                    createdoc(self, func, commands)
                    
                    for command in commands:
                        self.plugin_aliases[command] = func.name               
     
        if not function:
            name = os.path.basename(filename)[:-3]
            plugin = imp.load_source(name, filename)
            if hasattr(plugin, 'setup'): 
               plugin.setup(self)
            for name, func in vars(plugin).iteritems():
                handlefunc(func)
            return plugin
        else:
            handlefunc(function)
            return function

    def nickChanged(self, nick):
        """Called when my nick has been changed.
        """
        self.nickname = nick
        for funcname in self.plugins_nicktriggered:
            if funcname in self.plugins:
                del self.plugins[funcname]
                
            if funcname in self.plugins_regex:
                del self.plugins_regex[funcname]
                
            if funcname in self.doc:
                del self.doc[funcname]
                
            self.loadPlugin(filename=None, function = self.plugins_nicktriggered[funcname])

    def rehash(self):
        """Reload the config file and plugins for this network.
        If the current network has been removed or renamed only global settings
        from the config file will be reloaded.
        """

        self._print('Reloading configuration...')
        config_name = os.path.join(sys.path[0], 'config.py')
        if not os.path.isfile(config_name):
            self._print('Error: Unable to rehash, no config(.py) file found.', 'err')
            return False
    
        config = imp.load_source('config', config_name)
        config = config.__dict__
        serverconfig = config_defaults.copy()
        
        for setting in config:
            if not setting.startswith('__'):
                serverconfig[setting] = config[setting]
        
        if 'networks' in config:
            if self.config['network'] in config['networks']:
                for setting in config['networks'][self.config['network']]:
                    serverconfig[setting] = config['networks'][self.config['network']][setting]
        serverconfig['activeserver'] = self.config['activeserver']
        serverconfig['network'] = self.config['network']
        serverconfig['logevents'] = [s.upper() for s in serverconfig['logevents']]
        if isinstance(serverconfig['nick'], (list, tuple)):
            newnick = serverconfig['nick'][0]
            self.nickbucket = serverconfig['nick'][1:]
        else:
            newnick = serverconfig['nick']
                                   
        if not self.nickname == newnick:
            self.setNick(newnick)

        self.username = self.config.get('user', self.nickname)
        self.realname = self.config.get('name', self.nickname)

        added_settings = [(x, serverconfig[x]) for x in serverconfig if not x in self.config]
        removed_settings = [x for x in self.config if not x in serverconfig]
        changed_settings = [(x, self.config[x], serverconfig[x]) for x in serverconfig if (x in self.config) and (not serverconfig.get(x) == self.config.get(x)) and (not x == 'networks')]

        self.config = serverconfig
        

        oldplugins = self.plugins.keys()
        self.loadPlugins()
        newplugins = self.plugins.keys()
        removed_plugins = [x for x in oldplugins if x not in newplugins]
        added_plugins = [x for x in newplugins if x not in oldplugins]
        
        if added_settings:
            self._print('Added %s new settings:' % len(added_settings))
            for setting in added_settings:
                self._print(" + '%s': %s" % setting)

        if removed_settings:
            self._print('Removed %s settings:' % len(removed_settings))
            for setting in removed_settings:
                self._print(" - '%s'" % setting)

        if changed_settings:
            self._print('Changed %s settings:' % len(changed_settings))
            for setting in changed_settings:
                self._print(" * '%s': %s -> %s" % setting)
        
        if added_plugins:
            self._print('Loaded %s new plugins:' % len(added_plugins))
            self._print(", ".join(added_plugins))

        if removed_plugins:
            self._print('Removed %s plugins:' % len(removed_plugins))
            self._print(", ".join(removed_plugins))

        return {'plugins': {'removed': removed_plugins,
                            'added': added_plugins
                            },
                'settings': {'removed': removed_settings,
                             'added': added_settings,
                             'changed': changed_settings
                             }
                }
        
    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self._print("Disconnected at %s" % time.asctime(time.localtime(time.time())))

    def disconnect(self, reason = 'leaving'):
        self.config['reconnect'] = False
        self.sendLine('QUIT :%s' % reason)
        
    def connect(self):
        self.config['reconnect'] = 10
        self.transport.connector.connect()

    def jump(self, msg='Changing servers'):
        self.sendLine('QUIT :%s' % msg)
        
    def modeChanged(self, user, channel, set, modes, args):
        """Called when users or channel's modes are changed."""
        
        # If voice/op was added or removed, args is a tuple containing the
        # affected nickname(s)
        modedict = {"v": "+", #voice
                    "o": "@", #op
                    "h": "%", #halfop (used by Unreal)
                    "a": "&", #admin (used by Unreal)
                    "q": "~", #owner (used by Unreal)
                    "!": "!"  #service (used by KineIRCD)
                    }
        if args and channel in self.chanlist.channels:
            for user, mode in zip(args,list(modes)):
                if mode not in modedict.keys():
                    continue
                user = user.lower()
                
                if user in self.chanlist[channel]['users']:
                    currentmode = self.chanlist[channel]['users'][user]["mode"]
                    
                    if set:
                        if modedict[mode] not in currentmode:
                            currentmode += modedict[mode]
                    else:
                        currentmode = currentmode.replace(modedict[mode],"")

                    self.chanlist[channel]['users'][user]["mode"] = currentmode

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        channels = self.config.get('channels', [])
        for chan in channels:
            self.join(chan)

    def irc_ERR_ERRONEUSNICKNAME(self, prefix, params):
        """Called when we try to register an invalid nickname."""
        self.irc_ERR_NICKNAMEINUSE(prefix, params)
        
    def irc_ERR_NICKNAMEINUSE(self, prefix, params):
        """Called when we try to register an invalid nickname."""
        if len(self.nickbucket) > 0:
            newnick = self.nickbucket.pop(0)
        else:
            newnick = self.nickname+'_'
        self._print('Error using %s as nickname. (%s)' % (params[1], params[2]))
        self._print('Trying %s...' % newnick)
        self.nickChanged(newnick)
        self.register(newnick)
        

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self._print("Joined %s" % channel)

    def toUnicode(self, line, enc=None):
        if isinstance(line, str):
            done = False
            if isinstance(enc, str):
                try:
                    line = line.decode(enc)
                    done = True
                except:
                    pass
            if not done:            
                try:
                    line = line.decode('utf-8')
                except UnicodeDecodeError: 
                    try:
                        line = line.decode('iso-8859-1')
                    except UnicodeDecodeError: 
                        try:
                            line = line.decode('cp1252')
                        except UnicodeDecodeError:
                            line = line.decode('utf-8', 'ignore')
        elif isinstance(line, unicode):
            pass
        else:
            line = repr(line)
        return line

    def msg(self, receiver, message):

        # "It's easier to ask forgiveness than it is to get permission"
        # ...meaning that we force the message into a string!
        message = self.toUnicode(message)

        lines = message.split("\n")
        for line in lines:
            self.logger.log(self.me, 'PRIVMSG', [receiver], line)
            self.sendLine("PRIVMSG %s :%s" % (receiver, line))

    def notice(self, receiver, message):
        message = self.toUnicode(message)
        lines = message.split("\n")
        for line in lines:
            self.logger.log(self.me, 'NOTICE', [receiver], line)
            self.sendLine("NOTICE %s :%s" % (receiver, line))

    def sendLine(self, line):
        if self.encoding is not None:
            if isinstance(line, unicode):
                line = line.encode(self.encoding)
        self.transport.write("%s%s%s" % (line, chr(015), chr(012)))

    def lineReceived(self, line):
        self.lastmsg = time.mktime(time.gmtime())
        line = lowDequote(line)
        line = self.toUnicode(line)
        try:
            prefix, command, params, text = self.parsemsg(line)
            if numeric_to_symbolic.has_key(command):
                command = numeric_to_symbolic[command]
            self.handleCommand(command, prefix, params, text, line)
        except Exception, e:
            self._print("Error: %s" % e, 'err')
            print traceback.format_exc()


    def handleCommand(self, command, prefix, params, text, line):
        """Determine the function to call for the given command and call
        it with the given arguments."""

        method = getattr(self, "irc_%s" % command, None)
        if method is not None:
            try:
                method(prefix or '', text and params+[text] or params)
            except:
                pass

        command = (symbolic_to_numeric.get(command, command), command)

        self.logger.log(prefix, command, params, text) # Needs to be called before _handleChange
        
        if command[0].upper() in ("JOIN", "331", "332", "333", "352", "353", "KICK", "PART", "QUIT", "NICK", "TOPIC"):
            self.chanlist.handleChange(prefix, command, params, text)
        if command[0] == "005":
            self.sendLine('PROTOCTL NAMESX')
            
        if not text:
            return
        
        if text.startswith(self.config["prefix"]):
            splitline = text[1:].split(" ", 1)
            cmd = splitline[0]

            
            if len(splitline) == 1:
                args = None
            else:
                args = splitline[1:]
            
            
            if cmd in self.plugin_aliases:
                func = self.plugins[self.plugin_aliases[cmd]]
                
                if not func.event in command:
                    return

                input = CommandInput(self, prefix, command, params, text, None, line, func.name)
                bot = QuickReplyWrapper(self, input)
                targs = (func, bot, input)
                t = threading.Thread(target=self.runPlugin, args=targs)
                t.start()
                return
        
        for name, regexp in self.plugins_regex.iteritems():
            match = regexp.match(text)
            if match:
                func = self.plugins[name]
                
                input = CommandInput(self, prefix, command, params, text, match, line, func.name)
                bot = QuickReplyWrapper(self, input)
                targs = (func, bot, input)
                t = threading.Thread(target=self.runPlugin, args=targs)
                t.start()
       

    def runPlugin(self, func, bot, input):
        if hasattr(func, 'usage'):
            if input.args.split(' ',1)[0] in ('-h', '--help'):
                if func.name in bot.doc:
                    for e in bot.doc[func.name]:
                        if e:
                            bot.msg(input.sender, e)
                    return

        try:
            func(bot, input)
        except self.BadInputError, e:
            if input.sender:
                if e.value:
                    self.msg(input.sender, "\x02Error:\x02 %s" % e.value)
                if self.doc[func.__name__][1]:
                    self.msg(input.sender, self.doc[func.__name__][1])
                else:
                    self.msg(input.sender, 'Use %shelp %s for more info on how to use this command.'
                             % (self.config.get('prefix',''), func.__name__))
        except Exception, e:
            if self.config.get('chandebug', True) and input.sender:
                try:  
                    import traceback
                    trace = traceback.format_exc()
                    print trace
                    lines = list(reversed(trace.splitlines()))
           
                    report = [lines[0].strip()]
                    for line in lines: 
                        line = line.strip()
                        if line.startswith('File "'): 
                           report.append(line[0].lower() + line[1:])
                           break
                    else:
                        report.append('source unknown')
                    self.msg(input.sender, report[0] + ' (' + report[1] + ')')
                except Exception, e:
                    self.msg("Got an error: %s" % e)

    def ctcpQuery_VERSION(self, user, channel, data):
        if self.config.get('versionreply', None):
            nick = user.split("!",1)[0]
            self.ctcpMakeReply(nick, [('VERSION', '%s' % self.config['versionreply'])])
            
    def localtime(self):
        if timezone and self.config['timezone']:
            try:
                return datetime.datetime(*timezone(self.config['timezone']).fromutc(datetime.datetime.utcnow()).timetuple()[:6])
            except KeyError:
                pass
        return datetime.datetime.now()


class CommandInput(object):

    def __init__(self, bot, source, event, params, text, match, line, funcname):
        self.nick, self.user, self.host = sourcesplit(source or '')
        self.line = line
        self.funcname = funcname
        self.event = event
        
        if match: # plugin uses regex
            self.match = match
            self.group = match.group
            self.groups = match.groups
            self.command = self.args = text
        else: # plugin uses command list
            self.command = funcname
            self.args = text.split(" ",1)[1] if text.strip().count(" ") > 0 else ""
            
            self.group = lambda i: self.args if i == 2 else text # placeholder until plugins are ported
            
        self.params = params
        if len(params) > 0: 
            self.sender = params[0]
        else:
            self.sender = None

        mappings = {bot.nickname: self.nick, None: None}
        self.sender = mappings.get(self.sender, self.sender)
        self.channel = self.sender
        self._bot = bot

    def isowner(self, *args):
        if not 'ownermask' in self._bot.config:
            return False
        if re.search(self._bot.config['ownermask'], self.nick+'!'+self.user+'@'+self.host, re.IGNORECASE):
            return True
        return False
    
    def isprivate(self):
        """Returns False if the message was sent to a channel and True if
        the message was sent directly to the bot."""
        if self.sender == self.nick:
            return True
        return False

            
class QuickReplyWrapper(object): 

    def __init__(self, bot, input): 
        self.bot = bot
        self.input = input

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            return getattr(object.__getattribute__(self, 'bot'), attr)
        
    def reply(self, msg):
        if self.input.sender:
            self.bot.msg(self.input.sender, self.input.nick + ': ' + msg)
    
    def say(self, msg):
        if self.input.sender:
            self.bot.msg(self.input.sender, msg)
            
    def OptionParser(self):
        return self.ModOptionParser(self.bot, self.input)
        
    class ModOptionParser(optparse.OptionParser):
        def __init__(self, bot, input):
            self.bot = bot
            self.input = input
            optparse.OptionParser.__init__(self, add_help_option=False)

        def error(self, msg):
            raise self.bot.BadInputError(msg)
               
                
class ChanList(object):

    def __init__(self, bot):
        self.channels = {}
        self.bot = bot
        
    def __getitem__(self, attr, default=None):
        return self.channels[attr]
        
    def handleChange(self, prefix, command, params, text):
        command = command[0].lower()
        nick, user, host = sourcesplit(prefix or '')
        chan = text or params[0]
        chan = chan.lower()
        
        #JOIN
        if command == "join":
            #Clear the channels userlist and issue a who command when the bot joins a chan
            if nick == self.bot.nickname:
                self.channels[chan] = { 'users': {}, 'topic': [None, None, None], 'created': None, 'modes': None }
                self.bot.sendLine('MODE %s' % chan)
                self.bot.sendLine('WHO %s' % chan)
                self.bot.sendLine('NAMES %s' % chan)
            self.channels[chan]['users'][nick.lower()] = {'nick': nick, 'user': user, 'host': host, 'mode': None}

        #RPL_WHOREPLY
        elif command == "352":
            chan = params[1].lower()
            nick = params[5]
            user = params[2]
            host = params[3]
            if not chan in self.channels:
                self.channels[chan] = { 'users': {}, 'topic': [None, None, None], 'created': None, 'modes': None }
            self.channels[chan]['users'][nick.lower()] = {'nick': nick, 'user': user, 'host': host, 'mode': None}
            if nick == self.bot.nickname:
                self.bot.me = '%s!%s@%s' % (nick, user, host)
            
        #RPL_NAMREPLY
        elif command == "353":
            chan = params[2].lower()
            nicks = text.lower().split()
            if chan in self.channels:
                exp = re.compile(r'(?P<mode>[~%&@+]*)(?P<nick>[^~%&@+]*)')
                for nick in nicks:
                    m = exp.match(nick)
                    if m.group('nick') in self.channels[chan]:
                        self.channels[chan]['users'][m.group('nick')]['mode'] = m.group('mode')

        #KICK
        elif command == "kick":
            chan = params[0].lower()
            nick = params[1].lower()
            if chan in self.channels:
                if nick == self.bot.nickname.lower():
                    #Remove channel from userlist when the bot is kicked from the channel.
                    del self.self.channels[chan]
                elif nick in self.channels[chan]['users']:
                    del self.channels[chan]['users'][nick]

        #PART
        elif command == "part":
            chan = params[0].lower()
            nick = nick.lower()
            if chan in self.channels:
                if nick == self.bot.nickname.lower():
                    #Remove channel from userlist when the bot parts a channel
                    del self.self.channels[chan]
                elif nick in self.channels[chan]['users']:
                    del self.channels[chan]['users'][nick]                    

        #QUIT
        elif command == "quit":
            nick = nick.lower()
            for chan in self.channels:
                if nick in self.channels[chan]['users']:
                    del self.channels[chan]['users'][nick]
                
        #NICK
        elif command == "nick":
            nick = nick.lower()
            newnick = params[0]
            for chan in self.channels:
                if nick in self.channels[chan]['users']:
                    self.channels[chan]['users'][newnick.lower()] = self.channels[chan]['users'][nick]
                    self.channels[chan]['users'][newnick.lower()]['nick'] = newnick
                    if nick != newnick.lower():
                        del self.channels[chan]['users'][nick]

        #RPL_NOTOPIC
        elif command == "331":
            chan = params[1].lower()
            self.channels[chan]['topic'] = [None, None, None]

        #RPL_TOPIC
        elif command == "332":
            chan = params[1].lower()
            self.channels[chan]['topic'][0] = text

        #RPL_TOPIC_SETBY
        elif command == "333":
            chan = params[1].lower()
            self.channels[chan]['topic'][1] = params[2]
            try:
                self.channels[chan]['topic'][2] = datetime.datetime.fromtimestamp(int(params[3]))
            except (SyntaxError, ValueError, TypeError):
                pass

        #TOPIC
        elif command == "topic":
            chan = params[0].lower()
            self.channels[chan]['topic'] = [text, prefix, datetime.datetime.now()]

        #RPL_CHANNELMODEIS
        elif command == "324":
            chan = params[0].lower()
            self.channels[chan]['modes'] = params[2:]

        #RPL_CHANNEL_CREATED
        elif command == "329":
            chan = params[0].lower()
            try:
                self.channels[chan]['created'] = datetime.datetime.fromtimestamp(int(params[2]))
            except (SyntaxError, ValueError, TypeError):
                pass


    #Is <nick> on <chan>?
    def ison(self, nick, chan):
        nick = nick.lower()
        chan = chan.lower()
        if chan in self.channels:
            if nick in self.channels[chan]['users']:
                return True
        return False
    
    #Returns <nick>'s attributes on <chan>
    #Valid attributes are: 'nick', 'user', 'host', 'mode' (or 'all' for a dict with all attributes)
    def uinfo(self, nick, chan, attr):
        nick = nick.lower()
        chan = chan.lower()
        if self.ison(nick, chan):
            if attr == 'all':
                return self.channels[chan]['users'][nick]
            elif attr in ('nick', 'user', 'host', 'mode'):
                return self.channels[chan]['users'][nick][attr]
        return None
    
    #Returns <nick>'s modes on <chan>
    def getmode(self, nick, chan):
        nick = nick.lower()
        chan = chan.lower()
        if self.ison(nick, chan):
            return self.channels[chan]['users'][nick]['mode']
        return None
    
    #Is <nick> op'd on <chan>?
    def isop(self, nick, chan):
        if self.getmode(nick, chan):
            if '@' in self.getmode(nick, chan):
                return True
        return False
    
    #Is <nick> voiced on <chan>?
    def isvoice(self, nick, chan):
        if self.getmode(nick, chan):
            if '+' in self.getmode(nick, chan):
                return True
        return False
    
    #Is <nick> a regular user on <chan>?
    def isreg(self, nick, chan):
        if self.getmode(nick, chan) == None:
            return True
        return False
    
    #Return a list of channels <nick> is on
    def chans(self, nick):
        nick = nick.lower()
        return [chan for chan in self.channels if nick in
                self.channels[chan]['users']]

class RCursor(object):
    """A reconnecting cursor for MySQLdb."""
    def __init__(self, connection): 
        self.connection = connection
        self.cursor = connection.cursor()

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            return getattr(object.__getattribute__(self, 'cursor'), attr)
        
    def execute(self, sql, args=None):
        try:
            return self.cursor.execute(sql, args)
        except (AttributeError, MySQLdb.OperationalError), e:
            if e.args[0] == 2006: #MySQL server has gone away
                self.connection.ping(True) # Reconnect
                self.cursor = self.connection.cursor()
                return self.cursor.execute(sql, args)
            raise
    
    def executemany(self, sql, args=None):
        try:
            return self.cursor.executemany(sql, args)
        except (AttributeError, MySQLdb.OperationalError), e:
            if e.args[0] == 2006: #MySQL server has gone away
                self.connection.ping(True) # Reconnect
                self.cursor = self.connection.cursor()
                return self.cursor.executemany(sql, args)
            raise

class IRCLogger(object):

    def __init__(self, bot, logpath):
        if logpath == None:
            self.enabled = False
            return
        else:
            self.enabled = True
        self.bot = bot
        self.logdir = "logs"
        self.lastmsg = {}
        
        if logpath.lower().startswith("sqlite") or ("." in logpath and logpath.lower().rsplit(".",1)[1] in ["s3db", "db", "sqlite", "sqlite3"]):
            logtype = "sqlite"

        elif logpath.lower().startswith("mysql"):
            logtype = "mysql"

        else:
            logtype = 'text'
            
        if logtype in ['sqlite', 'mysql']:
            if not json:
                self.bot._print("WARNING! No json library found, logging to plaintext.", "err")
                logtype = "text"
                logpath = "logs"

        if logtype == "mysql":
            if not MySQLdb:
                self.bot._print("WARNING! No MySQLdb library found, logging to plaintext.", "err")
                logtype = "text"
                logpath = "logs"

            #mysql://user:password@host:port/db?params
            logpath = logpath.rsplit("?", 1)[0] #Remove params
            r = re.compile(r"mysql://([^:@]+):([^@]+)@([^:]+)(?::(\d+))?/([^/]+)")
            m = r.match(logpath)
            if not m:
                self.bot._print("WARNING! MySQL connection string is invalid, logging to plaintext.", "err")
                logtype = "text"
                logpath = "logs"
            else:
                self.mysql_user, self.mysql_pass, self.mysql_host, self.mysql_port, self.mysql_db = m.groups()
                try:
                    conn = MySQLdb.connect(host = self.mysql_host, user = self.mysql_user,
                                         passwd = self.mysql_pass, db = self.mysql_db,
                                         port = self.mysql_port or 3306, charset = 'utf8')
                except MySQLdb.Error, e:
                    self.bot._print("WARNING! Error connectiong to the MySQL database: %s. Logging to plaintext." % e, "err")
                    logtype = "text"
                    logpath = "logs"
                else:
                    c = RCursor(conn) #conn.cursor()
        
                    # Create a channel index table
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore") #Ignore table exists warnings from MySQL.
                        c.execute("""CREATE TABLE IF NOT EXISTS spiffy_channels (
                                        `hash` char(39) CHARSET utf8 COLLATE utf8_general_ci,
                                        plaintext text CHARSET utf8 COLLATE utf8_general_ci,
                                        unique `idx_spiffy_channels` (`hash`)
                                        ) charset=utf8 collate=utf8_general_ci""")
                    self.mysql_conn = conn
                    self.mysql_curs = c
                    
                    self._log = self._mysqllog

        
        if logtype == "sqlite":
            # logpath is either "sqlite://path/to/db.ext", "logs/db.ext", "/path/to/db.ext" or "C:\path\to\db.ext"
            self.logdir = os.path.abspath(re.sub("sqlite3?://", "", logpath))
                        
            if not os.path.basename(self.logdir):
                self.logdir = os.path.join(self.logdir, "logs.s3db")

            self.bot._print("Logging to SQLite database at %s" % self.logdir)
            
            conn = sqlite3.connect(self.logdir, detect_types = sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # check if the channel index exists in the database
            c.execute("select tbl_name from sqlite_master where tbl_name = 'spiffy_channels'")
            if not c.fetchone():
                c.execute("CREATE TABLE spiffy_channels (hash TEXT, plaintext TEXT)")
                self.bot._print("Created channel index table 'spiffy_channels' in SQLite database")
            c.close()
            conn.commit()
            conn.close()
            
            self._log = self._sqlitelog
                        
        elif logtype == "text":
            # logpath will be either an absolute path ("/path/to/logdir/", "C:\logs\", etc)
            # or a relative path (e.g. "logs/", which would mean a subdir "logs" in the
            # current working directory, or even "../../logs").
            self.logdir = os.path.abspath(logpath)
            
            if not os.path.exists(self.logdir):
                os.mkdir(self.logdir)
            self._log = self._plaintextlog

    def log(self, prefix, command, params, text):
        if not self.enabled:
            return
        
        command = command[0].upper()
        if not command in self.bot.config['logevents']:
            return

        self._log(prefix, command, params, text)
                                
                                
    def parsetotext(self, prefix, command, params, text, timestamp = None):
        if not timestamp:
            timestamp = time.strftime("[%H:%M:%S]")
                        
        nick, user, host = sourcesplit(prefix)
                
        args = (timestamp, nick, text)
        if command == "PRIVMSG":
            return (params[0].lower(), nick, "%s <%s> %s\r\n" % args)
        elif command == "PART":
            return (params[0].lower(), nick, "%s * %s %s\r\n" % (timestamp,nick, "(%s@%s) has left %s%s" % (user, host, params[0].lower(), text and ' ('+text+')' or '')))
        elif command == "JOIN":
            return (text or params[0].lower(), nick, "%s * %s %s\r\n" % (timestamp, nick, "(%s@%s) has joined %s" % (user, host, text or params[0].lower())))
        elif command == "KICK":
            return (params[0].lower(), nick, "%s * %s was kicked by %s\r\n" % (timestamp, params[1].lower(), "%s (%s)" % (nick, text)))
        elif command == "TOPIC":
            return (params[0].lower(), nick, "%s * %s changes topic to '%s'\r\n" % args)
        elif command == "MODE":
            return (params[0].lower(), nick, "%s * %s sets mode: %s\r\n" % (timestamp, nick, " ".join(params[1:])))
        elif command == "NICK":
            return (None, nick, "%s * %s is now known as %s\r\n" % (timestamp, nick, params[0]))
        elif command == "QUIT":
            return (None, nick, "%s * %s %s\r\n" % (timestamp, nick, "(%s@%s) Quit (%s)" % (user, host, text)))
        elif command == "332":
            return (params[1].lower(), nick, "%s * Topic is '%s'\r\n" % (timestamp, text))
        elif command == "333":
            return (params[1].lower(), nick, "%s * Set by %s on %s\r\n" % (timestamp, params[2], datetime.datetime.fromtimestamp(int(params[3]))))
        
    def _mysqllog(self, prefix, command, params, text):  
        nick, user, host = sourcesplit(prefix)
        if not user:
            return # Don't logg server messages.
        timestamp = datetime.datetime.now()
        
        if command in ["PRIVMSG", "PART", "KICK", "TOPIC", "MODE", "NOTICE"]:
            channels = [params[0].lower()]
        elif command in ["NICK", "QUIT"]:
            channels = self.bot.chanlist.chans(nick)
        elif command in ["332", "333"]:
            channels = [params[1].lower()]
        elif command in ["JOIN"]:
            channels = [text or params[0].lower()]
        else:
            channels = ["#debug"] # fixme

        """conn = MySQLdb.connect(host = self.mysql_host, user = self.mysql_user,
                             passwd = self.mysql_pass, db = self.mysql_db,
                             port = self.mysql_port or 3306, charset = 'utf8')
        c = conn.cursor()"""
        conn = self.mysql_conn
        c = self.mysql_curs

        for channel in channels:            
            if channel.startswith("#"):
                tablename = self.bot.config["network"] + u"." + channel
            else:
                tablename = self.bot.config["network"] + u"." + nick.lower()

            hashname = "spiffy_" + hashlib.md5(tablename.encode("utf-8")).hexdigest()

            # check if a table exists for the current channel. sqlite_master contains
            # info about all the tables in a particular SQLite database
            if nick.lower() == self.bot.nickname or not channel.startswith('#'):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")                    
                    c.execute("""CREATE TABLE IF NOT EXISTS %s (
                                    `ts` datetime,
                                    `prefix` varchar(512) CHARSET utf8 COLLATE utf8_general_ci,
                                    `nick` varchar(50) CHARSET utf8 COLLATE utf8_general_ci,
                                    `command` varchar(7) CHARSET utf8 COLLATE utf8_general_ci,
                                    `params` varchar(512) CHARSET utf8 COLLATE utf8_general_ci,
                                    `text` varchar(512) CHARSET utf8 COLLATE utf8_general_ci,
                                    KEY `nick` (`nick`,`command`) 
                                    ) charset=utf8 collate=utf8_general_ci;""" % hashname)
                c.execute("INSERT INTO spiffy_channels (hash, plaintext) VALUES (%s, %s) ON DUPLICATE KEY UPDATE hash=hash", (hashname, tablename))

            # table has been created if it didn't already exist, so we can do our insertions
            c.execute("INSERT INTO %s" % hashname + " (ts, prefix, nick, command, params, text) VALUES (%s, %s, %s, %s, %s, %s)", (timestamp, prefix, nick, command, json.dumps(params), text))


        #c.close()
        conn.commit()
        #conn.close()

    def _sqlitelog(self, prefix, command, params, text):  
        nick, user, host = sourcesplit(prefix)
        if not user:
            return # Don't logg server messages.
        timestamp = datetime.datetime.now()
        
        if command in ["PRIVMSG", "PART", "KICK", "TOPIC", "MODE", "NOTICE"]:
            channels = [params[0].lower()]
        elif command in ["NICK", "QUIT"]:
            channels = self.bot.chanlist.chans(nick)
        elif command in ["332", "333"]:
            channels = [params[1].lower()]
        elif command in ["JOIN"]:
            channels = [text or params[0].lower()]
        else:
            channels = ["#debug"] # fixme

        conn = sqlite3.connect(self.logdir, detect_types = sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        for channel in channels:            
            if channel.startswith("#"):
                tablename = self.bot.config["network"] + u"." + channel
            else:
                tablename = self.bot.config["network"] + u"." + nick.lower()

            # SQLite won't accept table names that start in 0-9, so we add spiffy_ in front
            hashname = "spiffy_" + hashlib.md5(tablename.encode("utf-8")).hexdigest()

            # check if a table exists for the current channel. sqlite_master contains
            # info about all the tables in a particular SQLite database
            if nick.lower() == self.bot.nickname or not channel.startswith('#'):
                c.execute("select tbl_name from sqlite_master where tbl_name = ?", (hashname,))
                if not c.fetchone():
                    c.execute("CREATE TABLE %s (ts TIMESTAMP, prefix TEXT, nick TEXT, command TEXT, params TEXT, text TEXT)" % hashname)
                    c.execute("CREATE INDEX idx_%s ON %s (command DESC, nick DESC, prefix DESC)" % (hashname, hashname))
                    self.bot._print("Created table %s (%s) in SQLite database" % (hashname, tablename))
                    c.execute("INSERT INTO spiffy_channels (hash, plaintext) VALUES (?,?)", (hashname, tablename))

            # table has been created if it didn't already exist, so we can do our insertions
            query = "INSERT INTO %s (ts, prefix, nick, command, params, text) VALUES (?,?,?,?,?,?)"
            c.execute(query % hashname, (timestamp, prefix, nick, command, json.dumps(params), text))


        c.close()
        conn.commit()
        conn.close()
                        
    def _plaintextlog(self, prefix, command, params, text):
        timestamp = time.strftime("[%H:%M:%S]")
        logs = getattr(self.bot, "logs", {})
        
        logstrings = self.parsetotext(prefix, command, params, text, timestamp)
        if not logstrings:
            return
        
        chan, sender, logstring = logstrings

        if command in ["NICK","QUIT"]:
            channels = self.bot.chanlist.chans(sender)
        else:
            channels = [chan]

        for channel in channels:
            if channel.startswith("#"):
                logpath = os.path.join(self.logdir,self.bot.config["network"] + "." + channel + ".log")
            else:
                logpath = os.path.join(self.logdir,self.bot.config["network"] + "." + sender + ".log")

            if channel not in logs:
                # nothing has been logged from this chan yet, must open file
                self.lastmsg[channel] = datetime.date.today()
                f = codecs.open(logpath,"a","utf-8")
                f.write("\r\nSession Start: %s\r\n" % time.strftime("%a %b %d %H:%M:%S %Y"))
                f.write("Session Ident: %s\r\n" % channel)
                f.write("%s * Now talking in %s\r\n" % (timestamp, channel))
               
                logs[channel] = f

            if datetime.date.today() > self.lastmsg[channel]:
                self.lastmsg[channel] = datetime.date.today()
                logs[channel].write("# Start of new day, %s.\r\n" % self.lastmsg[channel].isoformat())
                            
            logs[channel].write(logstring)
            logs[channel].flush()
                        
        self.bot.logs = logs


class BotFactory(protocol.ClientFactory):

    # the class of the protocol to build when new connection is made
    protocol = Bot

    def __init__(self, config, connections):
        self.config = config
        self.connections = connections

    def _print(self, text, output = 'out'):
        if self.config.get('verbose', True):
            timestamp = time.strftime("%H:%M:%S")
            if len(self.config['networks']) > 1:
                prefix = "[%s][%s] " % (self.config['network'], timestamp)
            else:
                prefix = "[%s] " % timestamp
            if output == 'err':
                output = sys.stderr
            else:
                output = sys.stdout
            
            print >> output, prefix+text

    def clientConnectionLost(self, connector, reason):
        """Attempt to connect to the next server or reconnect to the current
        if we get disconnected."""
        self._print('Disconnected from %s (%s:%s).' % (self.config.get('network'), self.config['activeserver'][0], self.config['activeserver'][1]))
        if not self.config.get('reconnect') == False:
            server = self.config.get('host')
            if isinstance(server, (tuple, list)):
                self.config['host'].append(self.config['host'].pop(0))
                server = self.config['host'][0]
                port = 6667
                if ':' in server:
                    server, port = server.split(':')
                    #TODO: Make it possible to reconnect to both SSL and regular servers.
                    #Probably requires a new connector object.
                    if port.startswith('+'):
                        port = port[1:]
                    port = int(port)

                self.config['activeserver'] = (server, port)
                connector.host = server
                connector.port = port

            try:
                rtime = int(self.config.get('reconnect'))
            except (ValueError, TypeError), e:
                rtime = 10
            self._print('Reconnecting in %s seconds...' % rtime)
            time.sleep(rtime)
            
            connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.clientConnectionLost(connector, reason)
        
