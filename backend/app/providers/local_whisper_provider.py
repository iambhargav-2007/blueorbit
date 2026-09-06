import io
import logging
from typing import Optional
from .base_stt_provider import BaseSpeechToTextProvider

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

logger = logging.getLogger(__name__)

class LocalWhisperProvider(BaseSpeechToTextProvider):
    def __init__(self, model_size: str = "small", device: str = "auto", compute_type: str = "default"):
        """
        Initializes the local Whisper model for offline transcription.
        
        Args:
            model_size: Size of the Whisper model (e.g., "tiny", "base", "small").
                        "small" is ~460MB and provides a good balance for Indic languages.
            device: "cpu", "cuda", or "auto".
            compute_type: "default", "int8", or "float16".
        """
        if WhisperModel is None:
            raise ImportError("faster-whisper is not installed. Run: pip install faster-whisper")
        
        logger.info(f"Loading local Whisper model ({model_size}) on {device} (compute: {compute_type})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("Local Whisper model loaded successfully.")

    def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """
        Transcribe the given audio bytes to text using faster-whisper.
        """
        if not audio_bytes:
            return ""

        audio_file = io.BytesIO(audio_bytes)
        
        try:
            # VAD filter prevents Whisper from hallucinating (e.g. Spanish gibberish) on silence.
            # condition_on_previous_text=False stops it from repeating itself.
            segments, info = self.model.transcribe(
                audio_file, 
                beam_size=5, 
                language=language,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=400),
                condition_on_previous_text=False
            )
            logger.info(f"STT Detected language '{info.language}' with probability {info.language_probability}")
            
            transcript_parts = []
            # segments is a generator, so we must iterate over it
            for segment in segments:
                transcript_parts.append(segment.text.strip())
            
            transcript = " ".join(transcript_parts).strip()
            logger.info(f"STT Transcript: {transcript}")
            return transcript
        except Exception as e:
            logger.error(f"Error during STT transcription: {e}")
            raise e
