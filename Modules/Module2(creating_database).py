import time
import re
import sys
from urllib.parse import urljoin
from urllib.parse import urlsplit
#import urllib.request, urllib.parse, urllib.error
import urllib.parse
from bs4 import BeautifulSoup
import requests
import sqlite3
#from urlparse import urljoin
#from pysqlite2 import dbapi2 as sqlite


# create ignore words list
ignorewords = set(['the','of','to','and','a','in','is','it'])


class MyOpener(urllib.request.FancyURLopener):
	version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15'

class crawler:
	def __init__(self,dbname):
		self.con = sqlite3.connect(dbname)
	def __del__(self):
		self.con.close()
	def dbcommit(self):
		self.con.commit()
	def getentryid(self,table,field,value,createnew=True):
		cur=self.con.execute('select rowid from %s where %s = "%s" ' %(table,field,value))
		res = cur.fetchone()
		if res==None:
			cur=self.con.execute('insert into %s (%s) values ("%s")' % (table,field,value))
			return cur.lastrowid
		else:
			return res[0]
	def addtoindex(self,url,soup):
		#get individual words
		if self.isindexed(url):
			return
		text = self.gettextonly(soup)
		words = self.separatewords(text)

		#Get url id
		urlid=self.getentryid('urllist','url',url)

		#link each word to this url
		for i in range(len(words)):
			word=words[i]
			if word in ignorewords: continue
			wordid = self.getentryid('wordlist','word',word)
			self.con.execute('insert into wordlocation(urlid,wordid,location) values(%d,%d,%d)' % (urlid,wordid,i))

		print("Indexxing " + str(url))
	def gettextonly(self,soup):
		v = soup.string
		if v==None:
			c=soup.contents
			resulttext=""
			for t in c:
				subtext=self.gettextonly(t)
				resulttext+=subtext+'\n'
			return resulttext
		else:
			return v.strip()
	def separatewords(self,text):
		splitter=re.compile('\\W*')
		return [s.lower() for s in splitter.split(text) if s!='']
	def isindexed(self,url):
		u = self.con.execute('select rowid from urllist where url="%s"' %(url)).fetchone()
		if u!=None:
			#check if it has actually been crawled
			v=self.con.execute('select * from wordlocation where urlid=%d' % (u[0])).fetchone()
			if v!=None: return True
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
	def createindextables(self):
		self.con.execute('create table if not exists urllist(url)')
		self.con.execute('create table if not exists wordlist(word)')
		self.con.execute('create table if not exists wordlocation(urlid,wordid,location)')
		self.con.execute('create table if not exists link(fromid integer,toid integer)')
		self.con.execute('create table if not exists linkwords(wordid,linkid)')
		self.con.execute('create index if not exists wordidx on wordlist(word)')
		self.con.execute('create index if not exists urlidx on urllist(url)')
		self.con.execute('create index if not exists wordurlidx on wordlocation(wordid)')
		self.con.execute('create index if not exists urltoidx on link(toid)')
		self.con.execute('create index if not exists urlfromidx on link(fromid)')
		self.dbcommit()