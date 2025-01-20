from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from ..database import get_db
from ..models.script import Script, ScriptStatus
from ..tasks import process_script_task
from pydantic import BaseModel

router = APIRouter()

class ScriptRequest(BaseModel):
    file_path: str
    channel_name: str
    callback_url: str = None
    callback_id: str = None

    class Config:scripts/
        from_attributes = True

@router.post("/process_script")
async def process_script(
    script_data: ScriptRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Endpoint để xử lý script file
    """
    try:
        # Tạo task ID
        task_id = f"task_{script_data.callback_id}" if script_data.callback_id else None

        # Tạo script record trong database
        script = Script(
            file_path=script_data.file_path,
            channel_name=script_data.channel_name,
            status=ScriptStatus.pending
        )
        db.add(script)
        db.commit()
        db.refresh(script)

        # Thêm task vào background
        background_tasks.add_task(
            process_script_task,
            task_id=task_id,
            file_path=script_data.file_path,
            channel_name=script_data.channel_name,
            callback_url=script_data.callback_url,
            callback_id=script_data.callback_id,
            db=db
        )

        return {
            "task_id": task_id,
            "script_id": script.id,
            "status": "processing"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task_status/{script_id}")
async def get_script_status(script_id: int, db: Session = Depends(get_db)):
    """
    Lấy trạng thái của script
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    return {
        "script_id": script.id,
        "status": script.status,
        "error": script.error if script.error else None,
        "created_at": script.created_at,
        "updated_at": script.updated_at
    }

@router.post("/task_callback/{callback_id}")
async def task_callback(callback_id: str, payload: Dict, db: Session = Depends(get_db)):
    """
    Callback endpoint để nhận kết quả xử lý
    """
    try:
        # Tìm script record dựa trên callback_id
        script = db.query(Script).filter(Script.callback_id == callback_id).first()
        if script:
            # Cập nhật trạng thái
            script.status = ScriptStatus.completed if payload.get('status') == 'completed' else ScriptStatus.failed
            if payload.get('error'):
                script.error = payload.get('error')
            
            # Lưu các đường dẫn file
            if payload.get('audio_path'):
                script.audio_path = payload.get('audio_path')
            if payload.get('srt_path'):
                script.srt_path = payload.get('srt_path')
            if payload.get('video_path'):
                script.video_path = payload.get('video_path')
            
            db.commit()
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
