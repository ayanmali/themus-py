from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.data.schemas.recordings import InsertRecordingDto, ClientMetadataDto, RecordingResponseDto
from app.repositories.recordings_repository import (
    create_recording,
    get_recording,
    get_all_recordings,
    update_recording,
    delete_recording,
    get_recordings_by_format,
    get_recordings_with_audio,
    search_recordings_by_title,
    #get_recordings_by_date_range,
    get_recordings_count
)
from typing import Optional, List
from app.dependencies import DBSessionDep, GCSServiceDep
import json
import os
from datetime import datetime

recordings_router = APIRouter(
    prefix="/api/recordings",
    tags=["recordings"],
    responses={404: {"description": "Not found"}},
)

# Get all recordings
@recordings_router.get("/", response_model=List[RecordingResponseDto])
async def get_recordings(
    session: DBSessionDep,
    skip: int = 0,
    limit: int = 100,
    format: Optional[str] = None,
    has_audio: Optional[bool] = None,
    search: Optional[str] = None
):
    """
    Get all recordings with optional filtering and pagination
    """
    try:
        if format:
            return await get_recordings_by_format(session, format, skip, limit)
        elif has_audio is not None:
            return await get_recordings_with_audio(session, has_audio, skip, limit)
        elif search:
            return await search_recordings_by_title(session, search, skip, limit)
        else:
            return await get_all_recordings(session, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recordings: {e}")

# Get specific recording
@recordings_router.get("/{recording_id}", response_model=RecordingResponseDto)
async def get_recording_by_id(session: DBSessionDep, recording_id: int):
    """
    Get a specific recording by ID
    """
    try:
        return await get_recording(session, recording_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recording: {e}")

# Create new recording
@recordings_router.post("/", response_model=RecordingResponseDto)
async def create_new_recording(
    session: DBSessionDep,
    gcs_service: GCSServiceDep,
    video: UploadFile = File(...),
    metadata: str = Form(...)
):
    """
    Create a new recording with video file upload to Google Cloud Storage
    """
    try:
        if not video:
            raise HTTPException(status_code=400, detail="No video file provided")
        # print("--------------------------------")
        # print("REQUEST RECEIVED")
        # print(f"metadata: {metadata}")
        # print("--------------------------------")

        # Parse metadata
        try:
            recording_data = json.loads(metadata)
            validated_data = ClientMetadataDto(**recording_data)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid metadata format: {e}")
        
        # Generate unique filename
        timestamp = int(datetime.now().timestamp() * 1000)
        file_extension = os.path.splitext(video.filename)[1] if video.filename else ".mp4"
        unique_filename = f"recordings/recording_{timestamp}{file_extension}"
        
        # Read video content
        content = await video.read()
        
        # Upload to Google Cloud Storage
        gcs_url = await gcs_service.upload_video_file(
            file_content=content,
            filename=unique_filename
        )
        # print("--------------------------------")
        # print(f"Video uploaded successfully: {gcs_url}")
        # print("--------------------------------")
        
        # # Get a signed URL for accessing the video
        # signed_url = gcs_service.get_signed_url(unique_filename, expiration_minutes=120)
        # print("--------------------------------")
        # print(f"Signed URL: {signed_url}")
        # print("--------------------------------")
        
        # Create recording record
        recording_dto = InsertRecordingDto(
            title=validated_data.title,
            filename=unique_filename,
            fileSize=len(content),
            duration=validated_data.duration,
            format=validated_data.format,
            hasAudio=validated_data.hasAudio,
            thumbnailUrl=validated_data.thumbnailUrl
        )
        
        return await create_recording(session, recording_dto)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save recording: {e}")

# Download recording file
@recordings_router.get("/{recording_id}/url")
async def get_file_url(
    session: DBSessionDep, 
    gcs_service: GCSServiceDep,
    recording_id: int
):
    """
    Get download URL for a recording file from Google Cloud Storage
    """
    try:
        recording = await get_recording(session, recording_id)
        
        if not recording.filename:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        # Get the public URL from GCS
        download_url = await gcs_service.get_file_url(recording.filename)
        
        if not download_url:
            raise HTTPException(status_code=404, detail="Recording file not found in cloud storage")
        
        return {
            "download_url": download_url,
            "filename": recording.title,
            "format": recording.format
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get download URL: {e}")

# Stream recording file
# @recordings_router.get("/{recording_id}/stream")
# async def stream_recording(
#     session: DBSessionDep, 
#     gcs_service: GCSServiceDep,
#     recording_id: int
# ):
#     """
#     Get streaming URL for a recording file from Google Cloud Storage
#     """
#     try:
#         recording = await get_recording(session, recording_id)
        
#         if not recording.filename:
#             raise HTTPException(status_code=404, detail="Recording file not found")
        
#         # Get the public URL from GCS for streaming
#         stream_url = await gcs_service.get_file_url(recording.filename)
        
#         if not stream_url:
#             raise HTTPException(status_code=404, detail="Recording file not found in cloud storage")
        
#         return {
#             "stream_url": stream_url,
#             "filename": recording.title,
#             "format": recording.format,
#             "content_type": f"video/{recording.format}"
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get stream URL: {e}")

# Get signed URL for secure access
@recordings_router.get("/{recording_id}/signed-url")
async def get_signed_url(
    session: DBSessionDep,
    gcs_service: GCSServiceDep,
    recording_id: int,
    expiration_minutes: int = 60
):
    """
    Get a signed URL for secure access to a recording file
    """
    try:
        recording = await get_recording(session, recording_id)
        
        if not recording.filename:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        # Generate signed URL
        signed_url = gcs_service.get_signed_url(
            filename=recording.filename,
            expiration_minutes=expiration_minutes
        )
        
        if not signed_url:
            raise HTTPException(status_code=404, detail="Recording file not found in cloud storage")
        
        return {
            "signed_url": signed_url,
            "expires_in_minutes": expiration_minutes,
            "filename": recording.title,
            "format": recording.format
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate signed URL: {e}")

# Update recording in the DB
@recordings_router.put("/{recording_id}", response_model=RecordingResponseDto)
async def update_recording_by_id(
    session: DBSessionDep,
    recording_id: int,
    recording_data: dict
):
    """
    Update a recording by ID
    """
    try:
        return await update_recording(session, recording_id, recording_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update recording: {e}")

# Delete recording
@recordings_router.delete("/{recording_id}")
async def delete_recording_by_id(
    session: DBSessionDep, 
    gcs_service: GCSServiceDep,
    recording_id: int
):
    """
    Delete a recording by ID from both database and Google Cloud Storage
    """
    try:
        recording = await get_recording(session, recording_id)
        
        # Delete file from Google Cloud Storage
        if recording.filename:
            await gcs_service.delete_file(recording.filename)
        
        # Delete from database
        await delete_recording(session, recording_id)
        return {"message": "Recording deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete recording: {e}")

# Get storage statistics
@recordings_router.get("/storage/stats")
async def get_storage_stats(session: DBSessionDep):
    """
    Get storage statistics
    """
    try:
        total_recordings = await get_recordings_count(session)
        total_size = 0
        
        # Calculate total size (you might want to optimize this)
        recordings = await get_all_recordings(session, skip=0, limit=1000)
        for recording in recordings:
            total_size += recording.fileSize
        
        return {
            "totalRecordings": total_recordings,
            "totalSize": total_size,
            "formats": {
                "mp4": len([r for r in recordings if r.format == "mp4"]),
                "webm": len([r for r in recordings if r.format == "webm"])
            },
            "withAudio": len([r for r in recordings if r.hasAudio]),
            "withoutAudio": len([r for r in recordings if not r.hasAudio])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch storage stats: {e}")