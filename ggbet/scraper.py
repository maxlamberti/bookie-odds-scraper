import time
import sentry_sdk
import logging.config
from bs4 import BeautifulSoup
from selenium import webdriver

from stopwords import STOPWORDS
from utils import remove_header, insert_row_breaks, transcribe_table_data, postgres_db_insert
from config import ENVIRONMENT, GGBET_URL, SENTRY_URL, DB_CREDENTIALS, LOGGING


# initialize logging and monitoring
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(ENVIRONMENT)
if ENVIRONMENT == 'PRODUCTION':
    sentry_sdk.init(SENTRY_URL)


if __name__ == '__main__':

    logger.info('Starting scrape job for ggbet table data.')

    # initialize headless selenium webdriver
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(chrome_options=chrome_options)

    # load website
    driver.get(GGBET_URL)
    html = driver.page_source
    time.sleep(5)  # give webpage time to load table
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")  # scroll down to load dynamic content
    time.sleep(1)

    # transcribe data table
    table = driver.find_element_by_id('betting__container').text
    soup = BeautifulSoup(table, 'html.parser')
    table_text = remove_header(soup.text)
    table_text = insert_row_breaks(table_text)
    table_rows = table_text.split('_ROW_BREAK_')
    formatted_data = transcribe_table_data(table_rows)
    logger.info('Finished processing of %s rows.', len(formatted_data))

    if len(formatted_data) > 0:
        logger.info('Inserting %s rows into database.', len(formatted_data))
        postgres_db_insert(formatted_data, DB_CREDENTIALS)
