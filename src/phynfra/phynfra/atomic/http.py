# -*- coding: utf-8 -*-

import requests

TIMEOUT = 30
VERIFY = True
STREAM = False

class Fetcher ():
	'''
	'''

	def __init__ (self, url = None, raw = False):
		'''
		url:str - URL
		raw:bool - Returns raw response or chopped one
		'''

		if not isinstance(url, str) or url == '':

			raise ValueError('URL must be a valid url string')

		self.url = url

		self.raw = raw

	def update (self, url = None, raw = False):
		'''
		url:str - URL
		raw:bool - Returns raw response or chopped one
		'''

		if url != None and (not isinstance(url, str) or url == ''):

			raise ValueError('URL must be a valid url string')

		else:

			self.url = url

		if raw != None and (not isinstance(raw, bool)):

			raise ValueError('RAW must be a valid boolean')

		else:

			self.raw = raw

	def fetch (self, verb = None, payload = None, headers = None, cookies = None, auth = None, stream = STREAM, timeout = TIMEOUT, verify = VERIFY):
		'''
		'''

		if not isinstance(verb, str) or verb == '':

			raise ValueError('VERB must be a valid HTTP Verb (GET, POST, PUT, PATCH, DELETE, OPTIONS...)')

		if headers and not isinstance(headers, dict):

			raise ValueError('If HEADERS are provided, must be a dict - key:value')

		if cookies and not isinstance(cookies, dict):

			raise ValueError('If COOKIES are provided, must be a dict - key:value')

		response = None

		caller = None

		try:

			caller = getattr(requests, verb.lower())

		except Exception as verbError:

			raise ValueError('%s is not a function in requests. Please, check HTTP verb' % verb) from verbError

		try:

			kwargs = {
				'stream': stream,
				'timeout': timeout,
				'verify': verify
			}

			if payload:

				kwargs['data'] = payload

			if headers:

				kwargs['headers'] = headers

			if cookies:

				kwargs['cookies'] = cookies

			if auth:

				kwargs['auth'] = auth

			response = caller(self.url, **kwargs)

			return response if self.raw == True else {
				'response': response.text if stream == False else response.content,
				'status': response.status_code,
				'headers': response.headers,
				'ok': str(response.status_code).startswith('2')
			}

		except Exception as requestError:

			raise ValueError('Request to %s by %s raised an internal error' % (url, verb)) from requestError
