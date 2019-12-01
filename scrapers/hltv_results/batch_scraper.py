import os
import time
import random
import logging.config
from selenium import webdriver

from config import LOGGING, HLTV_BASE_URL, OFFSET_RANGE
from utils import transcribe_table_data, calc_average_header_date, postgres_db_upsert


# get os config variables
ENVIRONMENT = os.environ['ENVIRONMENT']
DB_CREDENTIALS = {
	'host': os.environ['DB_HOST'],
	'user': os.environ['DB_USER'],
	'password': os.environ['DB_PASSWORD'],
	'dbname': os.environ['DB_NAME']
}


# initialize logging and monitoring
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(ENVIRONMENT)


if __name__ == '__main__':

	logger.info('Starting batch scrape job for hltv match results data.')

	# initialize headless selenium webdriver
	driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver')

	# iteratively load website / raw table data
	for offset in range(OFFSET_RANGE[0], OFFSET_RANGE[1], 100):

		driver.get(HLTV_BASE_URL + str(offset))
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

		# transcribe raw html to condensed tabular data
		headers = driver.find_elements_by_class_name('standard-headline')
		header_text = [header.text for header in headers]
		match_time = calc_average_header_date(header_text)
		table = driver.find_elements_by_class_name('result')
		result_text = [row.text for row in table]
		match_data = transcribe_table_data(result_text, match_time)
		logger.info('Finished processing of %s rows for an offset of %s.', len(table), offset)

		# insert to db
		if ENVIRONMENT == 'PRODUCTION' and len(table) > 0:
			logger.info('Upserting %s rows into database.', len(table))
			postgres_db_upsert(match_data, DB_CREDENTIALS)
		elif len(table) == 0:
			logger.warning('HLTV data scrape produced 0 data points.')
		else:
			logger.info('Produced data: %s', table)

		# sleep to not spam website
		time.sleep(random.uniform(1, 3))
