import os
import shutil
import httpx
from datetime import datetime
import json
import uuid
from ..utils.logging_config import logger
from ..config.paths import (
    get_pandrator_session_dir,
    get_channel_voice_dir,
    get_channel_config_path,
    VOICE_API_URL,
    XTTS_API_URL,
    CONFIG_DIR
)

class VoiceService:
    def __init__(self, voice_api_url: str = None):
        self.api_url = voice_api_url or VOICE_API_URL
        self.logger = logger.getChild('voice_service')

    async def process_voice(self, file_path: str, channel_name: str):
        """
        Xử lý voice với timeout 30 phút
        """
        self.logger.info(f"Starting voice processing for file: {file_path}")
        try:
            # Sinh session name duy nhất
            script_name = os.path.splitext(os.path.basename(file_path))[0]
            session_name = f"{script_name}_{uuid.uuid4().hex}"
            
            # Load config
            voice_config = self._load_channel_voice_config(channel_name)
            
            # Chuẩn bị payload
            payload = {
                "source_file": file_path.replace('/', '\\'),
                "session_name": session_name,
                "xtts_server_url": XTTS_API_URL,
                "speaker_voice": voice_config.get('speaker_voice', "EN_Ivy_Female"),
                "language": voice_config.get('language', 'en'),
                "temperature": voice_config.get('temperature', 0.75),
                "length_penalty": voice_config.get('length_penalty', 1),
                "repetition_penalty": voice_config.get('repetition_penalty', 5),
                "top_k": voice_config.get('top_k', 50),
                "top_p": voice_config.get('top_p', 0.85),
                "speed": voice_config.get('speed', 1),
                "stream_chunk_size": voice_config.get('stream_chunk_size', 200),
                "enable_text_splitting": voice_config.get('enable_text_splitting', True),
                "max_sentence_length": voice_config.get('max_sentence_length', 100),
                "enable_sentence_splitting": voice_config.get('enable_sentence_splitting', True),
                "enable_sentence_appending": voice_config.get('enable_sentence_appending', True),
                "remove_diacritics": voice_config.get('remove_diacritics', False),
                "output_format": voice_config.get('output_format', 'wav'),
                "bitrate": voice_config.get('bitrate', '312k'),
                "appended_silence": voice_config.get('appended_silence', 200),
                "paragraph_silence": voice_config.get('paragraph_silence', 200)
            }
            
            self.logger.debug(f"Sending request to voice service with payload: {payload}")
            
            # Gọi API với timeout 30 phút
            async with httpx.AsyncClient(timeout=1800.0) as client:
                response = await client.post(
                    f'{self.api_url}/process_with_pandrator',
                    json=payload
                )
                
                if response.status_code != 200:
                    raise Exception(f"Voice API error: {response.text}")
                
                # Đường dẫn cố định của Pandrator
                base_dir = get_pandrator_session_dir(session_name)
                
                # Kiểm tra file tồn tại
                wav_path = os.path.join(base_dir, 'final.wav')
                srt_path = os.path.join(base_dir, 'final.srt')
                
                if not os.path.exists(wav_path) or not os.path.exists(srt_path):
                    raise Exception("Voice files not generated")

                # Đường dẫn assets của channel
                channel_assets_dir = get_channel_voice_dir(channel_name)
                os.makedirs(channel_assets_dir, exist_ok=True)

                # Di chuyển WAV
                wav_filename = f"{session_name}.wav"
                wav_dest_path = os.path.join(channel_assets_dir, wav_filename)
                if os.path.exists(wav_path):
                    shutil.move(wav_path, wav_dest_path)
                else:
                    raise Exception("File final.wav không được tạo ra")

                # Di chuyển SRT
                srt_filename = f"{session_name}.srt"
                srt_dest_path = os.path.join(channel_assets_dir, srt_filename)
                if os.path.exists(srt_path):
                    shutil.move(srt_path, srt_dest_path)
                else:
                    raise Exception("File final.srt không được tạo ra")

                self.logger.info(f"Voice processing completed successfully for {file_path}")
                return {
                    'audio_path': wav_dest_path,
                    'srt_path': srt_dest_path,
                    'session_id': session_name
                }
                
        except Exception as e:
            self.logger.error(f"Error in voice processing: {e}")
            raise

    def _load_channel_voice_config(self, channel_name: str):
        """Load voice config cho channel"""
        try:
            config_path = get_channel_config_path(channel_name)
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading channel config: {e}")
            # Load config mặc định
            with open(os.path.join(CONFIG_DIR, 'voice_config.json'), 'r', encoding='utf-8') as f:
                return json.load(f)
