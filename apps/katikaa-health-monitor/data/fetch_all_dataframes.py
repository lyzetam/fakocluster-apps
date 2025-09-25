
# Add the directory containing aws_secrets_manager_client.py to sys.path
import sys
sys.path.insert(0, '../Scripts')
sys.path.insert(0, '../Scripts/externalconnections')
sys.path.insert(0, '../Scripts/datafetch')

import pandas as pd
from dbconnect import * 
import mysql.connector
import logging
from dbconnect import *
from logging_config import configure_database_logging
from fetch_data import *


def fetch_all_dataframes():
    """
    Connects to the database and fetches all required dataframes.
    Returns:
        dict: A dictionary containing all the dataframes.
    """
    connection = connect_to_database()
    dataframes = {}
    if connection:
        # Fetch data from the views
        dataframes['management_db_country_data_df'] = management_db_country_data(connection)
        dataframes['management_db_fixtures_events_data_df'] = management_db_fixtures_events_data(connection)
        dataframes['management_db_fixtures_lineups_data_df'] = management_db_fixtures_lineups_data(connection)
        dataframes['management_db_odss_market_data_df'] = management_db_odss_market_data(connection)
        dataframes['management_db_olympus_fixtures_events_data_df'] = management_db_olympus_fixtures_events_data(connection)
        dataframes['management_db_olympus_fixtures_formations_data_df'] = management_db_olympus_fixtures_formations_data(connection)
        dataframes['management_db_olympus_sidelines_data_df'] = management_db_olympus_sidelines_data(connection)
        dataframes['management_db_olympus_topscorer_data_df'] = management_db_olympus_topscorer_data(connection)
        dataframes['management_db_season_standings_data_df'] = management_db_season_standings_data(connection)
        dataframes['management_db_teams_history_data_df'] = management_db_teams_history_data(connection)
        dataframes['prediction_db_bonus_user_answer_data_df'] = prediction_db_bonus_user_answer_data(connection)
        dataframes['prediction_db_community_users_data_df'] = prediction_db_community_users_data(connection)
        dataframes['prediction_db_community_data_df'] = prediction_db_community_data(connection)
        dataframes['prediction_db_competition_data_df'] = prediction_db_competition_data(connection)
        dataframes['prediction_db_fixtures_data_df'] = prediction_db_fixtures_data(connection)
        dataframes['prediction_db_matchday_fixture_mapping_data_df'] = prediction_db_matchday_fixture_mapping_data(connection)
        dataframes['prediction_db_matchday_data_df'] = prediction_db_matchday_data(connection)
        dataframes['prediction_db_olympus_comp_bonus_community_mapping_data_df'] = prediction_db_olympus_comp_bonus_community_mapping_data(connection)
        dataframes['prediction_db_olympus_competition_question_data_df'] = prediction_db_olympus_competition_question_data(connection)
        dataframes['prediction_db_olympus_competition_user_answer_data_df'] = prediction_db_olympus_competition_user_answer_data(connection)
        dataframes['prediction_db_olympus_odss_market_data_df'] = prediction_db_olympus_odss_market_data(connection)
        dataframes['prediction_db_p2p_bets_data_df'] = prediction_db_p2p_bets_data(connection)
        dataframes['prediction_db_player_statistics_data_df'] = prediction_db_player_statistics_data(connection)
        dataframes['prediction_db_player_data_df'] = prediction_db_player_data(connection)
        dataframes['prediction_db_prediction_data_df'] = prediction_db_prediction_data(connection)
        dataframes['prediction_db_user_invitations_data_df'] = prediction_db_user_invitations_data(connection)
        dataframes['prediction_db_user_ticket_attachments_data_df'] = prediction_db_user_ticket_attachments_data(connection)
        dataframes['prediction_db_user_tickets_data_df'] = prediction_db_user_tickets_data(connection)
        dataframes['prediction_db_user_data_df'] = prediction_db_user_data(connection)
        dataframes['rules_db_game_rules_data_df'] = rules_db_game_rules_data(connection)
        dataframes['rules_db_point_rules_data_df'] = rules_db_point_rules_data(connection)
        dataframes['rules_db_winner_rules_master_data_df'] = rules_db_winner_rules_master_data(connection)
        dataframes['rules_db_winner_rules_data_df'] = rules_db_winner_rules_data(connection)
        dataframes['site_commission_view_data_df'] = site_commission_data(connection)
        dataframes['transaction_db_community_transactions_data_df'] = transaction_db_community_transactions_data(connection)
        dataframes['transaction_db_transaction_error_data_df'] = transaction_db_transaction_error_data(connection)
        dataframes['transaction_db_user_transactions_data_df'] = transaction_db_user_transactions_data(connection)
        dataframes['prediction_db_wallet_data_df'] = prediction_db_wallet_data(connection) # new view
        connection.close()
    else:
        print("Failed to connect to the database.")
    return dataframes

# # Fetch dataframes
# dataframes = fetch_all_dataframes()