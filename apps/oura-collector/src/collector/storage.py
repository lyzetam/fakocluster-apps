"""Data storage handlers"""
import os
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DataStorage:
    """Handle data storage to files"""
    
    def __init__(self, data_dir: str = '/data', output_format: str = 'json'):
        """Initialize storage handler
        
        Args:
            data_dir: Directory to store data files
            output_format: Output format ('json' or 'csv')
        """
        self.data_dir = Path(data_dir)
        self.output_format = output_format.lower()
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            self.data_dir,
            self.data_dir / 'sleep',
            self.data_dir / 'activity',
            self.data_dir / 'readiness',
            self.data_dir / 'daily_summaries',
            self.data_dir / 'raw'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def save_data(self, data: List[Dict[str, Any]], data_type: str, 
                  raw: bool = False) -> str:
        """Save data to file
        
        Args:
            data: Data to save
            data_type: Type of data (sleep, activity, readiness, etc.)
            raw: Whether this is raw or processed data
            
        Returns:
            Path to saved file
        """
        if not data:
            logger.warning(f"No data to save for {data_type}")
            return ""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        subdir = 'raw' if raw else data_type
        
        if self.output_format == 'json':
            return self._save_json(data, subdir, f"{data_type}_{timestamp}.json")
        elif self.output_format == 'csv':
            return self._save_csv(data, subdir, f"{data_type}_{timestamp}.csv")
        else:
            logger.error(f"Unsupported output format: {self.output_format}")
            return ""
    
    def _save_json(self, data: List[Dict], subdir: str, filename: str) -> str:
        """Save data as JSON
        
        Args:
            data: Data to save
            subdir: Subdirectory name
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.data_dir / subdir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(data)} records to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save JSON to {filepath}: {e}")
            return ""
    
    def _save_csv(self, data: List[Dict], subdir: str, filename: str) -> str:
        """Save data as CSV
        
        Args:
            data: Data to save
            subdir: Subdirectory name
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        filepath = self.data_dir / subdir / filename
        
        if not data:
            return ""
        
        try:
            # Get all unique keys from all records
            all_keys = set()
            for record in data:
                all_keys.update(self._flatten_dict(record).keys())
            
            fieldnames = sorted(all_keys)
            
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for record in data:
                    flattened = self._flatten_dict(record)
                    writer.writerow(flattened)
            
            logger.info(f"Saved {len(data)} records to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save CSV to {filepath}: {e}")
            return ""
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary for CSV export
        
        Args:
            d: Dictionary to flatten
            parent_key: Parent key for recursion
            sep: Separator for keys
            
        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict) and k != 'raw_data':  # Don't flatten raw_data
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
                
        return dict(items)
    
    def save_collection_summary(self, summary: Dict[str, Any]) -> str:
        """Save collection summary
        
        Args:
            summary: Collection summary data
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = self.data_dir / f"collection_summary_{timestamp}.json"
        
        try:
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"Saved collection summary to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save collection summary: {e}")
            return ""
    
    def list_saved_files(self, data_type: Optional[str] = None) -> List[str]:
        """List saved files
        
        Args:
            data_type: Optional filter by data type
            
        Returns:
            List of file paths
        """
        if data_type:
            pattern = f"**/{data_type}*"
        else:
            pattern = "**/*"
        
        files = []
        for file_path in self.data_dir.glob(pattern):
            if file_path.is_file():
                files.append(str(file_path))
        
        return sorted(files)