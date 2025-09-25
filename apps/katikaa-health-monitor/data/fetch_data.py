
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


# Generalized function to fetch data from a SQL view
def fetch_data_from_view(connection, view_name):
    try:
        sql_query = f"SELECT * FROM {view_name}"
        return pd.read_sql(sql_query, connection)
    except Exception as e:
        logging.error(f"Error fetching data from {view_name}: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on failure


# Management DB views
def management_db_country_data(connection):
    return fetch_data_from_view(connection, 'management_db_country_v')

def management_db_fixtures_events_data(connection):
    return fetch_data_from_view(connection, 'management_db_fixtures_events_v')

def management_db_fixtures_lineups_data(connection):
    return fetch_data_from_view(connection, 'management_db_fixtures_lineups_v')

def management_db_odss_market_data(connection):
    return fetch_data_from_view(connection, 'management_db_odss_market_v')

def management_db_olympus_fixtures_events_data(connection):
    return fetch_data_from_view(connection, 'management_db_olympus_fixtures_events_v')

def management_db_olympus_fixtures_formations_data(connection):
    return fetch_data_from_view(connection, 'management_db_olympus_fixtures_formations_v')

def management_db_olympus_sidelines_data(connection):
    return fetch_data_from_view(connection, 'management_db_olympus_sidelines_v')

def management_db_olympus_topscorer_data(connection):
    return fetch_data_from_view(connection, 'management_db_olympus_topscorer_v')

def management_db_season_standings_data(connection):
    return fetch_data_from_view(connection, 'management_db_season_standings_v')

def management_db_teams_history_data(connection):
    return fetch_data_from_view(connection, 'management_db_teams_history_v')


# Prediction DB views
def prediction_db_bonus_user_answer_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_bonus_user_answer_v')

def prediction_db_community_users_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_community_users_v')

def prediction_db_community_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_community_v')

def prediction_db_competition_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_competition_v')

def prediction_db_fixtures_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_fixtures_v')

def prediction_db_matchday_fixture_mapping_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_matchday_fixture_mapping_v')

def prediction_db_matchday_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_matchday_v')

def prediction_db_olympus_comp_bonus_community_mapping_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_olympus_comp_bonus_community_mapping_v')

def prediction_db_olympus_competition_question_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_olympus_competition_question_v')

def prediction_db_olympus_competition_user_answer_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_olympus_competition_user_answer_v')

def prediction_db_olympus_odss_market_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_olympus_odss_market_v')

def prediction_db_p2p_bets_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_p2p_bets_v')

def prediction_db_player_statistics_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_player_statistics')

def prediction_db_player_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_player_v')

def prediction_db_prediction_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_prediction_v')

def prediction_db_user_invitations_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_user_invitations_v')

def prediction_db_user_ticket_attachments_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_user_ticket_attachments_v')

def prediction_db_user_tickets_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_user_tickets_v')

def prediction_db_user_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_user_v')


# Rules DB views
def rules_db_game_rules_data(connection):
    return fetch_data_from_view(connection, 'rules_db_game_rules_v')

def rules_db_point_rules_data(connection):
    return fetch_data_from_view(connection, 'rules_db_point_rules_v')

def rules_db_winner_rules_master_data(connection):
    return fetch_data_from_view(connection, 'rules_db_winner_rules_master_v')

def rules_db_winner_rules_data(connection):
    return fetch_data_from_view(connection, 'rules_db_winner_rules_v')


# Transaction DB views
def transaction_db_community_transactions_data(connection):
    return fetch_data_from_view(connection, 'transaction_db_community_transactions_v')

def transaction_db_transaction_error_data(connection):
    return fetch_data_from_view(connection, 'transaction_db_transaction_error_v')

def transaction_db_user_transactions_data(connection):
    return fetch_data_from_view(connection, 'transaction_db_user_transactions_v')


# Site commission view
def site_commission_data(connection):
    return fetch_data_from_view(connection, 'site_commission_view')

#  'prediction_db_wallet_v'
def prediction_db_wallet_data(connection):
    return fetch_data_from_view(connection, 'prediction_db_wallet_v')