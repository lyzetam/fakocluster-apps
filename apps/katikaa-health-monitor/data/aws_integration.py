"""
Consolidated AWS Integration Module
Handles AWS Secrets Manager and S3 connections using environment variables
"""

import os
import json
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AWSIntegration:
    """Centralized AWS integration for Secrets Manager and S3"""
    
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        self._secrets_client = None
        self._s3_client = None
        
        # Validate AWS credentials are available
        if not all([self.access_key_id, self.secret_access_key]):
            logger.warning("AWS credentials not found in environment variables")
    
    def _create_aws_session(self) -> boto3.Session:
        """Create AWS session with credentials"""
        if not all([self.access_key_id, self.secret_access_key]):
            raise ValueError("AWS credentials not configured. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        
        return boto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region
        )
    
    @property
    def secrets_client(self):
        """Lazy-loaded Secrets Manager client"""
        if self._secrets_client is None:
            try:
                session = self._create_aws_session()
                self._secrets_client = session.client('secretsmanager')
                logger.info("AWS Secrets Manager client created successfully")
            except Exception as e:
                logger.error(f"Failed to create Secrets Manager client: {e}")
                raise
        return self._secrets_client
    
    @property
    def s3_client(self):
        """Lazy-loaded S3 client"""
        if self._s3_client is None:
            try:
                session = self._create_aws_session()
                self._s3_client = session.client('s3')
                logger.info("AWS S3 client created successfully")
            except Exception as e:
                logger.error(f"Failed to create S3 client: {e}")
                raise
        return self._s3_client
    
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Fetch a secret from AWS Secrets Manager
        
        Args:
            secret_name: Name or ARN of the secret to retrieve
            
        Returns:
            Dictionary containing the parsed secret data
            
        Raises:
            ClientError: If AWS error occurs
            ValueError: If secret is empty or invalid JSON
        """
        try:
            logger.info(f"Fetching secret: {secret_name}")
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            
            secret_string = response.get('SecretString')
            if not secret_string:
                raise ValueError(f"Secret '{secret_name}' is empty or does not contain a valid 'SecretString'")
            
            secret_data = json.loads(secret_string)
            logger.info(f"Successfully fetched secret: {secret_name}")
            return secret_data
            
        except ClientError as e:
            logger.error(f"Error retrieving secret '{secret_name}': {e}")
            raise
        except json.JSONDecodeError as e:
            error_msg = f"Error parsing secret '{secret_name}' as JSON: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_database_credentials(self, secret_name: str = "katikaa/views/mysql_db_credentials") -> Dict[str, str]:
        """
        Get database credentials from AWS Secrets Manager
        
        Args:
            secret_name: Name of the secret containing database credentials
            
        Returns:
            Dictionary with database connection parameters
        """
        try:
            credentials = self.get_secret(secret_name)
            
            # Map common secret key variations to standard names
            db_config = {
                'host': credentials.get('host') or credentials.get('hostname'),
                'port': int(credentials.get('port', 3306)),
                'database': credentials.get('database') or credentials.get('dbname'),
                'user': credentials.get('username') or credentials.get('user'),
                'password': credentials.get('password')
            }
            
            # Validate required fields
            required_fields = ['host', 'database', 'user', 'password']
            missing_fields = [field for field in required_fields if not db_config.get(field)]
            
            if missing_fields:
                raise ValueError(f"Missing required database fields in secret: {missing_fields}")
            
            return db_config
            
        except Exception as e:
            logger.error(f"Failed to get database credentials: {e}")
            raise
    
    def download_file_from_s3(self, bucket_name: str, object_key: str, local_path: str) -> bool:
        """
        Download a file from S3 to local storage
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key of the object in S3
            local_path: Local file path to save the downloaded file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading {object_key} from bucket {bucket_name} to {local_path}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(bucket_name, object_key, local_path)
            logger.info(f"Successfully downloaded {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to download {object_key} from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            return False
    
    def upload_file_to_s3(self, local_path: str, bucket_name: str, object_key: str) -> bool:
        """
        Upload a file to S3
        
        Args:
            local_path: Path to the local file to upload
            bucket_name: Name of the S3 bucket
            object_key: Key for the object in S3
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(local_path):
                logger.error(f"Local file does not exist: {local_path}")
                return False
            
            logger.info(f"Uploading {local_path} to bucket {bucket_name} as {object_key}")
            self.s3_client.upload_file(local_path, bucket_name, object_key)
            logger.info(f"Successfully uploaded {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload {local_path} to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            return False
    
    def list_s3_objects(self, bucket_name: str, prefix: str = "") -> list:
        """
        List objects in an S3 bucket with optional prefix
        
        Args:
            bucket_name: Name of the S3 bucket
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object keys
        """
        try:
            logger.info(f"Listing objects in bucket {bucket_name} with prefix '{prefix}'")
            
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            objects = response.get('Contents', [])
            object_keys = [obj['Key'] for obj in objects]
            
            logger.info(f"Found {len(object_keys)} objects")
            return object_keys
            
        except ClientError as e:
            logger.error(f"Failed to list objects in bucket {bucket_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing S3 objects: {e}")
            return []
    
    def get_s3_object_content(self, bucket_name: str, object_key: str) -> Optional[bytes]:
        """
        Get the content of an S3 object
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key of the object in S3
            
        Returns:
            Object content as bytes, or None if failed
        """
        try:
            logger.info(f"Getting content of {object_key} from bucket {bucket_name}")
            
            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response['Body'].read()
            
            logger.info(f"Successfully retrieved {len(content)} bytes from {object_key}")
            return content
            
        except ClientError as e:
            logger.error(f"Failed to get object {object_key} from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting S3 object: {e}")
            return None
    
    def test_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity to AWS services
        
        Returns:
            Dictionary with service connectivity status
        """
        results = {
            'secrets_manager': False,
            's3': False
        }
        
        # Test Secrets Manager
        try:
            self.secrets_client.list_secrets(MaxResults=1)
            results['secrets_manager'] = True
            logger.info("Secrets Manager connectivity: OK")
        except Exception as e:
            logger.error(f"Secrets Manager connectivity failed: {e}")
        
        # Test S3
        try:
            self.s3_client.list_buckets()
            results['s3'] = True
            logger.info("S3 connectivity: OK")
        except Exception as e:
            logger.error(f"S3 connectivity failed: {e}")
        
        return results

# Global instance
aws_integration = AWSIntegration()

# Convenience functions for backward compatibility
def get_secret(secret_name: str) -> Dict[str, Any]:
    """Get secret from AWS Secrets Manager"""
    return aws_integration.get_secret(secret_name)

def create_secrets_manager_client():
    """Create Secrets Manager client"""
    return aws_integration.secrets_client

def create_s3_client():
    """Create S3 client"""
    return aws_integration.s3_client
