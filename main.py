import asyncio

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, declarative_base

from utils import *

Base = declarative_base()
app = FastAPI()
DATABASE_URL = "postgresql://postgres:1332@localhost:5432/google-manager"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
pad_code = [
    "AC32010810092",
    "AC32010810553"
]


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


@app.post("/accounts", response_model=AccountResponse)
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


@app.get("/accounts", response_model=list[AccountResponse])
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
        account = db.query(Account).filter(Account.status == 0).with_for_update().first()
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
    result = replace_pad(pad_code, 48)
    if result["msg"] == "success":
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=400, detail=result["msg"])


@app.post("/callback")
async def callback(data: dict):
    task_business_type = data.get("taskBusinessType")
    print(data)
    match int(task_business_type):
        case 1000:
            print(data)

        case 1001:
            print(data)

        case 1003:
            print(data)
            if data["apps"]["result"]:
                print(f'{data["apps"]["padCode"]}: 安装成功')
                print(update_language("en", country="US", pad_code_list=[data["apps"]["padCode"]]))
                print(start_app(pad_code_list=[data["apps"]["padCode"]], pkg_name="com.aaee8h0kh.cejwrh616"))
            else:
                print("安装失败: " + data["apps"]["result"])

        case 1004:
            print(f"安装接口的回调{data}")

        case 1007:
            if data["taskStatus"] == 3:
                print("启动成功")

            else:
                print(data["taskStatus"])

        case 1009:
            print(data)

        case 1124:
            if data.get("padCode") in pad_code:
                if data["taskStatus"] == 3:
                    print(f'{data["padCode"]}: 一键新机成功')
                    clash_install_result = install_app(pad_code_list=[data["padCode"]],
                                      app_url="https://file.vmoscloud.com/userFile/55f0146b6110e4970e1d1f82db8322e8.apk")
                    script_install_result = install_app(pad_code_list=[data["padCode"]],
                                      app_url="https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk")
                    clash_task = asyncio.create_task(check_task_status(clash_install_result["data"][0]["taskId"], "Clash"))
                    script_task = asyncio.create_task(check_task_status(script_install_result["data"][0]["taskId"], "Script"))
                    await asyncio.gather(clash_task, script_task)
                else:
                    print(f'一键新机等待中 {data["taskStatus"]}')


@app.get("/hudson")
async def hudson(data: dict):
    print(data)

async def check_task_status(task_id, task_type):
    while True:
        await asyncio.sleep(3)
        result = get_cloud_file_task_info([str(task_id)])
        print(f"{task_type} task {task_id}: {result}")
        if result["data"][0]["errorMsg"] == "应用安装成功":  # Adjust this condition based on actual API response
            print(f'安装成功')
            print(update_language("en", country="US", pad_code_list=[result["data"][0]["padCode"]]))
            print(start_app(pad_code_list=[result["data"][0]["padCode"]], pkg_name="com.aaee8h0kh.cejwrh616"))
            break
        await asyncio.sleep(3)

@app.get("/")
async def index(data):
    print(data)


if __name__ == "__main__":
    replace_pad(pad_code, 48)
    Base.metadata.create_all(bind=engine)
    uvicorn.run("main:app", host="0.0.0.0", port=5000)
