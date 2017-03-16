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

class searcher:
	def __init__(self,dbname):
		self.con = sqlite3.connect(dbname)
	def __del__(self):
		self.con.close()

	def getmatchrows(self,q):
		#Strings to build the query
		fieldlist = 'w0.urlid'
		tablelist = ''
		clauselist=''
		wordids=[]

		#split the words by spaces
		words=q.split(" ")
		tablenumber=0
		for word in words:
			#Get the wordid
			wordrow = self.con.execute('select rowid from wordlist where word="%s"' %(word)).fetchone()
			if wordrow!=None:
				wordid=wordrow[0]
				wordids.append(wordid)
				if tablenumber>0:
					tablelist+=","
					clauselist+=" and "
					clauselist+="w%d.urlid=w%d.urlid and " %(tablenumber-1,tablenumber)
				fieldlist+=",w%d.location" %(tablenumber)
				tablelist+="wordlocation w%d" %(tablenumber)
				clauselist+="w%d.wordid=%d" %(tablenumber,wordid)
				tablenumber+=1
		#create complete query from separate parts
		fullquery = 'select %s from %s where %s' %(fieldlist,tablelist,clauselist)
		cur=self.con.execute(fullquery)
		rows = [row for row in cur]
		return rows,wordids
	def getscoredlist(self,rows,wordids):
		totalscores=dict([(row[0],0) for row in rows])

		#this is where you will later put the scoring functions
		#weights = [(1.0,self.frequencyscore(rows))]
		#weights = [(1.0,self.locationscore(rows))]
		weights = [(1.0,self.worddistance(rows))]
		for (weight,scores) in weights:
			#this loops over dictionary with url as variable for key and totalscores[url] as value and updates it
			for url in totalscores:
				totalscores[url]+=weight*scores[url]
		return totalscores

	def geturlname(self,id):
		return self.con.execute('select url from urllist where rowid=%d' %(id)).fetchone()[0]

	def query(self,q):
		rows,wordids=self.getmatchrows(q)
		scores=self.getscoredlist(rows,wordids)
		rankedscores=sorted([(score,url) for (url,score) in scores.items()],reverse=1)
		for(score,urlid) in rankedscores[0:10]:
			print("%f\t%s" %(score,self.geturlname(urlid)))

	def normalizescores(self,scores,smallIsBetter=0):
		vsmall=0.00001 #avoid division by 0
		if smallIsBetter:
			minscore=min(scores.values())
			return dict([(u,float(minscore)/max(vsmall,l)) for (u,l) in scores.items()])
		else:
			maxscore=max(scores.values())
			if maxscore==0:
				maxscore=vsmall
			return dict([(u,float(c)/maxscore) for (u,c) in scores.items()])

	def frequencyscore(self,rows):
		counts=dict([(row[0],0) for row in rows])
		for row in rows:
			counts[row[0]]+=1
		return self.normalizescores(counts)

	def locationscore(self,rows):
		locations = dict([(row[0],10000000) for row in rows])
		for row in rows:
			loc=sum(row[1:])
			if loc<locations[row[0]]:
				locations[row[0]]=loc
		return self.normalizescores(locations,smallIsBetter=1)

	def worddistance(self,rows):
		#if there is only one word everyone wins
		if len(rows[0])<=2:
			return dict([(rows[0],1.0) for row in rows])
		mindistance=dict([(row[0],1000000) for row in rows])
		for row in rows:
			dist=sum([abs(row[i]-row[i-1]) for i in range(2,len(row))])
			if dist<mindistance[row[0]]:
				mindistance[row[0]]=dist
		return self.normalizescores(mindistance,smallIsBetter=1)