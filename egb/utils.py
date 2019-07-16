import re
import time
import logging
import datetime
import psycopg2


logger = logging.getLogger(__name__)


def insert_row_breaks(flattened_table, break_token='ROW_BREAK'):
	"""For tokenized table data insert row breaks."""

	processed_flattened_table, insert_counter = [], 0
	for tok_idx, token in enumerate(flattened_table):

		# identify row break location and insert token
		if re.search(r'^(\d{1,2}(:\d{1,2}))$', token):
			processed_flattened_table.insert(tok_idx + insert_counter - 1, break_token)
			insert_counter += 1
		elif token == 'Live!':
			processed_flattened_table.insert(tok_idx + insert_counter, break_token)
			insert_counter += 1
		processed_flattened_table.append(token)

	# clean up first item if identified as row break
	if processed_flattened_table[0] == break_token:
		processed_flattened_table.pop(0)

	return processed_flattened_table


def reformat_list_to_table(flattened_table, break_token='ROW_BREAK'):
	"""Given a flattened table with row break tokens, reformat into 2d array."""

	table, row = [], []
	for token in flattened_table:
		if token == break_token:
			table.append(row)
			row = []
			continue
		row.append(token)

	return table


def get_match_time(tm, dt):
	"""Convert time and date to match time timestamp."""

	try:  # TODO: implement robust year filling method
		match_time = datetime.datetime.strptime(dt + ' ' + tm, '%d.%m %H:%M').replace(year=datetime.datetime.now().year)
		match_time = int(datetime.datetime.timestamp(match_time))
	except ValueError:
		match_time = -1

	return match_time


def string_to_float(s):
	"""Convert string s to float."""

	try:
		return float(s)
	except ValueError:
		return -1


def transcribe_row_data(row, scrape_time):
	"""Transcribe row data for db insertion"""

	dt, tm, tournament_name, contestant_1, contestant_1_odds, contestant_2, contestant_2_odds = row
	contestant_1_odds = string_to_float(contestant_1_odds)
	contestant_2_odds = string_to_float(contestant_2_odds)
	match_time = get_match_time(tm, dt)
	source, bet_type, draw_odds = 'egb', 'winner', -1
	row = (
		contestant_1, contestant_2, contestant_1_odds, contestant_2_odds, draw_odds,
		bet_type, scrape_time, match_time, tournament_name, source
	)

	return row


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
