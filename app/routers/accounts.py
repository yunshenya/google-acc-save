from fastapi import HTTPException, APIRouter
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.models.accounts import AccountResponse, AccountCreate, AccountUpdate
from app.services.database import SessionLocal, Account

router = APIRouter()

@router.post("/accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate):
    async with SessionLocal() as db:
        try:
            db_account = Account(
                account=account.account,
                password=account.password,
                type=account.type,
                code=account.code
            )
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            logger.success("账号上传成功")
            return db_account
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="账号已存在")


@router.get("/accounts", response_model=list[AccountResponse])
async def get_accounts():
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        return accounts


@router.get("/account/unique", response_model=AccountResponse)
async def get_unique_account():
    async with SessionLocal() as db:
        from sqlalchemy import select

        # 使用select语句并添加锁
        stmt = select(Account).filter(Account.status == 0).with_for_update()
        result = await db.execute(stmt)
        account = result.scalars().first()

        if account is None:
            raise HTTPException(status_code=404, detail="没有可用的账号（status=0）")

        account.status = 1
        await db.commit()
        await db.refresh(account)
        return account


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int):
    async with SessionLocal() as db:
        from sqlalchemy import select
        stmt = select(Account).filter(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return account


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_update: AccountUpdate):
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            stmt = select(Account).filter(Account.id == account_id)
            result = await db.execute(stmt)
            db_account = result.scalars().first()
            if db_account is None:
                raise HTTPException(status_code=404, detail="账号不存在")

            # 仅更新提供的字段
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

            await db.commit()
            await db.refresh(db_account)
            return db_account
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="账号已存在")


@router.delete("/accounts/{account_id}", response_model=dict)
async def delete_account(account_id: int):
    async with SessionLocal() as db:
        from sqlalchemy import select, delete
        stmt = select(Account).filter(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")

        await db.execute(delete(Account).filter(Account.id == account_id))
        await db.commit()
        logger.success(f"账号 {account_id} 删除成功")
        return {"detail": "账号删除成功"}