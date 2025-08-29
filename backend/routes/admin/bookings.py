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
    tags=["bookings"]
)

templates = Jinja2Templates(directory="../frontend/templates")

@router.post("/confirm-booking")
async def confirm_booking(
    id : Annotated[int, Form()],     
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    cursor.execute ("Update newestone.bookings set status = 'confirmed' where id = %s",(id,) )
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/pend-booking")
async def cancel_booking(
    id : Annotated[int, Form()],     
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    cursor.execute("Update newestone.bookings set status = 'pending' where id = %s",(id,) )
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/cancel-booking")
async def cancel_booking(
    id : Annotated[int, Form()],     
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    cursor.execute("Update newestone.bookings set status = 'cancelled' where id = %s",(id,) )
    db.commit()
    cursor.close()
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/remove_all_bookings")
async def remove_all_bookings(
    confirm : Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    
    if(confirm == "confirm"):
        cursor.execute("delete from newestone.bookings")
        db.commit()
        cursor.close()
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)