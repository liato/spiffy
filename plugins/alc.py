import re

def alc(self,input):
    """Calculates the amount of alcohol in a drink. Units used are cl and percent."""
    g = re.findall("[0-9+*\-\^/.,]+ [0-9+*\-\^/.,]+",input.args)

    if not g:
        raise self.BadInputError()
    
    newg = []
    for v,c in [e.split() for e in g]:
        nv, nc = v,c
        if not v.isdigit():
            try:
                nv = eval(v.replace("^","**").replace(",","."))
            except SyntaxError,NameError:
                self.say("Error in given volume: %s" % v)
                return
            
        if not c.isdigit():
            try:
                nc = eval(c.replace("^","**").replace(",","."))
            except SyntaxError,NameError:
                self.say("Error in given concentration: %s" % c)
                return
        newg.append([float(nv),float(nc)])

    g = newg
    
    if not all(c <= 100 for v,c in g):
        self.say(chr(2) + "Error:" + chr(2) + " concentration "+ "> 100%!")
        return

    total = sum(v*(c/100.0) for v,c in g)

    b = chr(2)
    eqv = total/0.4
    self.say("%sTotal%s: %s%.2f cl%s pure alcohol weighing %s%.2f grams%s (equivalent to %s%.2f cl%s vodka)" % (b,b,b,
                                                                          total,
                                                                          b,b,
                                                                          7.89*total,
                                                                          b,b,eqv,b))        

alc.rule = ["alc"]
alc.usage = [("Calculate the amount of pure alcohol in a drink, given amount (cl) and percent alcohol by volume",
              "$pcmd <amount> <percentage>"),
             ("Calculate for several drinks at once", "$pcmd <amt1> <per1> <amt2> <per2> [....]")]
alc.example = [("Calculate the amount of pure alcohol in a liter of vodka (40% ABV)", "$pcmd 100 40"),
             ("Calculate for several drinks (50 cl beer, 10 cl vodka)","$pcmd 50 5.2 10 40")]
