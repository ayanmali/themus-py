import mimetypes
import os
import logging
import tempfile
from typing import Optional, Union
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class GoogleCloudStorageService:
    """
    Service for handling Google Cloud Storage operations
    """
    
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable is required")
        
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID environment variable is required")
        
        # Initialize the GCS client
        try:
            self.client = storage.Client(project=self.project_id)
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not self.bucket.exists():
                raise ValueError(f"Bucket {self.bucket_name} does not exist")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to initialize cloud storage service"
            )

    async def download_file(self, filename: str) -> bytes:
        """
        Download a file from Google Cloud Storage as bytes
        
        Args:
            filename: The name of the file in GCS
            
        Returns:
            bytes: The file content
            
        Raises:
            HTTPException: If download fails
        """
        try:
            blob = self.bucket.blob(filename)
            
            if not blob.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"File {filename} not found in cloud storage"
                )
            
            # Download the file content
            content = blob.download_as_bytes()
            logger.info(f"Successfully downloaded {filename} from GCS")
            return content
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Storage error downloading {filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download file from cloud storage: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during file download"
            )

    async def download_to_temp_file(self, filename: str) -> str:
        """
        Download a file from Google Cloud Storage to a temporary file
        
        Args:
            filename: The name of the file in GCS
            
        Returns:
            str: Path to the temporary file
            
        Raises:
            HTTPException: If download fails
        """
        try:
            # Download file content
            content = await self.download_file(filename)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=True,
                suffix=os.path.splitext(filename)[1]  # Preserve original extension
            )
            
            # Write content to temp file
            temp_file.write(content)
            temp_file.close()
            
            logger.info(f"Successfully downloaded {filename} to temp file: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error downloading {filename} to temp file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download file to temporary location: {str(e)}"
            )

    async def get_video_for_processing(self, filename: str, use_temp_file: bool = True) -> Union[bytes, str]:
        """
        Get a video file for processing with OpenCV
        
        Args:
            filename: The name of the video file in GCS
            use_temp_file: If True, returns path to temp file. If False, returns bytes
            
        Returns:
            Union[bytes, str]: Video content as bytes or path to temp file
            
        Raises:
            HTTPException: If retrieval fails
        """
        try:
            if use_temp_file:
                # Download to temp file (better for large videos)
                return await self.download_to_temp_file(filename)
            else:
                # Download as bytes (better for small videos)
                return await self.download_file(filename)
                
        except Exception as e:
            logger.error(f"Error getting video {filename} for processing: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve video for processing: {str(e)}"
            )

    async def upload_file(self, file_content: bytes, filename: str, content_type: Optional[str] = None) -> str:
        """
        Upload a file to Google Cloud Storage bucket
        
        Args:
            file_content: The file content as bytes
            filename: The name of the file to store in GCS
            content_type: Optional content type. If not provided, will be auto-detected
            
        Returns:
            str: The public URL of the uploaded file
            
        Raises:
            HTTPException: If upload fails
        """
        try:
            # Auto-detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    # Default to application/octet-stream for unknown types
                    content_type = "application/octet-stream"
            
            # Create a blob object
            blob = self.bucket.blob(filename)
            
            # Set content type
            blob.content_type = content_type
            
            # Upload the file content
            blob.upload_from_string(
                file_content,
                content_type=content_type,
                timeout=300  # 5 minutes timeout for large video files
            )
            
            # Make the blob publicly readable (optional - remove if you want private files)
            # blob.make_public()
            
            logger.info(f"Successfully uploaded {filename} to bucket {self.bucket_name}")
            
            # Return the public URL or signed URL
            return f"gs://{self.bucket_name}/{filename}"
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Storage error uploading {filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to cloud storage: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading {filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during file upload"
            )

    async def upload_video_file(self, file_content: bytes, filename: str) -> str:
        """
        Specialized method for uploading video files with appropriate settings
        
        Args:
            file_content: The video file content as bytes
            filename: The name of the video file
            
        Returns:
            str: The GCS URL of the uploaded video
        """
        # Common video MIME types
        video_extensions = {
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.webm': 'video/webm',
            '.mkv': 'video/x-matroska',
            '.m4v': 'video/x-m4v'
        }
        
        # Get file extension
        file_ext = os.path.splitext(filename.lower())[1]
        content_type = video_extensions.get(file_ext, 'video/mp4')
        
        return await self.upload_file(file_content, filename, content_type)
    
    async def get_file_url(self, filename: str) -> Optional[str]:
        """
        Get the public URL of a file in Google Cloud Storage
        
        Args:
            filename: The name of the file
            
        Returns:
            The public URL if the file exists, None otherwise
        """
        try:
            blob = self.bucket.blob(filename)
            
            if blob.exists():
                # When uniform bucket-level access is enabled, construct URL manually
                return f"https://storage.googleapis.com/{self.bucket_name}/{filename}"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting URL for {filename}: {e}")
            return None
    
    def get_signed_url(self, filename: str, expiration_minutes: int = 60) -> str:
        """
        Generate a signed URL for accessing a private file
        
        Args:
            filename: Name of the file in the bucket
            expiration_minutes: URL expiration time in minutes
            
        Returns:
            str: Signed URL for the file
        """
        try:
            blob = self.bucket.blob(filename)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                expiration=expiration_minutes * 60,  # Convert to seconds
                method='GET'
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating signed URL for {filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate access URL"
            )

    async def delete_file(self, filename: str) -> bool:
        """
        Delete a file from Google Cloud Storage
        
        Args:
            filename: The name of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            blob = self.bucket.blob(filename)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Successfully deleted {filename} from GCS")
                return True
            else:
                logger.warning(f"File {filename} does not exist in GCS")
                return False
                
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Storage error deleting {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting {filename}: {e}")
            return False

# Global instance
gcs_service = GoogleCloudStorageService() 