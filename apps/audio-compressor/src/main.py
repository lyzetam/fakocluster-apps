"""Main entry point for audio compression service"""
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List

from . import config
from .sftp_client import SFTPClient
from .compressor import AudioCompressor
from .storage import StorageManager
from .exceptions import (
    AudioCompressorError,
    SFTPConnectionError,
    ConfigurationError
)

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def validate_configuration() -> None:
    """Validate required configuration"""
    required_configs = {
        'SFTP_HOST': config.SFTP_HOST,
        'OUTPUT_DIR': config.OUTPUT_DIR,
    }
    
    missing = [key for key, value in required_configs.items() if not value]
    
    if missing:
        raise ConfigurationError(f"Missing required configuration: {', '.join(missing)}")
    
    logger.info("Configuration validated successfully")


def load_sftp_credentials() -> Dict[str, str]:
    """Load SFTP credentials from AWS Secrets Manager or environment"""
    logger.info("Loading SFTP credentials")
    
    # Try to get from AWS Secrets Manager first
    try:
        from externalconnections.fetch_sftp_secrets import get_sftp_credentials
        credentials = get_sftp_credentials()
        logger.info("Loaded credentials from AWS Secrets Manager")
        return credentials
    except ImportError:
        logger.warning("AWS Secrets integration not available, using environment variables")
    except Exception as e:
        logger.warning(f"Failed to load from AWS Secrets Manager: {e}")
    
    # Fall back to environment variables
    username = os.environ.get('SFTP_USERNAME')
    password = os.environ.get('SFTP_PASSWORD')
    
    if not username or not password:
        raise ConfigurationError("SFTP credentials not found in environment or Secrets Manager")
    
    logger.info("Using credentials from environment variables")
    return {
        'username': username,
        'password': password
    }


def process_directory(
    directory: str,
    sftp_client: SFTPClient,
    compressor: AudioCompressor,
    storage: StorageManager
) -> Dict:
    """
    Process a single directory
    
    Returns:
        Dictionary with processing results
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing directory: {directory}")
    logger.info(f"{'='*60}")
    
    result = {
        'directory': directory,
        'status': 'pending',
        'original_size_mb': 0,
        'compressed_size_mb': 0,
        'error': None
    }
    
    # Create temp directory
    os.makedirs(config.TEMP_DIR, exist_ok=True)
    
    temp_audio_path = os.path.join(config.TEMP_DIR, f"{directory}_original.{config.AUDIO_FORMAT}")
    temp_compressed_path = os.path.join(config.TEMP_DIR, f"{directory}_compressed.{config.AUDIO_FORMAT}")
    temp_metadata_path = os.path.join(config.TEMP_DIR, f"{directory}_meta.xml")
    
    try:
        # Check if already processed
        if config.SKIP_PROCESSED and storage.is_processed(directory):
            logger.info(f"✓ SKIPPED - {directory} already processed")
            result['status'] = 'skipped'
            return result
        
        # Get directory info
        dir_info = sftp_client.get_directory_info(directory, config.SFTP_REMOTE_PATH)
        
        if not dir_info['has_audio']:
            logger.warning(f"✗ SKIP - No {config.AUDIO_FILENAME} found in {directory}")
            result['status'] = 'no_audio'
            result['error'] = f"No {config.AUDIO_FILENAME} found"
            return result
        
        logger.info(f"Found audio file: {dir_info['audio_size_mb']:.2f} MB")
        
        # Download audio file
        logger.info("Downloading audio file...")
        success, size_mb = sftp_client.download_file(
            dir_info['audio_path'],
            temp_audio_path
        )
        
        if not success:
            raise AudioCompressorError(f"Failed to download audio (size: {size_mb} MB)")
        
        result['original_size_mb'] = size_mb
        
        # Compress audio
        logger.info("Compressing audio...")
        _, original_mb, compressed_mb = compressor.compress_audio(
            temp_audio_path,
            temp_compressed_path
        )
        
        result['original_size_mb'] = original_mb
        result['compressed_size_mb'] = compressed_mb
        
        # Save to PVC
        logger.info("Saving to storage...")
        storage.save_compressed_file(temp_compressed_path, directory)
        
        # Download and save metadata if available
        if dir_info['has_metadata'] and config.COPY_METADATA:
            try:
                logger.info("Downloading metadata...")
                sftp_client.download_file(dir_info['metadata_path'], temp_metadata_path)
                storage.save_metadata_file(temp_metadata_path, directory)
            except Exception as e:
                logger.warning(f"Failed to process metadata: {e}")
        
        # Update manifest
        storage.update_manifest(
            directory,
            'success',
            original_mb,
            compressed_mb
        )
        
        result['status'] = 'success'
        logger.info(f"✓ SUCCESS - {directory} processed successfully")
        
        # Calculate savings
        space_saved = original_mb - compressed_mb
        compression_ratio = original_mb / compressed_mb if compressed_mb > 0 else 0
        logger.info(f"  Space saved: {space_saved:.2f} MB ({compression_ratio:.1f}x compression)")
        
    except Exception as e:
        logger.error(f"✗ FAILED - Error processing {directory}: {e}")
        result['status'] = 'failed'
        result['error'] = str(e)
        
        # Update manifest with failure
        storage.update_manifest(
            directory,
            'failed',
            result['original_size_mb'],
            result['compressed_size_mb'],
            str(e)
        )
    
    finally:
        # Clean up temp files
        for temp_file in [temp_audio_path, temp_compressed_path, temp_metadata_path]:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file}: {e}")
    
    return result


def main() -> int:
    """Main execution function"""
    start_time = time.time()
    
    logger.info("="*60)
    logger.info("Audio Compression Service Starting")
    logger.info("="*60)
    logger.info(f"Start time: {datetime.now().isoformat()}")
    
    try:
        # Validate configuration
        validate_configuration()
        
        # Verify FFmpeg is available
        if not AudioCompressor.verify_ffmpeg():
            logger.error("FFmpeg not found - cannot proceed")
            return 2
        
        # Initialize components
        storage = StorageManager(config.OUTPUT_DIR)
        logger.info(f"Output directory: {config.OUTPUT_DIR}")
        logger.info(f"Remote path: {config.SFTP_REMOTE_PATH}")
        
        # Load credentials
        credentials = load_sftp_credentials()
        
        # Connect to SFTP server
        logger.info(f"Connecting to SFTP server: {config.SFTP_HOST}:{config.SFTP_PORT}")
        with SFTPClient(
            config.SFTP_HOST,
            config.SFTP_PORT,
            credentials['username'],
            credentials['password']
        ) as sftp:
            
            # List directories
            logger.info("Scanning for audio directories...")
            directories = sftp.list_audio_directories(config.SFTP_REMOTE_PATH)
            
            if not directories:
                logger.warning("No audio directories found matching pattern")
                logger.info("Processing complete - no work to do")
                return 0
            
            logger.info(f"Found {len(directories)} directories to process")
            
            # Initialize compressor
            compressor = AudioCompressor()
            
            # Process each directory
            results = []
            for idx, directory in enumerate(directories, 1):
                logger.info(f"\nProgress: {idx}/{len(directories)}")
                result = process_directory(directory, sftp, compressor, storage)
                results.append(result)
        
        # Generate summary report
        elapsed_time = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("Processing Summary")
        logger.info("="*60)
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = sum(1 for r in results if r['status'] == 'failed')
        skipped_count = sum(1 for r in results if r['status'] in ['skipped', 'no_audio'])
        
        total_original_mb = sum(r['original_size_mb'] for r in results if r['original_size_mb'])
        total_compressed_mb = sum(r['compressed_size_mb'] for r in results if r['compressed_size_mb'])
        total_saved_mb = total_original_mb - total_compressed_mb
        
        logger.info(f"Total directories found: {len(directories)}")
        logger.info(f"Successfully processed: {success_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Skipped: {skipped_count}")
        logger.info(f"Total original size: {total_original_mb:.2f} MB")
        logger.info(f"Total compressed size: {total_compressed_mb:.2f} MB")
        logger.info(f"Total space saved: {total_saved_mb:.2f} MB ({total_saved_mb/1024:.2f} GB)")
        
        if total_compressed_mb > 0:
            avg_compression = total_original_mb / total_compressed_mb
            logger.info(f"Average compression ratio: {avg_compression:.1f}x")
        
        logger.info(f"Elapsed time: {elapsed_time:.1f} seconds")
        
        # Get storage statistics
        stats = storage.get_statistics()
        logger.info(f"\nStorage Statistics:")
        logger.info(f"Total files in storage: {stats['total_files']}")
        logger.info(f"Total storage used: {stats['total_size_gb']:.2f} GB")
        logger.info(f"Total space saved (all-time): {stats['total_space_saved_gb']:.2f} GB")
        
        # List failed directories if any
        if failed_count > 0:
            logger.warning("\nFailed directories:")
            for result in results:
                if result['status'] == 'failed':
                    logger.warning(f"  - {result['directory']}: {result['error']}")
        
        logger.info("\n" + "="*60)
        logger.info("Audio Compression Service Complete")
        logger.info("="*60)
        
        # Return appropriate exit code
        if failed_count == len(directories):
            return 2  # Total failure
        elif failed_count > 0:
            return 1  # Partial failure
        else:
            return 0  # Success
        
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        return 130
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 2
    except SFTPConnectionError as e:
        logger.error(f"SFTP connection error: {e}")
        return 2
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 2
    finally:
        # Clean up temp directory
        if os.path.exists(config.TEMP_DIR):
            try:
                storage = StorageManager(config.OUTPUT_DIR)
                storage.cleanup_temp_files(config.TEMP_DIR)
            except:
                pass


if __name__ == '__main__':
    sys.exit(main())
