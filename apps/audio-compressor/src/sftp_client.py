"""SFTP client for audio file retrieval"""
import logging
import re
import time
from typing import List, Dict, Optional, Tuple
import paramiko
from . import config
from .exceptions import SFTPConnectionError, AudioDownloadError

logger = logging.getLogger(__name__)


class SFTPClient:
    """SFTP client with directory scanning and file download capabilities"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        """Initialize SFTP client with connection parameters"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        
    def connect(self) -> None:
        """Establish SFTP connection with retry logic"""
        logger.info(f"Connecting to SFTP server {self.host}:{self.port}")
        
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=30,
                    look_for_keys=False,
                    allow_agent=False
                )
                
                self.sftp = self.client.open_sftp()
                logger.info("Successfully connected to SFTP server")
                return
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt}/{config.MAX_RETRIES} failed: {e}")
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_DELAY * attempt)
                else:
                    raise SFTPConnectionError(f"Failed to connect after {config.MAX_RETRIES} attempts: {e}")
    
    def disconnect(self) -> None:
        """Close SFTP connection"""
        if self.sftp:
            self.sftp.close()
            logger.debug("SFTP connection closed")
        if self.client:
            self.client.close()
            logger.debug("SSH client closed")
    
    def list_audio_directories(self, remote_path: str) -> List[str]:
        """
        List directories matching the audio pattern (MM-DD-YY or MM-DD-YY-NN)
        
        Args:
            remote_path: Base path on SFTP server to scan
            
        Returns:
            List of directory names matching the pattern
        """
        if not self.sftp:
            raise SFTPConnectionError("Not connected to SFTP server")
        
        logger.info(f"Scanning {remote_path} for audio directories")
        pattern = re.compile(config.DIR_PATTERN)
        matching_dirs = []
        
        try:
            # List all items in the remote path
            items = self.sftp.listdir_attr(remote_path)
            
            for item in items:
                # Check if it's a directory and matches the pattern
                if paramiko.sftp_attr.S_ISDIR(item.st_mode):
                    if pattern.match(item.filename):
                        matching_dirs.append(item.filename)
                        logger.debug(f"Found matching directory: {item.filename}")
            
            matching_dirs.sort()  # Sort chronologically
            logger.info(f"Found {len(matching_dirs)} matching directories")
            return matching_dirs
            
        except Exception as e:
            logger.error(f"Failed to list directories in {remote_path}: {e}")
            raise SFTPConnectionError(f"Failed to list directories: {e}")
    
    def check_file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the SFTP server"""
        if not self.sftp:
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            self.sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Error checking file existence {remote_path}: {e}")
            return False
    
    def get_file_size(self, remote_path: str) -> Optional[int]:
        """Get file size in bytes"""
        if not self.sftp:
            raise SFTPConnectionError("Not connected to SFTP server")
        
        try:
            stat = self.sftp.stat(remote_path)
            return stat.st_size
        except Exception as e:
            logger.warning(f"Failed to get file size for {remote_path}: {e}")
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> Tuple[bool, int]:
        """
        Download a file from SFTP server with retry logic
        
        Args:
            remote_path: Path to file on SFTP server
            local_path: Path to save file locally
            
        Returns:
            Tuple of (success: bool, file_size_mb: int)
        """
        if not self.sftp:
            raise SFTPConnectionError("Not connected to SFTP server")
        
        logger.info(f"Downloading {remote_path} to {local_path}")
        
        # Check file size before downloading
        file_size = self.get_file_size(remote_path)
        if file_size:
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"File size: {file_size_mb:.2f} MB")
            
            if file_size_mb > config.MAX_FILE_SIZE_MB:
                logger.warning(f"File size ({file_size_mb:.2f} MB) exceeds limit ({config.MAX_FILE_SIZE_MB} MB)")
                return False, int(file_size_mb)
        else:
            file_size_mb = 0
        
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                self.sftp.get(remote_path, local_path)
                actual_size_mb = file_size_mb if file_size else 0
                logger.info(f"Successfully downloaded {remote_path} ({actual_size_mb:.2f} MB)")
                return True, int(actual_size_mb)
                
            except Exception as e:
                logger.error(f"Download attempt {attempt}/{config.MAX_RETRIES} failed: {e}")
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_DELAY * attempt)
                else:
                    raise AudioDownloadError(f"Failed to download after {config.MAX_RETRIES} attempts: {e}")
        
        return False, 0
    
    def get_directory_info(self, directory: str, remote_base_path: str) -> Dict:
        """
        Get information about a directory and its audio files
        
        Args:
            directory: Directory name (e.g., "10-17-25")
            remote_base_path: Base path on SFTP server
            
        Returns:
            Dictionary with directory info
        """
        if not self.sftp:
            raise SFTPConnectionError("Not connected to SFTP server")
        
        dir_path = f"{remote_base_path}/{directory}"
        audio_path = f"{dir_path}/{config.AUDIO_FILENAME}"
        metadata_path = f"{dir_path}/{config.METADATA_FILENAME}"
        
        info = {
            "directory": directory,
            "has_audio": self.check_file_exists(audio_path),
            "has_metadata": self.check_file_exists(metadata_path),
            "audio_path": audio_path if self.check_file_exists(audio_path) else None,
            "metadata_path": metadata_path if self.check_file_exists(metadata_path) else None,
        }
        
        if info["has_audio"]:
            info["audio_size_mb"] = (self.get_file_size(audio_path) or 0) / (1024 * 1024)
        
        return info
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
