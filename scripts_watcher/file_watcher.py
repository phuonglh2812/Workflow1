import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import sys

# Thêm đường dẫn của app vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.script import Script, ScriptStatus, Base
from app.database import engine, SessionLocal

# Tạo thư mục logs nếu chưa tồn tại
os.makedirs('logs', exist_ok=True)

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/file_watcher.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ScriptWatcher(FileSystemEventHandler):
    def __init__(self, scripts_dir):
        """
        Khởi tạo file watcher cho các channel
        
        :param scripts_dir: Thư mục chứa các channel
        """
        self.scripts_dir = scripts_dir
        self.db = SessionLocal()
    
    def on_created(self, event):
        """
        Xử lý khi file mới được tạo
        """
        if not event.is_directory and event.src_path.endswith('.txt'):
            logger.info(f"Phát hiện file mới: {event.src_path}")
            self.process_file(event.src_path)
    
    def extract_channel_name(self, file_path):
        """
        Trích xuất tên channel từ đường dẫn file
        """
        parts = file_path.split(os.path.sep)
        for part in parts:
            if part.startswith('C') and part[1:].isdigit():
                return part
        return "C1"  # Mặc định
    
    def process_file(self, file_path):
        """
        Xử lý file script bằng cách thêm vào database
        """
        try:
            # Tạo record mới trong database
            script = Script(
                file_path=file_path,
                channel_name=self.extract_channel_name(file_path),
                status=ScriptStatus.pending,
                created_at=datetime.now()
            )
            
            # Thêm vào database
            self.db.add(script)
            self.db.commit()
            
            logger.info(f"Đã thêm file {os.path.basename(file_path)} vào database với ID: {script.id}")
            
        except Exception as e:
            logger.error(f"Lỗi xử lý file {file_path}: {str(e)}")
            # Không di chuyển file, chỉ ghi log

def start_watching(scripts_dir):
    """
    Bắt đầu giám sát thư mục scripts với các channel
    """
    try:
        # Tạo và khởi động observer
        event_handler = ScriptWatcher(scripts_dir)
        observer = Observer()
        observer.schedule(event_handler, scripts_dir, recursive=True)
        observer.start()
        
        logger.info(f"Bắt đầu theo dõi thư mục: {scripts_dir}")
        
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Dừng theo dõi thư mục")
        
        observer.join()
        
    except Exception as e:
        logger.error(f"Lỗi khởi động watcher: {e}")

if __name__ == "__main__":
    # Cấu hình từ biến môi trường hoặc giá trị mặc định
    SCRIPTS_DIR = os.getenv('SCRIPTS_DIR', 'e:/RedditWorkflow/WF/scripts')
    
    # Khởi động watcher
    start_watching(SCRIPTS_DIR)
