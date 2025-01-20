import os
import random
import shutil
import httpx
import asyncio
import logging
from typing import Dict, Optional
from ..utils.logging_config import setup_logging, CustomLoggerAdapter

# Setup logging
base_logger = setup_logging()
logger = CustomLoggerAdapter(base_logger, {})

class VideoService:
    def __init__(self, video_api_url: str):
        self.video_api_url = video_api_url
        
    def _get_random_overlay2(self, channel_name: str) -> tuple[str, str]:
        """
        Lấy ngẫu nhiên một file overlay2 từ thư mục tương ứng
        Trả về tuple (đường dẫn đầy đủ, tên file)
        """
        overlay2_dir = f"E:/RedditWorkflow/WF/assets/overlay2/{channel_name}"
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
        source_path = f"E:/RedditWorkflow/WF/assets/overlay2/{channel_name}/{overlay_name}"
        final_dir = f"E:/RedditWorkflow/WF/assets/final/{channel_name}"
        os.makedirs(final_dir, exist_ok=True)
        
        # Tạo tên mới cho overlay: tên_video_overlay.png
        new_name = f"{os.path.splitext(video_name)[0]}_overlay.png"
        target_path = os.path.join(final_dir, new_name)
        
        shutil.move(source_path, target_path)
        logger.info(f"Đã di chuyển overlay {overlay_name} đến {target_path}")

    def _move_video_to_final(self, channel_name: str, output_name: str) -> str:
        """Di chuyển video từ thư mục final về thư mục assets/final/channel"""
        source_path = f"E:/RedditWorkflow/final/{output_name}"
        final_dir = f"E:/RedditWorkflow/WF/assets/final/{channel_name}"
        os.makedirs(final_dir, exist_ok=True)
        
        final_path = os.path.join(final_dir, output_name)
        if os.path.exists(source_path):
            shutil.move(source_path, final_path)
            logger.info(f"Đã di chuyển video từ {source_path} đến {final_path}")
        return final_path

    async def process_video(self, audio_path: str, srt_path: str, channel_name: str) -> Dict[str, str]:
        """
        Xử lý video với overlay và timeout 30 phút
        """
        try:
            # Lấy overlay1 cố định theo channel
            overlay1_path = f"E:/RedditWorkflow/WF/assets/overlay1/{channel_name}/overlay1.png"
            if not os.path.exists(overlay1_path):
                raise ValueError(f"Không tìm thấy overlay1 cho channel {channel_name}")

            # Lấy ngẫu nhiên một overlay2
            overlay2_path, overlay2_name = self._get_random_overlay2(channel_name)
            
            # Tạo tên cho video output
            output_name = f"{os.path.splitext(os.path.basename(audio_path))[0]}.mp4"
            
            # Gửi request xử lý video
            async with httpx.AsyncClient(timeout=1800.0) as client:  # 30 phút timeout
                payload = {
                    "request": "",
                    "audio_path": audio_path.replace('\\', '/'),
                    "subtitle_path": srt_path.replace('\\', '/'),
                    "overlay1_path": overlay1_path.replace('\\', '/'),
                    "overlay2_path": overlay2_path.replace('\\', '/'),
                    "preset_name": "1",
                    "output_name": output_name
                }
                
                logger.debug(f"Sending request to video service with payload: {payload}")
                
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
                
                logger.info(f"Video processing started with task_id: {task_id}")
                
                # Kiểm tra trạng thái với retry trong 30 phút
                max_retries = 180  # 180 lần * 10 giây = 1800 giây = 30 phút
                retry_delay = 10   # 10 giây giữa các lần thử
                
                for attempt in range(max_retries):
                    try:
                        status_response = await client.get(
                            f"{self.video_api_url}/api/process/status/{task_id}",
                            headers={"accept": "application/json"}
                        )
                        
                        if status_response.status_code == 200:
                            # Nếu nhận được 200, coi như thành công
                            temp_video_path = f"E:/RedditWorkflow/final/{output_name}"
                            
                            # Di chuyển overlay2 đã sử dụng vào thư mục final
                            self._move_overlay_to_final(channel_name, overlay2_name, output_name)
                            
                            # Di chuyển video về thư mục final của channel
                            final_video_path = self._move_video_to_final(channel_name, output_name)
                            
                            logger.info(f"Video đã được xử lý thành công: {final_video_path}")
                            return {
                                'video_path': final_video_path,
                                'overlay_path': overlay2_path
                            }
                            
                    except Exception as e:
                        logger.warning(f"Lần thử {attempt + 1}/{max_retries} thất bại: {str(e)}")
                        
                    # Đợi trước khi thử lại
                    await asyncio.sleep(retry_delay)
                
                raise Exception(f"Không nhận được phản hồi thành công sau 30 phút")
                
        except Exception as e:
            logger.error(f"Error in video processing: {str(e)}")
            raise
