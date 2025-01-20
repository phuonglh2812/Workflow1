import os
import shutil
from typing import Dict
import httpx
from sqlalchemy.orm import Session
from .utils.logging_config import logger
from .services.voice_service import VoiceService
from .services.video_service import VideoService
import time
import uuid

# Khởi tạo các service với cấu hình
voice_service = VoiceService(voice_api_url="http://localhost:5003")
video_service = VideoService(video_api_url="http://localhost:5001")

async def send_callback(callback_url: str, payload: Dict[str, any]):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(callback_url, json=payload)
    except Exception as e:
        logger.error(f"Callback failed: {e}")

async def process_script_task(
    task_id: str, 
    file_path: str, 
    channel_name: str,
    callback_url: str,
    callback_id: str,
    db: Session
):
    voice_response = None
    try:
        # Log bắt đầu xử lý task
        logger.info(f"Starting processing for file: {file_path}")

        # Bước 1: Xử lý Voice
        logger.info("Processing voice...")
        try:
            voice_response = await voice_service.process_voice(
                file_path=file_path, 
                channel_name=channel_name
            )
            logger.info("Voice processing completed successfully.")

            # Đổi tên file audio và SRT
            script_name = os.path.splitext(os.path.basename(file_path))[0]
            unique_id = uuid.uuid4().hex
            audio_name = f"{script_name}_{unique_id}.wav"
            srt_name = f"{script_name}_{unique_id}.srt"

            # Di chuyển file audio và SRT đến thư mục assets
            audio_path = voice_response['audio_path']
            srt_path = voice_response['srt_path']
            shutil.move(audio_path, os.path.join('e:/RedditWorkflow/WF/assets/audio', audio_name))
            shutil.move(srt_path, os.path.join('e:/RedditWorkflow/WF/assets/srt', srt_name))

            voice_response['audio_path'] = os.path.join('e:/RedditWorkflow/WF/assets/audio', audio_name)
            voice_response['srt_path'] = os.path.join('e:/RedditWorkflow/WF/assets/srt', srt_name)

        except Exception as voice_error:
            logger.error(f"Voice processing error: {voice_error}")
            
            # Di chuyển file lỗi vào thư mục error
            error_dir = os.path.join('e:/RedditWorkflow/WF/scripts', channel_name, 'error')
            os.makedirs(error_dir, exist_ok=True)
            error_file_path = os.path.join(error_dir, os.path.basename(file_path))
            
            # Ghi log chi tiết lỗi
            error_log_path = os.path.join(error_dir, f"{os.path.basename(file_path)}_error.log")
            with open(error_log_path, 'w') as log_file:
                log_file.write(f"Voice Processing Error:\n{str(voice_error)}")
            
            # Di chuyển file gốc vào thư mục lỗi
            shutil.move(file_path, error_file_path)
            
            # Gửi callback lỗi
            await send_callback(
                callback_url, 
                {
                    'task_id': task_id,
                    'status': 'failed',
                    'stage': 'voice_processing',
                    'error': str(voice_error),
                    'error_file': error_file_path,
                    'error_log': error_log_path
                }
            )
            return

        # Bước 2: Xử lý Video
        logger.info("Processing video...")
        try:
            video_response = await video_service.process_video(
                audio_path=voice_response['audio_path'],
                srt_path=voice_response['srt_path'],
                channel_name=channel_name
            )
            # Tạo tên video cuối cùng
            final_video_name = f"{script_name}_{unique_id}.mp4"
            final_video_path = os.path.join('e:/RedditWorkflow/WF/assets/videos', final_video_name)
            # Di chuyển video đến đường dẫn mới
            shutil.move(video_response['video_path'], final_video_path)
            logger.info(f"Video đã được di chuyển tới: {final_video_path}")
        except Exception as video_error:
            logger.error(f"Video processing error: {video_error}")
            
            # Di chuyển file lỗi vào thư mục error
            error_dir = os.path.join('e:/RedditWorkflow/WF/scripts', channel_name, 'error')
            os.makedirs(error_dir, exist_ok=True)
            error_file_path = os.path.join(error_dir, os.path.basename(file_path))
            
            # Ghi log chi tiết lỗi
            error_log_path = os.path.join(error_dir, f"{os.path.basename(file_path)}_error.log")
            with open(error_log_path, 'w') as log_file:
                log_file.write(f"Video Processing Error:\n{str(video_error)}")
            
            # Di chuyển file gốc vào thư mục lỗi
            shutil.move(file_path, error_file_path)
            
            # Gửi callback lỗi - VẪN GIỮ NGUYÊN THÔNG TIN AUDIO VÀ SRT
            await send_callback(
                callback_url, 
                {
                    'task_id': task_id,
                    'status': 'failed',
                    'stage': 'video_processing',
                    'error': str(video_error),
                    'error_file': error_file_path,
                    'error_log': error_log_path,
                    'audio_path': voice_response['audio_path'],
                    'srt_path': voice_response['srt_path']
                }
            )
            return

        # Xử lý thành công
        # Di chuyển file đã xử lý vào thư mục processed
        processed_dir = os.path.join('e:/RedditWorkflow/WF/scripts', channel_name, 'processed')
        os.makedirs(processed_dir, exist_ok=True)
        processed_file_path = os.path.join(processed_dir, os.path.basename(file_path))
        shutil.move(file_path, processed_file_path)
        logger.info(f"File đã được di chuyển tới thư mục processed: {processed_file_path}")
        
        # Gửi callback thành công
        await send_callback(
            callback_url,
            {
                'task_id': task_id,
                'status': 'success',
                'processed_file': processed_file_path,
                'final_video': final_video_path
            }
        )

    except Exception as e:
        logger.error(f"Unexpected processing error: {e}")
        # Gửi callback lỗi
        if callback_url:
            await send_callback(
                callback_url, 
                {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': str(e)
                }
            )

def setup_channel_directories(channel_name: str):
    """
    Tạo cấu trúc thư mục cho channel mới
    """
    base_dir = "E:/RedditWorkflow/WF"
    directories = [
        f"{base_dir}/scripts/{channel_name}",
        f"{base_dir}/scripts/{channel_name}/error",
        f"{base_dir}/assets/overlay1/{channel_name}",
        f"{base_dir}/assets/overlay2/{channel_name}",
        f"{base_dir}/assets/voice/{channel_name}",
        f"{base_dir}/assets/final/{channel_name}"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Đã tạo thư mục: {directory}")

async def process_script_file(file_path: str):
    """
    Xử lý file script mới được thêm vào
    """
    try:
        # Lấy tên file kịch bản mà không có phần mở rộng
        script_name = os.path.splitext(os.path.basename(file_path))[0]
        channel_name = os.path.basename(os.path.dirname(file_path))

        # Kiểm tra xem thư mục kênh đã tồn tại hay chưa
        channel_dir = os.path.join('e:/RedditWorkflow/WF/scripts', channel_name)
        if not os.path.exists(channel_dir):
            # Nếu chưa có kênh, tạo cấu trúc thư mục cho channel
            setup_channel_directories(channel_name)

        # Xử lý file
        await process_script_task(
            task_id=f"{script_name}_{int(time.time())}",
            file_path=file_path,
            channel_name=channel_name,
            callback_url="",  # Có thể thêm callback URL nếu cần
            callback_id="",   # Có thể thêm callback ID nếu cần
            db=None          # Có thể thêm db session nếu cần
        )

    except Exception as e:
        logger.error(f"Lỗi xử lý file {file_path}: {str(e)}")
        
        # Di chuyển file lỗi vào thư mục error
        error_dir = os.path.join(os.path.dirname(file_path), 'error')
        os.makedirs(error_dir, exist_ok=True)
        error_file_path = os.path.join(error_dir, os.path.basename(file_path))
        shutil.move(file_path, error_file_path)
        logger.error(f"File lỗi đã được di chuyển tới: {error_file_path}")
