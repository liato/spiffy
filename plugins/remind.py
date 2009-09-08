import datetime
import os
import re
import sqlite3
from threading import Timer

from parsedatetime import parsedatetime as pdt

ltz = timezone("Europe/Stockholm")

def setup(self):
    self.tells = {}

    dbname = "tellremind.%s.s3db" % self.config["network"]

    if not os.path.exists("data"):
        os.mkdir("data")
    
    conn = sqlite3.connect(os.path.join("data",dbname))
    c = conn.cursor()

    c.execute("select tbl_name from sqlite_master where tbl_name = 'tells'")
    if not c.fetchone():
        query = """CREATE TABLE tells (
                id INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
                sender varchar(20)  NULL,
                receiver varchar(20)  NULL,
                message varchar(300)  NULL,
                time timestamp  NULL)""" 
        c.execute(query)
   

    c.execute("select tbl_name from sqlite_master where tbl_name = 'reminds'")
    if not c.fetchone():
        query = """CREATE TABLE reminds (
                id INTEGER  PRIMARY KEY AUTOINCREMENT NOT NULL,
                sender varchar(20)  NULL,
                receiver varchar(20)  NULL,
                message varchar(300)  NULL,
                time TIMESTAMP  NULL,
                asktime timestamp  NULL,
                chan varchar(30)  NULL
                )"""
        c.execute(query)

    c.execute("select * from tells")
    for row in c:
        id,sender,receiver,msg,time = row
        time = datetime.datetime.strptime(time,"%Y-%m-%d %H:%M:%S")
        self.tells.setdefault(receiver,[]).append((id,sender,receiver,msg,time))

    remove = []
    c.execute("select * from reminds")
    now = self.localtime()
    rows = c.fetchall()
    c.close()
    conn.close()

    for row in rows:
        id,sender,receiver,msg,time,asktime,chan = row
        time = datetime.datetime.strptime(time,"%Y-%m-%d %H:%M:%S")
        asktime = datetime.datetime.strptime(asktime,"%Y-%m-%d %H:%M:%S")

        delta = time-now
        seconds = delta.days*24*60*60 + delta.seconds
        if seconds < 1:
            remove.append(id)
            id = savetell(self,sender,receiver,msg,asktime)
            self.tells.setdefault(receiver,[]).append((id,sender,receiver,msg,asktime))
            continue

        t = Timer(seconds, lambda: tryremind(self,id,sender,receiver,msg,asktime,chan))
        t.start() 

    for id in remove:
        removeremind(self,id)

def formattell(tup):
    "returns a string ready to be sent"
    _,sender,receiver,msg,time = tup
    time = time.strftime("%H:%M:%S")
    
    return "%s: [%s] <%s> tell %s %s" % (receiver, time, sender, receiver, msg)
                                                  
                                                  
def savetell(self,sender,receiver,message,time):
    dbname = "tellremind.%s.s3db" % self.config["network"]
    
    conn = sqlite3.connect(os.path.join("data",dbname))
    c = conn.cursor()

    c.execute("""insert into tells (sender,receiver,message,time) values (?,?,?,?)""",
              (sender,receiver,message,time.strftime("%Y-%m-%d %H:%M:%S")))


    c.execute("select id from tells order by id desc limit 1")
    id = int(c.fetchone()[0])
    conn.commit()    
    c.close()
    conn.close()
    
    return id

def removetells(self,ids):
    dbname = "tellremind.%s.s3db" % self.config["network"]
    conn = sqlite3.connect(os.path.join("data",dbname))
    c = conn.cursor()

    query = "delete from tells where id in (%s)" % ",".join(map(str,ids))
    c.execute(query)

    conn.commit()
    c.close()
    conn.close()

def message(self,input):
    if not input.sender.startswith('#'):
        return
    receiver = input.nick

    if not hasattr(self.bot,"tells"):
        return
    
    tells = self.bot.tells.get(receiver,[])
    if not tells:
        return

    del self.bot.tells[receiver]

    for tell in tells:
        self.say(formattell(tell))

    ids = [t[0] for t in tells]
    removetells(self,ids)
    
message.rule = r'(.*)'
                                                  

def tell(self,input):
    "Delivers a message to a recipient the next time he or she says something."
    teller = input.nick

    m = re.search(r'([\S,]+) (.+)', input.args, re.I)
    if not m:
        raise self.BadInputError()
    tellee, msg = m.groups()
    tellee = tellee.encode('utf-8')
    msg = msg.encode('utf-8')
    
    time = datetime.datetime.now()


    if u"," in tellee:
        tellee = tellee.split(u",")
    else:
        tellee = [tellee]


    ids = [savetell(self,teller,t,msg,time) for t in tellee]

    if hasattr(self.bot,"tells"):
        for id,t in zip(ids,tellee):
            self.bot.tells.setdefault(t,[]).append((id,teller,t,msg,time))
    else:
        self.bot.tells = {}
        for id,t in zip(ids,tellee):
            self.bot.tells.setdefault(t,[]).append((id,teller,t,msg,time))
        self.say("FYI, something funky has probably happened, self.bot.tells didn't exist.")
        
    self.say("%s: I'll pass that along!" % teller)
    
tell.rule = ['tell', 'ask']
tell.usage = [("Give someone a message the next time they say something", "$pcmd <recipient> <message>")]
tell.example = [("Deliver a message to Joe when he shows up", "$pcmd joe What's up?")]


def humantime(seconds,style='tuple'):
    m,s = divmod(seconds, 60)
    h,m = divmod(m, 60)
    d,h = divmod(h, 24)
    w,d = divmod(d, 7)
    if style == 'string':
        return ((w and str(w)+"w " or "")+(d and str(d)+"d " or "")+(h and str(h)+"h " or "")+(m and str(m)+"m " or "")+(s and str(s)+"s" or "")).strip()
    else:
        return (w,d,h,m,s)

def saveremind(self,sender,receiver,message,time,asktime,chan):
    dbname = "tellremind.%s.s3db" % self.config["network"]
    
    conn = sqlite3.connect(os.path.join("data",dbname))
    c = conn.cursor()

    c.execute("""insert into reminds (sender,receiver,message,time,asktime,chan) values (?,?,?,?,?,?)""",
              (sender,receiver,message,time.strftime("%Y-%m-%d %H:%M:%S"),asktime.strftime("%Y-%m-%d %H:%M:%S"),chan))


    c.execute("select id from reminds order by id desc limit 1")
    id = int(c.fetchone()[0])
    conn.commit()    
    c.close()
    conn.close()
    
    return id

def removeremind(self,id):
    dbname = "tellremind.%s.s3db" % self.config["network"]
    
    conn = sqlite3.connect(os.path.join("data",dbname))
    c = conn.cursor()

    query = "delete from reminds where id = %s" % id
    c.execute(query)

    conn.commit()
    c.close()
    conn.close()

def tryremind(self,id,sender,receiver,message,time,chan):

    rawsay = lambda message: self.msg(chan, message)
    if self.bot.chanlist.ison(receiver, chan):
        timestr = time.strftime("%Y-%m-%d %H:%M:%S")
        if receiver.lower() != sender.lower():
            rawsay(u"%s: At %s, %s asked me to tell you: %s" % (receiver, timestr, sender, message))
        else:
            rawsay(u"%s: At %s, you asked me to tell you: %s" % (receiver, timestr, message))
        removeremind(self,id)
    else:
        removeremind(self,id)
        id = savetell(self,sender,receiver,message,time)
        if hasattr(self.bot,"tells"):
            self.bot.tells.setdefault(receiver,[]).append((id,sender,receiver,message,time))
        else:
            self.bot.tells = {}
            self.bot.tells[receiver] = [(id,sender,receiver,message,time)]


def remind(self, input):
    "Delivers a message at a specific time, either relative or absolute."
    i = 0
    use_in = None
    if re.search(r" in (\d{1,} ?d(?:ay)?s?)? ?(-?\d{1,} ?h(?:our)?s?)? ?(-?\d{1,} ?m(?:inute|in)?s?)? ?(-?\d{1,} ?s(?:econd|ec)?s?)?",input.args):
        # we have "remind someone blabla in 3d 1h 1m 3s"
        i = input.args.rindex(" in")
        use_in = True
    elif re.search(r" at (?:(20[0-9]{2})[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01]) ([01]?\d|2[0-3])[:.]?([0-5]\d)|(2[0-3]|[01]?\d)[:.]?([0-5]\d))", input.args):
        # we have "remind someone blabla at 2009-09-09 20:30 (or just 20:30)"
        i = input.args.rindex(" at")
        use_in = False
    else:
        self.say(usage)
        return
    
    try:
        nick = input.args.split()[0]
        reqnick = input.nick
        task = unicode(input.args[input.args.index(nick)+len(nick)+1:i])
        rtime = input.args[i+4:]
    except (ValueError,IndexError):
        raise self.BadInputError()

    if nick == "me":
        nick = input.nick

    seconds = 0
    now = self.localtime()
    if use_in:
        match = re.search(r"(\d{1,} ?d(?:ay)?s?)? ?(-?\d{1,} ?h(?:our)?s?)? ?(-?\d{1,} ?m(?:inute|in)?s?)? ?(-?\d{1,} ?s(?:econd|ec)?s?)?", rtime)
        if match:
            c = pdt.Calendar()
            tup = c.parse(rtime,now)[0]
            then = datetime.datetime(*tup[:-2])

            delta = then - now
            seconds = delta.days*24*60*60 + delta.seconds
            
        else:
            self.say(usage)
            return
    else:
        if len(rtime) > 6: # 2008-08-08 20:30 is always longer than 6 characters
            if not re.match(r"(20[0-9]{2})[- /.](0[1-9]|1[012])[- /.](0[1-9]|[12][0-9]|3[01]) ([01]?\d|2[0-3])[:.]?([0-5]\d)",rtime):
                self.say("Invalid time: " + rtime)
                return
            then = datetime.datetime.strptime(rtime,"%Y-%m-%d %H:%M")
        else:
            if not re.match(r"(2[0-3]|[01]?\d)[:.]?([0-5]\d)",rtime):
                self.say("Invalid time: " + rtime)
                return
            then = datetime.datetime.strptime(now.strftime("%Y-%m-%d ") + rtime,"%Y-%m-%d %H:%M")
        delta = then - now
        seconds = delta.days*24*60*60 + delta.seconds
    

    if seconds < 1:
        self.say("Aborting! Module not found: timetravel.py (you probably suck at entering the time)")
        return
    
    if nick == input.nick:
        self.say(u"I'll tell '%s' to you in %s!" % (task,humantime(seconds,'string')))
    else:
        self.say(u"I'll tell '%s' to %s in %s!" % (task,nick,humantime(seconds,'string')))

    
    
    id = saveremind(self,reqnick,nick,task,
                    self.localtime() + datetime.timedelta(*divmod(seconds,86400)),self.localtime(),input.sender)

    t = Timer(seconds, lambda: tryremind(self,id,reqnick,nick,task,now,input.sender))
    t.start()
        
remind.rule = ["remind"]

remind.usage = [("Add a reminder to be delivered at a specific time", "$pcmd <recipient> <message> at <[date]time>"),
              ("Add a reminder to be delivered in a certain amount of time", "$pcmd <recipient> <message> in <time>")]
remind.example = [("Remind yourself to watch Lost", "$nick, remind me Watch Lost! at 20:55"),
                ("Remind yourself to do whatever on New Year's Eve 2039", "$pcmd me Party like it's 1999! at 2039-12-31 20:00"),
                ("Remind Joe to give pick you up in a week", "$pcmd Joe Pick me up at the airport! in 1 week")]















