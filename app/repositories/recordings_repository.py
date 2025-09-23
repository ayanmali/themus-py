from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select #, delete
from app.data.schemas.recordings import Recording, InsertRecordingDto, RecordingResponseDto
from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional

def _recording_to_dto(recording: Recording) -> RecordingResponseDto:
    """Convert SQLModel Recording to RecordingResponseDto"""
    return RecordingResponseDto(
        id=recording.id,
        title=recording.title,
        filename=recording.filename,
        fileSize=recording.fileSize,
        duration=recording.duration,
        format=recording.format,
        hasAudio=recording.hasAudio,
        thumbnailUrl=recording.thumbnailUrl,
        createdAt=recording.createdAt
    )

async def create_recording(db_session: AsyncSession, recording: InsertRecordingDto) -> RecordingResponseDto:
    """Create a new recording in the database"""
    db_recording = Recording(
        title=recording.title,
        filename=recording.filename,
        fileSize=recording.fileSize,
        duration=recording.duration,
        format=recording.format,
        hasAudio=recording.hasAudio,
        thumbnailUrl=recording.thumbnailUrl,
        createdAt=datetime.now()
    )
    db_session.add(db_recording)
    await db_session.commit()
    await db_session.refresh(db_recording)
    return _recording_to_dto(db_recording)

async def get_recording(db_session: AsyncSession, recording_id: int) -> RecordingResponseDto:
    """Get a specific recording by ID"""
    recording = (await db_session.scalars(select(Recording).where(Recording.id == recording_id))).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return _recording_to_dto(recording)

async def get_recording_by_filename(db_session: AsyncSession, filename: str) -> Optional[RecordingResponseDto]:
    """Get a recording by filename"""
    recording = (await db_session.scalars(select(Recording).where(Recording.filename == filename))).first()
    return _recording_to_dto(recording) if recording else None

async def get_all_recordings(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[RecordingResponseDto]:
    """Get all recordings with pagination"""
    recordings = (await db_session.scalars(select(Recording).offset(skip).limit(limit))).all()
    return [_recording_to_dto(recording) for recording in recordings]

async def update_recording(db_session: AsyncSession, recording_id: int, recording_data: dict) -> RecordingResponseDto:
    """Update a recording by ID"""
    # recording = await get_recording(db_session, recording_id)
    
    # Get the actual database object for updating
    db_recording = (await db_session.scalars(select(Recording).where(Recording.id == recording_id))).first()
    
    for field, value in recording_data.items():
        if hasattr(db_recording, field):
            setattr(db_recording, field, value)
    
    await db_session.commit()
    await db_session.refresh(db_recording)
    return _recording_to_dto(db_recording)

async def delete_recording(db_session: AsyncSession, recording_id: int) -> bool:
    """Delete a recording by ID"""
    recording = (await db_session.scalars(select(Recording).where(Recording.id == recording_id))).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    await db_session.delete(recording)
    await db_session.commit()
    return True

async def get_recordings_by_format(db_session: AsyncSession, format: str, skip: int = 0, limit: int = 100) -> List[RecordingResponseDto]:
    """Get recordings filtered by format"""
    recordings = (await db_session.scalars(
        select(Recording).where(Recording.format == format).offset(skip).limit(limit)
    )).all()
    return [_recording_to_dto(recording) for recording in recordings]

async def get_recordings_with_audio(db_session: AsyncSession, has_audio: bool = True, skip: int = 0, limit: int = 100) -> List[RecordingResponseDto]:
    """Get recordings filtered by audio presence"""
    recordings = (await db_session.scalars(
        select(Recording).where(Recording.hasAudio == has_audio).offset(skip).limit(limit)
    )).all()
    return [_recording_to_dto(recording) for recording in recordings]

async def search_recordings_by_title(db_session: AsyncSession, title_query: str, skip: int = 0, limit: int = 100) -> List[RecordingResponseDto]:
    """Search recordings by title (case-insensitive partial match)"""
    recordings = (await db_session.scalars(
        select(Recording).where(Recording.title.ilike(f"%{title_query}%")).offset(skip).limit(limit)
    )).all()
    return [_recording_to_dto(recording) for recording in recordings]

async def get_recordings_by_date_range(db_session: AsyncSession, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100) -> List[RecordingResponseDto]:
    """Get recordings within a date range"""
    recordings = (await db_session.scalars(
        select(Recording).where(
            Recording.createdAt >= start_date,
            Recording.createdAt <= end_date
        ).offset(skip).limit(limit)
    )).all()
    return [_recording_to_dto(recording) for recording in recordings]

async def get_recordings_count(db_session: AsyncSession) -> int:
    """Get total count of recordings"""
    result = await db_session.scalar(select(Recording.id))
    return result if result else 0