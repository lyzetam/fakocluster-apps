import os
import sys
import logging
import mysql.connector
from mysql.connector import Error

# Print sys.path for debugging
print("Python sys.path before adding paths:")
print("\n".join(sys.path))

# Dynamically adjust sys.path to include required directories
current_file_path = os.path.abspath(os.path.dirname(__file__))
base_path = os.path.abspath(os.path.join(current_file_path, '../../'))  # Corrected base path

# Add directories to sys.path
externalconnections_path = os.path.join(base_path, 'Scripts/externalconnections')
datafetch_path = os.path.join(base_path, 'Scripts/datafetch')

sys.path.insert(0, externalconnections_path)
sys.path.insert(0, datafetch_path)

# Print updated sys.path for debugging
print("Python sys.path after adding paths:")
print("\n".join(sys.path))

# Check if fetch_secrets_from_aws.py exists in the added path
print(f"Checking if fetch_secrets_from_aws.py exists in {externalconnections_path}:")
print(os.path.exists(os.path.join(externalconnections_path, 'fetch_secrets_from_aws.py')))

# Import custom modules
from fetch_secrets_from_aws import get_secret
from aws_secrets_manager_client import create_secrets_manager_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_to_database():
    """
    Connect to the MySQL database using credentials from AWS Secrets Manager.
    """
    try:
        # Retrieve the database credentials from AWS Secrets Manager
        secret_name = "katikaa/views/mysql_db_credentials"
        secret_dict = get_secret(secret_name)

        # Connect to the database using credentials from Secrets Manager
        connection = mysql.connector.connect(
            host=secret_dict['host'],
            port=int(secret_dict['port']),
            user=secret_dict['username'],
            password=secret_dict['password'],
            database=secret_dict['database']
        )

        logging.info('Trying to connect to the database...')
        if connection.is_connected():
            logging.info('Successfully connected to the database')
            return connection
        else:
            logging.warning('Connection object created but not connected to the database.')
    except Error as err:
        logging.error(f'Error occurred: {err}', exc_info=True)
        raise Exception(f"Error connecting to the database: {err}")

    return None


# Testing in terminal
# if __name__ == "__main__":
#     try:
#         connection = connect_to_database()
#         if connection:
#             print("Database connection test successful.")
#             connection.close()
#             print("Database connection closed.")
#     except Exception as e:
#         print(f"Database connection test failed: {e}")