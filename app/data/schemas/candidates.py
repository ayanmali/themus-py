from app.data.database import Base
from sqlalchemy import Column, DateTime, Integer, String, func, ForeignKey
from datetime import datetime
from pydantic import BaseModel

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class CandidateBaseDto(BaseModel):
    name: str
    email: str

# For POST requests
class CandidateCreateDto(CandidateBaseDto):
    pass

# For API responses
class CandidateResponseDto(CandidateBaseDto):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Candidate attempts
class CandidateAttempt(Base):
    __tablename__ = "candidate_attempts"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    assessment_id = Column(Integer, ForeignKey("assessments.id")) # referenced from the primary DB
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    evaluated_at = Column(DateTime)
    status = Column(String, default="invited")
    language_choice = Column(String)
    github_repository_link = Column(String)