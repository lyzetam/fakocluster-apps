"""Oura Ring API client"""
import logging
import time
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import OURA_API_BASE_URL, API_TIMEOUT, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)

class OuraAPIClient:
    """Client for interacting with Oura Ring API v2"""
    
    def __init__(self, access_token: str):
        """Initialize Oura API client
        
        Args:
            access_token: Personal access token for Oura API
        """
        self.access_token = access_token
        self.base_url = OURA_API_BASE_URL
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Set auth header
        session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with error handling
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.RequestException: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f"Making request to {endpoint} with params: {params}")
            response = self.session.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"Received {len(data.get('data', []))} records from {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def get_sleep_data(self, start_date: Union[str, date], 
                      end_date: Union[str, date]) -> List[Dict[str, Any]]:
        """Get sleep data for date range
        
        Args:
            start_date: Start date (YYYY-MM-DD format or date object)
            end_date: End date (YYYY-MM-DD format or date object)
            
        Returns:
            List of sleep records
        """
        params = {
            'start_date': str(start_date),
            'end_date': str(end_date)
        }
        
        logger.info(f"Fetching sleep data from {start_date} to {end_date}")
        response = self._make_request('usercollection/sleep', params)
        return response.get('data', [])
    
    def get_activity_data(self, start_date: Union[str, date], 
                         end_date: Union[str, date]) -> List[Dict[str, Any]]:
        """Get daily activity data for date range
        
        Args:
            start_date: Start date (YYYY-MM-DD format or date object)
            end_date: End date (YYYY-MM-DD format or date object)
            
        Returns:
            List of activity records
        """
        params = {
            'start_date': str(start_date),
            'end_date': str(end_date)
        }
        
        logger.info(f"Fetching activity data from {start_date} to {end_date}")
        response = self._make_request('usercollection/daily_activity', params)
        return response.get('data', [])
    
    def get_readiness_data(self, start_date: Union[str, date], 
                          end_date: Union[str, date]) -> List[Dict[str, Any]]:
        """Get daily readiness data for date range
        
        Args:
            start_date: Start date (YYYY-MM-DD format or date object)
            end_date: End date (YYYY-MM-DD format or date object)
            
        Returns:
            List of readiness records
        """
        params = {
            'start_date': str(start_date),
            'end_date': str(end_date)
        }
        
        logger.info(f"Fetching readiness data from {start_date} to {end_date}")
        response = self._make_request('usercollection/daily_readiness', params)
        return response.get('data', [])
    
    def get_heart_rate_data(self, start_datetime: Union[str, datetime], 
                           end_datetime: Union[str, datetime]) -> List[Dict[str, Any]]:
        """Get heart rate data for datetime range
        
        Args:
            start_datetime: Start datetime (ISO format or datetime object)
            end_datetime: End datetime (ISO format or datetime object)
            
        Returns:
            List of heart rate records
        """
        if isinstance(start_datetime, datetime):
            start_datetime = start_datetime.isoformat()
        if isinstance(end_datetime, datetime):
            end_datetime = end_datetime.isoformat()
            
        params = {
            'start_datetime': start_datetime,
            'end_datetime': end_datetime
        }
        
        logger.info(f"Fetching heart rate data from {start_datetime} to {end_datetime}")
        response = self._make_request('usercollection/heartrate', params)
        return response.get('data', [])
    
    def get_workout_data(self, start_date: Union[str, date], 
                        end_date: Union[str, date]) -> List[Dict[str, Any]]:
        """Get workout data for date range
        
        Args:
            start_date: Start date (YYYY-MM-DD format or date object)
            end_date: End date (YYYY-MM-DD format or date object)
            
        Returns:
            List of workout records
        """
        params = {
            'start_date': str(start_date),
            'end_date': str(end_date)
        }
        
        logger.info(f"Fetching workout data from {start_date} to {end_date}")
        response = self._make_request('usercollection/workout', params)
        return response.get('data', [])
    
    def get_spo2_data(self, start_date: Union[str, date], 
                     end_date: Union[str, date]) -> List[Dict[str, Any]]:
        """Get SpO2 (blood oxygen) data for date range
        
        Args:
            start_date: Start date (YYYY-MM-DD format or date object)
            end_date: End date (YYYY-MM-DD format or date object)
            
        Returns:
            List of SpO2 records
        """
        params = {
            'start_date': str(start_date),
            'end_date': str(end_date)
        }
        
        logger.info(f"Fetching SpO2 data from {start_date} to {end_date}")
        response = self._make_request('usercollection/spo2', params)
        return response.get('data', [])
    
    def test_connection(self) -> bool:
        """Test API connection and token validity
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch minimal data to test connection
            response = self._make_request('usercollection/personal_info')
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False