import json
import traceback
import time
import requests

from phynfra.apache.spark import *
from phynfra.atomic.calendar import now
from phynfra.atomic.http import Fetcher
from phynfra.aws.s3 import S3
from phynfra.atomic.json import flatten
from phynfra.microsoft.powerbi import PowerBI
from phynfra.google.authentication import Authentication
from phynfra.google.drive import Drive
from phynfra.google.mail import Mail

def tryout (settings = None):

	headers = {
		'Authorization': 'Bearer x',
		'Content-Type': 'application/json'
	}

	u = 'https://www.googleapis.com/drive/v3/files'

	r = requests.get(u, headers = headers)
	
	#f = Fetcher(u, True)

	#r = f.fetch('GET', )

	print(r.text)

def gauth (settings = None):
	'''
	python -m phynfra --command run --module phynfra.tester.gauth
	'''

	sa = {
		"type": ",
		"project_id": ",
		"private_key_id": ",
		"private_key": "",
		"client_email": ",
		"client_id": ",
		"auth_uri": ",
		"token_uri": ",
		"auth_provider_x509_cert_url": ",
		"client_x509_cert_url": ""
	}

	scopes = [
		'https://mail.google.com/',
		'https://www.googleapis.com/auth/gmail.modify',
		'https://www.googleapis.com/auth/gmail.compose',
		'https://www.googleapis.com/auth/gmail.send',
		'https://www.googleapis.com/auth/drive',
		'https://www.googleapis.com/auth/drive.file',
		'https://www.googleapis.com/auth/drive.readonly',
		'https://www.googleapis.com/auth/drive.metadata.readonly'
	]

	try:

		# a = Authentication('eu@eu.com', sa, scopes)

		# res = a.get()
		# print(res)

		# ac = res['access_token']

		
		#drive = Drive(ac)

		#output = drive.fetchOrCreatePathInSharedDrive('xxx', 'Teste RC/abc/def')

		# h = open('/Users/bla.pdf', 'rb')
		# bf = h.read()
		# h.close()
		# output = drive.uploadFileToSharedDrive(bf, 'application/pdf', {
		# 	'description': 'colé',
		# 	'name': 'bla.pdf',
		# 	'parents': [
		# 		'xxxx'
		# 	]
		# })

		#output = drive.unloadFileFromSharedDrive('wqerfsd')
		
		#output = drive.downloadFileFromSharedDrive('wqerfsd', '/tmp/ble.pdf')
		
		#output = drive.copyFileInSharedDrive('e-qwefsd', '1-ew')

		#output = drive.moveFileInSharedDrive('ew', ['1-ew'], ['ew'])
		
		#print(output)

		# rdlfbpt = []
		# drive.recursivePlainListFilesByPageToken('0APPvs35lvONjUk9PVA', None, False, rplfbpt)
		# print(rplfbpt)

		# rdlfbpt = []
		# drive.recursiveDeepListFilesByPageToken('0APPvs35lvONjUk9PVA', None, False, rdlfbpt)
		# print(rdlfbpt)

		# rdtlfbpt = {'files': []}
		# drive.recursiveDeepTreeListFilesByPageToken('0APPvs35lvONjUk9PVA', None, False, rdtlfbpt)
		# print(json.dumps(rdtlfbpt, ensure_ascii = False, indent = '\t'))

		mail = Mail(ac)

		output = mail.send(to = 'eu@teste', reply = 'eu@teste', subject = 'teste', body = 'Oi')

		print(output)
	
	except Exception as googleError:

		print(googleError)
		
		traceback.print_exc()

def roda (settings = None):

	#fetch
	# inserir no redshift
	# upload no s3

	#print(settings)

	#mandaeletexto(settings)
	#mandaeimagem(settings)
	#scan(settings)
	#osdataframe(settings)
	#print(dict(os.environ))

	print('TESTE')

	nested_json = {
		"a": 1,
		"b": {
			"c": None,
			"d": None,
			"e": [
				"a1", "b2", "c3"
			],
			"f": {
				"g": "Qui ut aute.",
				"h": "Qui ut aute.",
				"i": {
					"jjj": [1,2,3,5,6,7,8,9,0],
					"kkk": [1,2,3]
				},
				"p": [
					{"l1": 1, "l2": 2},
					{"l1": 1, "l2": 2},
					{"l1": 1, "l2": 2},
					{"l1": 1, "l2": 2}
				]
			}
		}
	}

	ppp = [nested_json, nested_json, nested_json, nested_json]

	print('ppp', ppp)
	ooo = flatten(ppp)
	print('ooo', json.dumps(ooo, ensure_ascii = False, indent = '\t'))

	#pbi = PowerBI(tenantID = settings['TENANTID'], clientID = settings['CLIENTID'], clientSecret = settings['CLIENTSECRET'])

	#pbi.fetchOauth2Token()

def scan (settings = None):

	sss = S3('us-east-1', settings['spark.hadoop.fs.s3a.access.key'], settings['spark.hadoop.fs.s3a.secret.key'])

	print(sss)

	#ou = sss.scan(bucket = 'dev-houer-us-east-1-landing-zone')

	#print('ou', ou)

def mandaeletexto(settings = None):

	sss = S3('us-east-1', settings['spark.hadoop.fs.s3a.access.key'], settings['spark.hadoop.fs.s3a.secret.key'])

	payload = '{"a": "1", "b": "2"}'.encode('utf-8')

	sss.write(bucket = 'dev-houer-us-east-1-landing-zone', payload = payload, keyPrefix = 'a.json', public = False, contentType = 'application/json', contentDisposition = None)

	volta = sss.read(bucket = 'dev-houer-us-east-1-landing-zone', keyPrefix = 'a.json')	

	print('sauda', volta)

def mandaeimagem(settings = None):

	sss = S3('us-east-1', settings['spark.hadoop.fs.s3a.access.key'], settings['spark.hadoop.fs.s3a.secret.key'])

	handler = open('/private/tmp/teste.jpg', 'rb')

	payload = handler.read()

	ou = sss.write(bucket = 'dev-houer-us-east-1-landing-zone', payload = payload, keyPrefix = 'teste.jpg', public = False, contentType = 'image/jpeg', contentDisposition = None)

	print(ou)

	volta = sss.read(bucket = 'dev-houer-us-east-1-landing-zone', keyPrefix = 'teste.jpg', decoder = None)	

	handler2 = open('/private/tmp/teste2.jpg', 'wb')

	handler2.write(volta)

	handler2.close()

def posta (settings = None):

	#verb = None, payload = None, headers = None, cookies = None, auth = None, stream = STREAM, timeout = TIMEOUT, verify = VERIFY

	#response = Fetcher('https://jsonplaceholder.typicode.com/todos/1', False).fetch(verb = 'get')

	#print(response['response'])

	img = 'https://scontent.cdninstagram.com/v/t39.30808-6/420166116_18037299043731514_3435207397703335670_n.jpg?stp=dst-jpg_e15&efg=eyJ2ZW5jb2RlX3RhZyI6ImltYWdlX3VybGdlbi4xMDAweDEwMDAuc2RyIn0&_nc_ht=scontent.cdninstagram.com&_nc_cat=110&_nc_ohc=jTD-FgjHJWEAX-O4BAi&edm=APs17CUAAAAA&ccb=7-5&ig_cache_key=MzI4MjkwMzQ4OTkyMjcyMjgzNg%3D%3D.2-ccb7-5&oh=00_AfD--kZxjq6Qz6AIGnT6ByPY6K0nFdyvGJKGv5uACsykVA&oe=65B277A1&_nc_sid=10d13b'

	response = Fetcher(img, False).fetch(verb = 'get', stream = True)

	print(response['response'])	

def hora (settings = None):
	'''
	'''

	o = now()

	print(o)

	o1 = now(True)

	print(o1)

	o2 = now(True, 'America/Sao_Paulo')

	print(o2)

def osdataframe (settings = None):

	spark = Spark('roda.bat', {key:value for (key, value) in settings.items() if key.startswith('spark')})

	dfr = DataFramer(spark)

	#dfr.create(StructType([StructField('name', StringType(), True), StructField('age', IntegerType(), True)]))

	#dfr.get().show()

	#dfr.append([("Alice", 25), ("Bob", 30), ("Charlie", 35)])

	if False:
		dfr.read('file:///Volumes/Data/Desenvolvimento/Javascript/projekte-3/scripts/notificate-professional-by-email-invoices.tsv', {
			'format':'csv',
			'sep':'\t',
			'inferSchema':"true",
			'header':"true"
		})


		dfr.read('s3a://dev-houer-us-east-1-gold-zone/project-turboman/moreapp/manutencao/part-00000-179a6c62-e641-4a84-8e37-343310f4bc38-c000.snappy.parquet', {
			'format': 'parquet'
		})

	dfr.read('s3a://dev-houer-us-east-1-landing-zone/roda.csv', {
		'format':'csv',
		'sep':'\t',
		'inferSchema':"true",
		'header':"true"
	})

	
	#dfr.read('s3a://mybucket/coco/podrao.xls')

	df = dfr.get()

	filtered = df.filter(df.tipocontrato == 'Sócio')

	filtered.show()


	if False:

		dfr.write('s3a://dev-houer-us-east-1-landing-zone/roda2.csv', arguments = {
			'format':'csv',
			'sep':'\t',
			'inferSchema':"true",
			'header':"true"
		}, dataframe = filtered)

		dfr.write('s3a://dev-houer-us-east-1-landing-zone/roda2.parquet', arguments = None, dataframe = filtered)

	#dfr.write('file:///Users/teste.csv', arguments = None, dataframe = filtered)
	

	#print(dfr.toList())

	#spark.stop()


