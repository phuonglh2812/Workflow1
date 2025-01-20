import os
import random
import shutil
import httpx
import asyncio
import logging
import json
import uuid
from typing import Dict, Optional
from ..utils.logging_config import setup_logging, CustomLoggerAdapter
from ..config.paths import (
    get_channel_overlay1_dir,
    get_channel_overlay2_dir,
    get_channel_final_dir,
    get_video_service_temp_path,
    get_channel_config_path,
    VIDEO_API_URL
)

# Khởi tạo logger
logger = setup_logging()
video_logger = CustomLoggerAdapter(logger, {'service': 'video_service'})

class VideoService:
    def __init__(self, video_api_url: str = None):
        self.video_api_url = video_api_url or VIDEO_API_URL
        self.logger = video_logger

    def _get_random_overlay2(self, channel_name: str) -> tuple[str, str]:
        """
        Lấy ngẫu nhiên một file overlay2 từ thư mục tương ứng
        Trả về tuple (đường dẫn đầy đủ, tên file)
        """
        overlay2_dir = get_channel_overlay2_dir(channel_name)
        if not os.path.exists(overlay2_dir):
            raise ValueError(f"Không tìm thấy thư mục overlay2 cho channel {channel_name}")
            
        overlay_files = [f for f in os.listdir(overlay2_dir) if f.endswith('.png')]
        if not overlay_files:
            raise ValueError(f"Không tìm thấy file overlay2 nào trong thư mục {overlay2_dir}")
            
        selected_file = random.choice(overlay_files)
        return os.path.join(overlay2_dir, selected_file), selected_file

    def _move_overlay_to_final(self, channel_name: str, overlay_name: str, video_name: str):
        """
        Di chuyển file overlay đã sử dụng vào thư mục final và đổi tên
        """
        source_path = os.path.join(get_channel_overlay2_dir(channel_name), overlay_name)
        final_dir = get_channel_final_dir(channel_name)
        os.makedirs(final_dir, exist_ok=True)
        
        # Tạo tên mới cho overlay: tên_video_overlay.png
        new_name = f"{os.path.splitext(video_name)[0]}_overlay.png"
        target_path = os.path.join(final_dir, new_name)
        
        shutil.move(source_path, target_path)
        self.logger.info(f"Đã di chuyển overlay {overlay_name} đến {target_path}")

    def _move_video_to_final(self, channel_name: str, output_name: str) -> str:
        """Di chuyển video từ thư mục final về thư mục assets/final/channel"""
        source_path = get_video_service_temp_path(output_name)
        final_dir = get_channel_final_dir(channel_name)
        os.makedirs(final_dir, exist_ok=True)
        
        final_path = os.path.join(final_dir, output_name)
        if os.path.exists(source_path):
            shutil.move(source_path, final_path)
            self.logger.info(f"Đã di chuyển video từ {source_path} đến {final_path}")
        return final_path

    def _load_channel_config(self, channel_name: str):
        """Load cấu hình cho channel"""
        try:
            config_path = get_channel_config_path(channel_name)
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Không thể đọc file cấu hình cho channel {channel_name}: {e}")
            # Trả về cấu hình mặc định nếu không đọc được file
            return {
                "video_settings": {
                    "preset_name": "1"
                }
            }

    async def process_video(self, audio_path: str, srt_path: str, channel_name: str) -> Dict[str, str]:
        """
        Xử lý video với overlay và timeout 30 phút
        """
        try:
            # Load cấu hình channel
            channel_config = self._load_channel_config(channel_name)
            video_settings = channel_config.get("video_settings", {})
            preset_name = video_settings.get("preset_name", "1")

            # Lấy overlay1 cố định theo channel
            overlay1_path = os.path.join(get_channel_overlay1_dir(channel_name), 'overlay1.png')
            if not os.path.exists(overlay1_path):
                raise ValueError(f"Không tìm thấy overlay1 cho channel {channel_name}")

            # Lấy ngẫu nhiên một overlay2
            overlay2_path, overlay2_name = self._get_random_overlay2(channel_name)
            
            # Tạo tên cho video output
            unique_id = str(uuid.uuid4())[:8]
            output_name = f"video_{unique_id}.mp4"
            
            # Gửi request xử lý video
            async with httpx.AsyncClient(timeout=1800.0) as client:  # 30 phút timeout
                payload = {
                    "request": "",
                    "audio_path": audio_path.replace('\\', '/'),
                    "subtitle_path": srt_path.replace('\\', '/'),
                    "overlay1_path": overlay1_path.replace('\\', '/'),
                    "overlay2_path": overlay2_path.replace('\\', '/'),
                    "preset_name": preset_name,  # Sử dụng preset từ cấu hình
                    "output_name": output_name
                }
                
                self.logger.debug(f"Sending request to video service with payload: {payload}")
                
                # Gửi request tạo video với timeout 30 phút
                response = await client.post(
                    f"{self.video_api_url}/api/process/make",
                    headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
                    data=payload
                )
                response.raise_for_status()
                task_data = response.json()
                task_id = task_data.get('task_id')
                
                if not task_id:
                    raise ValueError("Không nhận được task_id từ video service")
                
                self.logger.info(f"Video processing started with task_id: {task_id}")
                
                # Kiểm tra trạng thái với retry trong 30 phút
                max_retries = 180  # 180 lần * 10 giây = 1800 giây = 30 phút
                retry_delay = 10   # 10 giây giữa các lần thử
                
                for attempt in range(max_retries):
                    try:
                        # Gửi yêu cầu kiểm tra trạng thái
                        status_response = await client.get(f"{self.video_api_url}/api/process/status/{task_id}")
                        
                        if status_response.status_code == 200:
                            # Thoát khỏi vòng lặp khi nhận được phản hồi 200 OK
                            break  # Thoát khỏi vòng lặp

                    except Exception as e:
                        logger.warning(f"Lần thử {attempt + 1}/{max_retries} thất bại: {str(e)}")
                        await asyncio.sleep(retry_delay)

                # Di chuyển overlay2 đã sử dụng vào thư mục final
                move_attempts = 2
                for attempt in range(move_attempts):
                    try:
                        self._move_overlay_to_final(channel_name, overlay2_name, output_name)
                        logger.info(f"Overlay2 đã được di chuyển thành công: {overlay2_name}")
                        break  # Thoát khỏi vòng lặp nếu di chuyển thành công
                    except Exception as e:
                        logger.warning(f"Lần thử di chuyển overlay2 {attempt + 1}/{move_attempts} thất bại: {str(e)}")
                        if attempt == move_attempts - 1:
                            logger.error("Không thể di chuyển overlay2 sau 2 lần thử.")
                        await asyncio.sleep(3)  # Thêm thời gian chờ 3 giây giữa các lần thử
                
                # Di chuyển video về thư mục final của channel
                move_attempts = 2
                for attempt in range(move_attempts):
                    try:
                        final_video_path = self._move_video_to_final(channel_name, output_name)
                        logger.info(f"Video đã được di chuyển thành công: {final_video_path}")
                        break  # Thoát khỏi vòng lặp nếu di chuyển thành công
                    except Exception as e:
                        logger.warning(f"Lần thử di chuyển video {attempt + 1}/{move_attempts} thất bại: {str(e)}")
                        if attempt == move_attempts - 1:
                            logger.error("Không thể di chuyển video sau 2 lần thử.")
                        await asyncio.sleep(3)  # Thêm thời gian chờ 3 giây giữa các lần thử
                
                self.logger.info(f"Video đã được xử lý thành công: {final_video_path}")
                return {
                    'video_path': final_video_path,
                    'overlay_path': overlay2_path
                }
                
        except Exception as e:
            self.logger.error(f"Error in video processing: {str(e)}")
            raise
