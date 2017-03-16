import urllib2
from BeauifulSoup import *
from urlparse import urljoin
from pysqlite2 import dbapi2 as sqlite

#create a list of words to ignore
ignorewords = set(['the','of','to','and','a','in','is','it'])

class crawler:
	#initialise the crawler with the name od database
	def __init__(self,dbname):
		self.con = sqlite.connect(dbname)

	def __del__(self):
		self.con.close()

	def dbcommnit(self):
		self.con.commit()
	#auxiallry function fot getting an entry id and adding if its not present
	def getentryid(self,table,field,value,createnew=True):
		cur=self.con.execute('select rowid from %s where %s="%s"' %(table,field,value))
		res = cur.fetchone()
		if res == None:
			cur = self.con.execute('insert into %s (%s) values ("%s")' %(table,field,value))
			return cur.lastrowid
		else:
			return res[0]

	#index an individual page
	def addtoindex(self,url,soup):
		if self.isindexed(url): return
		print('Indexing ' + url)

		#get individual words
		text = self.gettextonly(soup)
		words = self.separatewords(text)

		#get url id
		urlid = self.getentryid('urllist','url',url)
		#link each word to this url
		for i in range(len(words)):
			word = words[i]
			if word in ignorewords: continue
			wordid = self.getentryid('wordlist','word',word)
			self.con.execute('insert into wordlocation(urlid,wordid,location) values (%d,%d,%d)' %(urlid,worid,i))

	#extract text from an HTML page (tags)
	def gettextonly(self,soup):
		v = soup.starting
		if v == None:
			c = soup.contents
			resulttext = ''
			for t in c:
				subtext = self.gettextonly(t)
				resulttext+=subtext+'n'
			return resulttext
		else:
			return v.strip()

	#separate the words by non-whitespace character
	def separatewords(self,text):
		splitter = re.compile('\\W*')
		return [s.lower() for s in splitter.split(text) if s!='']

	#return true if url is already indexed
	def isindexed(self,url):
		u = self.con.execute('select rowid from urllist where url="%s"' %url).fetchone()
		if u!=None:
			#check if it has alreaddy been crawled
			v = self.con.execute('select * from wordlocation where urlid="%d"' %u[0]).fetchone()
			if v!= None: return True
		return False

	#add a link betwen 2 pages
	def addlinkref(self,urlFrom,urlTo,linkText):
		words=self.separateWords(linkText)
	    fromid=self.getentryid('urllist','url',urlFrom)
	    toid=self.getentryid('urllist','url',urlTo)
	    if fromid==toid: return
	    cur=self.con.execute("insert into link(fromid,toid) values (%d,%d)" % (fromid,toid))
	    linkid=cur.lastrowid
	    for word in words:
			if word in ignorewords: continue
			wordid=self.getentryid('wordlist','word',word)
			self.con.execute("insert into linkwords(linkid,wordid) values (%d,%d)" % (linkid,wordid))

	#starting with a list of pages,do a breadth first sarch to the given depth,indexing pages as we go
	def crawl(self,pages,depth=2):
		for i in range(depth):
			newpages = set()
			for page in pages:
				try:
					c= urllib2.urlopen(page)
				except:
					print('Could not open ' + str(page))
					continue
				soup = BeauifulSoup(c.read())
				self.addtoindex(page,soup)
				links = soup('a')
				for link in links:
					if ('href' in dict(link.attrs)):
						url = urljoin(page,link['href'])
						if url.find("'")!=-1: continue
						url = url.split('#')[0] #remove location portion
						if url[0:4] = 'http' and not self.isindexed(url):
							newpages.add(url)
						linkText = self.gettextonly(link)
						self.addlinkref(page,url,linkText)
					self.dbcommnit()
				pages = newpages

	#create the database tables
	def createindextables(self):
		self.con.execute('create table urllist(url)')
		self.con.execute('create table worlist(word)')
		self.con.execute('create table wordlocation(urlid,wordid,location)')
		self.con.execute('create table link(fromid integer, toid integer)')
		self.con.execute('create table linkwords(wordid,linkid)')
		self.con.execute('create index wordidx on wordlist(word)')
		self.con.execute('create index urlidx on urllist(url)')
		self.con.execute('create index wordurlidx on wordlocation(wordid)')
		self.con.execute('create index urltoidx on link(toid)')
		self.con.execute('create index urlfromidx on link(fromid)')
		self.dbcommnit()


############################################# SEARCH CLASS FOR SEARCHING ####################################
class searcher(object):
	"""docstring for searcher"""
	def __init__(self, dbname):
		self.con = sqlite.connect(dbname)

	def __del__(self):
		self.con.close()

	def getmatchrows(self,q):
		
		#string to build the query
		fieldlist = 'w0.urlid'
		tablelist = ''
		clauselist = ''
		wordids = []

		#split words by space
		word = q.spli(' ')
		tablenumber = 0

		for word in words:
			#get the word id
			wordrow = self.con.execute('select rowid from wordlist where word="%s"' %word).fetchone()
			if wordrow!=None:
				wordid = wordrow[0]
				wordids.append(wordid)
				if tablenumber > 0:
					tablelist+=','
					clauselist+=' and '
					clauselist+='w%d.urlid=w%d.urlid and ' %(tablenumber-1,tablenumber)
				fieldlist+=',w%d.location' %tablenumber
				tablelist+='wordlocation w%d' %tablenumber
				clauselist+='w%d.wordid=%d' %(tablenumber,wordid)
				tablenumber+=1

		#create query from the separate parts
		fullquery = 'select %s from %s where %s' %(fieldlist,tablelist,clauselist)
		cur = self.con.execute(fullquery)
		rows = [row for row in cur]
		return row,wordids

		def getscoredlist(self,rows,wordids):
			totalscores = dict([(row[0],0) for row in rows])

			#this is where u will later put the scoring functions
			weights = [(1.0,self.frequencyscore(rows))]

			for (weight,scores) in weights:
				for url in totalscores:
					totalscores[url]+=weight*scores[url]
			return totalscores

		def geturlname(self,id):
			return self.con.execute('select url from urllist where rowid=%d ' %id).fetchone()[0]

		def query(self,q):
			rows,wordids = self.getmatchrows(q)
			scores = self.getscoredlist(rows,wordids)
			rankedscores = sorted([(score,url) for (url,score) in score.items()],reverse=1)
			for (score,urlid) in rankedscores[0:10]
			print('%f \t %s ' %(score,self.geturlname(urlid)))

		def normalizedscores(self,scores,smallIsBetter=0):
			vsmall = 0.0001 #Avoid division by zero errors
			if smallIsBetter:
				minscore = min(scores.values())
				return dict([(u,float(minscore)/max(vsmall,l)) for (u,l) \
					in scores.items()])
			else:
				maxscore = max(scores.values())
				if maxscore==0:
					return maxscore=vsmall
				return dict([(u,float(c)/maxscore) for (u,c) in scores.items()])

		def frequencyscore(self,rows):
			counts = dict([(row[0],0) for row in rows])
			for row in rows:
				count[row[0]]+=1
			return self.normalizedscores(counts)

		def locationscore(self,rows):
			locations=dict([(row[0],1000000) for row in rows])
			for row in rows:
				loc=sum(row[1:])
				if loc<locations[row[0]]:
					locations[row[0]]=loc
			return self.normalizedscores(locations,smallIsBetter=1)

		def distancescore(self,rows):
			#if theres only one word
			if(len(row[0])<=2):
				return dict([row[0],1.0) for row in rows])
			#initialize the dictionary with large values
			mindistance=dict([(row[0],1.0) for row in rows])
			for row in rows:
				dist=sum([abs(row[i]-row[i-1]) for i in range(2,len(row))])
				if dist<mindistance[row[0]]:
					mindistance[row[0]]=dist
			return self.normalizedscores(mindistance,smallIsBetter=1)
			