import time
import logging
import datetime
import psycopg2


logger = logging.getLogger(__name__)


def get_match_time(date, time):
	"""Safely build a unix timestamp for the match time.

	Parameters
	----------
	date : datetime
		Date of the match.
	time : str
		String in form of '18:45 UTC'.

	Returns
	-------
	Unix timestamp of the match time. -1 if fails.

	"""

	try:
		time = [int(t) for t in time[:-4].split(':')]
		match_time = date.replace(hour=time[0], minute=time[1])
		match_time = int(match_time.timestamp())
	except:
		match_time = -1

	return match_time


def transcribe_table_data(table):
	"""Extract data from raw table and fit to sql schema.

	Parameters
	----------
	table : list
		List of raw match table data.

	Returns
	-------
	Transcribed data table according to SQL format.
	"""

	scrape_time = int(time.time())
	source, bet_type, draw_odds = 'rivalry', 'winner', -1

	start_index = table.index('Counter Strike Betting - Bet on Counter Strike Matches') + 1
	stop_index = table.index('CONNECT WITH US:')
	match_data = table[start_index:stop_index]

	formatted_data = []
	for element in range(len(match_data)):

		# get match date
		if match_data[element] == 'Today':
			date = datetime.datetime.now()
		elif match_data[element] == 'Tomorrow':
			date = datetime.datetime.now() + datetime.timedelta(days=1)

		# extract data
		if match_data[element] == 'VS':
			team_a = match_data[element - 2]
			team_b = match_data[element + 2]
			team_a_odds = match_data[element - 1]
			team_b_odds = match_data[element + 1]
			tournament = match_data[element - 4]
			match_time = match_data[element - 5]
			match_time = get_match_time(date, match_time)
			match = (team_a, team_b, team_a_odds, team_b_odds, draw_odds,
					 bet_type, scrape_time, match_time, tournament, source)
			formatted_data.append(match)

	return formatted_data


def postgres_db_insert(data, db_credentials):
	"""Insert odds data into database.

	PARAMS
	------
	data : list of tuples
		List of tuples containing ordered entries of team_1, team_2, team_1_winner_odds, team_2_winner_odds,
		scrape_time, match_time, tournament_name, source.
	db_credentials : dict
		A dictionary containing key-value log in credentials for the database.
	"""

	conn = None
	insert_statement = """
		INSERT INTO csgo_winner_odds (
			team_1, team_2, team_1_winner_odds, team_2_winner_odds, draw_odds, bet_type, scrape_time, match_time, tournament_name, source
		)
		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
	"""

	try:
		conn = psycopg2.connect(**db_credentials)
		cursor = conn.cursor()
		cursor.executemany(insert_statement, data)
		conn.commit()
		cursor.close()
		logger.info('Inserted %s rows.', len(data))
	except psycopg2.DatabaseError:
		logger.error('Failed to insert %s rows into database.', len(data))
	finally:
		if conn:
			conn.close()
