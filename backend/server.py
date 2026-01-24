from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from passlib.context import CryptContext
import jwt
import os
from dotenv import load_dotenv
import uuid
import httpx

load_dotenv()

app = FastAPI(title="Marketing SaaS API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Setup
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/marketing_saas")
client = MongoClient(MONGO_URL)
db = client.get_database()

# Collections
users_collection = db.users
companies_collection = db.companies
workspaces_collection = db.workspaces
team_members_collection = db.team_members
subscriptions_collection = db.subscriptions
metrics_collection = db.metrics
social_profiles_collection = db.social_profiles
assessments_collection = db.assessments
strategies_collection = db.strategies
tasks_collection = db.tasks
task_comments_collection = db.task_comments
invitations_collection = db.invitations
templates_collection = db.templates
user_sessions_collection = db.user_sessions

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Pydantic Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

# Helper Functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", 43200)))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user.pop("password", None)
    return user

# OAuth authentication helper - checks cookie first, then Authorization header
async def get_current_user_flexible(request: Request, authorization: Optional[str] = Header(None)):
    # Check for session_token in cookies first
    session_token = request.cookies.get("session_token")
    
    if session_token:
        # Validate session token from cookie
        session = user_sessions_collection.find_one({"session_token": session_token})
        if session:
            # Check expiry
            expires_at = session["expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Session expired")
            
            # Get user
            user = users_collection.find_one({"user_id": session["user_id"]}, {"_id": 0, "password": 0})
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return user
    
    # Fallback to Authorization header (JWT or session token)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        
        # Try session token first
        session = user_sessions_collection.find_one({"session_token": token})
        if session:
            expires_at = session["expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            if expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Session expired")
            
            user = users_collection.find_one({"user_id": session["user_id"]}, {"_id": 0, "password": 0})
            if user:
                return user
        
        # Try JWT token
        try:
            payload = decode_token(token)
            user_id = payload.get("user_id")
            if user_id:
                user = users_collection.find_one({"user_id": user_id}, {"_id": 0, "password": 0})
                if user:
                    return user
        except:
            pass
    
    raise HTTPException(status_code=401, detail="Not authenticated")

# Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserRegister):
    # Check if user exists
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "user_id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "full_name": user_data.full_name,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    users_collection.insert_one(user)
    
    # Create workspace if company name provided
    workspace_id = None
    if user_data.company_name:
        workspace_id = str(uuid.uuid4())
        workspace = {
            "workspace_id": workspace_id,
            "name": user_data.company_name,
            "owner_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "settings": {}
        }
        workspaces_collection.insert_one(workspace)
        
        # Add user as team member (owner)
        team_member = {
            "member_id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": "owner",
            "joined_at": datetime.utcnow().isoformat()
        }
        team_members_collection.insert_one(team_member)
    
    # Generate token
    token = create_access_token({"user_id": user_id, "email": user_data.email})
    
    user_response = {
        "user_id": user_id,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "workspace_id": workspace_id
    }
    
    return {"access_token": token, "token_type": "bearer", "user": user_response}

@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user = users_collection.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Get workspace
    team_member = team_members_collection.find_one({"user_id": user["user_id"]})
    workspace_id = team_member["workspace_id"] if team_member else None
    
    token = create_access_token({"user_id": user["user_id"], "email": user["email"]})
    
    user_response = {
        "user_id": user["user_id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "workspace_id": workspace_id
    }
    
    return {"access_token": token, "token_type": "bearer", "user": user_response}

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user_flexible)):
    # Get workspace info
    team_member = team_members_collection.find_one({"user_id": current_user["user_id"]})
    workspace = None
    if team_member:
        workspace = workspaces_collection.find_one({"workspace_id": team_member["workspace_id"]})
        if workspace:
            workspace.pop("_id", None)
    
    return {
        **current_user,
        "workspace": workspace,
        "role": team_member["role"] if team_member else None
    }

# OAuth Session Processing
@app.post("/api/auth/oauth/session")
async def process_oauth_session(x_session_id: str = Header(...), response: Response = None):
    """Process OAuth session_id from Emergent Auth and create user session"""
    
    # Exchange session_id for user data from Emergent Auth
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": x_session_id},
                timeout=10.0
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session ID")
            
            oauth_data = auth_response.json()
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Failed to validate session: {str(e)}")
    
    # Extract user data
    email = oauth_data.get("email")
    name = oauth_data.get("name")
    picture = oauth_data.get("picture")
    session_token = oauth_data.get("session_token")
    
    if not email or not session_token:
        raise HTTPException(status_code=400, detail="Invalid OAuth data")
    
    # Check if user exists
    user = users_collection.find_one({"email": email})
    
    if user:
        # Update existing user
        user_id = user["user_id"]
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "full_name": name,
                "picture": picture,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    else:
        # Create new user
        user_id = str(uuid.uuid4())
        user = {
            "user_id": user_id,
            "email": email,
            "full_name": name,
            "picture": picture,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        users_collection.insert_one(user)
        
        # Create default workspace
        workspace_id = str(uuid.uuid4())
        workspace = {
            "workspace_id": workspace_id,
            "name": f"{name}'s Workspace",
            "owner_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settings": {}
        }
        workspaces_collection.insert_one(workspace)
        
        # Add user as team member (owner)
        team_member = {
            "member_id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": "owner",
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        team_members_collection.insert_one(team_member)
    
    # Create session in database
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc)
    }
    
    # Remove old sessions for this user
    user_sessions_collection.delete_many({"user_id": user_id})
    user_sessions_collection.insert_one(session)
    
    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/"
    )
    
    # Get workspace
    team_member = team_members_collection.find_one({"user_id": user_id})
    workspace_id = team_member["workspace_id"] if team_member else None
    
    # Return user data
    return {
        "user_id": user_id,
        "email": email,
        "full_name": name,
        "picture": picture,
        "workspace_id": workspace_id
    }

# Logout
@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        # Delete session from database
        user_sessions_collection.delete_one({"session_token": session_token})
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"message": "Logged out successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
