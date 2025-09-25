# Add the directory containing aws_secrets_manager_client.py to sys.path
import sys
sys.path.insert(0, '../Scripts')
sys.path.insert(0, '../Scripts/externalconnections')
sys.path.insert(0, '../Scripts/datafetch')

import pandas as pd
from dbconnect import connect_to_database  
#from data_queries import *  # data_queries.py file with these functions



connection = connect_to_database()

def convert_data_types(df):
    # List of columns that are considered ID variables
    id_columns = [
        "user_id", 
        "created_by", 
        "last_modified_by", 
        "email_id",
        "facebook_id", 
        "fp_otp", 
        "gmail_id", 
        "phone_number", 
        "prediction_id",
        "community_id",	
        "fixture_id",
        "position",
        "rec_id",
        "CommunityAdminId",
        "CommunityUserId",
        "CommunityId",
        "FixtureId",
        "UserId",
        "PredictionId",
        "CommunityUserPredictionId"
    ]
    
    date_columns = ["creation_date", 
                    "created_date",
                    "last_modified_date",
                    "join_date",
                    "process_date",
                    "UserCreateDate",
                    "CommunityCreateDate",
                    "FixtureCreateDate"]
    
    for col in id_columns:
        if col in df.columns:
            # Convert the column to string, but keep NaN values as NaN
            df[col] = df[col].where(df[col].isna(), df[col].astype(str))
            
    for col in date_columns:
        if col in df.columns:
            # Convert to datetime format
            df[col] = pd.to_datetime(df[col])
            # Extract the date part:
            df[col + '_date'] = df[col].dt.date

    
    return df


