from sqlalchemy.orm import Session
import logging
from typing import Optional, Dict, List
from ..models.script import Script, ScriptStatus
from .voice_service import VoiceService
from .video_service import VideoService
from ..utils.resource_manager import resource_manager
import os
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class ScriptService:
    def __init__(self, db: Session):
        self.db = db
        self.voice_service = VoiceService()
        self.video_service = VideoService()
        self.temp_files: List[str] = []

    async def process_script(self, script: Script) -> bool:
        """
        Process a script through the entire workflow
        """
        try:
            # Acquire single process lock
            await resource_manager.acquire_process_lock()
            
            # Load channel config
            channel_config = await resource_manager.get_channel_config(script.channel_name)
            if not channel_config:
                raise ValueError(f"No configuration found for channel {script.channel_name}")

            # Generate audio (no task_id for voice)
            voice_result = await self.voice_service.generate_audio(
                source_file=script.file_path,
                session_name=f"session_{script.id}",
                voice_config=channel_config["voice_settings"]
            )
            
            if not voice_result or not voice_result.get("audio_path"):
                raise ValueError("Failed to generate audio")
            
            script.status = ScriptStatus.VOICE_DONE
            script.audio_path = voice_result["audio_path"]
            self.db.commit()

            # Get available overlay2 file
            overlay2_path = await resource_manager.get_next_overlay2(
                script.channel_name,
                channel_config["paths"]["overlay2_dir"]
            )
            if not overlay2_path:
                raise ValueError("No available overlay2 files")

            # Validate all required paths
            overlay1_path = os.path.join(os.getcwd(), channel_config["paths"]["overlay1"])
            resource_manager.validate_paths(
                voice_result["audio_path"],
                voice_result["subtitle_path"],
                overlay1_path,
                overlay2_path
            )

            # Create video (with task_id)
            output_name = f"{script.channel_name}_{script.id}.mp4"
            video_result = await self.video_service.create_video(
                audio_path=voice_result["audio_path"],
                subtitle_path=voice_result["subtitle_path"],
                overlay1_path=overlay1_path,
                overlay2_path=overlay2_path,
                preset_name=channel_config["video_settings"]["preset_name"],
                output_name=output_name
            )
            
            if not video_result or "task_id" not in video_result:
                raise ValueError("Failed to start video generation")

            script.video_task_id = video_result["task_id"]
            self.db.commit()

            # Store temp files for cleanup
            self.temp_files.extend([
                voice_result["audio_path"],
                voice_result["subtitle_path"]
            ])

            return True
            
        except Exception as e:
            logger.error(f"Error processing script {script.id}: {str(e)}")
            script.status = ScriptStatus.ERROR
            script.error_message = str(e)
            self.db.commit()
            return False
        finally:
            resource_manager.release_process_lock()

    async def check_task_status(self, script: Script) -> Optional[ScriptStatus]:
        """
        Check the status of ongoing tasks for a script
        """
        try:
            # Only check video status since voice is synchronous
            if script.status == ScriptStatus.VOICE_DONE and script.video_task_id:
                video_status = await self.video_service.check_status(script.video_task_id)
                if video_status and video_status.get("status") == "completed":
                    script.status = ScriptStatus.COMPLETED
                    script.video_path = video_status.get("output_path")
                    
                    # Move overlay2 to used directory
                    channel_config = await resource_manager.get_channel_config(script.channel_name)
                    if channel_config and video_status.get("overlay2_path"):
                        await resource_manager.move_overlay2(
                            video_status["overlay2_path"],
                            os.path.basename(script.video_path),
                            channel_config["paths"]["overlay2_used_dir"]
                        )
                    
                    # Cleanup temp files
                    await resource_manager.cleanup_temp_files(self.temp_files)
                    self.temp_files = []
                    
                    self.db.commit()
                elif video_status and video_status.get("status") == "error":
                    script.status = ScriptStatus.ERROR_VIDEO
                    script.error_message = video_status.get("error")
                    self.db.commit()

            return script.status

        except Exception as e:
            logger.error(f"Error checking task status for script {script.id}: {str(e)}")
            return None
