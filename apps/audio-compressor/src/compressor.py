"""Audio compression using FFmpeg"""
import logging
import os
import subprocess
from typing import Tuple, Optional
from . import config
from .exceptions import CompressionError

logger = logging.getLogger(__name__)


class AudioCompressor:
    """FFmpeg-based audio compression"""
    
    @staticmethod
    def compress_audio(
        input_path: str,
        output_path: str,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        bitrate: Optional[str] = None
    ) -> Tuple[bool, float, float]:
        """
        Compress audio file using FFmpeg
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save compressed file
            sample_rate: Target sample rate (Hz), defaults to config.SAMPLE_RATE
            channels: Number of audio channels, defaults to config.CHANNELS
            bitrate: Target bitrate (e.g., '32k'), defaults to config.BITRATE
            
        Returns:
            Tuple of (success: bool, original_size_mb: float, compressed_size_mb: float)
        """
        sample_rate = sample_rate or config.SAMPLE_RATE
        channels = channels or config.CHANNELS
        bitrate = bitrate or config.BITRATE
        
        # Get original file size
        try:
            original_size = os.path.getsize(input_path)
            original_size_mb = original_size / (1024 * 1024)
        except Exception as e:
            logger.error(f"Failed to get input file size: {e}")
            raise CompressionError(f"Cannot read input file: {e}")
        
        logger.info(f"Compressing {input_path} ({original_size_mb:.2f} MB)")
        logger.info(f"Settings: {sample_rate}Hz, {channels} channel(s), {bitrate}")
        
        # Build FFmpeg command
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', input_path,           # Input file
            '-ar', str(sample_rate),    # Audio sample rate
            '-ac', str(channels),       # Audio channels
            '-b:a', bitrate,            # Audio bitrate
            '-y',                       # Overwrite output file
            output_path                 # Output file
        ]
        
        try:
            # Run FFmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5 minutes timeout
                check=False
            )
            
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='ignore')
                logger.error(f"FFmpeg failed with return code {result.returncode}")
                logger.error(f"FFmpeg stderr: {stderr[-500:]}")  # Last 500 chars
                raise CompressionError(f"FFmpeg compression failed: {stderr[-200:]}")
            
            # Check output file was created
            if not os.path.exists(output_path):
                raise CompressionError("FFmpeg completed but output file not found")
            
            # Get compressed file size
            compressed_size = os.path.getsize(output_path)
            compressed_size_mb = compressed_size / (1024 * 1024)
            
            # Calculate compression ratio
            compression_ratio = original_size_mb / compressed_size_mb if compressed_size_mb > 0 else 0
            
            logger.info(f"Compression successful:")
            logger.info(f"  Original: {original_size_mb:.2f} MB")
            logger.info(f"  Compressed: {compressed_size_mb:.2f} MB")
            logger.info(f"  Ratio: {compression_ratio:.1f}x")
            logger.info(f"  Space saved: {(original_size_mb - compressed_size_mb):.2f} MB")
            
            return True, original_size_mb, compressed_size_mb
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg compression timed out after 5 minutes")
            raise CompressionError("Compression timed out")
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise CompressionError(f"Compression error: {e}")
    
    @staticmethod
    def verify_ffmpeg() -> bool:
        """Verify FFmpeg is installed and accessible"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False
            )
            
            if result.returncode == 0:
                version_info = result.stdout.decode('utf-8').split('\n')[0]
                logger.info(f"FFmpeg found: {version_info}")
                return True
            else:
                logger.error("FFmpeg command failed")
                return False
                
        except FileNotFoundError:
            logger.error("FFmpeg not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Error checking FFmpeg: {e}")
            return False
    
    @staticmethod
    def get_audio_info(file_path: str) -> dict:
        """
        Get audio file information using ffprobe
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio metadata
        """
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_format',
                    '-show_streams',
                    '-print_format', 'json',
                    file_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout.decode('utf-8'))
                
                # Extract relevant info
                info = {
                    'duration': float(data.get('format', {}).get('duration', 0)),
                    'size': int(data.get('format', {}).get('size', 0)),
                    'bitrate': int(data.get('format', {}).get('bit_rate', 0)),
                }
                
                # Get audio stream info
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        info['sample_rate'] = int(stream.get('sample_rate', 0))
                        info['channels'] = int(stream.get('channels', 0))
                        info['codec'] = stream.get('codec_name', 'unknown')
                        break
                
                return info
            else:
                logger.warning(f"Failed to get audio info for {file_path}")
                return {}
                
        except Exception as e:
            logger.warning(f"Error getting audio info: {e}")
            return {}
