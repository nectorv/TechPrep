import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import hash_password, verify_password, create_access_token, get_current_user
from ..database import get_db

router = APIRouter()


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.post("/telegram-link-code")
def generate_telegram_link_code(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Delete any existing codes for this user
    db.query(models.TelegramLinkCode).filter(
        models.TelegramLinkCode.user_id == current_user.id
    ).delete()

    # Generate a unique 6-digit code
    while True:
        code = "".join(random.choices(string.digits, k=6))
        if not db.query(models.TelegramLinkCode).filter(
            models.TelegramLinkCode.code == code
        ).first():
            break

    link = models.TelegramLinkCode(
        code=code,
        user_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(link)
    db.commit()
    return {"code": code, "expires_in": 600}
