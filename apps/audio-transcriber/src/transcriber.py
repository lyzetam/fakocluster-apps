"""Audio transcription using Whisper API endpoint"""
import logging
import os
import json
import requests
from typing import Dict, Optional
from . import config
from .exceptions import TranscriptionError

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """Whisper API-based audio transcription"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
        task: Optional[str] = None,
        output_format: Optional[str] = None,
        timeout: Optional[int] = None,
        word_timestamps: Optional[bool] = None
    ):
        """
        Initialize the transcriber with configuration

        Args:
            endpoint: Whisper API endpoint URL
            model: Whisper model to use (tiny, base, small, medium, large)
            language: Language code for transcription
            task: Task type ('transcribe' or 'translate')
            output_format: Output format ('json', 'text', 'srt', 'vtt')
            timeout: Request timeout in seconds
            word_timestamps: Whether to include word-level timestamps
        """
        self.endpoint = endpoint or config.WHISPER_ENDPOINT
        self.model = model or config.WHISPER_MODEL
        self.language = language or config.WHISPER_LANGUAGE
        self.task = task or config.WHISPER_TASK
        self.output_format = output_format or config.OUTPUT_FORMAT
        self.timeout = timeout or config.WHISPER_TIMEOUT
        self.word_timestamps = word_timestamps if word_timestamps is not None else config.WHISPER_WORD_TIMESTAMPS

        logger.info(f"AudioTranscriber initialized with endpoint: {self.endpoint}")
        logger.info(f"Model: {self.model}, Language: {self.language}, Task: {self.task}")

    def transcribe(
        self,
        audio_path: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Transcribe an audio file using the Whisper API

        Args:
            audio_path: Path to the audio file to transcribe
            output_path: Optional path to save the transcription result

        Returns:
            Dictionary containing transcription result
        """
        if not os.path.exists(audio_path):
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Transcribing: {audio_path} ({file_size_mb:.2f} MB)")
        logger.info(f"Using model: {self.model}, language: {self.language}")

        try:
            # Prepare the request
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'audio_file': (os.path.basename(audio_path), audio_file)
                }

                # Build query parameters based on endpoint expectations
                params = {
                    'task': self.task,
                    'language': self.language,
                    'output': self.output_format,
                    'word_timestamps': str(self.word_timestamps).lower()
                }

                # Some endpoints use encode parameter
                if self.model:
                    params['encode'] = 'true'

                logger.info(f"Sending request to {self.endpoint}")
                logger.debug(f"Parameters: {params}")

                response = requests.post(
                    self.endpoint,
                    files=files,
                    params=params,
                    timeout=self.timeout
                )

            if response.status_code != 200:
                error_msg = f"Whisper API returned status {response.status_code}: {response.text[:500]}"
                logger.error(error_msg)
                raise TranscriptionError(error_msg)

            # Parse response based on output format
            if self.output_format == 'json':
                result = response.json()
            else:
                result = {
                    'text': response.text,
                    'format': self.output_format
                }

            # Add metadata to result
            result['_metadata'] = {
                'audio_file': os.path.basename(audio_path),
                'file_size_mb': round(file_size_mb, 2),
                'model': self.model,
                'language': self.language,
                'task': self.task
            }

            logger.info("Transcription successful")

            # Extract text for logging
            text = result.get('text', '')
            if text:
                text_preview = text[:200] + '...' if len(text) > 200 else text
                logger.info(f"Transcription preview: {text_preview}")

            # Save result if output path provided
            if output_path:
                self._save_result(result, output_path)

            return result

        except requests.exceptions.Timeout:
            error_msg = f"Transcription request timed out after {self.timeout} seconds"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Failed to connect to Whisper endpoint: {e}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error during transcription: {e}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {e}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)

    def _save_result(self, result: Dict, output_path: str) -> None:
        """
        Save transcription result to file

        Args:
            result: Transcription result dictionary
            output_path: Path to save the result
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            if self.output_format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.get('text', ''))

            logger.info(f"Transcription saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save transcription result: {e}")
            raise TranscriptionError(f"Failed to save result: {e}")

    def verify_endpoint(self) -> bool:
        """
        Verify the Whisper endpoint is accessible

        Returns:
            True if endpoint is accessible, False otherwise
        """
        try:
            # Try to reach the endpoint
            health_url = self.endpoint.rsplit('/', 1)[0]
            response = requests.get(health_url, timeout=10)

            if response.status_code in [200, 404]:
                logger.info(f"Whisper endpoint is accessible: {self.endpoint}")
                return True
            else:
                logger.warning(f"Whisper endpoint returned status {response.status_code}")
                return True

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Whisper endpoint: {self.endpoint}")
            return False
        except Exception as e:
            logger.error(f"Error checking Whisper endpoint: {e}")
            return False
