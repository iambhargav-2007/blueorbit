from abc import ABC, abstractmethod

class BaseSpeechToTextProvider(ABC):
    """
    Abstract base class for Speech-to-Text (STT) providers.
    Any STT engine (local Whisper, cloud API, etc.) must implement this interface.
    """

    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str = None) -> str:
        """
        Transcribe the given audio bytes to text.
        
        Args:
            audio_bytes: The raw audio data (e.g., WAV, MP3, WebM bytes).
            language: Optional language code hint (e.g., "en", "hi", "te").
                      If None, the provider should auto-detect if capable.
                      
        Returns:
            The transcribed text.
        """
        pass
