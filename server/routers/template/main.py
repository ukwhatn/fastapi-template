from fastapi import APIRouter, Request, Response, Depends
import json
from sqlalchemy.orm import Session

from db import schemas
from db.session import get_db

from fastapi import APIRouter

# define router
router = APIRouter(
    tags=["template"],
)
