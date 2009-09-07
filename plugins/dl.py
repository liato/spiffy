import re

def fdur(t):
    hours, t = divmod(t, 60*60)
    minutes, seconds = divmod(t, 60)
    return (hours, minutes, seconds)
   
def dl(self, input):
    """Calculates how long a download will take, given file size and speed."""

    m = re.search(r"(?P<size>\d{1,}) ?(?P<sizesuf>(?:k|m|g|t|e|z|y)i?)?b?\s(?P<speed>\d{1,}) ?(?P<speedsuf>(?:k|m|g|t|e|z|y)i?)?b?", input.args, re.IGNORECASE)
    
    if not m:
        raise self.BadInputError()
        return

    multip = {"k":1,"m":2,"g":3,"t":4,"p":5,"e":6,"z":7,"y":8}
    sizesuf = "m"
    speedsuf = "k"


    if m.group("sizesuf"):
        sizesuf = m.group("sizesuf")
    if m.group("speedsuf"):
        speedsuf = m.group("speedsuf")
    
    if "i" in sizesuf:
        bytes = 1024
    else:
        bytes = 1000
    size = int(m.group("size"))*bytes**multip[sizesuf[0]]
    
    if "i" in speedsuf:
        bytes = 1024
    else:
        bytes = 1000
    speed = int(m.group("speed"))*bytes**multip[speedsuf[0]]
    
    duration = fdur(size/speed)
    h=("h","m","s")
    caltime = ""
    for x in range(len(duration)):
        if duration[x]:
            caltime += str(duration[x])+h[x]+" "
    
    caltime = caltime.rstrip(" ")
    self.say(caltime)


dl.rule = ["dl","dload"]
dl.usage = [("Calculate the estimated time to download a file using default units",
             "$pcmd <size (MiB)> <speed (kiB/s)>"),
            ("Calculate using other units", "$pcmd <size> <kb|mb|gb|tb|...> <speed> <kb|mb|gb|tb|...>/s")]
dl.example = [("Calculate how long it takes to download a DVD image at modem speeds", "$pcmd 4.4 gb 6 kb/s")]          

