from sqlalchemy import Column, Integer, String, Enum as SQLEnum, DateTime
from sqlalchemy.orm import declarative_base
import enum
from datetime import datetime

Base = declarative_base()

class ScriptStatus(str, enum.Enum):
    PENDING = "PENDING"
    VOICE_DONE = "VOICE_DONE"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    ERROR_VOICE = "ERROR_VOICE"
    ERROR_VIDEO = "ERROR_VIDEO"

class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    channel_name = Column(String, nullable=False)
    status = Column(SQLEnum(ScriptStatus), default=ScriptStatus.PENDING)
    error_message = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    video_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    voice_task_id = Column(String, nullable=True)
    video_task_id = Column(String, nullable=True)
