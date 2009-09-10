import re
import urllib
from xml.dom import minidom

def wval(xmlobj,el):
   try:
      return xmlobj.getElementsByTagName(el)[0].attributes.items()[0][1]
   except:
      return None

def f2c(fahrenheit):
   return (int(fahrenheit)-32)*(5.0/9.0)

def weather(self, input): 
   """Get the current weather conditions or a weather forecast"""
   
   m = re.search(r"(?P<forecast>-fc?)?(?:\t| )*?(?P<city>.+)?", input.args or "",re.IGNORECASE)
   city = m.group("city")
   if not city:
      city = "Stockholm,Sweden"
      
   forecast = m.group("forecast")
   city = city.encode('utf-8')
   city = urllib.quote(city)

   xmldoc = minidom.parse(urllib.urlopen("http://www.google.com/ig/api?weather=%s" % city))

   if not xmldoc.getElementsByTagName("city").length > 0:
      self.say("Sorry, no weather information could be found for the specified location.")
      return

   city = xmldoc.getElementsByTagName("city")[0].attributes.items()[0][1]
   cond = xmldoc.getElementsByTagName("condition")[0].attributes.items()[0][1]
   temp = xmldoc.getElementsByTagName("temp_c")[0].attributes.items()[0][1]
   wind = xmldoc.getElementsByTagName("wind_condition")[0].attributes.items()[0][1]
   humi = xmldoc.getElementsByTagName("humidity")[0].attributes.items()[0][1]
   
   if not forecast:
      self.say(u"Current weather in \x02%s\x02: %s and %s\u00B0C" % (city, cond, temp))
   else:
      self.say("Weather forecast for \x02%s\x02:" % city)
      for day in xmldoc.getElementsByTagName("forecast_conditions"):
         self.say(u"\x02%s\x02: From %d\u00B0C to %d\u00B0C and %s." % (wval(day,"day_of_week"), f2c(wval(day,"low")), f2c(wval(day,"high")), wval(day,"condition")))

weather.rule = ['weather']
weather.usage = [('Display the current weather in Stockholm, Sweden', '$pcmd'),
                ('Display the current weather in city', '$pcmd <city>'),
                ('Display a weather forecast for city', '$pcmd -f <city>')]
weather.example = [('Display the current weather in New York', '$pcmd New York'),
                ('Display a weather forecast for Los Angeles', '$pcmd -f Los Angeles')]