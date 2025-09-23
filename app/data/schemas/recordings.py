from app.data.database import Base
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from typing import Literal
from datetime import datetime
from pydantic import BaseModel

class Recording(Base):
    __tablename__ = "recordings"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    filename = Column(String, index=True)
    fileSize = Column(Integer, index=True)
    duration = Column(Integer, index=True)
    format = Column(String, index=True)
    createdAt = Column(DateTime, default=func.now())
    hasAudio = Column(Boolean, index=True)
    thumbnailUrl = Column(String, index=True)

class RecordingBaseDto(BaseModel):
    title: str
    filename: str
    fileSize: int
    duration: int
    format: str
    hasAudio: bool
    thumbnailUrl: str | None

class InsertRecordingDto(RecordingBaseDto):
    pass

class ClientMetadataDto(RecordingBaseDto):
    # TODO: add candidateAttemptId
    # candidateAttemptId: id
    pass

class RecordingOptionsDto(BaseModel):
    screenSource: Literal["entire", "window", "tab"]
    includeMicrophone: bool
    includeSystemAudio: bool
    microphoneVolume: int
    format: Literal["mp4", "webm"]

class RecordingResponseDto(RecordingBaseDto):
    id: int
    createdAt: datetime

    class Config:
        from_attributes = True

class RecordingListResponseDto(BaseModel):
    recordings: list[RecordingResponseDto]
    total: int
    skip: int
    limit: int