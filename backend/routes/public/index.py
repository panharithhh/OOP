from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    Request,
    status,
    UploadFile
)
from fastapi.templating import Jinja2Templates
from models.database import get_db_connection
import mysql.connector
from fastapi.responses import RedirectResponse
from config.settings import settings
import os
import shutil
from typing import List, Annotated
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import smtplib


router = APIRouter(
    tags=["index"]
)

templates = Jinja2Templates(directory="../frontend/templates")


@router.get("/")
async def get_index_page(request : Request):
    """Serves the index.html page."""
    return templates.TemplateResponse("index.html", {"request": request})

@router.post("/userd")
async def return_to_userdb():
    return RedirectResponse(url = "/userdash", status_code= status.HTTP_303_SEE_OTHER)


