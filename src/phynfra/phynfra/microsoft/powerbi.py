# -*- coding: utf-8 -*-

import json

from urllib.parse import urlencode
from phynfra.atomic.http import Fetcher
from phynfra.atomic.calendar import now

class PowerBI ():
	'''
	'''

	def __init__ (self, tenantID = None, clientID = None, clientSecret = None):
		'''
		'''

		if not isinstance(tenantID, str) or tenantID == '':

			raise ValueError('PowerBI.tenantID should be a valid string')

		if not isinstance(clientID, str) or clientID == '':

			raise ValueError('PowerBI.clientID should be a valid string')

		if not isinstance(clientSecret, str) or clientSecret == '':

			raise ValueError('PowerBI.clientSecret should be a valid string')


		self.settings = {
			'tenantID': tenantID,
			'clientID': clientID,
			'clientSecret': clientSecret
		}

		self.accesstoken =  None


	def fetchOauth2Token (self):
		'''
		'''

		url = 'https://login.microsoftonline.com/%s/oauth2/v2.0/token' % self.settings['tenantID']

		fetcher = Fetcher(url, True)

		response = None

		try:

			payload = urlencode({
				'client_id': self.settings['clientID'],
				'client_secret': self.settings['clientSecret'],
				'grant_type': 'client_credentials',
				'scope': 'https://analysis.windows.net/powerbi/api/.default'
			})

			response = fetcher.fetch(verb = 'POST', payload = payload, headers = {'content-type': 'application/x-www-form-urlencoded'}, stream = False, timeout = 7, verify = True)

		except Exception as fetchError:

			raise ValueError('Error obtaining the Microsoft OAuth2 Token to PowerBI') from fetchError

		try:

			self.accesstoken = json.loads(response.text, ensure_ascii = False)

			self.accesstoken['created_at'] = now(True, 'America/Sao_Paulo')

			return self

		except Exception as parseError:

			raise ValueError('Error parsing JSON response from Microsoft OAuth2') from parseError
	
	def fireRefresh (self, groupID = None, reportID = None):
		'''
		'''

		if not isinstance(groupID, str) or groupID == '':

			raise ValueError('PowerBI.groupID should be a valid string')

		if not isinstance(reportID, str) or reportID == '':

			raise ValueError('PowerBI.reportID should be a valid string')

		datasetID = None

		accesstoken = self.accesstoken['access_token']

		# DataSet

		url = 'https://api.powerbi.com/v1.0/myorg/groups/%s/reports/%s?$expand=datasets($select=id)' % (groupID, reportID)

		fetcher = Fetcher(url, True)

		response = None

		try:

			response = fetcher.fetch(verb = 'GET', headers = {'content-type': 'application/json', 'Authorization': 'Bearer %s' % accesstoken}, stream = False, timeout = 7, verify = True)

			datasetID = response['data']['datasetId']

		except Exception as fetchError:

			raise ValueError('Error obtaining datasets for %s/%s' % (groupID, reportID)) from fetchError

		# Parser

		try:

			datasetID = json.loads(response.text, ensure_ascii = False)

		except Exception as parseError:

			raise ValueError('Error parsing JSON response from Microsoft DataSet Fetcher') from parseError

		# Refresh

		url = 'https://api.powerbi.com/v1.0/myorg/groups/%s/datasets/%s/refreshes' % (groupID, datasetID)

		fetcher = Fetcher(url, True)

		try:

			response = fetcher.fetch(verb = 'POST', headers = {'content-type': 'application/json', 'Authorization': 'Bearer %s' % accesstoken}, stream = False, timeout = 7, verify = True)

			return response.status_code

		except Exception as fetchError:

			raise ValueError('Error refreshing dataset for %s/%s' % (groupID, datasetID)) from fetchError
	
	
