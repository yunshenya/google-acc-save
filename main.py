from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError

base = declarative_base()
app = FastAPI()
DATABASE_URL = "postgresql://postgres:1332@localhost:5432/google-manager"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Account(Base):
    __tablename__ = "google_account"
    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)

class AccountCreate(BaseModel):
    account: str
    password: str

class AccountResponse(BaseModel):
    id: int
    account: str
    password: str


# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 路由：创建账号
@app.post("/accounts/", response_model=AccountResponse)
async def create_account(account: AccountCreate):
    db = SessionLocal()
    try:
        db_account = Account(account=account.account, password=account.password)
        db.add(db_account)
        db.commit()
        db.refresh(db_account)
        return db_account
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="账号已存在")
    finally:
        db.close()

# 路由：获取所有账号
@app.get("/accounts/", response_model=list[AccountResponse])
async def get_accounts():
    db = SessionLocal()
    try:
        accounts = db.query(Account).all()
        return accounts
    finally:
        db.close()

# 路由：根据 ID 获取账号
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

@app.get("/status")
async def status():
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)


