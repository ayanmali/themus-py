# Import all models so SQLAlchemy can discover them
from .assessments import Assessment as Assessment
from .candidates import Candidate as Candidate, CandidateAttempt as CandidateAttempt 
from .recordings import Recording as Recording