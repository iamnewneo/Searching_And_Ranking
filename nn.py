from math import tanh
import sqlite3

def dtanh(y):
	return 1.0 - y*y

class searchnet:
	def __init__(self,dbname):
		self.con = sqlite3.connect(dbname)
	def __del__(self):
		self.con.close()

	def maketables(self):
		self.con.execute('create table if not exists hiddennode(create_key)')
		self.con.execute('create table if not exists wordhidden(fromid,toid,strength)')
		self.con.execute('create table if not exists hiddenurl(fromid,toid,strength)')
		self.con.commit()


	#----------STRENGTH = WEIGHT OF A CONNECTION-----------
	#-------VALUE OVER THE CONNECTION :p ------
	def getstrength(self,fromid,toid,layer):
		if layer==0:
			table='wordhidden'
		else:
			table='hiddenurl'
		res=self.con.execute('select strength from %s where fromid= %d and toid=%d' %(table,fromid,
			toid)).fetchone()
		if res==None:
			if layer==0: return -0.2
			if layer==1: return 0
		return res[0]

	def setstrength(self,fromid,toid,layer,strength):
		if layer==0:
			table='wordhidden'
		else:
			table='hiddenurl'
		res=self.con.execute('select rowid from %s where fromid= %d and toid=%d' %(table,fromid,
			toid)).fetchone()
		if res==None:
			self.con.execute('insert into %s (fromid,toid,strength) values (%d,%d,%f)' 
				%(table,fromid,toid,strength))
		else:
			rowid=res[0]
			self.con.execute('update %s set strength=%f where rowid=%d' %(table,strength,rowid))
		self.con.commit()

	#HIDDEN NODES ARE NOT DEFINED BEFOREHAND WE ADD NEW NODE EVERYTIME WE COME ACROSS NEW WORD PAIR

	def generatehiddennode(self,wordids,urls):
		if(len(wordids)) > 3:
			return None

		#Check if we already created a node for this set of words
		createkey='_'.join(sorted([str(wi) for wi in wordids]))
		res = self.con.execute('select rowid from hiddennode where create_key = "%s"' %(createkey)).fetchone()

		#if not create it
		if res==None:
			cur=self.con.execute('insert into hiddennode(create_key) values("%s")' %(createkey))
			hiddenid=cur.lastrowid

			#put in some default weights
			for wordid in wordids:
				self.setstrength(wordid,hiddenid,0,1.0/(len(wordids)))
			for urlid in urls:
				self.setstrength(hiddenid,urlid,1,0.1)
			self.con.commit()

	#######----GET THE RELEVANT HIDDEN IDS WITH REQUIRED WORDS AND URLS AND LEAVE REST ALONE----------------########
	def getallhiddennids(self,wordids,urlids):
		l1 = {}
		for wordid in wordids:
			cur=self.con.execute('select toid from wordhidden where fromid=%d' %(wordid))
			for row in cur:
				l1[row[0]]=1
		for urlid in urlids:
			cur=self.con.execute('select fromid from hiddenurl where toid=%d' %(urlid))
			for row in cur:
				l1[row[0]]=1
		return list(l1.keys())

	########SETUP NEW NEURAL NETWORK WHICH IS JUST A PORTION OF A VERY BIG NEURAL NETWORK ########
	def setupnetwork(self,wordids,urlids):
		#value lists
		self.wordids=wordids
		self.hiddenids=self.getallhiddennids(wordids,urlids)
		self.urlids=urlids

		#node output
		self.ai = [1.0]*len(self.wordids)
		self.ah = [1.0]*len(self.hiddenids)
		self.ao = [1.0]*len(self.urlids)

		#create weights matrix
		self.wi=[[self.getstrength(wordid,hiddenid,0) for hiddenid in self.hiddenids] for wordid in self.wordids]
		self.wo=[[self.getstrength(hiddenid,urlid,1) for urlid in self.urlids] for hiddenid in self.hiddenids]

	def feedforward(self):
		#the only inputs are the query inputs#
		#we set required inputs to 1 #
		#############-------FOR ACTIVATION OF INPUT LAYERS --------########
		for i in range(len(self.wordids)):
			self.ai[i]=1.0
		#############-------FOR ACTIVATION OF HIDDEN LAYERS --------########
		for j in range(len(self.hiddenids)):
			sum1=0.0
			for i in range(len(self.wordids)):
				sum1 = sum1+self.ai[i] * self.wi[i][j]
			self.ah[j]=tanh(sum1)

		#############-------FOR ACTIVATION OF output LAYERS --------########
		for k in range(len(self.urlids)):
			sum1=0.0
			for j in range(len(self.hiddenids)):
				sum1=sum1+ self.ah[j]*self.wo[j][k]
			self.ao[k] = tanh(sum1)
		return self.ao[:]		####----->>>THIS RETURNS relevance of the input urls

	def getresult(self,wordids,urlids):
		self.setupnetwork(wordids,urlids)
		return self.feedforward()

	

	def backPropagate(self,targets,N=0.5):

		#calculate the errors for the ouput

		# dtanh is global function at the top
		output_deltas = [0.0]*len(self.urlids)
		for k in range(len(self.urlids)):
			error = targets[k] - self.ao[k]
			output_deltas[k]=dtanh(self.ao[k])*error

		#calculate the errors for the hidden layer
		hidden_deltas = [0.0]*len(self.hiddenids)
		for j in range(len(self.hiddenids)):
			error=0.0
			for k in range(len(self.urlids)):
				error=error+output_deltas[k]*self.wo[j][k]
			hidden_deltas[j] = dtanh(self.ah[j])*error

		#update output weights
		for j in range(len(self.hiddenids)):
			for k in range(len(self.urlids)):
				change = output_deltas[k]*self.ah[j]
				#print("Output weights before")
				#print(self.wo[j][k])
				self.wo[j][k] = self.wo[j][k] + N*change
				#print("Output weights after")
				#print(self.wo[j][k])

		#update the input weights
		for i in range(len(self.wordids)):
			for j in range(len(self.hiddenids)):
				change= hidden_deltas[j]*self.ai[i]
				self.wi[i][j]+=N*change


	#####-------TRAINING METHOD-----###
	def trainquery(self,wordids,urlids,selectedurl):
		#generate a hidden node if necessary
		self.generatehiddennode(wordids,urlids)

		self.setupnetwork(wordids,urlids)
		self.feedforward()
		targets=[0.0]*len(urlids)
		targets[urlids.index(selectedurl)] = 1.0
		print("Bifore")
		print(self.wi)
		print(self.wo)
		print(self.ao)
		error = self.backPropagate(targets)
		print('After')
		print(self.wi)
		print(self.wo)
		print(self.ao)
		self.updatedatabase()

	def updatedatabase(self):
		#set them to database values
		for i in range(len(self.wordids)):
			for j in range(len(self.hiddenids)):
				self.setstrength(self.wordids[i],self.hiddenids[j],0,self.wi[i][j])
				#print(self.wi[i][j])

		for j in range(len(self.hiddenids)):
			for k in range(len(self.urlids)):
				self.setstrength(self.hiddenids[j],self.urlids[k],1,self.wo[j][k])
		self.con.commit()