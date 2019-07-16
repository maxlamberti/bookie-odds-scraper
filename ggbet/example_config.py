

GGBET_URL = 'https://gg.bet/en/counter-strike'


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
