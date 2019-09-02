import os
import time
import sentry_sdk
import logging.config
from selenium import webdriver

from config import LOGGING, RIVALRY_URL
from utils import transcribe_table_data, postgres_db_insert


# get os config variables
ENVIRONMENT = os.environ['ENVIRONMENT']
SENTRY_URL = os.environ['SENTRY_URL']
DB_CREDENTIALS = {
	'host': os.environ['DB_HOST'],
	'user': os.environ['DB_USER'],
	'password': os.environ['DB_PASSWORD'],
	'dbname': os.environ['DB_NAME']
}


# initialize logging and monitoring
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(ENVIRONMENT)
if ENVIRONMENT == 'PRODUCTION':
	sentry_sdk.init(SENTRY_URL)


if __name__ == '__main__':

	logger.info('Starting scrape job for rivalry table data.')

	# initialize headless selenium webdriver
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	driver = webdriver.Chrome(chrome_options=chrome_options)

	# load website / raw table data
	driver.get(RIVALRY_URL)
	time.sleep(5)  # give webpage time to load table
	driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down to load dynamic content
	time.sleep(1)
	table = driver.find_element_by_id('__nuxt')
	table = table.text.split('\n')
	table = transcribe_table_data(table)

	logger.info('Finished processing of %s rows.', len(table))

	# insert to db
	if ENVIRONMENT == 'PRODUCTION' and len(table) > 0:
		logger.info('Inserting %s rows into database.', len(table))
		postgres_db_insert(table, DB_CREDENTIALS)
	elif len(table) == 0:
		logger.warning('EGB data scrape produced 0 data points.')
	else:
		logger.info('Produced data: %s', table)
