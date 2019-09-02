

RIVALRY_URL = 'https://www.rivalry.com/matches/csgo-betting'


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
