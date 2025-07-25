# -*- coding: utf-8 -*-

import pytz

from datetime import datetime, timezone, timedelta

def now (string = True, zone = None):
	'''
	'''

	tz = timezone.utc

	if isinstance(zone, str):

		if zone != '':

			tz = pytz.timezone(zone)

	output = datetime.now(tz)

	return output if not string else output.strftime('%Y-%m-%dT%H:%M:%S.%f%z')

def difference (past = None, future = None, unit = 'minutes', duration = 1):
	'''
	'''

	difference = abs(future - past)

	kwargs = {}
	kwargs[unit] = duration

	return difference > timedelta(**kwargs)
