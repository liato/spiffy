import time
import imp
import os
import sys
import re
import threading
import codecs
import datetime

from twisted.words.protocols import irc
from twisted.words.protocols.irc import lowDequote, numeric_to_symbolic, symbolic_to_numeric, split
from twisted.internet import reactor, protocol


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
        self.config = self.factory.config
        self.connections = self.factory.connections
        self.connections[self.config['network']] = self
        self.nickname = self.config.get('nick', 'spiffy')
        self.username = self.config.get('user', self.nickname)
        self.realname = self.config.get('name', self.nickname)
        self.logger = IRCLogger(self, "plaintext")
        self.userlist = UserList(self)
        self.config['logevents'] = [s.upper() for s in self.config['logevents']]
        self.verbose = True
        self.encoding = 'utf-8'
        self.split = split #Make the split function accessible for modules
        
        self.loadModules()
        irc.IRCClient.connectionMade(self)
        print "Connected at %s" % time.asctime(time.localtime(time.time()))

        
    def loadModules(self):
        print "Loading modules..."
        self.modules = {} #Modules loaded from the modules directory.
        self.doc = {} #Documentation for modules.
        self.aliases = {} #Aliases for modules.
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
                    print >> sys.stderr, "Error loading %s: %s (in bot.py)" % (name, e)
                else:
                    modules.append(name)
        if modules: 
           print 'Registered modules:', ', '.join(modules)
        else:
            print >> sys.stderr, "Warning: Couldn't find any modules. Does /modules exist?"

    def loadModule(self, filename):

        def bind(self, regexp, func, commands = None): 
            # register documentation
            pcmd = self.config["prefix"] + func.name # pcmd = prefixed command

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
            #self.modules.setdefault(regexp, []).append(func)
            if func.name in self.modules:
                self.modules[func.name].setdefault(regexp, []).append(func)
            else:
                self.modules[func.name] = {regexp: [func]}
  
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
        
                    elif isinstance(func.rule, tuple): 
                        # 1) e.g. ('$nick', '(.*)')
                        if len(func.rule) == 2 and isinstance(func.rule[0], str): 
                            prefix, pattern = func.rule
                            prefix = sub(prefix)
                            regexp = re.compile(prefix + pattern, re.IGNORECASE)
                            bind(self, regexp, func)
         
                        # 2) e.g. (['p', 'q'], '(.*)')
                        elif len(func.rule) == 2 and isinstance(func.rule[0], list): 
                            prefix = self.config['prefix']
                            commands, pattern = func.rule
                            for command in commands:
                                command = r'(%s)(?: +(?:%s))?$' % (command, pattern)
                                regexp = re.compile(prefix + command, re.IGNORECASE)
                                bind(self, regexp, func, commands)
         
                        # 3) e.g. ('$nick', ['p', 'q'], '(.*)')
                        elif len(func.rule) == 3: 
                            prefix, commands, pattern = func.rule
                            prefix = sub(prefix)
                            for command in commands: 
                                command = r'(%s) +' % command
                                regexp = re.compile(prefix + command + pattern, re.IGNORECASE)
                                bind(self, regexp, func, commands)
       
                if hasattr(func, 'commands'): 
                    for command in func.commands: 
                        template = r'^%s(%s)(?: +(.*))?$'
                        pattern = template % (self.config['prefix'], command)
                        regexp = re.compile(pattern, re.IGNORECASE)
                        bind(self, regexp, func, func.commands)
        
        return module
        
    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        print "Disconnected at %s" % time.asctime(time.localtime(time.time()))

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
        print "[I have joined %s]" % channel

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
            print "Error: %s" % e

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
        if command[0].upper() in ("JOIN", "352", "353", "KICK", "PART", "QUIT", "NICK"):
            self.userlist._handleChange(prefix, command, params, text)
        if command[0] == "005":
            self.sendLine('PROTOCTL NAMESX') 
            #print self.modules.values()
        #"print line
        #print prefix, command, params, text
        #print "\n"

        self.handleLogging(prefix, command, params, text)
        
        modules = self.modules.values()
        for module in modules:
            for regexp, funcs in module.items():
                for func in funcs:
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
            

    def handleLogging(self, prefix, command, params, text):
        if not command[0].upper() in self.config['logevents']:
            return
        if command[0].upper() == "PRIVMSG":
            self.logger.log(sourcesplit(prefix)[0], params[0].lower(), "PRIVMSG", text)
        elif command[0].upper() == "MODE":
            self.logger.log(sourcesplit(prefix)[0], params[0].lower(), "MODE", " ".join(params[1:]))

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
            chan = input.rawline.split(' ')[2].lower()
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

    def __init__(self, bot, logtype, logdir = None):
        self.bot = bot
        self.logdir = logdir or "logs"
        self.lastmsg = {}        
        if logtype == "whatever, sqlite3/mysql in the future":
            pass
        elif logtype == "plaintext":
            self.log = self.plaintextlog
            if not os.path.exists(self.logdir):
                os.mkdir(self.logdir)

    def plaintextlog(self, sender, channel, event, text):
        logpath = os.path.join(self.logdir,self.bot.config["network"] + "." + channel + ".log")
        timestamp = time.strftime("[%H:%M:%S]")

        logs = getattr(self.bot, "logs", {})  
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
        if event.upper() == "PRIVMSG":
            logs[channel].write("%s <%s> %s\r\n" % (timestamp, sender, text))
        elif event.upper() == "MODE":
            logs[channel].write("%s * %s sets mode: %s\r\n" % (timestamp, sender, text))

        logs[channel].flush()
        self.bot.logs = logs


class BotFactory(protocol.ClientFactory):

    # the class of the protocol to build when new connection is made
    protocol = Bot

    def __init__(self, config, connections):
        self.config = config
        self.connections = connections

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()
