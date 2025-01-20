import os
import logging
from logging.handlers import RotatingFileHandler
import logging.config

class CustomLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter để thêm thông tin context vào log messages
    """
    def process(self, msg, kwargs):
        # Thêm extra context vào message nếu có
        if self.extra:
            msg = f"{msg} - Context: {self.extra}"
        return msg, kwargs

def setup_logging(log_level=logging.INFO):
    """
    Cấu hình logging cho toàn bộ ứng dụng
    """
    # Tạo thư mục logs nếu chưa tồn tại
    os.makedirs('logs', exist_ok=True)
    
    # Tạo logger
    logger = logging.getLogger('app')
    logger.setLevel(log_level)
    
    # Định dạng log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler với rotating
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Xóa handlers cũ nếu có
    logger.handlers.clear()
    
    # Thêm handlers mới
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Tạo logger mặc định cho ứng dụng
logger = setup_logging()
LoggerAdapter = CustomLoggerAdapter  # Export LoggerAdapter class
