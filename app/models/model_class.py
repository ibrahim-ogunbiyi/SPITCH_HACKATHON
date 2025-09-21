from core.config import settings
import io
from spitch import Spitch
import requests


class Models:

    # @classmethod
    # def get_asr_model(cls, audio_bytes:io.BytesIO):

    #     client = Groq(api_key=settings.GROQ_API_KEY)


    #     # Create a transcription of the audio file
    #     transcription = client.audio.transcriptions.create(
    #     file=audio_bytes, 
    #     model="whisper-large-v3-turbo", 
    #     language="en",  
    #     temperature=0.0  
    #     )
        
    #     return transcription.text
    
    @classmethod
    def get_spitch_asr_model(cls, audio_bytes:bytes, src_lang:str):

        client = Spitch(api_key=settings.SPITCH_API_KEY)

        response = client.speech.transcribe(
            language=src_lang,
            content= audio_bytes

        )

        return response.text
    
    @classmethod
    def get_speaker_diarization(cls, audio_bytes:bytes) -> list[dict]:

        data = io.BytesIO(audio_bytes)
        url = "https://ibrahim-geek-speaker-diarisation.hf.space/get_diarisation"
        content = {"audio_bytes":data}
        response = requests.post(url, files=content)

        return response.json()













