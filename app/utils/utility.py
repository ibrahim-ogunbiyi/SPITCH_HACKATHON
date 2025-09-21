import io
import os
import shutil
import tempfile
import base64
import streamlit as st
from pydub import AudioSegment
from moviepy import AudioFileClip, VideoFileClip
from models.model_class import Models
from pytubefix import YouTube
from pathlib import Path
from spitch import Spitch
from core.config import settings
from yt_dlp import YoutubeDL

def prepare_cookiefile():

    candidates = [
        os.environ.get("YTDLP_COOKIES"),          # explicit env
        "/etc/secrets/cookies.txt",               # Render secret
        "/secrets/cookies.txt",                   # GCP secret
        os.path.join(os.getcwd(), "cookies.txt"), # local dev (gitignored)
    ]
    for path in candidates:
        if path and os.path.exists(path):
            # copy to writable tmp file
            tmp_path = os.path.join(tempfile.gettempdir(), "cookies.txt")
            shutil.copy(path, tmp_path)
            return tmp_path
    return None

client = Spitch(api_key=settings.SPITCH_API_KEY)


def get_transcription_with_speaker(audio_bytes: bytes, src_lang: str) -> list[dict]:
    
    # perform speaker diarisation on audio
    
    records = Models.get_speaker_diarization(audio_bytes=audio_bytes)

    data = io.BytesIO(audio_bytes)
    audio = AudioSegment.from_file(data, format="wav")

    results = []

    # perform transcription of each audio chunk

    for i, record in enumerate(records):
        if not ((record["time_end"] - record["time_start"]) <= 0.01):
            segment = audio[record["time_start"] * 1000 : record["time_end"] * 1000]

            buffer = io.BytesIO()
            segment.export(buffer, format="wav")
            buffer.name = "audio.wav"

        
            transcription = Models.get_spitch_asr_model(
                    audio_bytes=buffer.read(), src_lang=src_lang
                )

            result = {"transcription": transcription, **record}

            results.append(result)

            print(f"Finished Processing {(i + 1)}/{len(records)}")
    return results


def insert_silence_placeholder(records: list) -> list:
    results = []
    for i, record in enumerate(records):
        results.append(record)

        if i < len(records) - 1:
            gap_end = record["time_end"]

            gap_start = records[i + 1]["time_start"]

            if (gap_start - gap_end) > 0.1:
                results.append(
                    {
                        "transcription": "__SILENCE__",
                        "speaker": "SILENCE",
                        "time_start": gap_end + 0.1,
                        "time_end": gap_start + 0.1,
                    }
                )

    results = sorted(results, key=lambda x: x["time_start"])
    return results


def download_youtube_video(url: str) -> tuple[str, bytes]:


    fd, video_temp_path = tempfile.mkstemp(suffix=".mp4", dir=Path.cwd())
    Path(video_temp_path).unlink(missing_ok=True)  

    ydl_opts = {
    "outtmpl": video_temp_path,
    "format": "best[ext=mp4][protocol^=http]",  
    "merge_output_format": "mp4",  # force MP4 final file
    "cookiefile": prepare_cookiefile(),
    "retries": 10,
    "fragment_retries": 10,
}

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


    # Extract audio using moviepy
    video = VideoFileClip(video_temp_path)
    audio_temp_file = tempfile.NamedTemporaryFile(
        dir=Path.cwd(), delete=False, suffix=".wav"
    )

    video.audio.write_audiofile(audio_temp_file.name)
    video.close()

    # finally delete the audio temp path
    try:
        with open(audio_temp_file.name, "rb") as file:
            audio_bytes = file.read()
        
        # return temp file of video and extracted audio in bytes format
        return video_temp_path, audio_bytes
    finally:
        os.remove(audio_temp_file.name)


def get_translation(results, target_lang) -> list[dict]:
    records = []
    for record in results:
        if record["transcription"] != "__SILENCE__":
            translation = client.text.translate(
                text=record["transcription"],
                source="en",
                target=target_lang,
            )

            result = {"translation": translation.text, **record}
            records.append(result)
        else:
            result = {"translation": "__SILENCE__", **record}
            records.append(result)

    return records


def merge_tts_chunks(
    chunks: list[dict], target_lang: str, speakers: dict
) -> str:
    combined = AudioSegment.empty()

    # Process each record
    for record in chunks:
        if record["time_end"] <= record["time_start"]:
            continue  # skip zero-length

        if record["transcription"] == "__SILENCE__":
            # create silence equal to gap duration
            silence_duration = (record["time_end"] - record["time_start"]) * 1000
            seg = AudioSegment.silent(duration=silence_duration)
            continue
        else:
            # generate TTS
            response = client.speech.generate(
                text=record["translation"],
                language=target_lang,
                voice=speakers[record["speaker"]],
            )
            b = response.read()
            seg = AudioSegment.from_file(io.BytesIO(b), format="wav")

        combined += seg

    temp_file = tempfile.NamedTemporaryFile(
        mode="wb", dir=Path.cwd(), suffix=".wav", delete=False
    )
    combined.export(temp_file.name, format="wav")

    print(f"This is the Audio file path:{temp_file.name}")
    temp_file.close()
    return temp_file.name


def dub_translated_audio_to_video(video_path: str, audio_path: str) -> str:
    try:
        video = VideoFileClip(video_path)

        new_audio = AudioFileClip(audio_path)

        final_video = video.with_audio(new_audio)

        temp_file = tempfile.NamedTemporaryFile(
            mode="wb", dir=Path.cwd(), suffix=".mp4", delete=False
        )

        final_video.write_videofile(temp_file.name, codec="libx264", audio_codec="aac")

        print(f"This is the video file path: {temp_file.name}")

        return temp_file.name

    finally:
        temp_file.close()
        new_audio.close()
        video.close()

        os.remove(audio_path)


def output_voice_base_on_lang(lang: str) -> list[str]:
    if lang == "Yoruba":
        return ["Sade", "Funmi", "Segun", "Femi"]
    elif lang == "Hausa":
        return ["Hasan", "Amina", "Zainab", "Aliyu"]
    elif lang == "Igbo":
        return ["Obinna", "Ngozi", "Amara", "Ebuka"]
    elif lang == "Amharic":
        return ["Hana", "Selam", "Tesfaye", "Tena"]

def render_video(video_path: str):
    """Render a video in Streamlit using base64 embedding."""

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    base64_video = base64.b64encode(video_bytes).decode("utf-8")

    st.markdown(
        f"""
        <video controls width="100%" height="600">
            <source src="data:video/mp4;base64,{base64_video}" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True,
    )
