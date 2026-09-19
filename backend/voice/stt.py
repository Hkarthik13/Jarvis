from pathlib import Path
from backend.ai.client import ai_client
from backend.config import settings
from backend.utils.logger import logger

async def transcribe_audio(file_path: str, model: str = None) -> str:
    """
    Transcribes the speech in an audio file to text using Groq's Whisper API asynchronously.
    
    Args:
        file_path: Absolute or relative system path to the audio file.
        model: Optional override for the Whisper model.
        
    Returns:
        The transcribed text string.
    """
    try:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Audio file not found at: {file_path}")

        # Get the AsyncGroq client from the AI module
        client = ai_client.get_client()
        selected_model = model or settings.stt_model
        
        logger.info(f"Initiating STT transcription for '{path.name}' using '{selected_model}'")
        
        # Async transcription request using pathlib.Path
        transcription = await client.audio.transcriptions.create(
            file=path,
            model=selected_model,
            response_format="json"
        )
        
        logger.info("Successfully transcribed audio.")
        return transcription.text

    except Exception as e:
        logger.error(f"Speech-to-Text transcription failed: {e}")
        raise
