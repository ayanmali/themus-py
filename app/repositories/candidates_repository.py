from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.data.schemas.candidates import Candidate, CandidateCreateDto
from fastapi import HTTPException

async def create_candidate(db_session: AsyncSession, candidate: CandidateCreateDto):
    db_candidate = Candidate(name=candidate.name, email=candidate.email)
    db_session.add(db_candidate)
    await db_session.commit()
    await db_session.refresh(db_candidate)
    return db_candidate

async def get_candidate(db_session: AsyncSession, candidate_id: int):
    candidate = (await db_session.scalars(select(Candidate).where(Candidate.id == candidate_id))).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate

async def get_candidate_by_email(db_session: AsyncSession, email: str):
    return (await db_session.scalars(select(Candidate).where(Candidate.email == email))).first()

async def get_candidates(db_session: AsyncSession, skip: int = 0, limit: int = 100):
    return (await db_session.scalars(select(Candidate).offset(skip).limit(limit))).all()