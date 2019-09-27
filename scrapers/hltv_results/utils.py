import logging
import psycopg2
from hashlib import md5
from datetime import datetime


logger = logging.getLogger(__name__)


def calc_average_header_date(headers):
	"""Calculate the average unix timestamp of the dates listed on the scrape site.

	Parameters
	----------
	headers : list
		List of text strings where each string is a header containing the date as a string.
	Returns
	-------
	Unix timestamp of the approximate match times on the current website.
	"""

	dates = []

	for header in headers:
		if len(header) < 8:
			continue

		datestring = header[12:]
		for suffix in ['nd', 'th', 'st', 'rd']:
			datestring = datestring.replace(suffix, '')
		datestring = datestring.split(' ')
		datestring[0] = datestring[0][:3]  # cut month
		datestring = ' '.join(datestring)
		date = datetime.strptime(datestring, '%b %d %Y')
		timestamp = int(date.timestamp())
		dates.append(timestamp)

	avg_date = int(sum(dates) / len(dates))

	return avg_date


def transcribe_table_data(text_table, match_time=-1):
	"""Extract and format relevant match data from raw rows of text.

	Parameters
	----------
	text_table : list
		List of text strings where each string is a row of data.
	match_time : int
		Unix timestamp of the approximate match time

	Returns
	-------
	List of tuples with processed data ready for database insertion.
	"""

	processed_data = []

	for text in text_table:
		hash_id = md5(text.encode('utf-8')).hexdigest()
		team_1, score, team_2, tournament, matchtype = text.split('\n')
		team_1_score, team_2_score = score.split(' - ')
		match_summary = (hash_id, team_1, team_2, int(team_1_score), int(team_2_score), tournament, matchtype, match_time)
		processed_data.append(match_summary)

	return processed_data


def postgres_db_upsert(data, db_credentials):
	"""Insert match results data from hltv into database.

	PARAMS
	------
	data : list of tuples
		List of tuples containing ordered entries of hash_id, team_1, team_2, team_1_score, team_2_score,
		tournament, matchtype, match_time.
	db_credentials : dict
		A dictionary containing key-value log in credentials for the database.
	"""

	conn = None
	insert_statement = """
		INSERT INTO csgo_match_results (
			hash_id, team_1, team_2, team_1_score, team_2_score, tournament, matchtype, match_time
		)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
		ON CONFLICT (hash_id) DO UPDATE 
		SET match_time = EXCLUDED.match_time;
	"""

	try:
		conn = psycopg2.connect(**db_credentials)
		cursor = conn.cursor()
		cursor.executemany(insert_statement, data)
		conn.commit()
		cursor.close()
		logger.info('Inserted %s rows.', len(data))
	except psycopg2.DatabaseError as e:
		logger.error('Failed to insert %s rows into database.', len(data))
		logger.error('Error: %s', e)
	finally:
		if conn:
			conn.close()
