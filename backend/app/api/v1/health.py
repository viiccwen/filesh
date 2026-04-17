from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db_session

router = APIRouter()
db_session_dependency = Depends(get_db_session)


@router.get("")
async def healthcheck(session: Session = db_session_dependency) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
