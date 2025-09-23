from app.data.database import Base
from sqlalchemy import Column, DateTime, Integer, String, func, Text

from datetime import datetime
from pydantic import BaseModel

# Table definition
class Assessment(Base):
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    assessment_type = Column(String(100), nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    duration = Column(Integer)
    user_id = Column(Integer, nullable=False) # The user that made the assessment, not a candidate
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class AssessmentBaseDto(BaseModel):
    id: int
    title: str

class AssessmentCreateDto(AssessmentBaseDto):
    pass

class AssessmentResponseDto(AssessmentBaseDto):
    createdAt: datetime

    class Config:
        from_attributes = True

class AssessmentListResponseDto(BaseModel):
    assessments: list[AssessmentResponseDto]
    total: int
    skip: int
    limit: int