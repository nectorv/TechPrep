import os
import tempfile
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio(file_bytes: bytes, file_ext: str = "ogg", language: str = "en") -> str:
    """
    Transcribe raw audio bytes using OpenAI Whisper API.

    file_ext: extension hint for the temp file ('ogg' for Telegram voice,
              'mp3'/'m4a' for other audio).
    language: BCP-47 language code to force — avoids misdetection for
              non-native speakers (default 'en').
    Returns the transcribed text.
    """
    with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
            )
        return transcript.text
    finally:
        os.unlink(tmp_path)
