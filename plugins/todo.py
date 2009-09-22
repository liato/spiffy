import sqlite3
import os

def todo(self, input):
    "Simple TODO list"
    
    cmd = input.args or ""
    
    parser = self.OptionParser()
    parser.add_option("-r", "--remove", dest="remove")
    
    options, args = parser.parse_args(cmd.split())
    
    if not os.path.exists("data"):
        os.mkdir("data")
    
    conn = sqlite3.connect(os.path.join("data","todo.s3db"), detect_types = sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("select tbl_name from sqlite_master where tbl_name = 'Todos'")
    if not c.fetchone():
        c.execute("CREATE TABLE Todos (id INTEGER  PRIMARY KEY AUTOINCREMENT NOT NULL, user VARCHAR(20), network VARCHAR(30), todo VARCHAR(300))")
        self.bot._print("Created table Todos in SQLite database at data/todo.s3db")

    if options.remove: # remove TODOs
        query = "DELETE FROM Todos WHERE user = ? AND network = ? AND todo LIKE ?"
        c.execute(query, (input.nick, self.config["network"], "%" + options.remove + "%",))
        if c.rowcount > 0:
            self.say("Removed %s TODOs!" % c.rowcount)
        else:
            self.say("Nothing removed, sorry. (%s)" % c.rowcount)
    elif not input.args: # list all TODOs for this user
        query = "SELECT todo FROM Todos WHERE network = '%s' AND user = '%s' ORDER BY id ASC"
        query = query % (self.config["network"], input.nick)
        
        c.execute(query)  
        rows = c.fetchall()
        
        if rows:
            self.say("Your TODOs:")
            for row in rows:
                self.say("- %s" % row["todo"])
        else:
            self.say("You have no TODOs!")
            
    else: # add a new todo
        query = "INSERT INTO Todos (user, network, todo) VALUES (?, ?, ?)"
        c.execute(query, (input.nick, self.config["network"], input.args))
        self.say("Added!")
    
    conn.commit()
    c.close()
    conn.close()

todo.rule = ["todo"]
todo.usage = [("Add a TODO item", "$pcmd <todo item>"),
    ("Remove all TODO items that contain a given pattern", "$pcmd -r <pattern>"),
    ("List all of your TODO items", "$pcmd")]
todo.example = [("Add 'read 1984' to your TODO list", "$pcmd Read 1984!"),
    ("Remove all TODOs that contain '1984'", "$pcmd -r 1984")]

