import re
import os
import hashlib
import edge_tts
from backend.config import settings
from backend.utils.logger import logger

# Disk and in-memory cache for instantaneous (0ms) voice response playback
AUDIO_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "audio_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
_MEMORY_AUDIO_CACHE: dict[str, bytes] = {}

def clean_text_for_speech(raw_text: str) -> str:
    """
    Cleans raw markdown, code blocks, URLs, and formatting so the neural TTS speaks
    smooth, natural, articulate conversational English, Tamil, and Tanglish without pronouncing symbols.
    """
    if not raw_text:
        return ""
        
    text = raw_text
    
    # 1. Strip code blocks ```...```
    text = re.sub(r'```[\s\S]*?```', ' Code block omitted. ', text)
    
    # 2. Strip inline code `code`
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 3. Strip URLs
    text = re.sub(r'https?://\S+', ' link ', text)
    
    # 4. Strip markdown images and links [text](url) -> text
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # 5. Strip markdown headers (#, ##, ###)
    text = re.sub(r'#+\s*', '', text)
    
    # 6. Strip bold, italics, strikethrough (**, *, __, ~~)
    text = re.sub(r'[*_~]{1,3}', '', text)
    
    # 7. Strip table formatting lines (| --- |)
    text = re.sub(r'\|[^\n]+\|', ' ', text)
    
    # 8. Clean up bullet points, dashes, arrows, and emojis
    text = re.sub(r'^\s*[-*+]\s+', ' ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', ' ', text, flags=re.MULTILINE)
    text = text.replace('→', ' to ').replace('⚡', '').replace('🎙️', '').replace('🧠', '').replace('💻', '').replace('🟢', '').replace('✨', '').replace('🔥', '')
    # Normalize unicode quotes and dashes for clean speech & logging
    text = text.replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-').replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    
    # 9. Clean up multiple spaces and excessive newlines
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def detect_best_voice(text: str, requested_voice: str = None) -> tuple[str, str]:
    """
    Intelligently select the most natural Edge-TTS neural voice and optimal speech rate:
    - Pure/Mixed Tamil Script (\u0B80-\u0BFF) -> 'ta-IN-ValluvarNeural' (rate: +8%)
    - Tanglish / Colloquial Tamil-English -> 'en-IN-PrabhatNeural' (rate: +10%)
    - Movie JARVIS Cadence (British English) -> 'en-GB-RyanNeural' (rate: +6%)
    """
    if requested_voice:
        return requested_voice, "+6%"
        
    # 1. Pure or Mixed Tamil Script Unicode Range (\u0B80-\u0BFF)
    if re.search(r'[\u0B80-\u0BFF]', text):
        logger.info("Detected Tamil script in text. Using 'ta-IN-ValluvarNeural' for fluent Tamil speech.")
        return "ta-IN-ValluvarNeural", "+8%"
        
    # 2. Comprehensive Tanglish vocabulary & phonetics
    tanglish_patterns = [
        r'\b(vanakkam|epdi|eppadi|irukinga|irukkeenga|irukken|irukku|iruku|sollu|sollunga|solunga)\b',
        r'\b(nalla|nallaa|panna|pannunga|panren|panra|romba|nanri|seri|enga|enna|ennachu|aachu)\b',
        r'\b(paas|boss|thala|machan|nanba|bro|kudunga|kudi|sapteengala|saapadu|vela|mudinjidha)\b',
        r'\b(kandippa|kavalapadatheenga|bayam|illai|illa|aama|aamam|ippo|appo|aprm|apram|konjam)\b',
        r'\b(parunga|paathukaren|theriyum|theriyala|podu|kelu|podunga|polaam|polam)\b'
    ]
    lower_text = text.lower()
    if any(re.search(pat, lower_text) for pat in tanglish_patterns):
        logger.info("Detected Tanglish phrasing in text. Using 'en-IN-PrabhatNeural' for natural conversational cadence.")
        return "en-IN-PrabhatNeural", "+10%"
        
    # 3. Default to authentic British Movie JARVIS voice
    default_voice = settings.tts_voice or "en-GB-RyanNeural"
    return default_voice, "+8%"

async def synthesize_speech(text: str, output_path: str, voice: str = None) -> None:
    """
    Synthesizes speech from text and saves it as an MP3 file using Microsoft Edge TTS asynchronously.
    Supports authentic British movie JARVIS cadence, English, Tamil (தமிழ்), and Tanglish.
    Features in-memory and disk caching for ultra-low latency playback without lag.
    """
    try:
        cleaned_text = clean_text_for_speech(text)
        if not cleaned_text:
            cleaned_text = "Standing by, sir."
            
        selected_voice, rate_param = detect_best_voice(cleaned_text, voice)
        cache_key = hashlib.md5(f"{selected_voice}:{cleaned_text}".encode("utf-8")).hexdigest()
        
        # 1. Check in-memory fast cache (0ms instant retrieval)
        if cache_key in _MEMORY_AUDIO_CACHE:
            logger.info("Serving speech instantly from in-memory cache.")
            with open(output_path, "wb") as f_out:
                f_out.write(_MEMORY_AUDIO_CACHE[cache_key])
            return
            
        # 2. Check disk cache
        cache_file = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.mp3")
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000:
            logger.info("Serving speech from disk audio cache.")
            with open(cache_file, "rb") as f_in, open(output_path, "wb") as f_out:
                data = f_in.read()
                f_out.write(data)
                _MEMORY_AUDIO_CACHE[cache_key] = data
            return
            
        # 3. Fast Edge-TTS synthesis with optimized conversational speech rate
        logger.info(f"Synthesizing speech ('{selected_voice}', rate: {rate_param}) for: '{cleaned_text[:60]}...'")
        communicate = edge_tts.Communicate(cleaned_text, selected_voice, rate=rate_param)
        
        # Save audio file
        await communicate.save(output_path)
        
        # Write to in-memory & disk cache for instant replay
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            try:
                with open(output_path, "rb") as f_in:
                    audio_data = f_in.read()
                if len(cleaned_text) < 250:
                    _MEMORY_AUDIO_CACHE[cache_key] = audio_data
                with open(cache_file, "wb") as f_out:
                    f_out.write(audio_data)
            except Exception:
                pass
                
        logger.info("Speech synthesis completed successfully.")
        
    except Exception as e:
        logger.error(f"Text-to-Speech synthesis failed: {e}")
        raise
