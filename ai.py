import json
import time
from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

STRUCTURING_SYSTEM_PROMPT = """You are Setu's intake analyst for Indian civic and development problems.
Given a citizen's report (a transcript or text), return ONLY valid JSON with EXACTLY these fields:
- "title": max 8 words, plain English, factual
- "description": exactly 2 sentences, neutral and factual, no drama
- "category": one of ["sanitation","water","roads","education","health","environment","elderly","other"]
- "legality_bin": one of ["fundable","statutory","reframe"]
    * "fundable" = can be funded by corporate CSR under Schedule VII (e.g. school toilets, safe drinking water, lake/pond revival, sanitation-worker safety gear, women/girls empowerment, elderly day-care)
    * "statutory" = the government's own legal duty (e.g. potholes, municipal road repair, garbage collection, streetlights, routine sewer/drain maintenance, municipal water supply)
    * "reframe" = mixed: partly statutory, partly fundable (e.g. a road accident black-spot = road repair is statutory, but road-safety education and trauma care are fundable)
- "severity": one of ["low","medium","high"]
If you are unsure about legality_bin, choose "reframe". Never invent facts not present in the report.
Output JSON only. No prose, no markdown."""


def _retry(fn, attempts=3, base_delay=2):
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) and i < attempts - 1:
                time.sleep(base_delay * (i + 1))
                continue
            raise


def transcribe(audio_path: str) -> dict:
    """Return {'text': str, 'language': str}. Works for .ogg, .mp3, .m4a, .wav, .mp4."""
    def call():
        with open(audio_path, "rb") as f:
            return client.audio.transcriptions.create(
                file=(audio_path, f.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
            )
    result = _retry(call)
    return {
        "text": result.text,
        "language": getattr(result, "language", "unknown"),
    }


def structure(report_text: str) -> dict:
    """Turn raw text into the structured fields. Returns a dict matching the schema."""
    def call():
        return client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": STRUCTURING_SYSTEM_PROMPT},
                {"role": "user", "content": report_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    completion = _retry(call)
    data = json.loads(completion.choices[0].message.content)
    # safety defaults
    data.setdefault("title", "Untitled report")
    data.setdefault("description", report_text[:200])
    data.setdefault("category", "other")
    data.setdefault("legality_bin", "reframe")
    data.setdefault("severity", "medium")
    return data


def detect_greeting_language(text: str) -> str:
    """Cheap heuristic: returns a language code for the greeting reply.
    Uses Unicode ranges so it costs zero API calls."""
    if not text:
        return "en"
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F: return "hi"   # Devanagari (Hindi)
        if 0x0980 <= o <= 0x09FF: return "bn"   # Bengali
        if 0x0B80 <= o <= 0x0BFF: return "ta"   # Tamil
        if 0x0C00 <= o <= 0x0C7F: return "te"   # Telugu
        if 0x0C80 <= o <= 0x0CFF: return "kn"   # Kannada
    return "en"
