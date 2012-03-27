import urlparse, urllib, urllib2, htmllib, cgi
import string, unicodedata, os, re, sys, time
from datetime import date
import datetime
from xml.dom import minidom

import xbmc, xbmcgui, xbmcplugin, xbmcaddon

import resources.tools as tools
import resources.config as config
settings = config.__settings__
from resources.tools import webpage

# http://tvnz.co.nz/ondemand/xl 

class tvnz:
 def __init__(self):
  self.base = sys.argv[0]
  self.channel = "TVNZ"
  self.urls = dict()
  self.urls['base'] = 'http://tvnz.co.nz'
  self.urls['content'] = 'content'
  self.urls['page'] = 'ps3_xml_skin.xml'
  self.urls['search'] = 'search'
  self.urls['play'] = 'ta_ent_smil_skin.smil?platform=PS3'
  self.urls['episodes'] = '_episodes_group'
  self.urls['extras'] = '_extras_group'
  self.bitrate_min = 400000
  self.xbmcitems = tools.xbmcItems()
  self.xbmcitems.fanart = os.path.join('extrafanart', self.channel + '.jpg')
  #self.xbmcitems.fanart = "/".join(('extrafanart', 'TVNZ.jpg'))

 def url(self, folder):
  u = self.urls
  return "/".join((u['base'], u['content'], folder, u['page']))

 def _xml(self, doc):
  try:
   document = minidom.parseString(doc)
  except:
   pass
  else:
   if document:
    return document.documentElement
  sys.stderr.write("No XML Data")
  return False

 def index(self):
  page = webpage(self.url("ps3_navigation")) # http://tvnz.co.nz/content/ps3_navigation/ps3_xml_skin.xml
  xml = self._xml(page.doc)
  if xml:
   for stat in xml.getElementsByTagName('MenuItem'):
    type = stat.attributes["type"].value
    if type in ('shows', 'alphabetical'): #, 'distributor'
     m = re.search('/([0-9]+)/',stat.attributes["href"].value)
     if m:
      item = tools.xbmcItem()
      info = item.info
      info["Title"] = stat.attributes["title"].value
      info["FileName"] = "%s?ch=%s&type=%s&id=%s" % (self.base, self.channel, type, m.group(1))
      self.xbmcitems.items.append(item)
   item = tools.xbmcItem() # Search
   info = item.info
   info["Title"] = "Search"
   info["FileName"] = "%s?ch=TVNZ&type=%s" % (self.base, "search")
   self.xbmcitems.items.append(item)
  else:
   sys.stderr.write("No XML Data")
  self.xbmcitems.addall()

 def show(self, id, search = False):
  if search:
   import urllib
   url = "%s/%s/%s?q=%s" % (self.urls['base'], self.urls['search'], self.urls['page'], urllib.quote_plus(id))
  else:
   url = self.url(id)
  page = webpage(url)
  xml = self._xml(page.doc)
  if xml:
   for show in xml.getElementsByTagName('Show'):
    se = re.search('/content/(.*)_(episodes|extras)_group/ps3_xml_skin.xml', show.attributes["href"].value)
    if se:
     if se.group(2) == "episodes":
      #videos = int(show.attributes["videos"].value) # Number of Extras 
	  #episodes = int(show.attributes["episodes"].value) # Number of Episodes
      #channel = show.attributes["channel"].value
      item = tools.xbmcItem()
      info = item.info
      info["FileName"] = "%s?ch=%s&type=singleshow&id=%s%s" % (self.base, self.channel, se.group(1), self.urls['episodes'])
      info["Title"] = show.attributes["title"].value
      info["TVShowTitle"] = info["Title"]
      #epinfo = self.firstepisode(se.group(1))
      #if epinfo:
      # info = dict(epinfo.items() + info.items())
      self.xbmcitems.items.append(item)
  #self.xbmcitems.type = "tvshows"
  self.xbmcitems.addall()

 def search(self):
  results = self.xbmcitems.search()
  if results:
   self.show(results, True)

 def episodes(self, id):
  page = webpage(self.url(id))
  if page.doc:
   xml = self._xml(page.doc)
   if xml:
    #for ep in xml.getElementsByTagName('Episode').extend(xml.getElementsByTagName('Extra')):
    #for ep in map(xml.getElementsByTagName, ['Episode', 'Extra']):
    for ep in xml.getElementsByTagName('Episode'):
     item = self._episode(ep)
     if item:
      self.xbmcitems.items.append(item)
    for ep in xml.getElementsByTagName('Extras'):
     item = self._episode(ep)
     if item:
      self.xbmcitems.items.append(item)
    self.xbmcitems.sorting.append("DATE")
    self.xbmcitems.type = "episodes"
    self.xbmcitems.addall()

 def firstepisode(self, id):
  page = webpage(self.url(id + self.urls['episodes']))
  if page.doc:
   xml = self._xml(page.doc)
   if xml:
    item = self._episode(xml.getElementsByTagName('Episode')[0])
    if item:
     return item.info
  return False

 def _episode(self, ep):
  #se = re.search('/([0-9]+)/', ep.attributes["href"].value)
  se = re.search('([0-9]+)', ep.attributes["href"].value)
  if se:
   item = tools.xbmcItem(folder = False)
   info = item.info
   link = se.group(1)
   if ep.firstChild:
    info["Plot"] = ep.firstChild.data.strip()
   title = ep.attributes["title"].value
   subtitle = ep.attributes["sub-title"].value
   if not subtitle:
    titleparts = title.split(': ', 1) # Some Extras have the Title and Subtitle put into the title attribute separated by ': '
    if len(titleparts) == 2:
     title = titleparts[0]
     subtitle = titleparts[1]
   sxe = ""
   episodeparts = string.split(ep.attributes["episode"].value, '|')
   if len(episodeparts) == 3:
    #see = re.search('Series ([0-9]+), Episode ([0-9]+)', episodeparts[0].strip()) # Need to catch "Episodes 7-8" as well as "Epsiode 7". Also need to catch episode without series
    see = re.search('(?P<s>Se(ries|ason) ([0-9]+), )?Episodes? (?P<e>[0-9]+)(-(?P<e2>[0-9]+))?', episodeparts[0].strip())
    if see:
     try:
      info["Season"]  = int(see.group("s"))
     except:
      info["Season"] = 1
     info["Episode"] = int(see.group("e"))
    sxe = item.sxe()
    if not sxe:
      sxe = episodeparts[0].strip() # E.g. "Coming Up" or "Catch Up"
    date = self._date(episodeparts[1].strip())
    if date:
     info["Date"] = date
    info["Premiered"] = episodeparts[1].strip()
    info["Duration"] = self._duration(episodeparts[2].strip())
   info["TVShowTitle"] = title
   info["Title"] = " ".join((title, sxe, subtitle)) #subtitle
   info["Thumb"] = ep.attributes["src"].value
   #info["FileName"] = "%s?ch=%s&type=video&id=%s&info=%s" % (self.base, self.channel, link, urllib.quote(str(info)))
   #info["FileName"] = "%s?ch=%s&type=video&id=%s" % (self.base, self.channel, link)
   #info["FileName"] = self._geturl(link)
   info["FileName"] = self._geturl(link, False)
   return item
  return False

 def play(self, id): #, info
  item = tools.xbmcItem(False)
  info = item.info
  info["Title"] = ""
  info["FileName"] = self._geturl(id, True)
  item.path = info["FileName"]
  self.xbmcitems.add(item, 1)

 def bitrates(self, id): #, info
  #self.xbmcitems.addurls(self._videourls(id))
  for bitrate, url in self._videourls(id).iteritems():
   item = tools.xbmcItem(False)
   info = item.info
   info['Title'] = str(bitrate) + 'MB'
   info['FileName'] = item.stack(url)
   self.xbmcitems.items.append(item)
  self.xbmcitems.addall()

 def _geturl(self, id, play):
  if settings.getSetting('%s_quality_play' % self.channel) == 'true':
   return "%s?ch=%s&bitrates=%s" % (self.base, self.channel, id) #self.xbmcitems.addurls(self._videourls(id))
  elif play:
   return self.xbmcitems.url(self._videourls(id), settings.getSetting('%s_quality' % self.channel))
  else:
   return "%s?ch=%s&type=video&id=%s" % (self.base, self.channel, id)

 def _videourls(self, id):
  page = webpage("/".join((self.urls['base'], self.urls['content'], id, self.urls['play'])))
  if page.doc:
   xml = self._xml(page.doc)
   if xml:
    urls = dict()
    for chapter in xml.getElementsByTagName('seq'):
     for video in chapter.getElementsByTagName('video'):
      bitrate = int(video.attributes["systemBitrate"].value)
      urls[bitrate] = list()
    for chapter in xml.getElementsByTagName('seq'):
     for video in chapter.getElementsByTagName('video'):
      bitrate = int(video.attributes["systemBitrate"].value)
      url = video.attributes["src"].value
      if url[:7] == 'http://': # easy case - we have an http URL
       urls[bitrate].append(url)
       #print "HTTP URL: " + url
      elif url[:5] == 'rtmp:': # rtmp case
       rtmp_url = "rtmpe://fms-streaming.tvnz.co.nz/tvnz.co.nz"
       playpath = " playpath=" + url[5:]
       flashversion = " flashVer=MAC%2010,0,32,18"
       swfverify = " swfurl=http://tvnz.co.nz/stylesheets/tvnz/entertainment/flash/ondemand/player.swf swfvfy=true"
       conn = " conn=S:-720"
       urls[bitrate].append(url)
       #print "RTMP URL: " + rtmp_url + playpath + flashversion + swfverify + conn
      else:
       return False
    return urls

 def advert(self, chapter):
  advert = chapter.getElementsByTagName('ref')
  if len(advert):
   # fetch the link - it'll return a .asf file
   page = webpage(advert[0].attributes['src'].value)
   if page.doc:
    xml = self._xml(page.doc)
    if xml:
     # grab out the URL to the actual flash ad
     for flv in xml.getElementsByTagName('FLV'):
      if flv.firstChild and len(flv.firstChild.wholeText):
       return(flv.firstChild.wholeText)

 def _duration(self, dur):
  # Durations are formatted like 0:43:15
  minutes = 0
  parts = dur.split(":")
  if len(parts) == 3:
   try:
    minutes = int(parts[0]) * 60 + int(parts[1])
   except:
    pass
  return str(minutes)

 def _date(self, str):
  # Dates are formatted like 23 Jan 2010.
  # Can't use datetime.strptime as that wasn't introduced until Python 2.6
  formats = ["%d %b %y", "%d %B %y", "%d %b %Y", "%d %B %Y"]
  for format in formats:
   try:
    return datetime.datetime.strptime(str, format).strftime("%d.%m.%Y")
   except:
    pass
  return False