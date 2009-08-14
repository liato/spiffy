import time, imp, os, sys, re, threading
from twisted.words.protocols import irc
from twisted.words.protocols.irc import lowDequote, numeric_to_symbolic, symbolic_to_numeric
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
        config = self.factory.config
        connections = self.factory.connections
        connections[config['network']] = self
  
        self.nickname = config.get('nick', 'spiffy')
        self.username = config.get('user', self.nickname)
        self.realname = config.get('name', self.nickname)
        self.versionName = config.get('versionreply', None)
        self.channels = config.get('channels', [])
        self.config = config
        self.connections = connections
        self.verbose = True
        self.encoding = 'utf-8'
        self.userlist = UserList(self)
        

        print "Loading modules..."
        self.variables = {}
        self.doc = {}
        modules = []

        if os.path.exists(os.path.join(sys.path[0], 'modules')):
            filenames = []
            for fn in os.listdir(os.path.join(sys.path[0], 'modules')): 
               if fn.endswith('.py') and not fn.startswith('_'): 
                  filenames.append(os.path.join(sys.path[0], 'modules', fn))

            for filename in filenames: 
               name = os.path.basename(filename)[:-3]
               try: module = imp.load_source(name, filename)
               except Exception, e: 
                  print >> sys.stderr, "Error loading %s: %s (in bot.py)" % (name, e)
               else: 
                  if hasattr(module, 'setup'): 
                     module.setup(self)
                  self.register_module(vars(module))
                  modules.append(name)
            
  
        if modules: 
           print >> sys.stderr, 'Registered modules:', ', '.join(modules)
        else:
            print >> sys.stderr, "Warning: Couldn't find any modules. Does /modules exist?"
        
        self.bind_commands()
        
        irc.IRCClient.connectionMade(self)
        print "Connected at %s" % time.asctime(time.localtime(time.time()))
        
    def register_module(self, variables): 
        # This is used by reload.py, hence it being methodised
        for name, obj in variables.iteritems(): 
            if hasattr(obj, 'commands') or hasattr(obj, 'rule'): 
                self.variables[name] = obj

    def bind_commands(self): 
        self.commands = {}
        
        def bind(self, regexp, func): 
            print regexp.pattern.encode('utf-8'), func
            # register documentation
            if not hasattr(func, 'name'): 
                func.name = func.__name__
            if func.__doc__:
                pcmd = self.config["prefix"] + func.name # pcmd = prefixed command
        
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
                                  
                self.doc[func.name] = (func.__doc__, usage, example)
            self.commands.setdefault(regexp, []).append(func)
  
        def sub(pattern, self=self): 
            # These replacements have significant order
            pattern = pattern.replace('$nickname', self.nickname)
            return pattern.replace('$nick', r'%s[,:] +' % self.nickname)
  
        for name, func in self.variables.iteritems(): 
            # print name, func
            if not hasattr(func, 'event'): 
                func.event = 'PRIVMSG'
            else:
                func.event = func.event.upper()
   
            if hasattr(func, 'rule'): 
                if isinstance(func.rule, str): 
                    pattern = sub(func.rule)
                    regexp = re.compile(pattern)
                    bind(self, regexp, func)
    
                if isinstance(func.rule, tuple): 
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
                            bind(self, regexp, func)
     
                    # 3) e.g. ('$nick', ['p', 'q'], '(.*)')
                    elif len(func.rule) == 3: 
                        prefix, commands, pattern = func.rule
                        prefix = sub(prefix)
                        for command in commands: 
                            command = r'(%s) +' % command
                            regexp = re.compile(prefix + command + pattern, re.IGNORECASE)
                            bind(self, regexp, func)
   
            if hasattr(func, 'commands'): 
                for command in func.commands: 
                    template = r'^%s(%s)(?: +(.*))?$'
                    pattern = template % (self.config['prefix'], command)
                    regexp = re.compile(pattern, re.IGNORECASE)
                    bind(self, regexp, func)        
        
    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        print "Disconnected at %s" % time.asctime(time.localtime(time.time()))

    # callbacks for events

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
        for chan in self.channels:
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
            prefix, command, params, text = parsemsg(line)
            if numeric_to_symbolic.has_key(command):
                command = numeric_to_symbolic[command]
            self.handleCommand(command, prefix, params, text, line)
        except Exception, e:
            print "Error: %s" % e
        

        
    def handleCommand(self, command, prefix, params, text, line):
        """Determine the function to call for the given command and call
        it with the given arguments.
        """
        method = getattr(self, "irc_%s" % command, None)
        if method is not None:
            try:
                method(prefix or '', text and params+[text] or params)
            except:
                pass

        command = (symbolic_to_numeric.get(command, command), command)
        if command[0].upper() in ("JOIN", "352", "353", "KICK", "PART", "QUIT", "NICK"):#, "MODE"):
            self.userlist._handleChange(prefix, command, params, text)
        if command[0] == "005":
            self.sendLine('PROTOCTL NAMESX') 
            
        print line
        print prefix, command, params, text
        print "\n"

        items = self.commands.items()
        for regexp, funcs in items: 
            for func in funcs:
                if not func.event in command:
                    continue

                match = regexp.match(text)
                if match:
                    input = CommandInput(self, prefix, command, params, text, match, line)
                    bot = QuickReplyWrapper(self, input)
                    targs = (func, bot, input)
                    t = threading.Thread(target=self.call, args=targs)
                    t.start()

    def call(self, func, bot, input):
        try:
            func(bot, input)
        except self.BadInputError, e:
            if input.sender:
                if self.doc[func.__name__][1]:
                    self.msg(input.sender, self.doc[func.__name__][1])
                else:
                    self.msg(input.sender, 'Use %shelp %s for more info on how to use this command.'
                             % (self.config.get('prefix',''), func.__name__))
        #except Exception, e:
            #print "Error: %s" % str(e)
            #if self.config.get('chandebug', True):
            #    self.msg(input.sender, str(e))
            #self.error(input)



    def ctcpQuery_VERSION(self, user, channel, data):
        nick = user.split("!",1)[0]
        if self.versionName:
            self.ctcpMakeReply(nick, [('VERSION', '%s' % self.versionName)])

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
