

HLTV_URL = 'https://www.hltv.org/results?offset=100'
HLTV_BASE_URL = 'https://www.hltv.org/results?offset='


OFFSET_RANGE = (19300, 48000)  # (start, end)


LOGGING = {
	'disable_existing_loggers': False,
	'version': 1,
	'formatters': {
		'simple': {
			'format': '%(asctime)s - %(levelname)s - %(message)s'
		},
	},
	'handlers': {
		'console': {
			'level': 'DEBUG',
			'formatter': 'simple',
			'class': 'logging.StreamHandler',
		}
	},
	'loggers': {
		'PRODUCTION': {
			'handlers': ['console'],
			'level': 'INFO',
		},
		'DEV': {
			'handlers': ['console'],
			'level': 'DEBUG',
		}
	}
}
