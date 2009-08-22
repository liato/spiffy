import codecs
import datetime
import hashlib
import imp
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

def parsemsg(s):
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


def sourcesplit(source):
    """Split nick!user@host and return a 3-value tuple."""
    r = re.compile(r'([^!]*)!?([^@]*)@?(.*)')
    m = r.match(source)
    return m.groups()


class Bot(irc.IRCClient):
    
    class BadInputError(Exception):
        def __str__(self):
            return repr(self)

    def connectionMade(self):
        self._print = self.factory._print
        self.config = self.factory.config
        self.connections = self.factory.connections
        self.connections[self.config['network']] = self
        self.nickname = self.config.get('nick', 'spiffy')
        self.username = self.config.get('user', self.nickname)
        self.realname = self.config.get('name', self.nickname)
        self.config['logevents'] = [s.upper() for s in self.config['logevents']]
        self.logger = IRCLogger(self, self.config.get('logpath'))
        self.userlist = UserList(self)
        self.encoding = 'utf-8'
        self.split = split #Make the split function accessible to modules
        
        
        self.loadModules()
        irc.IRCClient.connectionMade(self)
        self._print("Connected to %s:%s at %s" % (self.transport.connector.host, self.transport.connector.port, time.asctime(time.localtime(time.time()))))

        
    def loadModules(self):
        self._print("Loading modules...")
        self.modules = {} #Modules loaded from the modules directory.
        self.doc = {} #Documentation for modules.
        self.aliases = {} #Aliases for module commands.
        modules = []
        if os.path.exists(os.path.join(sys.path[0], 'modules')):
            filenames = []
            for fn in os.listdir(os.path.join(sys.path[0], 'modules')): 
                if fn.endswith('.py') and not fn.startswith('_'): 
                    filenames.append(os.path.join(sys.path[0], 'modules', fn))
            for filename in filenames:
                name = os.path.basename(filename)[:-3]
                try:
                    self.loadModule(filename)
                except Exception, e: 
                    self._print("Error loading %s: %s (in bot.py)" % (name, e), 'err')
                else:
                    modules.append(name)
        if modules: 
           self._print('Registered modules:', ', '.join(modules))
        else:
            self._print("Warning: Couldn't find any modules. Does /modules exist?", 'err')

    def loadModule(self, filename):

        def bind(self, regexp, func): 
            if func.name in self.modules:
                self.modules[func.name].append((regexp, func))
            else:
                self.modules[func.name] = [(regexp, func)]

        def createdoc(self, func, commands = None):
            pcmd = self.config["prefix"] + func.name # pcmd = prefixed command
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
                self.aliases[command.lower()] = func.name
            if func.name in commands:
                commands.remove(func.name)
            if commands:
                aliases = "\x02Aliases for the %s command:\x02\n  " % func.name
                aliases += ", ".join(commands)
            else:
                aliases = None
            
            self.doc[func.name] = (doc, usage, example, aliases)            
  
        def sub(pattern, self=self): 
            # These replacements have significant order
            pattern = pattern.replace('$nickname', self.nickname)
            return pattern.replace('$nick', r'%s[,:] +' % self.nickname)

        name = os.path.basename(filename)[:-3]
        module = imp.load_source(name, filename)
        if hasattr(module, 'setup'): 
           module.setup(self)
        for name, func in vars(module).iteritems(): 
            if hasattr(func, 'commands') or hasattr(func, 'rule'):
                if not hasattr(func, 'name'): 
                    func.name = func.__name__
                func.name = func.name.lower()
                if func.name in self.modules:
                    del self.modules[func.name]
                
                if not hasattr(func, 'event'):
                    func.event = 'PRIVMSG'
                else:
                    func.event = func.event.upper()
       
                if hasattr(func, 'rule'):
                    # 0) e.g. '(hi|hey) $nick'
                    if isinstance(func.rule, str): 
                        pattern = sub(func.rule)
                        regexp = re.compile(pattern)
                        bind(self, regexp, func)
                        createdoc(self, func)
        
                    elif isinstance(func.rule, tuple): 
                        # 1) e.g. ('$nick', '(.*)')
                        if len(func.rule) == 2 and isinstance(func.rule[0], str): 
                            prefix, pattern = func.rule
                            prefix = sub(prefix)
                            regexp = re.compile(prefix + pattern, re.IGNORECASE)
                            bind(self, regexp, func)
                            createdoc(self, func)
         
                        # 2) e.g. (['p', 'q'], '(.*)')
                        elif len(func.rule) == 2 and isinstance(func.rule[0], list): 
                            prefix = self.config['prefix']
                            commands, pattern = func.rule
                            createdoc(self, func, commands)
                            for command in commands:
                                command = r'(%s)(?: +(?:%s))?$' % (command, pattern)
                                regexp = re.compile(prefix + command, re.IGNORECASE)
                                bind(self, regexp, func)
         
                        # 3) e.g. ('$nick', ['p', 'q'], '(.*)')
                        elif len(func.rule) == 3: 
                            prefix, commands, pattern = func.rule
                            prefix = sub(prefix)
                            createdoc(self, func, commands)
                            for command in commands: 
                                command = r'(%s) +' % command
                                regexp = re.compile(prefix + command + pattern, re.IGNORECASE)
                                bind(self, regexp, func)
       
                if hasattr(func, 'commands'):
                    createdoc(self, func, func.commands)
                    for command in func.commands: 
                        template = r'^%s(%s)(?: +(.*))?$'
                        pattern = template % (self.config['prefix'], command)
                        regexp = re.compile(pattern, re.IGNORECASE)
                        bind(self, regexp, func)
        
        return module
        
    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self._print("Disconnected at %s" % time.asctime(time.localtime(time.time())))

    def disconnect(self, reason = 'leaving'):
        self.config['reconnect'] = False
        self.sendLine('QUIT :%s' % reason)
        
    def connect(self):
        self.config['reconnect'] = 10
        self.transport.connector.connect()

    def jump(self):
        self.sendLine('QUIT :Changing servers')
        
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
        if args and channel in self.userlist.channels:
            for user, mode in zip(args,list(modes)):
                if mode not in modedict.keys():
                    continue
                user = user.lower()
                
                if user in self.userlist[channel]:
                    currentmode = self.userlist[channel][user]["mode"]
                    
                    if set:
                        if modedict[mode] not in currentmode:
                            currentmode += modedict[mode]
                    else:
                        currentmode = currentmode.replace(modedict[mode],"")

                    self.userlist[channel][user]["mode"] = currentmode

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        channels = self.config.get('channels', [])
        for chan in channels:
            self.join(chan)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self._print("Joined %s" % channel)

    def msg(self,receiver,msg):
        lines = msg.split("\n")
        for line in lines:
            self.sendLine("PRIVMSG %s :%s" % (receiver, line))

    def sendLine(self, line):
        if self.encoding is not None:
            if isinstance(line, unicode):
                line = line.encode(self.encoding)
        self.transport.write("%s%s%s" % (line, chr(015), chr(012)))

    def lineReceived(self, line):
        line = lowDequote(line)
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

        try:
            prefix, command, params, text = parsemsg(line)
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
        
        if command[0].upper() in ("JOIN", "352", "353", "KICK", "PART", "QUIT", "NICK"):
            self.userlist._handleChange(prefix, command, params, text)
        if command[0] == "005":
            self.sendLine('PROTOCTL NAMESX') 
            #print self.modules.values()
        #"print line
        #print prefix, command, params, text
        #print "\n"
        
        modules = self.modules.values()
        for module in modules:
            for regexp, func in module:
                if not func.event in command:
                    continue

                match = regexp.match(text)
                if match:
                    input = CommandInput(self, prefix, command, params, text, match, line)
                    bot = QuickReplyWrapper(self, input)
                    targs = (func, bot, input)
                    t = threading.Thread(target=self.runModule, args=targs)
                    t.start()


    def runModule(self, func, bot, input):
        try:
            func(bot, input)
        except self.BadInputError, e:
            if input.sender:
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


class CommandInput(object):

    def __init__(self, bot, source, command, params, text, match, line):
        self.nick, self.user, self.host = sourcesplit(source or '')
        self.line = line
        self.command = command
        self.match = match
        self.group = match.group
        self.groups = match.groups
        self.args = params
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


class UserList(object):

    def __init__(self, bot):
        self.channels = {}
        self.bot = bot
        
    def __getitem__(self, attr, default=None):
        return self.channels[attr]
        
    def _handleChange(self, prefix, command, params, text):
        command = command[0]
        nick, user, host = sourcesplit(prefix or '')
        chan = text or params[0]
        chan = chan.lower()
        
        #JOIN
        if command.lower() == "join":
            #Clear the channels userlist and issue a who command when the bot joins a chan
            if nick == self.bot.nickname:
                self.channels[chan] = {}
                self.bot.sendLine("WHO %s" % chan)
                self.bot.sendLine("NAMES %s" % chan)
            self.channels[chan][nick.lower()] = {'nick': nick, 'user': user, 'host': host, 'mode': None}

        #RPL_WHOREPLY
        elif command == "352":
            chan = params[1].lower()
            nick = params[5]
            user = params[2]
            host = params[3]
            if not chan in self.channels:
                self.channels[chan] = {}
            self.channels[chan][nick.lower()] = {'nick': nick, 'user': user, 'host': host, 'mode': None}
            
        #RPL_NAMREPLY
        elif command == "353":
            chan = params[2].lower()
            nicks = text.lower().split()
            if chan in self.channels:
                exp = re.compile(r'(?P<mode>[~%&@+]*)(?P<nick>[^~%&@+]*)')
                for nick in nicks:
                    m = exp.match(nick)
                    if m.group('nick') in self.channels[chan]:
                        self.channels[chan][m.group('nick')]['mode'] = m.group('mode')

        #KICK
        elif command.lower() == "kick":
            chan = params[0].lower()
            nick = params[1].lower()
            if chan in self.channels:
                if nick == self.bot.nickname.lower():
                    #Remove channel from userlist when the bot is kicked from the channel.
                    del self.self.channels[chan]
                elif nick in self.channels[chan]:
                    del self.channels[chan][nick]

        #PART
        elif command.lower() == "part":
            chan = params[0].lower()
            nick = nick.lower()
            if chan in self.channels:
                if nick == self.bot.nickname.lower():
                    #Remove channel from userlist when the bot is kicked from the channel.
                    del self.self.channels[chan]
                elif nick in self.channels[chan]:
                    del self.channels[chan][nick]                    

        #QUIT
        elif command.lower() == "quit":
            nick = nick.lower()
            for chan in self.channels:
                if nick in self.channels[chan]:
                    del self.channels[chan][nick]
                
        #NICK
        elif command.lower() == "nick":
            nick = nick.lower()
            newnick = params[0]
            for chan in self.channels:
                if nick in self.channels[chan]:
                    self.channels[chan][newnick.lower()] = self.channels[chan][nick]
                    self.channels[chan][newnick.lower()]['nick'] = newnick
                    if nick != newnick.lower():
                        del self.channels[chan][nick] 

    #Is <nick> on <chan>?
    def ison(self, nick, chan):
        nick = nick.lower()
        chan = chan.lower()
        if chan in self.channels:
            if nick in self.channels[chan]:
                return True
        return False
    
    #Returns <nick>'s attributes on <chan>
    #Valid attributes are: 'nick', 'user', 'host', 'mode' (or 'all' for a dict with all attributes)
    def uinfo(self, nick, chan, attr):
        nick = nick.lower()
        chan = chan.lower()
        if self.ison(nick, chan):
            if attr == 'all':
                return self.channels[chan][nick]
            elif attr in ('nick', 'user', 'host', 'mode'):
                return self.channels[chan][nick][attr]
        return None
    
    #Returns <nick>'s modes on <chan>
    def getmode(self, nick, chan):
        nick = nick.lower()
        chan = chan.lower()
        if self.ison(nick, chan):
            return self.channels[chan][nick]['mode']
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
                self.channels[chan]]


class IRCLogger(object):

    def __init__(self, bot, logpath):
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
                    c = conn.cursor()
        
                    # Create a channel index table
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")                    
                        c.execute("""CREATE TABLE IF NOT EXISTS spiffy_channels (
                                        `hash` char(39) CHARSET utf8 COLLATE utf8_general_ci,
                                        plaintext text CHARSET utf8 COLLATE utf8_general_ci,
                                        unique `idx_spiffy_channels` (`hash`)
                                        ) charset=utf8 collate=utf8_general_ci""")
                    c.close()
                    conn.close()
                    
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

        
    def _mysqllog(self, prefix, command, params, text):  
        nick, user, host = sourcesplit(prefix)
        if not user:
            return # Don't logg server messages.
        timestamp = datetime.datetime.now()
        
        if command in ["PRIVMSG", "PART", "KICK", "TOPIC", "MODE", "NOTICE"]:
            channels = [params[0].lower()]
        elif command in ["NICK", "QUIT"]:
            channels = self.bot.userlist.chans(nick)
        elif command in ["JOIN"]:
            channels = [text or params[0].lower()]
        else:
            channels = ["#debug"] # fixme

        conn = MySQLdb.connect(host = self.mysql_host, user = self.mysql_user,
                             passwd = self.mysql_pass, db = self.mysql_db,
                             port = self.mysql_port or 3306, charset = 'utf8')
        c = conn.cursor()

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


        c.close()
        conn.commit()
        conn.close()

    def _sqlitelog(self, prefix, command, params, text):  
        nick, user, host = sourcesplit(prefix)
        if not user:
            return # Don't logg server messages.
        timestamp = datetime.datetime.now()
        
        if command in ["PRIVMSG", "PART", "KICK", "TOPIC", "MODE", "NOTICE"]:
            channels = [params[0].lower()]
        elif command in ["NICK", "QUIT"]:
            channels = self.bot.userlist.chans(nick)
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
            channels = self.bot.userlist.chans(sender)
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
                
                # not sure how to get this info, but it's necessary if we strive for
                # compatibility with the mIRC log format (to allow the use of third
                # party log analyzers for stats and the like)
                f.write("%s * Topic is 'XXXXXXXXXXXX'\r\n" % timestamp)
                f.write("%s * Set by XXXXXXX on XXXXXXX\r\n" % timestamp)
                
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
        """If we get disconnected, reconnect to server."""
        self._print('Disconnected from %s.' % self.config.get('network'))
        if not self.config.get('reconnect') == False:
            activeservernum = self.config.get('activeservernum', -1)
            if activeservernum >= 0:
                activeservernum += 1
                if activeservernum > (len(self.config['host'])-1):
                    activeservernum = 0
                server = self.config['host'][activeservernum]
                port = 6667
                if ':' in server:
                    server, port = server.split(':')
                    port = int(port)
                self.config['activeserver'] = (server, port)
                self.config['activeservernum'] = activeservernum
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
        self._print("Connection failed: %s" % reason, 'err')
        reactor.stop()
