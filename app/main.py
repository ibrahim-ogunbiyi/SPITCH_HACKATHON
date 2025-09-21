import os
import streamlit as st
from utils.utility import (
    download_youtube_video,
    get_transcription_with_speaker,
    insert_silence_placeholder,
    get_translation,
    merge_tts_chunks,
    dub_translated_audio_to_video,
    output_voice_base_on_lang,
    render_video
)
# App config
st.set_page_config(page_title="AI Video Dubbing", page_icon="🎬", layout="centered")

# Title
st.title("🎬 Learn in Your Language")
st.markdown("Upload an English YouTube video, translate, and dub it into your local language.")

# Sidebar for settings
st.sidebar.header("⚙️ Settings")
youtube_url = st.sidebar.text_input("YouTube Video URL", placeholder="https://youtube.com/watch?v=...")
source_lang = st.sidebar.selectbox("Source Language of Video", ["English", "Yoruba", "Hausa", "Igbo", "Amharic"], index=None)
target_lang = st.sidebar.selectbox("Target Language", ["Yoruba", "Hausa", "Igbo", "Amharic"], index=None)

target_lang_map = {
    "Yoruba": "yo",
    "Hausa": "ha",
    "Igbo": "ig",
    "Amharic": "am"

}

source_lang_map = {
    "English": "en",
    "Yoruba": "yo",
    "Hausa": "ha",
    "Igbo": "ig",
    "Amharic": "am" 
}

if target_lang:
    target_lang_value = target_lang_map[target_lang]

if source_lang:
    source_lang_value = source_lang_map[source_lang]


# Speaker mapping
st.sidebar.subheader("🎙️ Speaker Voices")
num_speakers = st.sidebar.selectbox(label="What is the the Number of Speakers in Video (Max 2)", options= [1, 2])

if num_speakers == 1:
    voices = output_voice_base_on_lang(lang=target_lang)
    speaker1_voice = st.sidebar.selectbox("Speaker 1 Voice", voices)
else:
    voices = output_voice_base_on_lang(lang=target_lang)
    speaker1_voice = st.sidebar.selectbox("Speaker 1 Voice", voices)
    speaker2_voice = st.sidebar.selectbox("Speaker 2 Voice", voices)

# Action button
if st.sidebar.button("Translate & Dub 🚀"):
    if youtube_url.strip() == "":
        st.error("Please provide a YouTube URL.")
    else:
        try:
            with st.spinner("Processing video... This may take a while ⏳"):

                original_video_temp_path, audio_bytes = download_youtube_video(url=youtube_url)

                transcription_result = get_transcription_with_speaker(audio_bytes=audio_bytes, src_lang=source_lang_value)

                result = insert_silence_placeholder(transcription_result)

                result = get_translation(result, target_lang=target_lang_value)

                if num_speakers == 1:
                    speakers = {"SPEAKER_00": speaker1_voice.lower()}
                else:
                    speakers = {"SPEAKER_00": speaker1_voice.lower(), "SPEAKER_01": speaker2_voice.lower()}

                translated_audio_path = merge_tts_chunks(chunks=result, target_lang=target_lang_value, speakers=speakers)
            
                dubbed_video_path = dub_translated_audio_to_video(video_path=original_video_temp_path, audio_path=translated_audio_path)

                render_video(dubbed_video_path)

                # Expander for original video
                with st.expander("See Original Video"):
                    render_video(original_video_temp_path)

                # Optional download
                with open(dubbed_video_path, "rb") as f:
                    st.download_button("Download Dubbed Video", f, file_name="dubbed_video.mp4", mime="video/mp4")
                
        finally:
            try:
                os.remove(original_video_temp_path)
                os.remove(dubbed_video_path)
            except Exception:
                pass    