# FILE: app/routes/users.py
from fastapi import APIRouter, HTTPException, Body
from app.services.user_service import user_service
from app.models.user import SearchLog, User

router = APIRouter()

# 1. Identity Handshake (Extension calls this on install/startup)
@router.post("/connect", summary="Connect User")
async def connect_user(user: User):
    result = await user_service.register_user_if_new(user.user_id)
    return result

# 2. Passive Tracking (Extension calls this when URL changes)
@router.post("/track", summary="Log Search History")
async def track_search(log: SearchLog):
    return await user_service.log_search(log)

# 3. Get Chat Sessions (For the 'History' tab in popup)
@router.get("/{user_id}/sessions", summary="Get Chat History")
async def get_sessions(user_id: str):
    return await user_service.get_user_sessions(user_id)

# 4. Get Specific Chat (When user clicks a past conversation)
@router.get("/session/{session_id}", summary="Get Message Log")
async def get_session_messages(session_id: str):
    return await user_service.get_session_history(session_id)