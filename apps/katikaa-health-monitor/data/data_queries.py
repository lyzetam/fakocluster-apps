# Add the directory containing aws_secrets_manager_client.py to sys.path
import sys
sys.path.insert(0, '../Scripts')
sys.path.insert(0, '../Scripts/externalconnections')
sys.path.insert(0, '../Scripts/datafetch')

import pandas as pd
from dbconnect import *  # dbconnect.py file with this function
from data_prep import convert_data_types


# db_credentials = fetch_db_credentials()
# connection = connect_to_database(db_credentials)
connection = connect_to_database()
#convert_data_types = convert_data_types()


##### User Analytics #####

def predictionDetails_views_data(connection):
    query = "SELECT * FROM predictionDetails"
    predictionDetails_views_data = pd.read_sql(query, connection)
    predictionDetails_views_data = convert_data_types(predictionDetails_views_data)
    return predictionDetails_views_data

def communityDetails_views_data(connection):
    query = "SELECT * FROM communityDetails"
    communityDetails_views_data = pd.read_sql(query, connection)
    communityDetails_views_data = convert_data_types(communityDetails_views_data)
    return communityDetails_views_data

def communitywisetrans_data(connection):
    sql_query = "SELECT * FROM communitywisetrans"  
    communitywisetrans_data = pd.read_sql(sql_query, connection)

    return communitywisetrans_data

def usertrans_data(connection):
    sql_query = "SELECT * FROM communitywiseusertrans"  
    usertrans_data = pd.read_sql(sql_query, connection)
    return usertrans_data

def prediction_data(connection):
    sql_query = "SELECT * FROM growthmetrics_commuwiseprediction"  
    commuwiseprediction_data = pd.read_sql(sql_query, connection)

    return commuwiseprediction_data

def growth_data(connection):
    sql_query = "SELECT * FROM growthmetrics_prediction"  
    growthmetrics_prediction_data = pd.read_sql(sql_query, connection)

    return growthmetrics_prediction_data

def relevancy_data(connection):
    sql_query = "SELECT * FROM relevantmetrics_user"  
    relevancy_data = pd.read_sql(sql_query, connection)

    return relevancy_data

def communitywinner_data(connection):
    sql_query = "SELECT * FROM communityWinner"  
    communitywinner_data = pd.read_sql(sql_query, connection)

    return  communitywinner_data

def livetipr_community_users_data(connection):
    sql_query = "SELECT * FROM v_livetipr_community_users"  
    livetipr_community_users_data = pd.read_sql(sql_query, connection)
    livetipr_community_users_data = convert_data_types(livetipr_community_users_data)
    return livetipr_community_users_data

def livetipr_declare_winner_data(connection):
    sql_query = "SELECT * FROM v_livetipr_declare_winner"  
    livetipr_declare_winner_data = pd.read_sql(sql_query, connection)
    livetipr_declare_winner_data = convert_data_types(livetipr_declare_winner_data)
    return livetipr_declare_winner_data

def livetipr_gas_price_live_data(connection):
    sql_query = "SELECT * FROM v_livetipr_gas_price_live"  
    livetipr_gas_price_live_data = pd.read_sql(sql_query, connection)
    return livetipr_gas_price_live_data

def livetipr_prediction_data(connection):
    sql_query = "SELECT * FROM v_livetipr_prediction"  
    livetipr_prediction_data = pd.read_sql(sql_query, connection)
    livetipr_prediction_data = convert_data_types(livetipr_prediction_data)
    return livetipr_prediction_data

def livetipr_user_data(connection):
    sql_query = "SELECT * FROM v_livetipr_user"  
    livetipr_user_data = pd.read_sql(sql_query, connection)
    livetipr_user_data = convert_data_types(livetipr_user_data)
    return livetipr_user_data

def livetipr_user_creation_data(connection):
    sql_query = """
        SELECT
            DATE(creation_date) AS created_date, 
            COUNT(DISTINCT user_id) AS unique_user_count
        FROM v_livetipr_user
        GROUP BY CAST(creation_date AS DATE) 
        ORDER BY CAST(creation_date AS DATE)  
    """
    livetipr_user_creation_data = pd.read_sql(sql_query, connection)
    livetipr_user_creation_data = convert_data_types(livetipr_user_creation_data)
    return livetipr_user_creation_data


def number_user_per_community_data(connection):
    sql_query = """
        SELECT 
            community_id, 
            community_name, 
            name, 
            CommunitiAdminEmail AS AdminEmail,
            COUNT(DISTINCT CommunityUser_id) AS num_users
        FROM communityDetails 
        GROUP BY community_id, community_name, name
    """
    number_user_per_community_data = pd.read_sql(sql_query, connection)
    number_user_per_community_data = convert_data_types(number_user_per_community_data)
    return number_user_per_community_data


def number_predictions_per_day_data(connection):
    
    sql_query = """
    SELECT 
        DATE(creation_date) AS Date, 
        COUNT(prediction_id) AS 'Number of Predictions'
    FROM 
        v_livetipr_prediction
    GROUP BY 
        Date
    ORDER BY 
        Date ASC;
    """
    number_predictions_per_day_data = pd.read_sql(sql_query, connection)
    number_predictions_per_day_data = convert_data_types(number_predictions_per_day_data)
    return number_predictions_per_day_data

def number_predictions_per_community_data(connection):
    sql_query = """
        SELECT 
            p.community_id, 
            COUNT(p.prediction_id) AS number_of_predictions,
            c.community_name,
            c.name
        FROM 
            v_livetipr_prediction AS p
        INNER JOIN 
            communityDetails AS c ON p.community_id = c.community_id
        GROUP BY 
            p.community_id, c.community_name, c.name
        ORDER BY 
            number_of_predictions DESC
        LIMIT 50;
    """
    number_predictions_per_community_data = pd.read_sql(sql_query, connection)
    number_predictions_per_community_data = convert_data_types(number_predictions_per_community_data)
    return number_predictions_per_community_data


########## Game Analytics #######
def livetipr_history_data(connection):
    sql_query = "SELECT * FROM v_history_data"  
    livetipr_history_data = pd.read_sql(sql_query, connection)
    livetipr_history_data = convert_data_types(livetipr_history_data)
    return livetipr_history_data

## Champions league data for 2018-2023  ##
def livetipr_championsleague_data(connection):
    sql_query = """
        SELECT * 
        FROM v_history_data 
        WHERE league_id = 2 
        AND year BETWEEN 2018 AND 2023
        AND (
            status NOT IN ('Cancelled', 'Postponed', 'Suspended', 'Abandoned', 'Not Started') 
            OR short_status NOT IN ('CANCELLED', 'POSTPONED', 'SUSPENDED', 'ABANDONED', 'NS')
        )
    """
    livetipr_championsleague_data = pd.read_sql(sql_query, connection)
    return livetipr_championsleague_data



