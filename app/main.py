import os
import shutil
from fastapi import FastAPI, Request, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import time
from datetime import datetime
from .database import get_db, engine
from .models.script import Base, Script, ScriptStatus
from .services.voice_service import VoiceService
from .services.video_service import VideoService
from .services.watcher_service import WatcherService
from .utils.logging_config import setup_logging, LoggerAdapter
from .tasks import process_script_file
from .config.paths import (
    SCRIPTS_DIR,
    get_channel_error_dir,
    get_channel_completed_dir,
    get_channel_processed_dir,
    VOICE_API_URL,
    VIDEO_API_URL
)

# Setup logging
logger = LoggerAdapter(setup_logging(os.getenv("LOG_LEVEL", "DEBUG")), {})

# Create database tables
Base.metadata.create_all(bind=engine)

# Khởi tạo các service
voice_service = VoiceService(voice_api_url=VOICE_API_URL)
video_service = VideoService(video_api_url=VIDEO_API_URL)
watcher_service = WatcherService()

app = FastAPI(
    title="Video Generation Workflow",
    description="API for processing scripts into videos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request and response details"""
    start_time = time.time()
    logger.info(
        "Request started",
        extra={
            "request_info": {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host if request.client else None,
            }
        }
    )
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        extra={
            "response_info": {
                "status_code": response.status_code,
                "process_time": process_time,
            }
        }
    )
    return response

async def process_pending_script(script: Script, db: Session):
    """
    Xử lý một script đang pending
    """
    try:
        logger.info(f"Bắt đầu xử lý script: {script.file_path}")
        
        # Cập nhật trạng thái
        script.status = ScriptStatus.processing
        script.started_at = datetime.now()
        db.commit()

        # Bước 1: Xử lý Voice
        try:
            voice_result = await voice_service.process_voice(
                file_path=script.file_path,
                channel_name=script.channel_name
            )
            script.audio_path = voice_result['audio_path']
            script.srt_path = voice_result['srt_path']
            db.commit()
            
        except Exception as voice_error:
            logger.error(f"Lỗi xử lý voice: {voice_error}")
            await handle_error(script, "voice_processing", str(voice_error), db)
            return

        # Bước 2: Xử lý Video
        try:
            video_result = await video_service.process_video(
                audio_path=script.audio_path,
                srt_path=script.srt_path,
                channel_name=script.channel_name
            )
            script.video_path = video_result['video_path']
            
        except Exception as video_error:
            logger.error(f"Lỗi xử lý video: {video_error}")
            await handle_error(script, "video_processing", str(video_error), db)
            return

        # Xử lý thành công
        await handle_success(script, db)

    except Exception as e:
        logger.error(f"Lỗi không mong đợi: {e}")
        await handle_error(script, "unexpected", str(e), db)

async def handle_error(script: Script, error_stage: str, error_message: str, db: Session):
    """
    Xử lý khi có lỗi
    """
    try:
        # Cập nhật database
        script.status = ScriptStatus.failed
        script.error_stage = error_stage
        script.error_message = error_message
        script.completed_at = datetime.now()
        db.commit()

        # Tạo thư mục error
        error_dir = get_channel_error_dir(script.channel_name)
        os.makedirs(error_dir, exist_ok=True)

        # Di chuyển file gốc vào thư mục error
        error_file = os.path.join(error_dir, f"{os.path.basename(script.file_path)}")
        shutil.move(script.file_path, error_file)

        # Ghi log lỗi
        error_log = os.path.join(error_dir, f"{os.path.basename(script.file_path)}.error.log")
        with open(error_log, 'w', encoding='utf-8') as f:
            f.write(f"Error Stage: {error_stage}\n")
            f.write(f"Error Message: {error_message}\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            if script.audio_path:
                f.write(f"Audio Path: {script.audio_path}\n")
            if script.srt_path:
                f.write(f"SRT Path: {script.srt_path}\n")

        logger.info(f"Đã xử lý lỗi cho script {script.file_path}")

    except Exception as e:
        logger.error(f"Lỗi khi xử lý error handling: {e}")

async def handle_success(script: Script, db: Session):
    """
    Xử lý khi thành công
    """
    try:
        # Cập nhật database
        script.status = ScriptStatus.completed
        script.completed_at = datetime.now()
        db.commit()

        # Di chuyển file kịch bản vào thư mục processed
        processed_dir = get_channel_processed_dir(script.channel_name)
        script_file_path = script.file_path  # Cập nhật đường dẫn file kịch bản từ script
        try:
            shutil.move(script_file_path, processed_dir)
            logger.info(f"File kịch bản đã được di chuyển vào thư mục processed: {script_file_path}")
        except Exception as e:
            logger.error(f"Không thể di chuyển file kịch bản vào thư mục processed: {str(e)}")

    except Exception as e:
        logger.error(f"Lỗi khi xử lý success handling: {e}")
        await handle_error(script, "success_handling", str(e), db)

@app.get("/process_pending")
async def process_pending_scripts(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Endpoint để xử lý các script đang pending
    """
    try:
        # Lấy một script pending
        pending_script = db.query(Script).filter(
            Script.status == ScriptStatus.pending
        ).first()

        if pending_script:
            # Thêm vào background task
            background_tasks.add_task(process_pending_script, pending_script, db)
            return {
                "status": "processing",
                "script_id": pending_script.id,
                "file_path": pending_script.file_path
            }
        else:
            return {"status": "no_pending_scripts"}

    except Exception as e:
        logger.error(f"Lỗi khi xử lý pending scripts: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/scripts/{script_id}")
async def get_script_status(script_id: int, db: Session = Depends(get_db)):
    """
    Lấy thông tin của một script
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        return {"status": "not_found"}
    
    return {
        "id": script.id,
        "status": script.status,
        "file_path": script.file_path,
        "channel_name": script.channel_name,
        "audio_path": script.audio_path,
        "srt_path": script.srt_path,
        "video_path": script.video_path,
        "error_stage": script.error_stage,
        "error_message": script.error_message,
        "created_at": script.created_at,
        "started_at": script.started_at,
        "completed_at": script.completed_at
    }

async def process_file(file_path: str, channel_name: str):
    """
    Xử lý file script
    """
    try:
        logger.info(f"Bắt đầu xử lý file: {file_path}")
        
        # Bước 1: Xử lý Voice
        voice_result = await voice_service.process_voice(
            file_path=file_path,
            channel_name=channel_name
        )
        audio_path = voice_result['audio_path']
        srt_path = voice_result['srt_path']
        
        # Bước 2: Xử lý Video
        video_result = await video_service.process_video(
            audio_path=audio_path,
            srt_path=srt_path,
            channel_name=channel_name
        )
        video_path = video_result['video_path']
        
        # Di chuyển file vào thư mục processed
        processed_dir = get_channel_processed_dir(channel_name)
        os.makedirs(processed_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(processed_dir, os.path.basename(file_path)))
        logger.info(f"Đã xử lý thành công file: {file_path}")

    except Exception as e:
        logger.error(f"Lỗi xử lý file {file_path}: {str(e)}")
        # Di chuyển file vào thư mục error
        error_dir = get_channel_error_dir(channel_name)
        os.makedirs(error_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(error_dir, os.path.basename(file_path)))
        logger.error(f"File lỗi đã được di chuyển tới: {os.path.join(error_dir, os.path.basename(file_path))}")

@app.on_event("startup")
async def startup_event():
    """Khởi động các watcher khi app bắt đầu"""
    # Khởi động watcher cho thư mục scripts
    scripts_dir = SCRIPTS_DIR
    os.makedirs(scripts_dir, exist_ok=True)
    
    # Lấy danh sách các channel hiện có
    channels = [d for d in os.listdir(scripts_dir) 
               if os.path.isdir(os.path.join(scripts_dir, d))]
    
    # Nếu chưa có channel nào, tạo channel mặc định C1
    if not channels:
        channel_name = "C1"
        setup_channel_directories(channel_name)
        channels = [channel_name]
    
    # Khởi động watcher và xử lý các file có sẵn cho mỗi channel
    for channel in channels:
        channel_dir = os.path.join(scripts_dir, channel)
        
        # Xử lý các file .txt có sẵn trong thư mục
        for file_name in os.listdir(channel_dir):
            if file_name.endswith('.txt') and not file_name.startswith('error_'):
                file_path = os.path.join(channel_dir, file_name)
                if os.path.isfile(file_path):
                    logger.info(f"Xử lý file có sẵn: {file_path}")
                    try:
                        await process_script_file(file_path)
                    except Exception as e:
                        logger.error(f"Lỗi khi xử lý file có sẵn {file_path}: {str(e)}")
                
        # Khởi động watcher cho channel
        watcher_service.start_watching(
            directory=channel_dir,
            process_callback=process_script_file,
            channel_name=channel
        )
        
    logger.info(f"Đã khởi động watcher cho các channel: {channels}")

@app.on_event("shutdown")
async def shutdown_event():
    """Dừng tất cả các watcher khi app dừng"""
    watcher_service.stop_all()
    logger.info("Đã dừng tất cả các watcher")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
