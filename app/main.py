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
    get_video_through_upload,
    render_video
)


st.set_page_config(page_title="AI Video Dubbing", page_icon="🎬", layout="centered")

defaults = {
    "youtube_url": None,
    "youtube_video": None,
    "channel_url": None,
    "short_list": None,
    "current_short_index": 0,
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


st.title("🎬 Learn in Your Language")
st.markdown("On the deployed website, please use only offline videos. If running locally, you can use both links and offline videos.")
st.markdown(
    "Upload or link to an English or Nigerian YouTube video, then translate and dub it into your local language."
)



# Sidebar options
st.sidebar.header("⚙️ Settings")
select_youtube = st.sidebar.selectbox(
    "How would you like to provide YouTube content?",
    [
        "Enter URL (may not always be available)",
        "Upload a YouTube video directly"
    ],
    index=None,
)

if select_youtube == "Enter URL (may not always be available)":
    st.session_state.youtube_url = st.sidebar.text_input(
        "YouTube Video URL", placeholder="https://youtube.com/watch?v=..."
    )
elif select_youtube == "Upload a YouTube video directly":
    st.session_state.youtube_video = st.file_uploader(
        label="Upload YouTube Video", type=".mp4"
    )


# Language settings
source_lang = st.sidebar.selectbox(
    "Source Language of Video", ["English", "Yoruba", "Hausa", "Igbo"], index=None
)
target_lang = st.sidebar.selectbox(
    "Target Language", ["Yoruba", "Hausa", "Igbo"], index=None
)

target_lang_map = {"Yoruba": "yo", "Hausa": "ha", "Igbo": "ig", "Amharic": "am"}
source_lang_map = {"English": "en", "Yoruba": "yo", "Hausa": "ha", "Igbo": "ig", "Amharic": "am"}

target_lang_value = target_lang_map.get(target_lang)
source_lang_value = source_lang_map.get(source_lang)

# Speaker settings
st.sidebar.subheader("🎙️ Speaker Voices")
if st.session_state.channel_url:
    num_speakers = 1  # simplified for channel/playlist
else:
    num_speakers = st.sidebar.selectbox(
        label="Number of Speakers in Video (Max 2)", options=[1, 2]
    )

voices = output_voice_base_on_lang(lang=target_lang) if target_lang else []
speaker1_voice = st.sidebar.selectbox("Speaker 1 Voice", voices) if voices else None
speaker2_voice = None
if num_speakers == 2 and voices:
    speaker2_voice = st.sidebar.selectbox("Speaker 2 Voice", voices)


if st.sidebar.button("Translate & Dub 🚀"):
    if select_youtube == "Enter URL (may not always be available)" and not st.session_state.youtube_url:
        st.error("Please enter a YouTube URL.")
    elif select_youtube == "Upload a YouTube video directly" and not st.session_state.youtube_video:
        st.error("Please upload a video file.")
    elif select_youtube == "Learn from a Channel or Playlist" and not st.session_state.channel_url:
        st.error("Please enter a channel or playlist URL.")
    else:
        original_video_temp_path, dubbed_video_path = None, None
        try:
            with st.spinner("Processing video... This may take a while ⏳"):
                try:
                    if st.session_state.youtube_url:
                        original_video_temp_path, audio_bytes = download_youtube_video(
                            url=st.session_state.youtube_url
                        )

                    elif st.session_state.youtube_video:
                        original_video_temp_path, audio_bytes = get_video_through_upload(
                        uploaded_file=st.session_state.youtube_video
                    )

                except Exception:
                    st.error("Ooops! Unable to Download Video: If you're running the deployed website, please use only offline videos")
                    st.stop()

                transcription_result = get_transcription_with_speaker(
                    audio_bytes=audio_bytes, src_lang=source_lang_value
                )
                result = insert_silence_placeholder(transcription_result)
                result = get_translation(result, target_lang=target_lang_value)

                speakers = {"SPEAKER_00": speaker1_voice.lower()} if num_speakers == 1 else {
                    "SPEAKER_00": speaker1_voice.lower(),
                    "SPEAKER_01": speaker2_voice.lower(),
                }

                translated_audio_path = merge_tts_chunks(
                    chunks=result, target_lang=target_lang_value, speakers=speakers
                )

                dubbed_video_path = dub_translated_audio_to_video(
                    video_path=original_video_temp_path, audio_path=translated_audio_path
                )

                render_video(dubbed_video_path)

                with st.expander("See Original Video"):
                    render_video(original_video_temp_path)

                with open(dubbed_video_path, "rb") as f:
                    st.download_button(
                        "Download Dubbed Video", f, file_name="dubbed_video.mp4", mime="video/mp4"
                    )

        except Exception as e:
            st.error(f"Failed to process video: {e}")
            st.stop()
        finally:
            for path in [original_video_temp_path, dubbed_video_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass



