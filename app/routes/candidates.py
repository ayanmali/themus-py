from typing import List
from app.dependencies import DBSessionDep
from fastapi import APIRouter, HTTPException
from app.repositories import candidates_repository
from app.data.schemas.candidates import CandidateCreateDto, CandidateResponseDto

candidates_router = APIRouter(
    prefix="/api/candidates",
    tags=["candidates"],
    responses={404: {"description": "Not found"}},
)

@candidates_router.get(
    "/{candidate_id}",
    response_model=CandidateResponseDto,
)
async def candidate_details(
    candidate_id: int,
    db_session: DBSessionDep,
):
    """
    Get any candidate details
    """
    candidate = await candidates_repository.get_candidate(db_session, candidate_id)
    return candidate

@candidates_router.post("/", response_model=CandidateResponseDto)
async def create_candidate(
    candidate: CandidateCreateDto, 
    db_session: DBSessionDep
):
    return await candidates_repository.create_user(db_session, user=candidate)

@candidates_router.get("/{candidate_id}", response_model=CandidateResponseDto)
async def read_candidate(
    candidate_id: int, 
    db_session: DBSessionDep
):
    db_candidate = await candidates_repository.get_candidate(db_session, candidate_id=candidate_id)
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return db_candidate

@candidates_router.get("/", response_model=List[CandidateResponseDto])
async def read_candidates(
    db_session: DBSessionDep,
    skip: int = 0, 
    limit: int = 100, 
):
    candidates = await candidates_repository.get_candidates(db_session, skip=skip, limit=limit)
    return candidates