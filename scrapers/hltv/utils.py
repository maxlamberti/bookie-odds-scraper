import time
import logging
import psycopg2
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def convert_to_number(s):
	"""Converts string s into a number. Returns -1 on failure."""

	try:
		num = float(s)
	except ValueError:
		num = -1
	return num


def get_bookie_name(html):
	"""Extract the book maker name a given entry in the odds table."""

	name = 'Not Found'
	for html_attr in html.contents:
		try:
			class_string = ' '.join(html_attr['class'])
			if 'betting-list-odds-provider' in class_string:
				name = class_string.split('-')[-1]
				break
		except TypeError:
			continue

	return name


def get_book_makers(driver):
	"""Get a list of all book makers."""

	bookmakers = driver.find_elements_by_class_name('provider-cell')
	bookmakers = [bookie.get_attribute('class') for bookie in bookmakers]
	bookmakers = [bookie[27:] for bookie in bookmakers if 'hidden' not in bookie]

	return bookmakers


def get_team_names(raw_html):
	"""Get a list of team names for a given tournament."""

	html = BeautifulSoup(raw_html).find_all("div", class_="team-name")
	team_names = [team.text for team in html]

	return team_names


def get_bet_types(raw_html):
	"""Get the bet type of the match, for example BO3."""

	html = BeautifulSoup(raw_html).find_all("div", class_="bet-best-of")
	bet_types = [bet.text for bet in html]

	return bet_types


def get_tournament_name(raw_html):
	"""Get the tournament name from the html object of the tournament."""

	html = BeautifulSoup(raw_html)
	tournament_name = html.contents[0].contents[0].text

	return tournament_name


def get_odds_rows(raw_html):
	"""Filters rows and returns only the rows that contain odds data."""

	separator = '/td>'
	rows = [tok + separator for tok in raw_html.split(separator) if 'odds betting-list-odds' in tok]
	html_rows = [BeautifulSoup(r, 'html.parser') for r in rows]

	return html_rows


def is_valid_bookie(row):
	"""Returns a boolean value if the bookie is active."""

	name = get_bookie_name(row)

	if 'hidden' in name:
		is_valid = False
	else:
		is_valid = True

	return is_valid


def decode_row(row):
	"""Extract the bookie name and the odds for a team from a row of data."""

	bookie_name = get_bookie_name(row)
	odds = convert_to_number(row.text)

	return bookie_name, odds


def transcribe_data(driver):
	"""Transcribe the raw html data to a tabular format for database insertion."""

	scrape_time = int(time.time())

	table_data = []
	bookmakers = get_book_makers(driver)
	num_bookmakers = len(bookmakers)
	html = driver.page_source
	tournaments = ['<div class="event-header' + s for s in html.split('<div class="event-header')][1:]

	for tournament in tournaments:

		tournament_name = get_tournament_name(tournament)
		team_names = get_team_names(tournament)
		bet_types = get_bet_types(tournament)
		html_rows = get_odds_rows(tournament)

		row_idx = 0
		rows_by_team = []
		for row in html_rows:  # extract data, still in wrong format

			if not is_valid_bookie(row):
				continue

			contestant_idx = int(row_idx / num_bookmakers)
			bet_type_idx = int(row_idx / (2 * num_bookmakers))
			row_idx += 1
			bookie_name, odds = decode_row(row)

			row_data = {
				'tournament_name': tournament_name,
				'team_name': team_names[contestant_idx],
				'bookie_name': bookie_name,
				'odds': odds,
				'bet_type': bet_types[bet_type_idx]
			}
			rows_by_team.append(row_data)

		# reformat data for postgres insertion
		for match_idx, match in enumerate(rows_by_team):

			if (int(match_idx / num_bookmakers) % 2) != 0:
				continue

			row = (
				match['team_name'],
				rows_by_team[match_idx + num_bookmakers]['team_name'],
				match['odds'],
				rows_by_team[match_idx + num_bookmakers]['odds'],
				-1,  # draw odds
				match['bet_type'],
				scrape_time,
				-1,  # match time
				match['tournament_name'],
				match['bookie_name'] + ' (hltv)'
			)
			table_data.append(row)

	return table_data


def postgres_db_insert(data, db_credentials):
	"""Insert GGBet odds data into database.

	PARAMS
	------
	data : list of tuples
		List of tuples containing ordered entries of team_1, team_2, team_1_winner_odds, team_2_winner_odds, draw_odds,
		bet_type, scrape_time, match_time, tournament_name, source.
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
