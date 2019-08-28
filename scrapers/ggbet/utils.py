import re
import time
import logging
import datetime
import psycopg2
from stopwords import STOPWORDS


logger = logging.getLogger(__name__)


def is_number(s):
    """Checks if string s is a number and returns boolean."""

    try:
        float(s)
        return True
    except ValueError:
        return False


def remove_header(html, cutoff='RESULTS', separator='\n', padding_token='_PADDING_'):
    """Removes table header and inserts padding_tokens instead of the separator."""

    tokenized_html = html.split(separator)
    for idx, token in enumerate(tokenized_html):
        if token == cutoff:
            break
    headless_html = padding_token.join(tokenized_html[idx+1:])

    return headless_html


def insert_row_breaks(html, separator='_PADDING_', row_break_token='_ROW_BREAK_', padding_token='_PADDING_'):
    """Inserts a token to indicate row breaks in the table. Very contrived rules."""

    tokenized_html = html.split(separator)
    num_tokens = len(tokenized_html)
    insert = False
    processed_html = [tokenized_html[0]]
    for idx in range(1, num_tokens):        
        if insert and not is_number(tokenized_html[idx]):
            insert = False
            processed_html.append(row_break_token)
        elif tokenized_html[idx - 1] == 'Over' and tokenized_html[idx] == 'Under':
            insert = True
            continue
        processed_html.append(tokenized_html[idx])
    processed_html = padding_token.join(processed_html)

    return processed_html


def idx_search(l, s):
    """Get the index of the first occurrence of a string s within strings in a list l.
    Only returns the first occurrence.
    """
    
    res_idx = -1
    for idx, token in enumerate(l):
        if s in token:
            res_idx = idx
            break

    return res_idx


def idx_time_regex_search(row):
    """Get the index of the first occurrence of a time in xx:xx format."""

    res_idx = -1
    for idx, token in enumerate(row):
        if re.search(r'^(\d{1,2}(:\d{1,2}))$', token):
            res_idx = idx
            break

    return res_idx


def get_tournament_name(token_list, stopwords=STOPWORDS, default="NA"):
    """Extract the tournament name."""
    
    tournament_name = default
    filtered_tokens = set(token_list) - stopwords
    if len(filtered_tokens) == 1:  # exact match
        tournament_name = filtered_tokens.pop()
    elif len(filtered_tokens) > 1:  # not exact match - go to default
        tournament_name = default
        
    return tournament_name


def idx_search_on_hard_string(row, s, discard=0):
    res_idx = -1
    for idx, token in enumerate(row):
        if token == s and discard == 0:
            res_idx = idx
            break
        elif token == s:
            discard -= 1
    return res_idx


def get_tournament_cut_index(row):
    """Find the index of the element in the data which separates the tournament title from the rest."""
    idx = idx_time_regex_search(row)  # match on xx:xx time
    if idx == -1:  # if it fails usually ongoing match - then match on TODAY
        idx = idx_search(row, 'TODAY')
    return idx


def get_match_time(row, idx):
    """Extract the match time from a row od data."""

    tm = row[idx]
    dt = row[idx + 1]
    try:
        match_time = datetime.datetime.strptime(dt + ' ' + tm, '%b %d %H:%M').replace(year=2019)
        match_time = int(datetime.datetime.timestamp(match_time))
    except:  # usually screws up when match is TODAY
        match_time = -1

    return match_time


def get_contestants(row):
    """Get the names of the two contestant teams from a row of data in the table."""

    idx = idx_search_on_hard_string(row, 'X')
    contestant_1 = row[idx - 1]
    contestant_2 = row[idx + 1]

    return contestant_1, contestant_2


def get_bet_type(row):
    """Get the type of the bet for row data of the table."""

    is_three_way_match = '1X2' in ''.join(str(s) for s in row)
    winner_in_row = -1 != idx_search_on_hard_string(row, 'WINNER')

    if is_three_way_match:
        bet_type = 'three-way'
    elif winner_in_row:
        bet_type = 'winner'
    else:
        bet_type = 'NA'

    return bet_type


def get_odds(row, bet_type):
    """Get bet odds from a row of table data. bet_type is either winner or three-way.
    Perform two index searches in the methods to cover two different types or row formatting.
    """

    contestant_1_odds = contestant_2_odds = draw_odds = -1

    if bet_type == 'three-way':

        x_idx_1 = idx_search_on_hard_string(row, 'X', discard=0)
        x_idx_2 = idx_search_on_hard_string(row, 'X', discard=1)

        if x_idx_2 != -1:
            contestant_1_odds = row[x_idx_2 + 2]
            contestant_2_odds = row[x_idx_2 + 3]
            draw_odds = row[x_idx_2 + 4]
        elif x_idx_1 != -1:
            contestant_1_odds = row[x_idx_1 + 2]
            contestant_2_odds = row[x_idx_1 + 3]
            draw_odds = row[x_idx_1 + 4]

    elif bet_type == 'winner':

        draw_odds = -1
        winner_idx = idx_search_on_hard_string(row, 'WINNER')
        x_idx = idx_search_on_hard_string(row, 'X')

        if winner_idx != -1:
            contestant_1_odds = row[winner_idx + 1]
            contestant_2_odds = row[winner_idx + 2]
        elif x_idx != -1:
            contestant_1_odds = row[x_idx + 2]
            contestant_2_odds = row[x_idx + 3]

    # clean up
    if not(is_number(contestant_1_odds) and is_number(contestant_2_odds) and is_number(draw_odds)):
        contestant_1_odds = -1
        contestant_2_odds = -1
        draw_odds = -1

    return contestant_1_odds, contestant_2_odds, draw_odds


def transcribe_table_data(table):
    """Extract relevant fields from table and output it as a list of tuples."""

    scrape_time = int(time.time())

    # sort rows by tournament
    tournaments, tournament = [], []
    for row in reversed(table):
        row = row.split('_PADDING_')
        tournament.append(row)
        time_idx = get_tournament_cut_index(row)
        tournament_name = get_tournament_name(row[:time_idx], stopwords=STOPWORDS)
        if tournament_name != 'NA':
            tournaments.append(tournament)
            tournament = []

    # process each match in the context of the tournament
    data = []
    for tournament in tournaments:
        for idx, match in enumerate(reversed(tournament)):
            cut_idx = get_tournament_cut_index(match)
            if idx == 0:
                tournament_name = get_tournament_name(match[:cut_idx], stopwords=STOPWORDS)
                bet_type = get_bet_type(match)
            match_time = get_match_time(match, cut_idx)
            contestant_1, contestant_2 = get_contestants(match)

            contestant_1_odds, contestant_2_odds, draw_odds = get_odds(match, bet_type)
            db_row = (contestant_1, contestant_2, contestant_1_odds, contestant_2_odds, draw_odds,
                      bet_type, scrape_time, match_time, tournament_name, 'ggbet')
            data.append(db_row)

    return data


def postgres_db_insert(data, db_credentials):
    """Insert GGBet odds data into database.

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
