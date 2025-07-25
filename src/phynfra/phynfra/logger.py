# -*- coding: utf-8 -*-

import sys

from datetime import datetime

def log (message = None, level = None):
	'''
	logger
	'''

	file = sys.stderr if level == 'ERROR' else sys.stdout

	print('[PYTHNFRA.%s - %s] %s' % (
		'DEBUG' if not level else level,
		datetime.now().isoformat(),
		message
	), file = file)