import datetime
from typing import cast

from fastapi import HTTPException, APIRouter, Query
from loguru import logger
from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError

from app.curd.proxy import update_proxies
from app.curd.status import update_cloud_status
from app.models.accounts import AccountResponse, AccountCreate, AccountUpdate, ForwardRequest, SecondaryEmail
from app.services.database import SessionLocal, Account

router = APIRouter()


@router.post("/create_accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate) -> AccountResponse:
    async with SessionLocal() as db:
        if account.account is None or account.password is None:
            raise HTTPException(status_code=404, detail="Account or password is empty")
        try:
            db_account = Account(
                account=account.account,
                password=account.password,
                type=account.type,
                code=account.code,
                for_email=account.for_email,
                for_password=account.for_password,
                created_at=datetime.datetime.now()
            )
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            if account.pad_code is not None:
                logger.success(f"{account.pad_code}: 账号上传成功")
                await update_proxies(pade_code=account.pad_code)
                await update_cloud_status(pad_code=account.pad_code, num_of_success=1)

            return db_account
        except IntegrityError:
            await db.rollback()
            logger.info("账号已经传过了, fuck")
            raise HTTPException(status_code=400, detail="账号已存在")


@router.get("/accounts", response_model=list[AccountResponse])
async def get_accounts() -> list[AccountResponse]:
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Account).order_by(cast(ColumnElement[bool], Account.id)))
        accounts = result.scalars().all()
        return accounts


## 获取之后就会删除之前那条数据
@router.get("/account/unique", response_model=AccountResponse)
async def get_unique_account(
        delete: bool = Query(default=False, description="是否删除账号，False则将status改为1")
) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select
        stmt = select(Account).filter(cast(ColumnElement[bool], Account.status == 0)).with_for_update()
        result = await db.execute(stmt)
        account = result.scalars().first()

        if account is None:
            raise HTTPException(status_code=404, detail="没有可用的账号")
        account_data = AccountResponse(
            id=account.id,
            account=account.account,
            password=account.password,
            for_email=account.for_email,
            for_password=account.for_password,
            type=account.type,
            status=account.status,
            code=account.code,
            created_at=account.created_at,
            is_boned_secondary_email=account.is_boned_secondary_email
        )

        if delete:
            await db.delete(account)
            logger.info(f"账号 {account.account} 已被删除")
        else:
            account.status = 1
        await db.commit()
        return account_data


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select
        stmt = select(Account).filter(cast(ColumnElement[bool], Account.id == account_id))
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return account


@router.post("/update_forward", response_model=AccountResponse)
async def update_forward(forward: ForwardRequest) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select
        stmt = select(Account).filter(cast(ColumnElement[bool], Account.account == forward.account))
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        account.for_email = forward.for_email
        account.for_password = forward.for_password
        await db.commit()
        await db.refresh(account)
        await update_cloud_status(pad_code=forward.pad_code, forward_num=1)
        return account


@router.post("/update_secondary_mail", response_model=AccountResponse)
async def update_secondary_mail(secondary_mail: SecondaryEmail) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select
        stmt = select(Account).filter(cast(ColumnElement[bool], Account.account == secondary_mail.account))
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        account.is_boned_secondary_email = secondary_mail.is_boned_secondary_email
        await db.commit()
        await db.refresh(account)
        await update_cloud_status(pad_code=secondary_mail.pad_code, secondary_email_num=1)
        return account


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_update: AccountUpdate) -> AccountResponse:
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select
            stmt = select(Account).filter(cast(ColumnElement[bool], Account.id == account_id))
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
async def delete_account(account_id: int) -> dict:
    async with SessionLocal() as db:
        from sqlalchemy import select, delete
        stmt = select(Account).filter(cast(ColumnElement[bool], Account.id == account_id))
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")

        await db.execute(delete(Account).filter(cast(ColumnElement[bool], Account.id == account_id)))
        await db.commit()
        logger.success(f"账号 {account_id} 删除成功")
        return {"detail": "账号删除成功"}
