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
    allow_origins=[
        "http://localhost:3000",
        "https://eac43bf6-8376-434e-9f51-be04df910ffc.preview.emergentagent.com"
    ],
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
payment_transactions_collection = db.payment_transactions

# Subscription Packages
SUBSCRIPTION_PACKAGES = {
    "starter": {"name": "Starter", "base_price": 19.0, "base_users": 5, "additional_cost": 10.0},
    "professional": {"name": "Professional", "base_price": 49.0, "base_users": 5, "additional_cost": 15.0},
    "agency": {"name": "Agency", "base_price": 99.0, "base_users": 5, "additional_cost": 20.0}
}

# Stripe Setup
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")

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
    except jwt.InvalidTokenError:
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
        "workspace_id": workspace["workspace_id"] if workspace else None,
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

# Workspace Management
@app.get("/api/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str, current_user: dict = Depends(get_current_user_flexible)):
    # Check if user is member of workspace
    team_member = team_members_collection.find_one({
        "workspace_id": workspace_id,
        "user_id": current_user["user_id"]
    })
    
    if not team_member:
        raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
    
    workspace = workspaces_collection.find_one({"workspace_id": workspace_id}, {"_id": 0})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return workspace

@app.put("/api/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    name: str,
    current_user: dict = Depends(get_current_user_flexible)
):
    # Check if user is owner or admin
    team_member = team_members_collection.find_one({
        "workspace_id": workspace_id,
        "user_id": current_user["user_id"]
    })
    
    if not team_member or team_member["role"] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to update workspace")
    
    workspaces_collection.update_one(
        {"workspace_id": workspace_id},
        {"$set": {"name": name}}
    )
    
    return {"message": "Workspace updated successfully"}

# Team Management
@app.get("/api/workspaces/{workspace_id}/members")
async def get_team_members(workspace_id: str, current_user: dict = Depends(get_current_user_flexible)):
    # Check if user is member of workspace
    team_member = team_members_collection.find_one({
        "workspace_id": workspace_id,
        "user_id": current_user["user_id"]
    })
    
    if not team_member:
        raise HTTPException(status_code=403, detail="Not authorized to access this workspace")
    
    # Get all team members
    members = list(team_members_collection.find({"workspace_id": workspace_id}, {"_id": 0}))
    
    # Enrich with user data
    for member in members:
        user = users_collection.find_one({"user_id": member["user_id"]}, {"_id": 0, "password": 0})
        if user:
            member["user"] = user
    
    return members

class InvitationCreate(BaseModel):
    email: EmailStr
    workspace_id: str
    role: str = "member"

@app.post("/api/invitations")
async def create_invitation(
    invitation: InvitationCreate,
    current_user: dict = Depends(get_current_user_flexible)
):
    # Check if user is owner or admin
    team_member = team_members_collection.find_one({
        "workspace_id": invitation.workspace_id,
        "user_id": current_user["user_id"]
    })
    
    if not team_member or team_member["role"] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to invite members")
    
    # Check if user already exists in workspace
    existing_user = users_collection.find_one({"email": invitation.email})
    if existing_user:
        existing_member = team_members_collection.find_one({
            "workspace_id": invitation.workspace_id,
            "user_id": existing_user["user_id"]
        })
        if existing_member:
            raise HTTPException(status_code=400, detail="User already in workspace")
    
    # Check if invitation already exists
    existing_invitation = invitations_collection.find_one({
        "workspace_id": invitation.workspace_id,
        "email": invitation.email,
        "status": "pending"
    })
    
    if existing_invitation:
        raise HTTPException(status_code=400, detail="Invitation already sent")
    
    # Get workspace details
    workspace = workspaces_collection.find_one({"workspace_id": invitation.workspace_id})
    
    # Create invitation
    invitation_id = str(uuid.uuid4())
    invitation_doc = {
        "invitation_id": invitation_id,
        "workspace_id": invitation.workspace_id,
        "workspace_name": workspace["name"],
        "email": invitation.email,
        "role": invitation.role,
        "invited_by": current_user["user_id"],
        "invited_by_name": current_user["full_name"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    invitations_collection.insert_one(invitation_doc)
    
    return {"message": "Invitation sent", "invitation_id": invitation_id}

@app.get("/api/invitations")
async def get_invitations(current_user: dict = Depends(get_current_user_flexible)):
    """Get pending invitations for current user"""
    invitations = list(invitations_collection.find({
        "email": current_user["email"],
        "status": "pending"
    }, {"_id": 0}))
    
    return invitations

@app.post("/api/invitations/{invitation_id}/accept")
async def accept_invitation(invitation_id: str, current_user: dict = Depends(get_current_user_flexible)):
    invitation = invitations_collection.find_one({
        "invitation_id": invitation_id,
        "email": current_user["email"],
        "status": "pending"
    })
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Add user to workspace
    member_id = str(uuid.uuid4())
    team_member = {
        "member_id": member_id,
        "workspace_id": invitation["workspace_id"],
        "user_id": current_user["user_id"],
        "role": invitation["role"],
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    team_members_collection.insert_one(team_member)
    
    # Update invitation status
    invitations_collection.update_one(
        {"invitation_id": invitation_id},
        {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Invitation accepted", "workspace_id": invitation["workspace_id"]}

@app.post("/api/invitations/{invitation_id}/decline")
async def decline_invitation(invitation_id: str, current_user: dict = Depends(get_current_user_flexible)):
    invitation = invitations_collection.find_one({
        "invitation_id": invitation_id,
        "email": current_user["email"],
        "status": "pending"
    })
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Update invitation status
    invitations_collection.update_one(
        {"invitation_id": invitation_id},
        {"$set": {"status": "declined", "declined_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Invitation declined"}

@app.delete("/api/workspaces/{workspace_id}/members/{member_id}")
async def remove_member(
    workspace_id: str,
    member_id: str,
    current_user: dict = Depends(get_current_user_flexible)
):
    # Check if user is owner or admin
    requester = team_members_collection.find_one({
        "workspace_id": workspace_id,
        "user_id": current_user["user_id"]
    })
    
    if not requester or requester["role"] not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized to remove members")
    
    # Get member to remove
    member = team_members_collection.find_one({
        "member_id": member_id,
        "workspace_id": workspace_id
    })
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Cannot remove owner
    if member["role"] == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove workspace owner")
    
    # Admins cannot remove other admins
    if requester["role"] == "admin" and member["role"] == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot remove other admins")
    
    # Remove member
    team_members_collection.delete_one({"member_id": member_id})
    
    return {"message": "Member removed successfully"}

@app.put("/api/workspaces/{workspace_id}/members/{member_id}/role")
async def update_member_role(
    workspace_id: str,
    member_id: str,
    new_role: str,
    current_user: dict = Depends(get_current_user_flexible)
):
    # Only owners can change roles
    requester = team_members_collection.find_one({
        "workspace_id": workspace_id,
        "user_id": current_user["user_id"]
    })
    
    if not requester or requester["role"] != "owner":
        raise HTTPException(status_code=403, detail="Only workspace owner can change roles")
    
    # Get member
    member = team_members_collection.find_one({
        "member_id": member_id,
        "workspace_id": workspace_id
    })
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Cannot change owner role
    if member["role"] == "owner":
        raise HTTPException(status_code=400, detail="Cannot change owner role")
    
    # Validate new role
    if new_role not in ["admin", "member"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Update role
    team_members_collection.update_one(
        {"member_id": member_id},
        {"$set": {"role": new_role}}
    )
    
    return {"message": "Role updated successfully"}

# ============================================
# PHASE 4: STRIPE PAYMENT INTEGRATION
# ============================================

def calculate_subscription_price(package_id: str, user_count: int) -> float:
    """Calculate total subscription price based on package and user count"""
    if package_id not in SUBSCRIPTION_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    package = SUBSCRIPTION_PACKAGES[package_id]
    base_price = package["base_price"]
    
    if user_count <= package["base_users"]:
        return base_price
    
    # Calculate additional users (in groups of 5)
    additional_users = user_count - package["base_users"]
    additional_groups = (additional_users + 4) // 5  # Round up to nearest 5
    additional_cost = additional_groups * package["additional_cost"]
    
    return base_price + additional_cost

def workspace_user(request: Request, user: dict = Depends(get_current_user_flexible)):
    """Resolve current membership for company-scoped records on each request."""
    query = {"user_id": user["user_id"]}
    if "workspace_id" in request.path_params:
        query["workspace_id"] = request.path_params["workspace_id"]
    membership = team_members_collection.find_one(query)
    if not membership:
        raise HTTPException(403, "Company workspace membership required.")
    return {**user, "workspace_id": membership["workspace_id"]}


class CheckoutRequestModel(BaseModel):
    package_id: str
    user_count: int = 5
    origin_url: str

@app.post("/api/payments/checkout")
async def create_checkout_session(
    checkout_req: CheckoutRequestModel,
    current_user: dict = Depends(workspace_user),
    request: Request = None
):
    """Create Stripe checkout session for subscription"""
    # Calculate price on backend
    amount = calculate_subscription_price(checkout_req.package_id, checkout_req.user_count)
    
    # Create success and cancel URLs
    success_url = f"{checkout_req.origin_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{checkout_req.origin_url}/subscription"
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": current_user["user_id"],
            "workspace_id": current_user.get("workspace_id", ""),
            "package_id": checkout_req.package_id,
            "user_count": str(checkout_req.user_count)
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    transaction = {
        "transaction_id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": current_user["user_id"],
        "workspace_id": current_user.get("workspace_id", ""),
        "package_id": checkout_req.package_id,
        "user_count": checkout_req.user_count,
        "amount": amount,
        "currency": "usd",
        "payment_status": "pending",
        "status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    payment_transactions_collection.insert_one(transaction)
    
    return {"url": session.url, "session_id": session.session_id}

@app.get("/api/payments/status/{session_id}")
async def get_payment_status(
    session_id: str,
    current_user: dict = Depends(workspace_user),
    request: Request = None
):
    """Get payment status for a checkout session"""
    if not payment_transactions_collection.find_one({"session_id": session_id, "workspace_id": current_user["workspace_id"]}):
        raise HTTPException(404, "Checkout session not found.")
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Get checkout status from Stripe
    checkout_status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction in database
    transaction = payment_transactions_collection.find_one({"session_id": session_id})
    if transaction:
        update_data = {
            "payment_status": checkout_status.payment_status,
            "status": checkout_status.status,
            "amount_total": checkout_status.amount_total,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # If payment is complete and not already processed
        if checkout_status.payment_status == "paid" and transaction.get("processed") != True:
            # Create/update subscription
            metadata = checkout_status.metadata
            subscription = {
                "subscription_id": str(uuid.uuid4()),
                "workspace_id": metadata.get("workspace_id"),
                "package_id": metadata.get("package_id"),
                "user_count": int(metadata.get("user_count", 5)),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "next_billing_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            }
            subscriptions_collection.insert_one(subscription)
            
            update_data["processed"] = True
        
        payment_transactions_collection.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
    
    return checkout_status

@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    # Initialize Stripe
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction based on webhook event
        if webhook_response.session_id:
            payment_transactions_collection.update_one(
                {"session_id": webhook_response.session_id},
                {"$set": {
                    "payment_status": webhook_response.payment_status,
                    "event_type": webhook_response.event_type,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/subscriptions/workspace/{workspace_id}")
async def get_workspace_subscription(
    workspace_id: str,
    current_user: dict = Depends(workspace_user)
):
    """Get active subscription for workspace"""
    subscription = subscriptions_collection.find_one(
        {"workspace_id": workspace_id, "status": "active"},
        {"_id": 0}
    )
    if not subscription:
        return {"status": "none", "message": "No active subscription"}
    return subscription

# ============================================
# PHASE 5: COMPANY PROFILE MANAGEMENT
# ============================================

class CompanyProfileModel(BaseModel):
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None

@app.post("/api/companies")
async def create_company_profile(
    profile: CompanyProfileModel,
    current_user: dict = Depends(workspace_user)
):
    """Create company profile"""
    company_id = str(uuid.uuid4())
    company = {
        "company_id": company_id,
        "workspace_id": current_user.get("workspace_id"),
        "company_name": profile.company_name,
        "website": profile.website,
        "industry": profile.industry,
        "description": profile.description,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    companies_collection.insert_one(company)
    return {"company_id": company_id, "message": "Company profile created"}

@app.get("/api/companies/workspace/{workspace_id}")
async def get_company_profile(
    workspace_id: str,
    current_user: dict = Depends(workspace_user)
):
    """Get company profile for workspace"""
    company = companies_collection.find_one({"workspace_id": workspace_id}, {"_id": 0})
    if not company:
        return {"status": "none", "message": "No company profile found"}
    return company

class SocialMediaModel(BaseModel):
    platform: str
    url: str
    followers: Optional[int] = 0

@app.post("/api/social-profiles")
async def add_social_profile(
    profile: SocialMediaModel,
    current_user: dict = Depends(workspace_user)
):
    """Add social media profile"""
    profile_id = str(uuid.uuid4())
    social_profile = {
        "profile_id": profile_id,
        "workspace_id": current_user.get("workspace_id"),
        "platform": profile.platform,
        "url": profile.url,
        "followers": profile.followers,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    social_profiles_collection.insert_one(social_profile)
    return {"profile_id": profile_id, "message": "Social profile added"}

@app.get("/api/social-profiles/workspace/{workspace_id}")
async def get_social_profiles(
    workspace_id: str,
    current_user: dict = Depends(workspace_user)
):
    """Get all social profiles for workspace"""
    profiles = list(social_profiles_collection.find({"workspace_id": workspace_id}, {"_id": 0}))
    return profiles

# ============================================
# PHASE 6: MARKETING METRICS DASHBOARD
# ============================================

class MetricModel(BaseModel):
    metric_type: str
    value: float
    date: str
    notes: Optional[str] = None

@app.post("/api/metrics")
async def add_metric(
    metric: MetricModel,
    current_user: dict = Depends(workspace_user)
):
    """Add marketing metric"""
    metric_id = str(uuid.uuid4())
    metric_data = {
        "metric_id": metric_id,
        "workspace_id": current_user.get("workspace_id"),
        "metric_type": metric.metric_type,
        "value": metric.value,
        "date": metric.date,
        "notes": metric.notes,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    metrics_collection.insert_one(metric_data)
    return {"metric_id": metric_id, "message": "Metric added"}

@app.get("/api/metrics/workspace/{workspace_id}")
async def get_metrics(
    workspace_id: str,
    metric_type: Optional[str] = None,
    current_user: dict = Depends(workspace_user)
):
    """Get metrics for workspace"""
    query = {"workspace_id": workspace_id}
    if metric_type:
        query["metric_type"] = metric_type
    metrics = list(metrics_collection.find(query, {"_id": 0}).sort("date", -1).limit(100))
    return metrics

# ============================================
# PHASE 8: TASK MANAGEMENT
# ============================================

class TaskCreateModel(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    status: str = "todo"

@app.post("/api/tasks")
async def create_task(
    task: TaskCreateModel,
    current_user: dict = Depends(workspace_user)
):
    """Create a new task"""
    task_id = str(uuid.uuid4())
    task_data = {
        "task_id": task_id,
        "workspace_id": current_user.get("workspace_id"),
        "title": task.title,
        "description": task.description,
        "assigned_to": task.assigned_to,
        "created_by": current_user["user_id"],
        "priority": task.priority,
        "due_date": task.due_date,
        "status": task.status,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    tasks_collection.insert_one(task_data)
    return {"task_id": task_id, "message": "Task created"}

@app.get("/api/tasks/workspace/{workspace_id}")
async def get_tasks(
    workspace_id: str,
    status: Optional[str] = None,
    current_user: dict = Depends(workspace_user)
):
    """Get tasks for workspace"""
    query = {"workspace_id": workspace_id}
    if status:
        query["status"] = status
    tasks = list(tasks_collection.find(query, {"_id": 0}).sort("created_at", -1))
    
    # Enrich with user data
    for task in tasks:
        if task.get("assigned_to"):
            assignee = users_collection.find_one({"user_id": task["assigned_to"]}, {"_id": 0, "password": 0})
            if assignee:
                task["assignee"] = assignee
    
    return tasks

@app.put("/api/tasks/{task_id}")
async def update_task(
    task_id: str,
    update_data: dict,
    current_user: dict = Depends(workspace_user)
):
    """Update task"""
    if set(update_data) - set(TaskCreateModel.model_fields):
        raise HTTPException(400, "Unknown task field.")
    result = tasks_collection.update_one(
        {"task_id": task_id, "workspace_id": current_user["workspace_id"]},
        {"$set": {**update_data, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if not result.matched_count:
        raise HTTPException(404, "Task not found.")
    return {"message": "Task updated"}

# ============================================
# PHASE 10: STRATEGY CREATOR
# ============================================

class StrategyModel(BaseModel):
    title: str
    description: str
    goals: Optional[List[str]] = []
    tactics: Optional[List[str]] = []

@app.post("/api/strategies")
async def create_strategy(
    strategy: StrategyModel,
    current_user: dict = Depends(workspace_user)
):
    """Create marketing strategy"""
    strategy_id = str(uuid.uuid4())
    strategy_data = {
        "strategy_id": strategy_id,
        "workspace_id": current_user.get("workspace_id"),
        "title": strategy.title,
        "description": strategy.description,
        "goals": strategy.goals,
        "tactics": strategy.tactics,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    strategies_collection.insert_one(strategy_data)
    return {"strategy_id": strategy_id, "message": "Strategy created"}

@app.get("/api/strategies/workspace/{workspace_id}")
async def get_strategies(
    workspace_id: str,
    current_user: dict = Depends(workspace_user)
):
    """Get strategies for workspace"""
    strategies = list(strategies_collection.find({"workspace_id": workspace_id}, {"_id": 0}).sort("created_at", -1))
    return strategies

# ============================================
# PHASE 7 & 11: AI-POWERED FEATURES
# ============================================


EMERGENT_LLM_KEY = os.getenv("EMERGENT_LLM_KEY")

class AIAssessmentRequest(BaseModel):
    company_name: str
    industry: Optional[str] = None
    current_metrics: Optional[dict] = None

@app.post("/api/ai/assessment")
async def generate_ai_assessment(
    request: AIAssessmentRequest,
    current_user: dict = Depends(workspace_user)
):
    """Generate AI-powered marketing health assessment"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"assessment_{current_user['user_id']}",
        system_message="You are a marketing expert who provides actionable insights and recommendations."
    ).with_model("openai", "gpt-5.2")
    
    prompt = f"""Analyze the marketing health for {request.company_name} in the {request.industry or 'general'} industry.
    
Current metrics: {request.current_metrics or 'No metrics provided yet'}

Provide:
1. Overall marketing health score (0-100)
2. Top 3 strengths
3. Top 3 areas for improvement
4. 5 specific actionable recommendations

Format your response as JSON with keys: score, strengths, improvements, recommendations"""
    
    user_message = UserMessage(text=prompt)
    response = await chat.send_message(user_message)
    
    # Save assessment
    assessment_id = str(uuid.uuid4())
    assessment = {
        "assessment_id": assessment_id,
        "workspace_id": current_user.get("workspace_id"),
        "company_name": request.company_name,
        "ai_response": response,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    assessments_collection.insert_one(assessment)
    
    return {"assessment_id": assessment_id, "response": response}

class CopywriterRequestModel(BaseModel):
    content_type: str  # blog, social_media, email, ad_copy
    topic: str
    tone: str = "professional"
    length: str = "medium"

@app.post("/api/ai/copywriter")
async def generate_copy(
    request: CopywriterRequestModel,
    current_user: dict = Depends(workspace_user)
):
    """AI copywriting tool"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"copy_{current_user['user_id']}",
        system_message="You are an expert copywriter who creates engaging, conversion-focused content."
    ).with_model("openai", "gpt-5.2")
    
    length_guide = {"short": "100-150 words", "medium": "300-500 words", "long": "800-1200 words"}
    
    prompt = f"""Create {request.content_type} content about: {request.topic}

Tone: {request.tone}
Length: {length_guide.get(request.length, '300-500 words')}

Make it engaging, actionable, and optimized for {request.content_type}."""
    
    user_message = UserMessage(text=prompt)
    response = await chat.send_message(user_message)
    
    return {"content": response}

class AdCreatorRequestModel(BaseModel):
    product_name: str
    target_audience: str
    platform: str
    goal: str = "conversion"

@app.post("/api/ai/ad-creator")
async def create_ad(
    request: AdCreatorRequestModel,
    current_user: dict = Depends(workspace_user)
):
    """AI ad creation tool"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"ad_{current_user['user_id']}",
        system_message="You are an advertising expert who creates compelling ad copy."
    ).with_model("openai", "gpt-5.2")
    
    prompt = f"""Create an ad for {request.product_name} targeting {request.target_audience} on {request.platform}.

Goal: {request.goal}

Provide:
1. Headline (attention-grabbing)
2. Body copy (compelling and clear)
3. Call-to-action (strong and specific)
4. Key messaging points

Format as JSON with keys: headline, body, cta, messaging_points"""
    
    user_message = UserMessage(text=prompt)
    response = await chat.send_message(user_message)
    
    return {"ad": response}

class TaskGeneratorRequest(BaseModel):
    strategy_id: str

@app.post("/api/ai/generate-tasks")
async def generate_tasks_from_strategy(
    request: TaskGeneratorRequest,
    current_user: dict = Depends(workspace_user)
):
    """AI task generator from strategy"""
    # Get strategy
    strategy = strategies_collection.find_one({"strategy_id": request.strategy_id}, {"_id": 0})
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"tasks_{current_user['user_id']}",
        system_message="You are a project manager who breaks down strategies into actionable tasks."
    ).with_model("openai", "gpt-5.2")
    
    prompt = f"""Based on this marketing strategy, generate 5-10 specific, actionable tasks:

Strategy: {strategy.get('title')}
Description: {strategy.get('description')}
Goals: {strategy.get('goals', [])}

For each task provide:
- Title (clear and specific)
- Description (what needs to be done)
- Priority (high/medium/low)
- Estimated timeline

Format as JSON array with keys: title, description, priority, timeline"""
    
    user_message = UserMessage(text=prompt)
    response = await chat.send_message(user_message)
    
    # Optionally auto-create tasks
    # Parse response and create tasks in database
    
    return {"tasks": response}

class StrategyGeneratorRequest(BaseModel):
    company_name: str
    industry: str
    goals: List[str]
    budget: Optional[str] = None

@app.post("/api/ai/generate-strategy")
async def generate_strategy(
    request: StrategyGeneratorRequest,
    current_user: dict = Depends(workspace_user)
):
    """AI strategy generator"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"strategy_{current_user['user_id']}",
        system_message="You are a marketing strategist who creates comprehensive marketing plans."
    ).with_model("openai", "gpt-5.2")
    
    prompt = f"""Create a comprehensive marketing strategy for {request.company_name} in the {request.industry} industry.

Goals: {', '.join(request.goals)}
Budget: {request.budget or 'Flexible'}

Provide a detailed strategy including:
1. Executive Summary
2. Target Audience Analysis
3. Channel Strategy (which platforms and why)
4. Content Strategy
5. Key Tactics (specific actions)
6. Success Metrics
7. Timeline (monthly breakdown)

Make it actionable and specific."""
    
    user_message = UserMessage(text=prompt)
    response = await chat.send_message(user_message)
    
    # Save as strategy
    strategy_id = str(uuid.uuid4())
    strategy = {
        "strategy_id": strategy_id,
        "workspace_id": current_user.get("workspace_id"),
        "title": f"AI-Generated Strategy for {request.company_name}",
        "description": response,
        "goals": request.goals,
        "created_by": current_user["user_id"],
        "ai_generated": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    strategies_collection.insert_one(strategy)
    
    return {"strategy_id": strategy_id, "strategy": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)


from campaign_routes import register_campaign_routes

register_campaign_routes(app, get_current_user_flexible, team_members_collection, workspaces_collection)
