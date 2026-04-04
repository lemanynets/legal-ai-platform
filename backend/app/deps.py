from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db


def get_current_user_dep() -> CurrentUser:
    return Depends(get_current_user)


def get_db_dep() -> Session:
    return Depends(get_db)