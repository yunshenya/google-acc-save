from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError
import uvicorn

Base = declarative_base()
app = FastAPI()
DATABASE_URL = "postgresql://postgres:1332@localhost:5432/google-manager"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Account(Base):
    __tablename__ = "google_account"
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    type = Column(Integer, default=0, nullable=False)
    status = Column(Integer, default=0, nullable=False)
    code = Column(String(32), nullable=True)

class AccountCreate(BaseModel):
    account: str
    password: str
    type: int = 0
    code: str | None = None

class AccountUpdate(BaseModel):
    account: str | None = None
    password: str | None = None
    type: int | None = None
    status: int | None = None
    code: str | None = None

class AccountResponse(BaseModel):
    id: int
    account: str
    password: str
    type: int
    status: int
    code: str | None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/accounts/", response_model=AccountResponse)
async def create_account(account: AccountCreate):
    db = SessionLocal()
    try:
        db_account = Account(
            account=account.account,
            password=account.password,
            type=account.type,
            code=account.code
        )
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        return db_account
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="账号已存在")
    finally:
        db.close()

@app.get("/accounts/", response_model=list[AccountResponse])
async def get_accounts():
    db = SessionLocal()
    try:
        accounts = db.query(Account).all()
        return accounts
    finally:
        db.close()

@app.get("/account/unique", response_model=AccountResponse)
async def get_unique_account():
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.status == 0).first()
        if account is None:
            raise HTTPException(status_code=404, detail="没有可用的账号（status=0）")
        account.status = 1
        db.commit()
        db.refresh(account)
        return account
    finally:
        db.close()

@app.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int):
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return account
    finally:
        db.close()

@app.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_update: AccountUpdate):
    db = SessionLocal()
    try:
        db_account = db.query(Account).filter(Account.id == account_id).first()
        if db_account is None:
            raise HTTPException(status_code=404, detail="账号不存在")

        # Update only provided fields
        if account_update.account is not None:
            db_account.account = account_update.account
        if account_update.password is not None:
            db_account.password = account_update.password
        if account_update.type is not None:
            db_account.type = account_update.type
        if account_update.status is not None:
            db_account.status = account_update.status
        if account_update.code is not None:
            db_account.code = account_update.code

        db.commit()
        db.refresh(db_account)
        return db_account
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="账号已存在")
    finally:
        db.close()

@app.get("/status")
async def status():
    return {"status": "ok"}

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run("main:app", host="0.0.0.0", port=5000)