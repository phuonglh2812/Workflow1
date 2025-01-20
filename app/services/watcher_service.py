import os
import time
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from typing import Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ScriptFileHandler(FileSystemEventHandler):
    def __init__(self, process_callback: Callable[[str], Any], channel_name: str):
        self.process_callback = process_callback
        self.channel_name = channel_name
        self.processed_files = set()
        self.loop = asyncio.new_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def _run_async(self, coro):
        """Chạy coroutine trong event loop"""
        asyncio.set_event_loop(self.loop)
        return self.loop.run_until_complete(coro)
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        if not event.src_path.endswith('.txt'):
            return
            
        # Kiểm tra xem file đã được xử lý chưa
        if event.src_path in self.processed_files:
            return
            
        logger.info(f"Phát hiện file mới: {event.src_path}")
        
        # Đợi một chút để đảm bảo file đã được ghi hoàn toàn
        time.sleep(1)
        
        try:
            # Đánh dấu file đã được xử lý
            self.processed_files.add(event.src_path)
            
            # Chạy callback trong event loop
            self.executor.submit(self._run_async, self.process_callback(event.src_path))
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý file {event.src_path}: {str(e)}")
            
    def __del__(self):
        """Cleanup khi handler bị hủy"""
        self.executor.shutdown(wait=False)
        if self.loop.is_running():
            self.loop.stop()
        if not self.loop.is_closed():
            self.loop.close()

class WatcherService:
    def __init__(self):
        self.observers: Dict[str, Observer] = {}
        self.handlers: Dict[str, ScriptFileHandler] = {}
        
    def start_watching(self, directory: str, process_callback: Callable[[str], Any], channel_name: str):
        """
        Bắt đầu theo dõi một thư mục cho channel cụ thể
        
        Args:
            directory: Đường dẫn thư mục cần theo dõi
            process_callback: Callback được gọi khi có file mới
            channel_name: Tên channel
        """
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        # Tạo handler và observer mới cho channel
        handler = ScriptFileHandler(process_callback, channel_name)
        observer = Observer()
        observer.schedule(handler, directory, recursive=False)
        
        # Lưu handler và observer vào dictionary
        self.handlers[channel_name] = handler
        self.observers[channel_name] = observer
        
        # Khởi động observer
        observer.start()
        logger.info(f"Bắt đầu theo dõi thư mục {directory} cho channel {channel_name}")
        
    def stop_watching(self, channel_name: str):
        """Dừng theo dõi cho một channel cụ thể"""
        if channel_name in self.observers:
            self.observers[channel_name].stop()
            self.observers[channel_name].join()
            del self.observers[channel_name]
            
            if channel_name in self.handlers:
                del self.handlers[channel_name]
                
            logger.info(f"Đã dừng theo dõi channel {channel_name}")
            
    def stop_all(self):
        """Dừng tất cả các observer"""
        for channel_name in list(self.observers.keys()):
            self.stop_watching(channel_name)
