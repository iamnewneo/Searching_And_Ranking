import time
import re
import sys
from urllib.parse import urljoin
from urllib.parse import urlsplit
#import urllib.request, urllib.parse, urllib.error
import urllib.parse
from bs4 import BeautifulSoup
import requests
#from urlparse import urljoin
#from pysqlite2 import dbapi2 as sqlite
class MyOpener(urllib.request.FancyURLopener):
	version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15'

class crawler:
	def __init__(self,dbname):
		pass
	def __del__(self):
		pass
	def dbcommit(self):
		pass
	def getentryid(self,table,field,value,createnew=True):
		return None
	def addtoindex(self,url,soup):
		print("Indexxing " + str(url))
	def gettextonly(self,soup):
		return None
	def separatewords(self,text):
		return None
	def isindexed(self,url):
		return False
	def addlinkref(self,urlfrom,urlto,linktext):
		pass
	def crawl(self,pages,depth=2):
		myopener = MyOpener()
		for i in range(depth):
			newpages = set()
			for page in pages:
			#try:
				r=requests.get(page)
				#c=urllib2.open(text.read())
			#except:
				#print("Could not open")
				#continue
				soup=BeautifulSoup(r.content,'lxml')
				self.addtoindex(page,soup)
				links=soup('a')
				for link in links:
					if ('href' in dict(link.attrs)):
						url=urljoin(page,link['href'])
						if url.find("'")!=-1:continue
						url=url.split('#')[0]
						if url[0:4]=='http' and not self.isindexed(url):
							newpages.add(url)
						linktext=self.gettextonly(link)
						self.addlinkref(page,url,linktext)
				self.dbcommit()
			pages=newpages