"""Storage management for compressed audio files and manifest tracking"""
import logging
import os
import json
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from . import config
from .exceptions import StorageError

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def save_compressed_file(self, source_path: str, directory_name: str) -> str:
        """Save compressed audio file to storage backend"""
        pass
    
    @abstractmethod
    def save_metadata_file(self, source_path: str, directory_name: str) -> Optional[str]:
        """Save metadata file to storage backend"""
        pass
    
    @abstractmethod
    def is_processed(self, directory_name: str) -> bool:
        """Check if directory has already been processed"""
        pass
    
    @abstractmethod
    def get_output_path(self, directory_name: str, file_type: str = 'compressed') -> str:
        """Get output path for a file"""
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage (PVC)"""
    
    def __init__(self, output_dir: str):
        """Initialize local storage manager"""
        self.output_dir = output_dir
        self.manifest_path = os.path.join(output_dir, 'manifest.json')
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """Create output directory if it doesn't exist"""
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            logger.debug(f"Output directory ready: {self.output_dir}")
        except Exception as e:
            raise StorageError(f"Failed to create output directory: {e}")
    
    def is_processed(self, directory_name: str) -> bool:
        """Check if directory has already been processed"""
        compressed_filename = f"{directory_name}_compressed.{config.AUDIO_FORMAT}"
        compressed_path = os.path.join(self.output_dir, compressed_filename)
        
        exists = os.path.exists(compressed_path)
        if exists:
            logger.debug(f"{directory_name} already processed (file exists)")
        return exists
    
    def get_output_path(self, directory_name: str, file_type: str = 'compressed') -> str:
        """Get output path for a file"""
        if file_type == 'compressed':
            filename = f"{directory_name}_compressed.{config.AUDIO_FORMAT}"
        elif file_type == 'metadata':
            filename = f"{directory_name}_meta.xml"
        else:
            raise ValueError(f"Unknown file type: {file_type}")
        
        return os.path.join(self.output_dir, filename)
    
    def save_compressed_file(self, source_path: str, directory_name: str) -> str:
        """Save compressed file to local PVC"""
        output_path = self.get_output_path(directory_name, 'compressed')
        
        try:
            shutil.copy2(source_path, output_path)
            logger.info(f"Saved compressed file to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save compressed file: {e}")
            raise StorageError(f"Cannot save compressed file: {e}")
    
    def save_metadata_file(self, source_path: str, directory_name: str) -> Optional[str]:
        """Save metadata file to local PVC"""
        if not config.COPY_METADATA:
            logger.debug("Metadata copying disabled")
            return None
        
        output_path = self.get_output_path(directory_name, 'metadata')
        
        try:
            shutil.copy2(source_path, output_path)
            logger.info(f"Saved metadata file to {output_path}")
            return output_path
        except Exception as e:
            logger.warning(f"Failed to save metadata file: {e}")
            return None
    
    def load_manifest(self) -> Dict:
        """Load existing manifest or create new one"""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, 'r') as f:
                    manifest = json.load(f)
                logger.info(f"Loaded manifest with {len(manifest.get('directories', []))} entries")
                return manifest
            except Exception as e:
                logger.warning(f"Failed to load manifest, creating new one: {e}")
        
        # Create new manifest
        return {
            "last_run": None,
            "total_processed": 0,
            "total_failed": 0,
            "total_space_saved_gb": 0.0,
            "directories": []
        }
    
    def save_manifest(self, manifest: Dict) -> None:
        """Save manifest to disk"""
        try:
            with open(self.manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            logger.debug("Manifest saved successfully")
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
            raise StorageError(f"Cannot save manifest: {e}")
    
    def update_manifest(
        self,
        directory_name: str,
        status: str,
        original_size_mb: float = 0,
        compressed_size_mb: float = 0,
        error_message: Optional[str] = None,
        storage_location: str = 'local'
    ) -> None:
        """Update manifest with processing result"""
        manifest = self.load_manifest()
        
        # Calculate compression ratio
        compression_ratio = 0.0
        if compressed_size_mb > 0:
            compression_ratio = original_size_mb / compressed_size_mb
        
        # Create entry
        entry = {
            "directory": directory_name,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "original_size_mb": round(original_size_mb, 2),
            "compressed_size_mb": round(compressed_size_mb, 2),
            "compression_ratio": round(compression_ratio, 1),
            "status": status,
            "storage_location": storage_location
        }
        
        if error_message:
            entry["error"] = error_message
        
        # Update statistics
        manifest["last_run"] = datetime.utcnow().isoformat() + "Z"
        
        if status == "success":
            manifest["total_processed"] += 1
            space_saved_gb = (original_size_mb - compressed_size_mb) / 1024
            manifest["total_space_saved_gb"] = round(
                manifest.get("total_space_saved_gb", 0) + space_saved_gb, 2
            )
        else:
            manifest["total_failed"] += 1
        
        # Add or update directory entry
        existing_idx = None
        for idx, item in enumerate(manifest.get("directories", [])):
            if item.get("directory") == directory_name:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            manifest["directories"][existing_idx] = entry
        else:
            manifest["directories"].append(entry)
        
        # Keep only last 1000 entries
        if len(manifest["directories"]) > 1000:
            manifest["directories"] = manifest["directories"][-1000:]
        
        self.save_manifest(manifest)
    
    def get_statistics(self) -> Dict:
        """Get storage statistics"""
        manifest = self.load_manifest()
        
        total_files = len([f for f in os.listdir(self.output_dir) 
                          if f.endswith(f'_compressed.{config.AUDIO_FORMAT}')])
        
        total_size_mb = 0
        for filename in os.listdir(self.output_dir):
            if filename.endswith(f'_compressed.{config.AUDIO_FORMAT}'):
                file_path = os.path.join(self.output_dir, filename)
                try:
                    total_size_mb += os.path.getsize(file_path) / (1024 * 1024)
                except:
                    pass
        
        return {
            "total_files": total_files,
            "total_size_mb": round(total_size_mb, 2),
            "total_size_gb": round(total_size_mb / 1024, 2),
            "total_processed": manifest.get("total_processed", 0),
            "total_failed": manifest.get("total_failed", 0),
            "total_space_saved_gb": manifest.get("total_space_saved_gb", 0),
            "last_run": manifest.get("last_run"),
        }
    
    def cleanup_temp_files(self, temp_dir: str) -> None:
        """Clean up temporary files"""
        if os.path.exists(temp_dir):
            try:
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")
                logger.debug(f"Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")


class SFTPStorage(StorageBackend):
    """SFTP remote storage backend with local fallback"""
    
    def __init__(self, sftp_client, remote_path: str, local_fallback: LocalStorage):
        """
        Initialize SFTP storage backend
        
        Args:
            sftp_client: SFTPClient instance (already connected)
            remote_path: Remote base path for uploads (e.g., '/compressed')
            local_fallback: LocalStorage instance for fallback and manifest
        """
        self.sftp = sftp_client
        self.remote_path = remote_path
        self.local_fallback = local_fallback
        logger.info(f"SFTP storage backend initialized (remote: {remote_path}, fallback: {local_fallback.output_dir})")
    
    def is_processed(self, directory_name: str) -> bool:
        """Check if directory has been processed (checks SFTP first, then local fallback)"""
        # Check SFTP remote first
        compressed_filename = f"{directory_name}_compressed.{config.AUDIO_FORMAT}"
        remote_file_path = f"{self.remote_path}/{compressed_filename}"
        
        try:
            if self.sftp.check_file_exists(remote_file_path):
                logger.debug(f"{directory_name} already processed (exists on SFTP)")
                return True
        except Exception as e:
            logger.warning(f"Error checking SFTP for {directory_name}: {e}")
        
        # Fall back to checking local storage
        return self.local_fallback.is_processed(directory_name)
    
    def get_output_path(self, directory_name: str, file_type: str = 'compressed') -> str:
        """Get remote output path for a file"""
        if file_type == 'compressed':
            filename = f"{directory_name}_compressed.{config.AUDIO_FORMAT}"
        elif file_type == 'metadata':
            filename = f"{directory_name}_meta.xml"
        else:
            raise ValueError(f"Unknown file type: {file_type}")
        
        return f"{self.remote_path}/{filename}"
    
    def save_compressed_file(self, source_path: str, directory_name: str) -> str:
        """
        Save compressed file to SFTP with retry and fallback to local
        
        Returns:
            Path where file was saved (remote or local)
        """
        remote_path = self.get_output_path(directory_name, 'compressed')
        
        # Check for duplicates and get unique filename if needed
        unique_remote_path = self.sftp.get_unique_remote_filename(remote_path)
        
        # Attempt upload with retry
        logger.info(f"Attempting to upload to SFTP: {unique_remote_path}")
        success, final_path = self.sftp.upload_file(
            source_path,
            unique_remote_path,
            retry_attempts=config.UPLOAD_RETRY_ATTEMPTS,
            retry_delay=config.UPLOAD_RETRY_DELAY
        )
        
        if success:
            logger.info(f"✓ Successfully uploaded to SFTP: {final_path}")
            return final_path
        else:
            # Upload failed, fall back to local storage
            logger.warning(f"✗ SFTP upload failed, falling back to local storage")
            try:
                local_path = self.local_fallback.save_compressed_file(source_path, directory_name)
                logger.info(f"✓ Saved to local fallback: {local_path}")
                return local_path
            except Exception as e:
                logger.error(f"✗ Local fallback also failed: {e}")
                raise StorageError(f"Both SFTP and local storage failed: {e}")
    
    def save_metadata_file(self, source_path: str, directory_name: str) -> Optional[str]:
        """Save metadata file to SFTP with fallback to local"""
        if not config.COPY_METADATA:
            logger.debug("Metadata copying disabled")
            return None
        
        remote_path = self.get_output_path(directory_name, 'metadata')
        
        # Check for duplicates and get unique filename if needed
        unique_remote_path = self.sftp.get_unique_remote_filename(remote_path)
        
        # Attempt upload (metadata is not critical, so single attempt)
        logger.info(f"Attempting to upload metadata to SFTP: {unique_remote_path}")
        success, final_path = self.sftp.upload_file(
            source_path,
            unique_remote_path,
            retry_attempts=1,
            retry_delay=config.UPLOAD_RETRY_DELAY
        )
        
        if success:
            logger.info(f"✓ Successfully uploaded metadata to SFTP: {final_path}")
            return final_path
        else:
            # Fall back to local storage for metadata
            logger.warning(f"SFTP metadata upload failed, falling back to local")
            try:
                return self.local_fallback.save_metadata_file(source_path, directory_name)
            except Exception as e:
                logger.warning(f"Local metadata fallback also failed: {e}")
                return None
    
    # Delegate manifest and stats operations to local storage
    def load_manifest(self) -> Dict:
        """Load manifest from local storage"""
        return self.local_fallback.load_manifest()
    
    def save_manifest(self, manifest: Dict) -> None:
        """Save manifest to local storage"""
        return self.local_fallback.save_manifest(manifest)
    
    def update_manifest(
        self,
        directory_name: str,
        status: str,
        original_size_mb: float = 0,
        compressed_size_mb: float = 0,
        error_message: Optional[str] = None,
        storage_location: str = 'sftp'
    ) -> None:
        """Update manifest in local storage"""
        return self.local_fallback.update_manifest(
            directory_name,
            status,
            original_size_mb,
            compressed_size_mb,
            error_message,
            storage_location
        )
    
    def get_statistics(self) -> Dict:
        """Get statistics from local storage manifest"""
        return self.local_fallback.get_statistics()
    
    def cleanup_temp_files(self, temp_dir: str) -> None:
        """Clean up temporary files"""
        return self.local_fallback.cleanup_temp_files(temp_dir)


class StorageFactory:
    """Factory for creating storage backends"""
    
    @staticmethod
    def create_storage(sftp_client=None) -> StorageBackend:
        """
        Create appropriate storage backend based on configuration
        
        Args:
            sftp_client: SFTPClient instance (required for SFTP backend)
            
        Returns:
            StorageBackend instance (LocalStorage or SFTPStorage)
        """
        backend_type = config.STORAGE_BACKEND.lower()
        
        # Always create local storage (used standalone or as fallback)
        local_storage = LocalStorage(config.OUTPUT_DIR)
        
        if backend_type == 'local':
            logger.info(f"Using LOCAL storage backend: {config.OUTPUT_DIR}")
            return local_storage
        
        elif backend_type == 'sftp':
            if sftp_client is None:
                logger.error("SFTP storage backend requires sftp_client parameter")
                logger.warning("Falling back to local storage")
                return local_storage
            
            logger.info(f"Using SFTP storage backend: {config.SFTP_DEST_PATH} (fallback: {config.OUTPUT_DIR})")
            return SFTPStorage(
                sftp_client=sftp_client,
                remote_path=config.SFTP_DEST_PATH,
                local_fallback=local_storage
            )
        
        else:
            logger.warning(f"Unknown storage backend '{backend_type}', defaulting to local")
            return local_storage


# Backward compatibility alias
StorageManager = LocalStorage
