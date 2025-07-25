# -*- coding: utf-8 -*-

from phynfra.atomic.http import Fetcher
from phynfra.atomic.calendar import now, difference

from datetime import timedelta
from urllib.parse import urlencode, quote

import jwt
import json

class Authentication ():
	'''
	Authentication - Scopes + Service Account
	NOTE: All service accounts MUST BE authorized, through CLIENT ID, in https://admin.google.com/u/0/ac/owl/domainwidedelegation
	'''

	def __init__ (self, account = None, credentials = None, scopes = None):
		'''
		'''

		self.credentials = credentials
		self.scopes = scopes
		self.account = account
		self.accessToken = None
		self.time = None

	def get (self):
		'''
		'''

		n = now(False, None)

		if self.accessToken:

			if difference(self.time, n) == True:

				return self.accessToken

			else:

				try:

					self.__fetch()

					return self.accessToken

				except Exception as fetchError:

					raise RuntimeError("Error fetching access token after expiring") from fetchError

		else:

			try:

				self.__fetch()

				return self.accessToken

			except Exception as fetchError:

				raise RuntimeError("Error fetching access token due to it's inexistence") from fetchError

	def __fetch (self):
		'''
		response['access_token']
		response['expires_in']
		response['token_type']
		'''

		self.time = now(False, None)

		sign = {
			'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
			'assertion': jwt.encode({
				'iss': self.credentials['client_email'],
				'sub': self.account if self.account else self.credentials['client_email'],
				'scope': ' '.join(self.scopes),
				'aud': 'https://oauth2.googleapis.com/token',
				'iat': self.time.timestamp(),
				'exp': (self.time + timedelta(hours = 1)).timestamp()
			}, self.credentials['private_key'], algorithm = 'RS256')
		}

		try:

			f = Fetcher('https://oauth2.googleapis.com/token', False)

			response = f.fetch('POST', payload = urlencode(sign, doseq = True, quote_via = quote), headers = {
				'content-type': 'application/x-www-form-urlencoded'
			})

			if response['ok'] == True:

				self.accessToken = json.loads(response['response'])

			else:

				raise RuntimeError("Fail to fetch token from Google -> %s" % response['response'])

		except Exception as fetchError:

			raise RuntimeError("Fail to perform fetch Access Token to Google") from fetchError
