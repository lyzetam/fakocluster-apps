"""Storage management for compressed audio files and manifest tracking"""
import logging
import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from . import config
from .exceptions import StorageError

logger = logging.getLogger(__name__)


class StorageManager:
    """Manage file storage and manifest tracking"""
    
    def __init__(self, output_dir: str):
        """Initialize storage manager"""
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
    
    def is_processed(self, directory_name: str) -> bool:
        """Check if directory has already been processed"""
        compressed_filename = f"{directory_name}_compressed.{config.AUDIO_FORMAT}"
        compressed_path = os.path.join(self.output_dir, compressed_filename)
        
        exists = os.path.exists(compressed_path)
        if exists:
            logger.debug(f"{directory_name} already processed (file exists)")
        return exists
    
    def get_output_path(self, directory_name: str, file_type: str = 'compressed') -> str:
        """
        Get output path for a file
        
        Args:
            directory_name: Source directory name (e.g., "10-17-25")
            file_type: Type of file ('compressed' or 'metadata')
            
        Returns:
            Full path to output file
        """
        if file_type == 'compressed':
            filename = f"{directory_name}_compressed.{config.AUDIO_FORMAT}"
        elif file_type == 'metadata':
            filename = f"{directory_name}_meta.xml"
        else:
            raise ValueError(f"Unknown file type: {file_type}")
        
        return os.path.join(self.output_dir, filename)
    
    def save_compressed_file(self, source_path: str, directory_name: str) -> str:
        """
        Save compressed file to PVC
        
        Args:
            source_path: Path to compressed file
            directory_name: Source directory name
            
        Returns:
            Path where file was saved
        """
        output_path = self.get_output_path(directory_name, 'compressed')
        
        try:
            shutil.copy2(source_path, output_path)
            logger.info(f"Saved compressed file to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save compressed file: {e}")
            raise StorageError(f"Cannot save compressed file: {e}")
    
    def save_metadata_file(self, source_path: str, directory_name: str) -> Optional[str]:
        """
        Save metadata file to PVC
        
        Args:
            source_path: Path to metadata file
            directory_name: Source directory name
            
        Returns:
            Path where file was saved, or None if failed
        """
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
    
    def update_manifest(
        self,
        directory_name: str,
        status: str,
        original_size_mb: float = 0,
        compressed_size_mb: float = 0,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update manifest with processing result
        
        Args:
            directory_name: Directory that was processed
            status: 'success' or 'failed'
            original_size_mb: Original file size in MB
            compressed_size_mb: Compressed file size in MB
            error_message: Error message if failed
        """
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
            "status": status
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
