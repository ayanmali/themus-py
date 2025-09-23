import logging
import sys
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.candidates import candidates_router
from app.routes.recordings import recordings_router
from app.data.database import session_manager
# Import schemas to ensure all models are loaded for table creation
# from app.data import schemas

import os

load_dotenv()

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS").split(",")

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    # Create database tables on startup
    await session_manager.create_db_and_tables()
    
    yield
    
    if session_manager._engine is not None:
        # Close the DB connection
        await session_manager.close()


app = FastAPI(lifespan=lifespan, title="Themus Candidate Screen Recording Service", docs_url="/docs")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}


# Routers
app.include_router(candidates_router)
app.include_router(recordings_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)