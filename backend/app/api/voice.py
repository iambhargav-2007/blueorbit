from fastapi import APIRouter, HTTPException, UploadFile, File
import logging
from typing import Optional
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts
import asyncio

logger = logging.getLogger(__name__)

# The router prefix is usually set in main.py, but we can set it here too if preferred.
# Following existing patterns, chat.py uses prefix="/api/v1".
router = APIRouter(prefix="/api/v1", tags=["voice"])

import os
from groq import Groq
from fastapi import Form

# Initialize Groq client
# This requires GROQ_API_KEY to be set in the environment/ .env
_groq_client = None

def get_groq_client() -> Groq:
    global _groq_client
    if _groq_client is None:
        try:
            _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise HTTPException(status_code=503, detail="Voice service unavailable (Groq config error)")
    return _groq_client

@router.post("/voice/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """
    Accepts an audio file/blob from the frontend and returns the text transcription
    using the lightning-fast Groq Whisper API, avoiding local 1.5GB downloads and small model hallucinations.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
            
        client = get_groq_client()
        
        # Groq API expects a tuple (filename, bytes) or file-like object
        # The frontend sends webm audio
        file_tuple = ("audio.webm", audio_bytes)
        
        # Whisper-large-v3 natively supports multilingual detection.
        # If language is explicitly provided via dropdown (e.g. 'te'), pass it to Groq.
        transcription_kwargs = {
            "model": "whisper-large-v3",
            "file": file_tuple,
            "response_format": "verbose_json",
            "temperature": 0.0
        }
        if language and language != "auto":
            transcription_kwargs["language"] = language
            
        logger.info(f"Sending audio to Groq Whisper API (language={language})")
        transcript = client.audio.transcriptions.create(**transcription_kwargs)
        
        final_text = transcript.text.strip()
        detected_lang = transcript.language
        logger.info(f"Groq Transcription Result: {final_text} (Detected Lang: {detected_lang})")
        
        return {"transcript": final_text, "language": detected_lang}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during transcription route: {e}")
        raise HTTPException(status_code=500, detail="Internal transcription error")

class SynthesizeRequest(BaseModel):
    text: str
    language: str

VOICE_MAP = {
    "hi": "hi-IN-SwaraNeural",
    "hindi": "hi-IN-SwaraNeural",
    "te": "te-IN-ShrutiNeural",
    "telugu": "te-IN-ShrutiNeural",
    "mr": "mr-IN-AarohiNeural",
    "marathi": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "gujarati": "gu-IN-DhwaniNeural",
    "ta": "ta-IN-PallaviNeural",
    "tamil": "ta-IN-PallaviNeural",
    "en": "en-IN-NeerjaNeural",
    "english": "en-IN-NeerjaNeural",
    "auto": "en-IN-NeerjaNeural"
}

@router.post("/voice/synthesize")
async def synthesize_voice(req: SynthesizeRequest):
    """
    Localization Agent endpoint.
    Translates English text to the user's regional language and generates an MP3 audio stream using edge-tts.
    """
    if not req.text:
        raise HTTPException(status_code=400, detail="Empty text provided for synthesis")
        
    client = get_groq_client()
    target_lang = req.language.lower()
    
    # 1. Translate to target language using Groq
    translated_text = req.text
    if target_lang and target_lang != "en" and target_lang != "auto":
        try:
            lang_name_map = {
                "te": "Telugu",
                "hi": "Hindi",
                "mr": "Marathi",
                "gu": "Gujarati",
                "ta": "Tamil"
            }
            lang_name = lang_name_map.get(target_lang, target_lang)
            prompt = f"Translate the following marine report into {lang_name}. Return ONLY the translated text. Do not include any quotes, explanations, or English text. Here is the report:\n\n{req.text}"
            
            logger.info(f"Translating text to {lang_name}...")
            res = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0.1,
                max_tokens=512,
            )
            translated_text = res.choices[0].message.content.strip()
            logger.info(f"Translation successful: {translated_text}")
        except Exception as e:
            logger.error(f"Groq translation failed: {e}")
            # Fallback to English if translation fails
            pass
            
    # 2. Synthesize using edge-tts
    voice = VOICE_MAP.get(target_lang, "en-IN-NeerjaNeural")
    
    async def generate_audio():
        try:
            communicate = edge_tts.Communicate(translated_text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"edge-tts synthesis failed: {e}")
            
    return StreamingResponse(generate_audio(), media_type="audio/mpeg")
