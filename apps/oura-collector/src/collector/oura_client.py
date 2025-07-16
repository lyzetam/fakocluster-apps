"""Improved Oura Ring API client with pagination and full endpoint support"""
import logging
import time
from datetime import datetime, date, timedelta
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
        
    def __enter__(self) -> 'OuraAPIClient':
        """Enter context manager"""
        return self
        
    def __exit__(self, *_) -> None:
        """Exit context manager"""
        self.close()
        
    def close(self):
        """Close the requests session"""
        self.session.close()
        
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
    
    def _format_dates(self, start_date: Optional[Union[str, date]], 
                     end_date: Optional[Union[str, date]]) -> tuple[str, str]:
        """Format and validate date parameters
        
        Args:
            start_date: Start date (string or date object)
            end_date: End date (string or date object)
            
        Returns:
            Tuple of (start_date_str, end_date_str)
            
        Raises:
            ValueError: If start_date is after end_date
        """
        # Handle end date
        if end_date is None:
            end = date.today()
        elif isinstance(end_date, str):
            end = date.fromisoformat(end_date)
        else:
            end = end_date
            
        # Handle start date
        if start_date is None:
            start = end - timedelta(days=1)
        elif isinstance(start_date, str):
            start = date.fromisoformat(start_date)
        else:
            start = start_date
            
        if start > end:
            raise ValueError(f"Start date ({start}) is after end date ({end})")
            
        return str(start), str(end)
    
    def _format_datetimes(self, start_datetime: Optional[Union[str, datetime]], 
                         end_datetime: Optional[Union[str, datetime]]) -> tuple[str, str]:
        """Format and validate datetime parameters
        
        Args:
            start_datetime: Start datetime (string or datetime object)
            end_datetime: End datetime (string or datetime object)
            
        Returns:
            Tuple of (start_datetime_str, end_datetime_str)
            
        Raises:
            ValueError: If start_datetime is after end_datetime
        """
        # Handle end datetime
        if end_datetime is None:
            end = datetime.now()
        elif isinstance(end_datetime, str):
            end = datetime.fromisoformat(end_datetime)
        else:
            end = end_datetime
            
        # Handle start datetime
        if start_datetime is None:
            start = end - timedelta(days=1)
        elif isinstance(start_datetime, str):
            start = datetime.fromisoformat(start_datetime)
        else:
            start = start_datetime
            
        if start > end:
            raise ValueError(f"Start datetime ({start}) is after end datetime ({end})")
            
        # Return ISO format strings
        return start.isoformat(), end.isoformat()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with error handling (single page)
        
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
            logger.debug(f"Received response from {endpoint}")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def _make_paginated_request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Make paginated API request to get all results
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            List of all records from all pages
        """
        if params is None:
            params = {}
            
        all_data = []
        next_token = None
        page_count = 0
        
        while True:
            # Add next_token to params if available
            if next_token:
                params['next_token'] = next_token
                
            try:
                response_data = self._make_request(endpoint, params)
                page_count += 1
                
                # Extract data from response
                page_data = response_data.get('data', [])
                all_data.extend(page_data)
                
                logger.debug(f"Page {page_count}: Retrieved {len(page_data)} records from {endpoint}")
                
                # Check for next page
                next_token = response_data.get('next_token')
                if not next_token:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to retrieve page {page_count + 1} from {endpoint}: {e}")
                # Return what we have so far rather than failing completely
                if all_data:
                    logger.warning(f"Returning partial results: {len(all_data)} records")
                    break
                else:
                    raise
        
        logger.info(f"Retrieved total of {len(all_data)} records from {endpoint} across {page_count} pages")
        return all_data
    
    # Core Data Endpoints
    
    def get_personal_info(self) -> Dict[str, Any]:
        """Get personal info data
        
        Returns:
            Personal information dictionary
        """
        logger.info("Fetching personal info")
        return self._make_request('usercollection/personal_info')
    
    def get_daily_sleep(self, start_date: Optional[Union[str, date]] = None,
                       end_date: Optional[Union[str, date]] = None,
                       document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily sleep data (scores and contributors)
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of sleep score records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching daily sleep document: {document_id}")
            return self._make_request(f'usercollection/daily_sleep/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching daily sleep data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_sleep', params)
    
    def get_sleep_periods(self, start_date: Optional[Union[str, date]] = None,
                         end_date: Optional[Union[str, date]] = None,
                         document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get detailed sleep period data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of sleep period records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching sleep period document: {document_id}")
            return self._make_request(f'usercollection/sleep/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching sleep period data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/sleep', params)
    
    def get_daily_activity(self, start_date: Optional[Union[str, date]] = None,
                          end_date: Optional[Union[str, date]] = None,
                          document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily activity data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of activity records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching activity document: {document_id}")
            return self._make_request(f'usercollection/daily_activity/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching activity data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_activity', params)
    
    def get_daily_readiness(self, start_date: Optional[Union[str, date]] = None,
                           end_date: Optional[Union[str, date]] = None,
                           document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily readiness data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of readiness records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching readiness document: {document_id}")
            return self._make_request(f'usercollection/daily_readiness/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching readiness data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_readiness', params)
    
    def get_heart_rate(self, start_datetime: Optional[Union[str, datetime]] = None,
                      end_datetime: Optional[Union[str, datetime]] = None) -> List[Dict[str, Any]]:
        """Get heart rate time series data
        
        Args:
            start_datetime: Start datetime
            end_datetime: End datetime
            
        Returns:
            List of heart rate records
        """
        start_str, end_str = self._format_datetimes(start_datetime, end_datetime)
        params = {'start_datetime': start_str, 'end_datetime': end_str}
        
        logger.info(f"Fetching heart rate data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/heartrate', params)
    
    def get_workouts(self, start_date: Optional[Union[str, date]] = None,
                    end_date: Optional[Union[str, date]] = None,
                    document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get workout data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of workout records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching workout document: {document_id}")
            return self._make_request(f'usercollection/workout/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching workout data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/workout', params)
    
    def get_daily_spo2(self, start_date: Optional[Union[str, date]] = None,
                      end_date: Optional[Union[str, date]] = None,
                      document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily SpO2 (blood oxygen) data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of SpO2 records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching SpO2 document: {document_id}")
            return self._make_request(f'usercollection/daily_spo2/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching SpO2 data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_spo2', params)
    
    def get_sessions(self, start_date: Optional[Union[str, date]] = None,
                    end_date: Optional[Union[str, date]] = None,
                    document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get meditation/breathing session data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of session records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching session document: {document_id}")
            return self._make_request(f'usercollection/session/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching session data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/session', params)
    
    def get_tags(self, start_date: Optional[Union[str, date]] = None,
                end_date: Optional[Union[str, date]] = None,
                document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get tag data (deprecated - use enhanced_tag)
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of tag records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching tag document: {document_id}")
            return self._make_request(f'usercollection/tag/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching tag data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/tag', params)
    
    def get_enhanced_tags(self, start_date: Optional[Union[str, date]] = None,
                         end_date: Optional[Union[str, date]] = None,
                         document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get enhanced tag data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of enhanced tag records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching enhanced tag document: {document_id}")
            return self._make_request(f'usercollection/enhanced_tag/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching enhanced tag data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/enhanced_tag', params)
    
    def get_daily_stress(self, start_date: Optional[Union[str, date]] = None,
                        end_date: Optional[Union[str, date]] = None,
                        document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily stress data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of stress records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching stress document: {document_id}")
            return self._make_request(f'usercollection/daily_stress/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching stress data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_stress', params)
    
    def get_rest_mode_periods(self, start_date: Optional[Union[str, date]] = None,
                             end_date: Optional[Union[str, date]] = None,
                             document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get rest mode period data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of rest mode records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching rest mode document: {document_id}")
            return self._make_request(f'usercollection/rest_mode_period/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching rest mode data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/rest_mode_period', params)
    
    def get_ring_configuration(self, start_date: Optional[Union[str, date]] = None,
                              end_date: Optional[Union[str, date]] = None,
                              document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get ring configuration data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of ring configuration records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching ring configuration document: {document_id}")
            return self._make_request(f'usercollection/ring_configuration/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching ring configuration from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/ring_configuration', params)
    
    def get_sleep_time(self, start_date: Optional[Union[str, date]] = None,
                      end_date: Optional[Union[str, date]] = None,
                      document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get recommended sleep time data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of sleep time records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching sleep time document: {document_id}")
            return self._make_request(f'usercollection/sleep_time/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching sleep time data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/sleep_time', params)
    
    def get_vo2_max(self, start_date: Optional[Union[str, date]] = None,
                    end_date: Optional[Union[str, date]] = None,
                    document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get VO2 max data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of VO2 max records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching VO2 max document: {document_id}")
            return self._make_request(f'usercollection/vO2_max/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching VO2 max data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/vO2_max', params)
    
    def get_daily_cardiovascular_age(self, start_date: Optional[Union[str, date]] = None,
                                   end_date: Optional[Union[str, date]] = None,
                                   document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily cardiovascular age data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of cardiovascular age records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching cardiovascular age document: {document_id}")
            return self._make_request(f'usercollection/daily_cardiovascular_age/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching cardiovascular age data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_cardiovascular_age', params)
    
    def get_daily_resilience(self, start_date: Optional[Union[str, date]] = None,
                           end_date: Optional[Union[str, date]] = None,
                           document_id: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Get daily resilience data
        
        Args:
            start_date: Start date
            end_date: End date
            document_id: Specific document ID to fetch
            
        Returns:
            List of resilience records or single record if document_id provided
        """
        if document_id:
            logger.info(f"Fetching resilience document: {document_id}")
            return self._make_request(f'usercollection/daily_resilience/{document_id}')
            
        start_str, end_str = self._format_dates(start_date, end_date)
        params = {'start_date': start_str, 'end_date': end_str}
        
        logger.info(f"Fetching resilience data from {start_str} to {end_str}")
        return self._make_paginated_request('usercollection/daily_resilience', params)
    
    def test_connection(self) -> bool:
        """Test API connection and token validity
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch personal info to test connection
            self.get_personal_info()
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    # Backward compatibility aliases for your existing code
    def get_sleep_data(self, start_date, end_date):
        """Alias for get_sleep_periods for backward compatibility"""
        return self.get_sleep_periods(start_date, end_date)
    
    def get_activity_data(self, start_date, end_date):
        """Alias for get_daily_activity for backward compatibility"""
        return self.get_daily_activity(start_date, end_date)
    
    def get_readiness_data(self, start_date, end_date):
        """Alias for get_daily_readiness for backward compatibility"""
        return self.get_daily_readiness(start_date, end_date)
    
    def get_heart_rate_data(self, start_datetime, end_datetime):
        """Alias for get_heart_rate for backward compatibility"""
        return self.get_heart_rate(start_datetime, end_datetime)
    
    def get_workout_data(self, start_date, end_date):
        """Alias for get_workouts for backward compatibility"""
        return self.get_workouts(start_date, end_date)
    
    def get_spo2_data(self, start_date, end_date):
        """Alias for get_daily_spo2 for backward compatibility"""
        return self.get_daily_spo2(start_date, end_date)
