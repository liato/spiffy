import re
import urllib
words = dict(hostname="Hostname", country="Country", region_name="Region",
             city="City", isp="ISP", organization="Organization", private="Private")

def geoip(self, input):
    "Geographical information about an IP/host"
    if not input.args:
        raise self.BadInputError()

    host = input.args
    host = urllib.quote(host.encode('utf-8'))

    try:
        data = urllib.urlopen('http://www.maxmind.com/app/lookup_city?ips=%s' % host).read()
    except IOError: 
        self.say("Error: Unable to establish connection to maxmind.com.")
        return

    m = re.search(r'<td><font size="-1">(?P<hostname>[^<]*)</font></td>\s*(?:<td><font size="-1">(?P<country_code>[^<]*)</font></td>\s*<td><font size="-1">(?P<country>[^<]*)</font></td>\s*<td><font size="-1">(?P<region>[^<]*)</font></td>\s*<td><font size="-1">(?P<region_name>[^<]*)</font></td>\s*<td><font size="-1">(?P<city>[^<]*)</font></td>\s*<td><font size="-1">(?P<postal_code>[^<]*)</font></td>\s*<td><font size="-1">(?P<latitude>[^<]*)</font></td>\s*<td><font size="-1">(?P<longitude>[^<]*)</font></td>\s*<td><font size="-1">(?P<isp>[^<]*)</font></td>\s*<td><font size="-1">(?P<organization>[^<]*)</font></td>\s*<td><font size="-1">(?P<metro_code>[^<]*)</font></td>\s*<td><font size="-1">(?P<area_code>[^<]*)</font></td>|<td col[^>]+><fo[^>]+>(?P<private>[^<]+))', data, re.I|re.DOTALL)
    if not m:
        self.say("Error: An error occurred while trying to retrieve data.")
        return
    m = m.groupdict()
    output = ""
    for f in m:
        if f in words and m[f]:
            output += "\x02%s:\x02 %s " % (words[f], m[f])

    if m["longitude"] and m["latitude"]:
        output += "\x02GMaps:\x02 "+"http://maps.google.com/maps?q="+m["latitude"]+","+m["longitude"]
    self.say(output.strip())

geoip.rule = ["geo", "geoip"]
geoip.usage = [("Get information about where an IP/host is geographically located", "$pcmd <ip|host>")]
geoip.usage = [("Get information about where google.com is geographically located", "$pcmd google.com")]
