#!/usr/bin/env python3
"""
Example script demonstrating how to process videos from Google Cloud Storage using OpenCV
"""

import asyncio
import sys
import os

# Add the service directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.video_processor import video_processor
from app.services.gcs_service import gcs_service

async def example_video_processing():
    """
    Example of how to process a video from GCS
    """
    
    # Example GCS filename (replace with actual filename)
    gcs_filename = "recordings/recording_1754328825380.mp4"
    
    print(f"Processing video: {gcs_filename}")
    
    try:
        # Method 1: Create a comprehensive video summary
        print("\n1. Creating video summary...")
        summary = await video_processor.create_video_summary(gcs_filename)
        
        print(f"Video Info: {summary['video_info']}")
        print(f"Motion Detection: {summary['motion_detection']['total_motion_frames']} motion frames detected")
        print(f"Content Analysis: Average brightness = {summary['content_analysis']['average_brightness']:.2f}")
        
        # Method 2: Process specific operations
        print("\n2. Processing specific operations...")
        operations = ['extract_frames', 'detect_motion']
        results = await video_processor.process_video(gcs_filename, operations)
        
        print(f"Extracted {results['frames']['total_frames_extracted']} frames")
        print(f"Detected motion in {results['motion_detection']['total_motion_frames']} frames")
        
        # Method 3: Download video for custom processing
        print("\n3. Downloading video for custom processing...")
        
        # Option A: Download as bytes (for small videos)
        video_bytes = await gcs_service.get_video_for_processing(gcs_filename, use_temp_file=False)
        print(f"Downloaded video as bytes: {len(video_bytes)} bytes")
        
        # Option B: Download to temp file (for large videos)
        temp_file_path = await gcs_service.get_video_for_processing(gcs_filename, use_temp_file=True)
        print(f"Downloaded video to temp file: {temp_file_path}")
        
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print("Cleaned up temp file")
        
        print("\nVideo processing completed successfully!")
        
    except Exception as e:
        print(f"Error processing video: {e}")

async def example_custom_opencv_processing():
    """
    Example of custom OpenCV processing with downloaded video
    """
    import cv2
    import numpy as np
    
    gcs_filename = "recordings/recording_1754328825380.mp4"
    
    print(f"\nCustom OpenCV processing for: {gcs_filename}")
    
    try:
        # Download video to temp file
        temp_video_path = await gcs_service.get_video_for_processing(gcs_filename, use_temp_file=True)
        
        # Open video with OpenCV
        cap = cv2.VideoCapture(temp_video_path)
        
        if not cap.isOpened():
            print("Error: Could not open video file")
            return
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"Video properties: {width}x{height}, {fps} FPS, {frame_count} frames")
        
        # Example: Process first 10 frames
        frame_idx = 0
        while frame_idx < 10:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Example processing: Convert to grayscale and detect edges
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Count edge pixels
            edge_pixels = cv2.countNonZero(edges)
            edge_percentage = (edge_pixels / (height * width)) * 100
            
            print(f"Frame {frame_idx}: {edge_percentage:.2f}% edge pixels")
            
            frame_idx += 1
        
        cap.release()
        
        # Clean up
        if os.path.exists(temp_video_path):
            os.unlink(temp_video_path)
        
        print("Custom OpenCV processing completed!")
        
    except Exception as e:
        print(f"Error in custom processing: {e}")

if __name__ == "__main__":
    # Run the examples
    asyncio.run(example_video_processing())
    asyncio.run(example_custom_opencv_processing()) 