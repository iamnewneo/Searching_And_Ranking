f = open('links.txt','r')
flist = list(f)

f2 = open('html.txt','w')
for item in flist:
	string="<a href=\""+str(item)+"\""+">"+str(item)+"</a>"
	f2.write(string+"\n")