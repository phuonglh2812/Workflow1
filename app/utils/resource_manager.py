import os
import logging
import json
from typing import Dict, Optional
from filelock import FileLock
import asyncio
from datetime import datetime, timedelta
import shutil

logger = logging.getLogger(__name__)

class ResourceManager:
    _instance = None
    _config_cache = {}
    _config_last_loaded = {}
    _locks = {}
    _process_lock = None
    CONFIG_CACHE_DURATION = timedelta(minutes=5)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """Initialize the resource manager"""
        self._process_lock = asyncio.Lock()  # Single process lock
        self.setup_locks()
        
    def setup_locks(self):
        """Setup locks for critical resources"""
        base_path = os.getcwd()
        lock_files = {
            'overlay2': os.path.join(base_path, 'locks', 'overlay2.lock'),
            'config': os.path.join(base_path, 'locks', 'config.lock'),
        }
        
        # Create locks directory if it doesn't exist
        os.makedirs(os.path.join(base_path, 'locks'), exist_ok=True)
        
        # Initialize locks
        for name, path in lock_files.items():
            self._locks[name] = FileLock(path)
            
    async def get_channel_config(self, channel_name: str) -> Optional[Dict]:
        """Get channel configuration with caching"""
        cache_key = f"channel_{channel_name}"
        
        # Check if cached config is still valid
        if (cache_key in self._config_cache and
            cache_key in self._config_last_loaded and
            datetime.now() - self._config_last_loaded[cache_key] < self.CONFIG_CACHE_DURATION):
            return self._config_cache[cache_key]
            
        try:
            async with self._locks['config']:
                config_path = f"config/channels/{channel_name}.json"
                if not os.path.exists(config_path):
                    logger.error(f"Configuration not found for channel: {channel_name}")
                    return None
                    
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                self._config_cache[cache_key] = config
                self._config_last_loaded[cache_key] = datetime.now()
                return config
                
        except Exception as e:
            logger.error(f"Error loading channel config: {str(e)}")
            return None
            
    async def get_next_overlay2(self, channel_name: str, overlay2_dir: str) -> Optional[str]:
        """Get next available overlay2 file with locking"""
        try:
            async with self._locks['overlay2']:
                # Get all PNG files in overlay2 directory
                overlay_files = [f for f in os.listdir(overlay2_dir) if f.endswith('.png')]
                if not overlay_files:
                    return None
                    
                # Get the first file (oldest)
                selected_file = overlay_files[0]
                return os.path.join(os.getcwd(), overlay2_dir, selected_file)
                
        except Exception as e:
            logger.error(f"Error getting next overlay2: {str(e)}")
            return None
            
    async def move_overlay2(self, overlay2_path: str, video_name: str, target_dir: str) -> Optional[str]:
        """Move overlay2 file to target directory"""
        try:
            async with self._locks['overlay2']:
                if not os.path.exists(overlay2_path):
                    return None
                    
                new_name = f"{os.path.splitext(video_name)[0]}_overlay2.png"
                target_path = os.path.join(target_dir, new_name)
                
                # Create target directory if it doesn't exist
                os.makedirs(target_dir, exist_ok=True)
                
                # Move the file
                shutil.move(overlay2_path, target_path)
                logger.info(f"Moved overlay2 to {target_path}")
                return target_path
                
        except Exception as e:
            logger.error(f"Error moving overlay2: {str(e)}")
            return None
            
    async def cleanup_temp_files(self, file_paths: list):
        """Clean up temporary files"""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Cleaned up temporary file: {path}")
            except Exception as e:
                logger.error(f"Error cleaning up file {path}: {str(e)}")
                
    async def acquire_process_lock(self):
        """Acquire the single process lock"""
        await self._process_lock.acquire()
        logger.info("Process lock acquired")
        
    def release_process_lock(self):
        """Release the single process lock"""
        try:
            self._process_lock.release()
            logger.info("Process lock released")
        except Exception as e:
            logger.error(f"Error releasing process lock: {str(e)}")
        
    def validate_paths(self, *paths):
        """Validate that all paths exist"""
        missing_paths = []
        for path in paths:
            if not os.path.exists(path):
                missing_paths.append(path)
        if missing_paths:
            raise ValueError(f"Files not found: {', '.join(missing_paths)}")
            
resource_manager = ResourceManager()
