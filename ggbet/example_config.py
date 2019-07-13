

ENVIRONMENT = 'PRODUCTION'


GGBET_URL = 'https://gg.bet/en/counter-strike'


SENTRY_URL = 'https://xxxxxxxxxxxx@sentry.io/xxxxxx'


DB_CREDENTIALS = {
    'host': 'xxx',
    'user': 'xxx',
    'password': 'xxx',
    'dbname': 'xxx'
}


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
			'level': 'WARNING',
		},
		'DEV': {
			'handlers': ['console'],
			'level': 'DEBUG',
		}
	}
}
