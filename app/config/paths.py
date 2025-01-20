"""
Quản lý tập trung các đường dẫn trong ứng dụng.

Cấu hình đường dẫn:
1. Đường dẫn gốc (ROOT):
   - Mặc định: 'E:/RedditWorkflow'
   - Để thay đổi: Đặt biến môi trường 'WF_ROOT'
   - Ví dụ: set WF_ROOT=D:/MyWorkflow

2. URLs API (có thể thay đổi qua biến môi trường):
   - VOICE_API_URL: URL của voice service (mặc định: http://localhost:5003)
   - VIDEO_API_URL: URL của video service (mặc định: http://localhost:5001)
   - XTTS_API_URL: URL của XTTS service (mặc định: http://localhost:8020)
   - APP_API_URL: URL của main app (mặc định: http://localhost:8000)

Cấu trúc thư mục:
WF_ROOT/
├── WF/                      # Thư mục chính của ứng dụng
│   ├── scripts/            # Chứa các script theo channel
│   │   └── {channel}/     # Thư mục channel
│   │       ├── error/     # Scripts bị lỗi
│   │       ├── processed/ # Scripts đã xử lý
│   │       └── completed/ # Scripts hoàn thành
│   ├── assets/            # Chứa tài nguyên
│   │   ├── audio/        # File âm thanh
│   │   ├── srt/          # File phụ đề
│   │   ├── videos/       # Video đầu ra
│   │   ├── overlay1/     # Overlay cố định theo channel
│   │   ├── overlay2/     # Overlay ngẫu nhiên theo channel
│   │   ├── final/        # Video hoàn chỉnh
│   │   └── voice/        # File giọng nói
│   └── config/           # Cấu hình
│       └── channels/     # Cấu hình riêng cho từng channel
└── Pandrator/            # Thư mục Pandrator
    └── Pandrator/
        └── sessions/     # Phiên làm việc của Pandrator

Lưu ý:
1. Tất cả các thư mục sẽ được tự động tạo khi khởi động ứng dụng
2. Đường dẫn được xây dựng tương thích với mọi hệ điều hành
3. Để thay đổi cấu trúc thư mục, chỉ cần sửa các biến và hàm trong file này
4. Mọi thay đổi sẽ được áp dụng cho toàn bộ ứng dụng
"""

import os
import json
import shutil

# Base directories
WF_ROOT = os.getenv('WF_ROOT', 'E:/RedditWorkflow')
WF_DIR = os.path.join(WF_ROOT, 'WF')
PANDRATOR_DIR = os.path.join(WF_ROOT, 'Pandrator/Pandrator')

# WF directories
SCRIPTS_DIR = os.path.join(WF_DIR, 'scripts')
ASSETS_DIR = os.path.join(WF_DIR, 'assets')
CONFIG_DIR = os.path.join(WF_DIR, 'config')

# Assets subdirectories
AUDIO_DIR = os.path.join(ASSETS_DIR, 'audio')
SRT_DIR = os.path.join(ASSETS_DIR, 'srt')
VIDEOS_DIR = os.path.join(ASSETS_DIR, 'videos')
OVERLAY1_DIR = os.path.join(ASSETS_DIR, 'overlay1')
OVERLAY2_DIR = os.path.join(ASSETS_DIR, 'overlay2')
FINAL_DIR = os.path.join(ASSETS_DIR, 'final')
VOICE_DIR = os.path.join(ASSETS_DIR, 'voice')

# Templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

# Channel paths
def get_channel_dir(channel_name):
    """Lấy đường dẫn thư mục gốc của channel"""
    return os.path.join(SCRIPTS_DIR, channel_name)

def get_channel_error_dir(channel_name):
    """Lấy đường dẫn thư mục chứa scripts lỗi của channel"""
    return os.path.join(get_channel_dir(channel_name), 'error')

def get_channel_processed_dir(channel_name):
    """Lấy đường dẫn thư mục chứa scripts đã xử lý của channel"""
    return os.path.join(get_channel_dir(channel_name), 'processed')

def get_channel_completed_dir(channel_name):
    """Lấy đường dẫn thư mục chứa scripts đã hoàn thành của channel"""
    return os.path.join(get_channel_dir(channel_name), 'completed')

def get_channel_overlay1_dir(channel_name):
    """Lấy đường dẫn thư mục chứa overlay cố định của channel"""
    return os.path.join(OVERLAY1_DIR, channel_name)

def get_channel_overlay2_dir(channel_name):
    """Lấy đường dẫn thư mục chứa overlay ngẫu nhiên của channel"""
    return os.path.join(OVERLAY2_DIR, channel_name)

def get_channel_final_dir(channel_name):
    """Lấy đường dẫn thư mục chứa video hoàn chỉnh của channel"""
    return os.path.join(FINAL_DIR, channel_name)

def get_channel_voice_dir(channel_name):
    """Lấy đường dẫn thư mục chứa file giọng nói của channel"""
    return os.path.join(VOICE_DIR, channel_name)

def get_channel_config_path(channel_name):
    """Lấy đường dẫn file cấu hình của channel"""
    return os.path.join(CONFIG_DIR, 'channels', f'{channel_name}.json')

# Pandrator paths
def get_pandrator_session_dir(session_name):
    """Lấy đường dẫn thư mục phiên làm việc của Pandrator"""
    return os.path.join(PANDRATOR_DIR, 'sessions', session_name)

# API URLs
VOICE_API_URL = os.getenv('VOICE_API_URL', 'http://localhost:5003')
VIDEO_API_URL = os.getenv('VIDEO_API_URL', 'http://localhost:5001')
XTTS_API_URL = os.getenv('XTTS_API_URL', 'http://localhost:8020')
APP_API_URL = os.getenv('APP_API_URL', 'http://localhost:8000')

def ensure_base_directories():
    """Tạo tất cả các thư mục cơ bản nếu chưa tồn tại"""
    dirs = [
        SCRIPTS_DIR,
        ASSETS_DIR,
        AUDIO_DIR,
        SRT_DIR,
        VIDEOS_DIR,
        OVERLAY1_DIR,
        OVERLAY2_DIR,
        FINAL_DIR,
        VOICE_DIR,
        CONFIG_DIR,
        os.path.join(CONFIG_DIR, 'channels')
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

def ensure_channel_directories(channel_name):
    """Tạo tất cả các thư mục cần thiết cho một channel"""
    dirs = [
        get_channel_dir(channel_name),
        get_channel_error_dir(channel_name),
        get_channel_processed_dir(channel_name),
        get_channel_completed_dir(channel_name),
        get_channel_overlay1_dir(channel_name),
        get_channel_overlay2_dir(channel_name),
        get_channel_final_dir(channel_name),
        get_channel_voice_dir(channel_name)
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)

def create_sample_channel(channel_name):
    """Tạo một kênh mẫu với đầy đủ cấu trúc thư mục và file cấu hình"""
    # Tạo các thư mục cần thiết cho channel
    ensure_channel_directories(channel_name)
    
    # Tạo file cấu hình cho channel
    channel_config = os.path.join(CONFIG_DIR, 'channels', f'{channel_name}.json')
    if not os.path.exists(channel_config):
        shutil.copy(
            os.path.join(TEMPLATES_DIR, 'channel_config.json'),
            channel_config
        )
    
    # Tạo file overlay mẫu
    overlay1_dir = get_channel_overlay1_dir(channel_name)
    if not os.path.exists(os.path.join(overlay1_dir, 'overlay1.png')):
        shutil.copy(
            os.path.join(TEMPLATES_DIR, 'overlay1.png'),
            os.path.join(overlay1_dir, 'overlay1.png')
        )

def create_sample_channels():
    """Tạo các kênh mẫu"""
    sample_channels = ['Channel_1', 'Channel_2']
    for channel in sample_channels:
        create_sample_channel(channel)

def create_sample_configs():
    """Tạo các file cấu hình mẫu trong thư mục config"""
    # Tạo thư mục channels nếu chưa tồn tại
    channels_dir = os.path.join(CONFIG_DIR, 'channels')
    os.makedirs(channels_dir, exist_ok=True)
    
    # Copy voice config mẫu
    voice_config = os.path.join(CONFIG_DIR, 'voice_config.json')
    if not os.path.exists(voice_config):
        shutil.copy(
            os.path.join(TEMPLATES_DIR, 'voice_config.json'),
            voice_config
        )

def initialize_workspace():
    """Khởi tạo không gian làm việc với các thư mục và file mẫu"""
    # Tạo các thư mục cơ bản
    ensure_base_directories()
    
    # Tạo các file cấu hình mẫu
    create_sample_configs()
    
    # Tạo các kênh mẫu
    create_sample_channels()
    
    print("""
Workspace đã được khởi tạo thành công!

Hướng dẫn sử dụng Workflow:
1. Cấu trúc thư mục:
   - WF_ROOT (mặc định: E:/RedditWorkflow)
     ├── WF/                  # Thư mục chính
     │   ├── scripts/        # Chứa scripts theo channel
     │   ├── assets/         # Chứa tài nguyên (audio, video, overlays)
     │   └── config/         # Chứa cấu hình

2. Các kênh mẫu đã được tạo:
   - Channel_1
   - Channel_2
   Mỗi kênh có:
   - File cấu hình riêng trong WF/config/channels/
   - Overlay mẫu trong WF/assets/overlay1/
   - Các thư mục cần thiết (error, processed, completed)

3. Cách thêm kênh mới:
   - Tạo thư mục kênh trong WF/scripts/
   - Copy file cấu hình mẫu từ channel mẫu
   - Thêm overlay1.png vào thư mục overlay1 của kênh

4. Quy trình làm việc:
   a. Đặt script vào thư mục WF/scripts/{tên_kênh}/
   b. Script sẽ được tự động xử lý:
      - Tạo audio và SRT → WF/assets/audio và srt/
      - Tạo video → WF/assets/videos/
      - Kết hợp với overlay → WF/assets/final/{tên_kênh}/
   c. Script được xử lý sẽ chuyển vào thư mục processed/
   d. Nếu có lỗi, script sẽ chuyển vào thư mục error/

5. Cấu hình:
   - Thay đổi đường dẫn gốc: Đặt biến môi trường WF_ROOT
   - Thay đổi API URLs: Đặt các biến môi trường tương ứng
   - Chỉnh sửa cấu hình kênh trong WF/config/channels/

6. Các file quan trọng:
   - voice_config.json: Cấu hình mặc định cho giọng nói
   - {tên_kênh}.json: Cấu hình riêng cho từng kênh
   - overlay1.png: Overlay cố định của kênh

Lưu ý:
- Đảm bảo các dịch vụ (voice, video) đang chạy
- Kiểm tra file cấu hình trước khi chạy
- Backup dữ liệu quan trọng thường xuyên
""")

# Tạo workspace khi module được import lần đầu
if not os.path.exists(WF_DIR):
    initialize_workspace()
