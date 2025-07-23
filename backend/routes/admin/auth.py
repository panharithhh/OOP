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
import random
import secrets

router = APIRouter()

templates = Jinja2Templates(directory="../frontend/templates")

@router.get("/admin")
async def admin(request : Request):
    return templates.TemplateResponse("admin.html", {
        "request" : request 
    })


@router.post("/test")
async def login_user(
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: mysql.connector.MySQLConnection = Depends(get_db_connection),
):
    cursor = db.cursor()
    query = "SELECT * FROM newestone.users WHERE email = %s"
    cursor.execute(query, (email,))
    data = cursor.fetchone()
    cursor.close()
    
    if not data or data[3] != password:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/code")
async def auth_code(auth_code : Annotated[str, Form()]):
    
    # ran_pass = []
    
    
    # for i in range(0,6):
    #     ran_num = random.randint(0,9)
    #     ran_pass.append((ran_num)) 
    
    # ran_pass_as_str =[]
    # for num in ran_pass:
    #     ran_pass_as_str.append(str(num))
        
    # final_ran_pass = "".join(ran_pass_as_str)
    print(auth_code) 
    if( auth_code == final_ran_pass):
        return RedirectResponse(url = "/dashboard")
    
    
    

@router.get("/auth")
async def to_auth_page(request : Request):
    
    ran_pass = []
     
    for i in range(0,6):
        ran_num = random.randint(0,9)
        ran_pass.append((ran_num)) 
    
    ran_pass_as_str =[]
    for num in ran_pass:
        ran_pass_as_str.append(str(num))
        
    final_ran_pass = "".join(ran_pass_as_str)
        
    
    return templates.TemplateResponse("authentication.html", {
        "request" : request 
    })
    
