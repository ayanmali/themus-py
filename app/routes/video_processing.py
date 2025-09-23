from fastapi import APIRouter

from app.dependencies import DBSessionDep, VideoProcessorDep
from app.services.video_processor import VideoOperation
from app.routes.recordings import get_recording
from fastapi import HTTPException
from typing import List

video_processing_router = APIRouter(
    prefix="/api/video-processing",
    tags=["video-processing"]
)

# Process video with OpenCV
@video_processing_router.post("/{recording_id}/process")
async def process_video(
    session: DBSessionDep,
    video_processor: VideoProcessorDep,
    recording_id: int,
    operations: List[VideoOperation]
):
    """
    Process a video recording with OpenCV operations
    
    Available operations:
    - extract_frames: Extract key frames from video
    - detect_motion: Detect motion in video
    - generate_thumbnail: Generate and upload thumbnail
    - analyze_content: Analyze video content (brightness, contrast)
    - extract_audio_info: Extract audio information
    """
    try:
        # Get recording from database
        recording = await get_recording(session, recording_id)
        
        if not recording.filename:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        # Process video with OpenCV
        results = await video_processor.process_video(recording.filename, operations)
        
        return {
            "recording_id": recording_id,
            "filename": recording.filename,
            "operations": operations,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video: {e}")

# Create video summary
@video_processing_router.post("/{recording_id}/summary")
async def create_video_summary(
    session: DBSessionDep,
    video_processor: VideoProcessorDep,
    recording_id: int
):
    """
    Create a comprehensive video summary with all available analysis
    """
    try:
        # Get recording from database
        recording = await get_recording(session, recording_id)
        
        if not recording.filename:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        # Create comprehensive summary
        summary = await video_processor.create_video_summary(recording.filename)
        
        return {
            "recording_id": recording_id,
            "filename": recording.filename,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create video summary: {e}")

# Extract frames from video
@video_processing_router.get("/{recording_id}/frames")
async def extract_video_frames(
    session: DBSessionDep,
    video_processor: VideoProcessorDep,
    recording_id: int,
    frame_count: int = 10
):
    """
    Extract key frames from a video recording
    """
    try:
        # Get recording from database
        recording = await get_recording(session, recording_id)
        
        if not recording.filename:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        # Process video to extract frames
        results = await video_processor.process_video(recording.filename, ['extract_frames'])
        
        return {    
            "recording_id": recording_id,
            "filename": recording.filename,
            "frames": results.get('frames', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract frames: {e}")

# Detect motion in video
@video_processing_router.get("/{recording_id}/motion")
async def detect_video_motion(
    session: DBSessionDep,
    video_processor: VideoProcessorDep,
    recording_id: int
):
    """
    Detect motion in a video recording
    """
    try:
        # Get recording from database
        recording = await get_recording(session, recording_id)
        
        if not recording.filename:
            raise HTTPException(status_code=404, detail="Recording file not found")
        
        # Process video to detect motion
        results = await video_processor.process_video(recording.filename, ['detect_motion'])
        
        return {
            "recording_id": recording_id,
            "filename": recording.filename,
            "motion_detection": results.get('motion_detection', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect motion: {e}")