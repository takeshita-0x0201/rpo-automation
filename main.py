from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uuid
from config import settings

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# FastAPI app
app = FastAPI(
    title="RPO Automation API",
    description="API for RPO Automation Chrome Extension",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String)
    role = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    requirements = relationship("JobRequirement", back_populates="client")

class JobRequirement(Base):
    __tablename__ = "job_requirements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    title = Column(String, nullable=False)
    description = Column(Text)
    requirement_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    client = relationship("Client", back_populates="requirements")

class ScrapingSession(Base):
    __tablename__ = "scraping_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("auth.users.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    requirement_id = Column(String, nullable=False)  # Textフィールドとして定義されている
    status = Column(String, default="active")
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scraping_session_id = Column(UUID(as_uuid=True), ForeignKey("scraping_sessions.id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("job_requirements.id"))
    candidate_id = Column(String, nullable=False)
    candidate_link = Column(Text, nullable=False)
    candidate_company = Column(String)
    candidate_resume = Column(Text)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    enrolled_company_count = Column(Integer, nullable=True)
    platform = Column(String, default="bizreach")
    scraped_at = Column(DateTime, default=datetime.utcnow)
    scraped_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    is_active: bool
    is_admin: bool

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ClientResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

class RequirementResponse(BaseModel):
    id: str
    client_id: str
    title: str
    description: Optional[str]
    target_count: Optional[int]
    status: str

class SessionCreate(BaseModel):
    client_id: str
    requirement_id: str

class CandidateCreate(BaseModel):
    candidate_id: str
    candidate_link: str
    candidate_company: str
    candidate_resume: str
    age: Optional[int] = None
    gender: Optional[str] = None
    enrolled_company_count: Optional[int] = None
    platform: str
    client_id: str
    requirement_id: str
    scraping_session_id: str

class CandidateBatch(BaseModel):
    candidates: List[CandidateCreate]
    session_id: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Routes
@app.get("/")
def read_root():
    return {"message": "RPO Automation API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/auth/extension/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "is_admin": user.is_admin
        }
    }

@app.post("/api/auth/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        name=user_data.name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "is_active": user.is_active,
        "is_admin": user.is_admin
    }

@app.get("/api/clients", response_model=List[ClientResponse])
def get_clients(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    clients = db.query(Client).all()
    return [
        {
            "id": str(client.id),
            "name": client.name,
            "created_at": client.created_at
        }
        for client in clients
    ]

@app.get("/api/requirements", response_model=List[RequirementResponse])
def get_all_requirements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requirements = db.query(Requirement).all()
    return [
        {
            "id": str(req.id),
            "client_id": str(req.client_id),
            "title": req.title,
            "description": req.description,
            "target_count": req.target_count,
            "status": req.status
        }
        for req in requirements
    ]

@app.get("/api/requirements/{requirement_id}", response_model=RequirementResponse)
def get_requirement(requirement_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requirement = db.query(Requirement).filter(Requirement.id == requirement_id).first()
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    return {
        "id": str(requirement.id),
        "client_id": str(requirement.client_id),
        "title": requirement.title,
        "description": requirement.description,
        "target_count": requirement.target_count,
        "status": requirement.status
    }

@app.post("/api/extension/scraping/start")
def start_scraping(session_data: SessionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Create new scraping session
    session = ScrapingSession(
        user_id=current_user.id,
        client_id=uuid.UUID(session_data.client_id),
        requirement_id=uuid.UUID(session_data.requirement_id)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {"session_id": str(session.id), "status": "started"}

@app.post("/api/extension/scraping/end")
def end_scraping(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(ScrapingSession).filter(ScrapingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.ended_at = datetime.utcnow()
    session.status = "completed"
    db.commit()
    
    return {"session_id": str(session.id), "status": "completed"}

@app.post("/api/extension/candidates/batch")
def save_candidates(batch_data: CandidateBatch, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    saved_count = 0
    
    for candidate_data in batch_data.candidates:
        candidate = Candidate(
            session_id=uuid.UUID(batch_data.session_id),
            client_id=uuid.UUID(candidate_data.client_id),
            requirement_id=uuid.UUID(candidate_data.requirement_id),
            candidate_id=candidate_data.candidate_id,
            candidate_link=candidate_data.candidate_link,
            candidate_company=candidate_data.candidate_company,
            candidate_resume=candidate_data.candidate_resume,
            age=candidate_data.age,
            gender=candidate_data.gender,
            enrolled_company_count=candidate_data.enrolled_company_count,
            platform=candidate_data.platform
        )
        db.add(candidate)
        saved_count += 1
    
    db.commit()
    
    return {
        "processed": len(batch_data.candidates),
        "saved": saved_count,
        "success": True
    }

# Media platforms endpoint
@app.get("/api/media-platforms")
def get_media_platforms(current_user: User = Depends(get_current_user)):
    return [
        {"id": "bizreach", "name": "BizReach", "url": "https://www.bizreach.jp"},
        {"id": "openwork", "name": "OpenWork", "url": "https://www.openwork.jp"},
        {"id": "rikunabihrtech", "name": "リクナビHR Tech", "url": "https://hrtech.rikunabi.com"}
    ]

# Create tables
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)