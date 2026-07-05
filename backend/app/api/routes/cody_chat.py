"""
Cody chat endpoint (platform side).

The tenant is ALWAYS derived from the authenticated user's session — never from
the request body. For a tenant user that is their own tenant; for a CodeCore
operator it is whichever tenant they are currently authenticated into (via the
normal tenant session / impersonation token). This is the isolation boundary:
the user cannot ask Cody about a tenant they are not authorized for.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.cody import ask_cody, CodyNotConfigured, CodyUnreachable

router = APIRouter()
log = logging.getLogger("cody.route")


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    message: str
    history: Optional[List[ChatTurn]] = None


@router.post("/chat")
async def chat(data: ChatIn, user: User = Depends(get_current_user),
               db: AsyncSession = Depends(get_db)):
    msg = (data.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="Empty message")

    # TENANT IS DERIVED FROM THE SESSION — the security boundary.
    tenant_id = user.tenant_id
    if not tenant_id:
        raise HTTPException(status_code=400, detail="No tenant context for this session")

    history = [{"role": t.role, "content": t.content} for t in (data.history or [])]

    try:
        answer = await ask_cody(db, tenant_id, msg, history)
    except CodyNotConfigured as e:
        return {"answer": None, "error": str(e), "configured": False}
    except CodyUnreachable as e:
        log.warning("Cody unreachable: %s", e)
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable.")

    return {"answer": answer, "configured": True}
