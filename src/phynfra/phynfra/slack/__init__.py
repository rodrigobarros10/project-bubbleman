# -*- coding: utf-8 -*-

import json

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class Slack ():
	'''
	'''

	def __init__ (self, token = None):
		'''
		'''

		self.__token = token

		self.__client = WebClient(token = self.__token)

	def notify (self, channel = None, message = None):
		'''
		channel:str
		message:str
		'''

		try:
		
			response = self.__client.chat_postMessage(channel = channel, text = message)

			return response

		except Exception as postError:

			raise RuntimeError("Fail to post message to channel in Slack") from postError
