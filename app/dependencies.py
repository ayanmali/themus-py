from typing import Annotated

from app.data.database import get_db_session
from app.services.gcs_service import gcs_service
from app.services.video_processor import video_processor
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Async Database Session Dependency
DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Google Cloud Storage Service Dependency
GCSServiceDep = Annotated[type(gcs_service), Depends(lambda: gcs_service)]

VideoProcessorDep = Annotated[type(video_processor), Depends(lambda: video_processor)]