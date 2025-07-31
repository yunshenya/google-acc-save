import asyncio
import csv
import random
from asyncio import Task
from collections import defaultdict
from typing import List

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from utils import *

Base = declarative_base()
app = FastAPI()
DATABASE_URL = "postgresql+asyncpg://postgres:1332@localhost:5432/google-manager"
engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(class_=AsyncSession, bind=engine, autoflush=False, autocommit=False)
pad_code_list = [
    "AC32010810553",
    "ACP250317XGMWV7A"
]
temple_id_list = [375]
pkg_name = "com.aaee8h0kh.cejwrh616"
clash_install_url = "https://file.vmoscloud.com/userFile/b250a566f01210cb6783cf4e5d82313f.apk"
script_install_url = "https://file.vmoscloud.com/userFile/e529d87b651fa55ebe2bb4743d2e8da2.apk"
# 默认代理设置
default_proxy = {
    "country": "危地马拉",
    "code": "gt",
    "proxy_url": "https://raw.githubusercontent.com/heisiyyds999/clash-conf/refs/heads/master/proxys/gt.yaml",
    "time_zone": "America/Guatemala",
    "language": "English",
    "latitude": 14.6419,
    "longitude": -90.5133
}

# 加载代理国家列表
proxy_countries = []

def load_proxy_countries():
    global proxy_countries
    try:
        with open("代理国家列表 - IPIDEA.csv", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 9:
                    # 读取所有字段，但只保留模型中需要的字段
                    country_data = {
                        "country": row[0],  # 国家名称
                        "code": row[1],    # 国家代码
                        "proxy_url": row[2],  # 代理URL
                        "time_zone": row[3],  # 时区
                        "language": row[4],   # 语言
                        "latitude": float(row[5]),  # 纬度
                        "longitude": float(row[6]),  # 经度
                    }
                    # 仅用于内部过滤，不包含在API响应中
                    if row[7] == "是":  # 只添加可用的代理
                        proxy_countries.append(country_data)
            print(f"已加载 {len(proxy_countries)} 个代理国家信息")
    except Exception as e:
        print(f"加载代理国家列表失败: {e}")
        # 如果加载失败，使用默认代理
        proxy_countries = [default_proxy]

# 获取当前使用的代理信息
current_proxy = default_proxy.copy()

# 使用默认代理设置初始化变量
proxy_url = current_proxy["proxy_url"]
time_zone = current_proxy["time_zone"]
latitude = current_proxy["latitude"]
longitude = current_proxy["longitude"]


operations = defaultdict(lambda: Task[None])
lock = asyncio.Lock()

async def handle_timeout(pad_code_str: str):
    try:
        await asyncio.sleep(5 * 60)
        async with lock:
            if operations.get(pad_code_str) is not None:
                print(f"标识符超时: {pad_code_str}")
                result = await replace_pad([pad_code_str], template_id=random.choice(temple_id_list))
                print(f"正在一键新机: {result}")
                del operations[pad_code_str]
    except asyncio.CancelledError:
        print(f"标识符的超时任务: {pad_code_str} 被取消了.")


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


class AndroidPadCodeRequest(BaseModel):
    pad_code: str


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


async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


@app.post("/accounts", response_model=AccountResponse)
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
            return db_account
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="账号已存在")


@app.get("/accounts", response_model=list[AccountResponse])
async def get_accounts():
    async with SessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(Account))
        accounts = result.scalars().all()
        return accounts


@app.get("/account/unique", response_model=AccountResponse)
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


@app.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int):
    async with SessionLocal() as db:
        from sqlalchemy import select
        stmt = select(Account).filter(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        return account


@app.put("/accounts/{account_id}", response_model=AccountResponse)
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


@app.post("/status")
async def status(android_code: AndroidPadCodeRequest):
    result = await replace_pad([android_code.pad_code], template_id=random.choice(temple_id_list))
    print(result)
    async with lock:
        task = operations.get(android_code.pad_code)
        if task is not None:
            task.cancel()
            del operations[android_code.pad_code]
            print("已在规定时间内完成， 超时任务已移除")
    return {"message": "Task cancelled"}


@app.post("/callback")
async def callback(data: dict):
    task_business_type = data.get("taskBusinessType")
    match int(task_business_type):
        case 1000:
            _id = data.get("padCode")
            print(f"{_id}: 重启成功")
            print(f"设置语言、时区和GPS信息（使用代理国家: {current_proxy['country']} ({current_proxy['code']}))")
            
            # 设置语言
            lang_result = await update_language("en", country=current_proxy['code'], pad_code_list=[data["padCode"]])
            print(f"Language update result: {lang_result}")
            
            # 设置时区
            tz_result = await update_time_zone(pad_code_list=[data["padCode"]], time_zone=current_proxy["time_zone"])
            print(f"Timezone update result: {tz_result}")
            
            # 设置GPS信息
            gps_result = await gps_in_ject_info(
                pad_code_list=[data["padCode"]], 
                latitude=current_proxy["latitude"], 
                longitude=current_proxy["longitude"]
            )
            print(f"GPS injection result: {gps_result}")
            await asyncio.sleep(2)
            print(f"{_id}: 开始启动app")
            app_result = await start_app(pad_code_list=[data["padCode"]], pkg_name=pkg_name)
            print(f"Start app result: {app_result}")

        case 1001:
            print("1001接口回调")

        case 1003:
            print(f'安装成功接口回调 {data["apps"]["padCode"]}: 安装成功')
            print(data)
            # lang_result = await update_language("en", country=current_proxy['code'], pad_code_list=[data["apps"]["padCode"]])
            # print(f"Language update result: {lang_result}")
            # app_result = await start_app(pad_code_list=[data["apps"]["padCode"]], pkg_name=pkg_name)
            # print(f"Start app result: {app_result}")


        case 1004:
            print(f"安装接口的回调{data}")

        case 1006:
            print("应用重启")

        case 1007:
            print("应用启动成功回调")
            if data["taskStatus"] == 3:
                print("启动成功")

            else:
                task = data["taskStatus"]
                print(f"应用启动等待中: {task}")

        case 1009:
            print("1009接口回调")

        case 1124:
            if data.get("padCode") in pad_code_list:
                if data["taskStatus"] == 3:
                    pad_code_str = data.get("padCode")
                    print(f'{data["padCode"]}: 一键新机成功')
                    async with lock:
                        if operations.get(pad_code_str) is not None:
                            raise HTTPException(status_code=400, detail=f"Identifier {pad_code_str} is already in use")
                    task = asyncio.create_task(handle_timeout(pad_code_str))
                    operations[pad_code_str] = task
                    print("全局超时任务开启成功")
                    clash_install_result = await install_app(pad_code_list=[data["padCode"]],
                                                       app_url=clash_install_url)
                    print(f"Clash install result: {clash_install_result}")
                    script_install_result = await install_app(pad_code_list=[data["padCode"]],
                                                        app_url=script_install_url)
                    print(f"Script install result: {script_install_result}")
                    clash_task = asyncio.create_task(
                        check_task_status(clash_install_result["data"][0]["taskId"], "Clash"))
                    script_task = asyncio.create_task(
                        check_task_status(script_install_result["data"][0]["taskId"], "Script"))
                    try:
                        await asyncio.gather(clash_task, script_task)
                    except asyncio.CancelledError:
                        print(f"任务被取消: {data['padCode']}")
                        # 确保取消所有子任务
                        if not clash_task.done():
                            clash_task.cancel()
                        if not script_task.done():
                            script_task.cancel()
                else:
                    print(f'一键新机等待中 {data["taskStatus"]}')
        case _:
            print(f"其他接口回调: {data}")


async def check_task_status(task_id, task_type):
    TIMEOUT_SECONDS = 3 * 60
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            while True:
                result = await get_cloud_file_task_info([str(task_id)])
                print(f"{task_type} task {task_id}: {result}")
                if result["data"][0]["errorMsg"] == "应用安装成功":
                    if task_type.lower() == "script":
                        print(f'{task_type}安装成功')
                        app_install_result = await get_app_install_info([result["data"][0]["padCode"]], "Clash for Android")
                        if len(app_install_result["data"][0]["apps"]) == 2:
                            print("真安装成功")
                            root_result = await open_root(pad_code_list=[result["data"][0]["padCode"]], pkg_name=pkg_name)
                            print(root_result)
                            print("开始重启")
                            reboot_result = await reboot(pad_code_list=[result["data"][0]["padCode"]])
                            print(reboot_result)
                            break

                        elif len(app_install_result["data"][0]["apps"]) == 0:
                            print("假安装成功，重新安装")
                            clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                              app_url=clash_install_url)
                            print(clash_result)
                            script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                              app_url=script_install_url)
                            print(script_result)
                            await asyncio.sleep(10)

                        elif len(app_install_result["data"][0]["apps"]) == 1:
                            app_result = app_install_result["data"][0]["apps"]
                            print(f"安装成功一个:{app_result[0]}")
                            await install_app(pad_code_list=[result["data"][0]["padCode"]],app_url=clash_install_url)
                            await asyncio.sleep(10)




                    elif task_type.lower() == "clash":
                        print(f"{task_type}安装成功")
                        app_install_result = await get_app_install_info([result["data"][0]["padCode"]], "Clash for Android")
                        if len(app_install_result["data"][0]["apps"]) == 2:
                            print("真安装成功")
                            break
                        elif len(app_install_result["data"][0]["apps"]) == 0:
                            print("假安装成功，重新安装")
                            clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                              app_url=clash_install_url)
                            print(clash_result)
                            script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                              app_url=script_install_url)
                            print(script_result)
                            await asyncio.sleep(10)

                        elif len(app_install_result["data"][0]["apps"]) == 1:
                            app_result = app_install_result["data"][0]["apps"]
                            print(f"安装成功一个:{app_result[0]}")
                            await install_app(pad_code_list=[result["data"][0]["padCode"]],app_url=script_install_url)
                            await asyncio.sleep(10)

                elif result["data"][0]["errorMsg"] == "文件下载失败 请求被中断，请重试":
                    if task_type.lower() == "clash":
                        print("clash下载失败")
                        clash_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                          app_url=clash_install_url)
                        print(clash_result)
                    else:
                        print("脚本下载失败")
                        script_result = await install_app(pad_code_list=[result["data"][0]["padCode"]],
                                          app_url=script_install_url)
                        print(script_result)
                    await asyncio.sleep(10)

                elif result["data"][0]["errorMsg"] == "任务已超时，当前设备状态为离线状态。":
                    print("设备离线，停止安装")
                    break
                await asyncio.sleep(1)

    except asyncio.TimeoutError:
        print(f"{task_type} task {task_id}: Installation timed out after {TIMEOUT_SECONDS} seconds")
        try:
            pad_code = result["data"][0]["padCode"]
            async with lock:
                task = operations.get(pad_code)
                if task is not None:
                    task.cancel()
                    del operations[pad_code]
            replace_result = await replace_pad([pad_code], template_id=random.choice(temple_id_list))
            print(replace_result)
            print("因为长时间安装不上，已移除任务")
        except (NameError, KeyError, IndexError) as e:
            print(f"无法处理超时：{e}，任务ID：{task_id}")
        return



class ProxyCountry(BaseModel):
    country: str
    code: str
    proxy_url: str
    time_zone: str
    language: str
    latitude: float
    longitude: float

class ProxyResponse(BaseModel):
    proxy: str
    country: str
    code: str
    time_zone: str
    language: str
    latitude: float
    longitude: float

class ProxyRequest(BaseModel):
    country_code: str

@app.get("/proxy", response_model=ProxyResponse)
async def get_proxy():
    """获取当前使用的代理信息"""
    return {
        "proxy": proxy_url,
        "country": current_proxy["country"],
        "code": current_proxy["code"],
        "time_zone": current_proxy["time_zone"],
        "language": current_proxy["language"],
        "latitude": current_proxy["latitude"],
        "longitude": current_proxy["longitude"]
    }

@app.get("/proxy/countries", response_model=List[ProxyCountry])
async def get_proxy_countries():
    """获取所有可用的代理国家列表"""
    # 如果代理国家列表为空，尝试加载
    if not proxy_countries:
        load_proxy_countries()
    return proxy_countries

@app.post("/proxy/set", response_model=ProxyResponse)
async def set_proxy(proxy_request: ProxyRequest):
    """根据国家代码设置代理"""
    global proxy_url, time_zone, latitude, longitude, current_proxy
    
    # 如果代理国家列表为空，尝试加载
    if not proxy_countries:
        load_proxy_countries()
    
    # 查找指定国家代码的代理信息
    found = False
    for country in proxy_countries:
        if country["code"].lower() == proxy_request.country_code.lower():
            current_proxy = country
            proxy_url = country["proxy_url"]
            time_zone = country["time_zone"]
            latitude = country["latitude"]
            longitude = country["longitude"]
            found = True
            break
    
    if not found:
        raise HTTPException(status_code=404, detail=f"未找到国家代码为 {proxy_request.country_code} 的代理信息")
    
    return {
        "proxy": proxy_url,
        "country": current_proxy["country"],
        "code": current_proxy["code"],
        "time_zone": current_proxy["time_zone"],
        "language": current_proxy["language"],
        "latitude": current_proxy["latitude"],
        "longitude": current_proxy["longitude"]
    }


@app.get("/")
async def index(data):
    print(data)
    return {"status": "ok"}


async def startup():
    # 加载代理国家列表
    load_proxy_countries()
    
    # 一键新机
    result = await replace_pad(pad_code_list, template_id=random.choice(temple_id_list))
    print(result)
    
    # 创建数据库表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(startup())
    uvicorn.run("main:app", host="0.0.0.0", port=5000)


