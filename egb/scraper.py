import os
import time
import sentry_sdk
import logging.config
from selenium import webdriver

from config import LOGGING, EGB_URL
from utils import insert_row_breaks, reformat_list_to_table, transcribe_row_data, postgres_db_insert


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

	logger.info('Starting scrape job for egb table data.')

	# initialize headless selenium webdriver
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-dev-shm-usage')
	driver = webdriver.Chrome(chrome_options=chrome_options)

	# load website / raw table data
	driver.get(EGB_URL)
	time.sleep(5)  # give webpage time to load table
	driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down to load dynamic content
	time.sleep(1)
	table = driver.find_elements_by_class_name('table-bets')
	table = table[0].text

	# transcribe data table
	scrape_time = int(time.time())
	table = table.split('\n')[6:]  # tokenize and cut header
	table = insert_row_breaks(table)  # insert break token for row breaks
	table = reformat_list_to_table(table)  # reformat into 2d table
	table = [transcribe_row_data(row, scrape_time) for row in table if len(row) == 7]  # filter out live games
	logger.info('Finished processing of %s rows.', len(table))

	# insert to db
	if ENVIRONMENT == 'PRODUCTION' and len(table) > 0:
		logger.info('Inserting %s rows into database.', len(table))
		postgres_db_insert(table, DB_CREDENTIALS)
	elif len(table) == 0:
		logger.warning('EGB data scrape produced 0 data points.')
	else:
		logger.info('Produced data: %s', table)
