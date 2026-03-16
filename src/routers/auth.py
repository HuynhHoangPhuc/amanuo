"""Auth endpoints — API key CRUD and session auth."""

import importlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

_auth_middleware = importlib.import_module("src.middleware.auth-middleware")
_auth_service = importlib.import_module("src.services.auth-service")
_workspace_models = importlib.import_module("src.models.workspace")

get_workspace_id = _auth_middleware.get_workspace_id

router = APIRouter(tags=["auth"])


# --- API Key endpoints ---

@router.post("/api-keys", status_code=201)
async def create_api_key(
    req: _workspace_models.ApiKeyCreate,
    workspace_id: str = Depends(get_workspace_id),
):
    """Create a new API key. Returns the full key (shown only once)."""
    return await _auth_service.create_api_key(workspace_id, req.name)


@router.get("/api-keys")
async def list_api_keys(workspace_id: str = Depends(get_workspace_id)):
    """List API keys for the workspace (prefix only)."""
    return await _auth_service.list_api_keys(workspace_id)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, workspace_id: str = Depends(get_workspace_id)):
    """Revoke an API key."""
    revoked = await _auth_service.revoke_api_key(workspace_id, key_id)
    if not revoked:
        raise HTTPException(404, "API key not found")
    return {"revoked": True}


# --- Session Auth endpoints ---

class RegisterRequest(BaseModel):
    email: str
    password: str
    workspace_id: str = "default"


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/register", status_code=201)
async def register(req: RegisterRequest):
    """Register a new user."""
    try:
        user = await _auth_service.register_user(req.email, req.password, req.workspace_id)
        return user
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(409, "Email already registered")
        raise


@router.post("/auth/login")
async def login(req: LoginRequest):
    """Login with email/password. Returns JWT tokens."""
    result = await _auth_service.login_user(req.email, req.password)
    if not result:
        raise HTTPException(401, "Invalid email or password")
    return result


@router.post("/auth/logout")
async def logout():
    """Logout (placeholder — client should discard tokens)."""
    return {"message": "Logged out"}
