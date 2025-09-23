import cv2
import numpy as np
import os
import logging
import tempfile
from typing import List, Dict, Any, Literal, Optional, Tuple
from fastapi import HTTPException
from .gcs_service import gcs_service

logger = logging.getLogger(__name__)

VideoOperation = Literal["extract_frames", "detect_motion", "generate_thumbnail", "analyze_content", "extract_audio_info"]

class VideoProcessor:
    """
    Service for processing videos using OpenCV
    """
    
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.webm', '.mkv']
    
    async def process_video(self, gcs_filename: str, operations: List[VideoOperation]) -> Dict[str, Any]:
        """
        Process a video from GCS with specified operations
        
        Args:
            gcs_filename: The filename in GCS
            operations: List of operations to perform
            
        Returns:
            Dict containing processing results
        """
        try:
            # Download video to temp file
            temp_video_path = await gcs_service.get_video_for_processing(gcs_filename, use_temp_file=True)
            
            results = {}
            
            # Open video
            cap = cv2.VideoCapture(temp_video_path)
            if not cap.isOpened():
                raise HTTPException(status_code=400, detail="Could not open video file")
            
            try:
                # Get video properties
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                duration = frame_count / fps if fps > 0 else 0
                
                results['video_info'] = {
                    'fps': fps,
                    'frame_count': frame_count,
                    'width': width,
                    'height': height,
                    'duration': duration,
                    'resolution': f"{width}x{height}"
                }
                
                # Perform requested operations
                for operation in operations:
                    if operation == 'extract_frames':
                        results['frames'] = await self._extract_frames(cap, temp_video_path)
                    elif operation == 'detect_motion':
                        results['motion_detection'] = await self._detect_motion(cap)
                    elif operation == 'generate_thumbnail':
                        results['thumbnail'] = await self._generate_thumbnail(cap, gcs_filename)
                    elif operation == 'analyze_content':
                        results['content_analysis'] = await self._analyze_content(cap)
                    elif operation == 'extract_audio_info':
                        results['audio_info'] = await self._extract_audio_info(temp_video_path)
                
            finally:
                cap.release()
                
            # Clean up temp file
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing video {gcs_filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")
    
    async def _extract_frames(self, cap: cv2.VideoCapture, video_path: str) -> Dict[str, Any]:
        """
        Extract key frames from video
        """
        frames = []
        frame_interval = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / 10))  # Extract 10 frames
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % frame_interval == 0:
                # Convert frame to base64 for storage
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = buffer.tobytes()
                
                frames.append({
                    'frame_number': frame_idx,
                    'timestamp': frame_idx / cap.get(cv2.CAP_PROP_FPS),
                    'size': len(frame_data)
                })
            
            frame_idx += 1
        
        return {
            'total_frames_extracted': len(frames),
            'frame_interval': frame_interval,
            'frames': frames
        }
    
    async def _detect_motion(self, cap: cv2.VideoCapture) -> Dict[str, Any]:
        """
        Detect motion in video
        """
        motion_frames = []
        prev_frame = None
        motion_threshold = 30
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if prev_frame is not None:
                # Calculate frame difference
                frame_delta = cv2.absdiff(prev_frame, gray)
                thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
                
                # Count non-zero pixels (motion)
                motion_pixels = cv2.countNonZero(thresh)
                motion_percentage = (motion_pixels / (gray.shape[0] * gray.shape[1])) * 100
                
                if motion_percentage > motion_threshold:
                    motion_frames.append({
                        'frame_number': frame_idx,
                        'timestamp': frame_idx / cap.get(cv2.CAP_PROP_FPS),
                        'motion_percentage': motion_percentage
                    })
            
            prev_frame = gray
            frame_idx += 1
        
        return {
            'total_motion_frames': len(motion_frames),
            'motion_threshold': motion_threshold,
            'motion_frames': motion_frames
        }
    
    async def _generate_thumbnail(self, cap: cv2.VideoCapture, gcs_filename: str) -> str:
        """
        Generate and upload thumbnail
        """
        # Read middle frame
        middle_frame = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / 2)
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
        ret, frame = cap.read()
        
        if not ret:
            raise HTTPException(status_code=400, detail="Could not read frame for thumbnail")
        
        # Resize thumbnail
        thumbnail = cv2.resize(frame, (320, 240))
        
        # Save to temp file
        temp_thumb_path = tempfile.mktemp(suffix='.jpg')
        cv2.imwrite(temp_thumb_path, thumbnail)
        
        try:
            # Upload thumbnail to GCS
            with open(temp_thumb_path, 'rb') as f:
                thumbnail_content = f.read()
            
            # Generate thumbnail filename
            base_name = os.path.splitext(gcs_filename)[0]
            thumbnail_filename = f"{base_name}_thumbnail.jpg"
            
            # Upload to GCS
            await gcs_service.upload_file(
                thumbnail_content,
                thumbnail_filename,
                content_type='image/jpeg'
            )
            
            return thumbnail_filename
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_thumb_path):
                os.unlink(temp_thumb_path)
    
    async def _analyze_content(self, cap: cv2.VideoCapture) -> Dict[str, Any]:
        """
        Analyze video content (basic analysis)
        """
        brightness_values = []
        contrast_values = []
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate brightness (mean pixel value)
            brightness = np.mean(frame)
            brightness_values.append(brightness)
            
            # Calculate contrast (standard deviation)
            contrast = np.std(frame)
            contrast_values.append(contrast)
            
            frame_count += 1
            if frame_count > 100:  # Limit analysis to first 100 frames
                break
        
        return {
            'average_brightness': np.mean(brightness_values) if brightness_values else 0,
            'average_contrast': np.mean(contrast_values) if contrast_values else 0,
            'brightness_range': {
                'min': np.min(brightness_values) if brightness_values else 0,
                'max': np.max(brightness_values) if brightness_values else 0
            },
            'frames_analyzed': len(brightness_values)
        }
    
    async def _extract_audio_info(self, video_path: str) -> Dict[str, Any]:
        """
        Extract basic audio information (requires additional audio processing library)
        """
        # This is a placeholder - you'd need to use a library like ffmpeg-python
        # or moviepy to extract audio information
        return {
            'has_audio': True,  # Placeholder
            'audio_codec': 'unknown',
            'sample_rate': 0,
            'channels': 0
        }
    
    async def create_video_summary(self, gcs_filename: str) -> Dict[str, Any]:
        """
        Create a comprehensive video summary
        """
        operations = [
            'extract_frames',
            'detect_motion', 
            'generate_thumbnail',
            'analyze_content'
        ]
        
        return await self.process_video(gcs_filename, operations)

# Global instance
video_processor = VideoProcessor() 