import datetime
from typing import cast

from fastapi import HTTPException, APIRouter, Query
from loguru import logger
from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError
from starlette.responses import HTMLResponse

from app.curd.proxy import update_proxies
from app.curd.status import update_cloud_status, get_proxy_status
from app.models.accounts import (
    AccountResponse,
    AccountCreate,
    AccountUpdate,
    ForwardRequest,
    SecondaryEmail,
)
from app.models.proxy import ProxyResponse
from app.services.database import SessionLocal, Account

router = APIRouter()


@router.post("/create_accounts", response_model=AccountResponse)
async def create_account(account: AccountCreate) -> AccountResponse:
    async with SessionLocal() as db:
        if account.account is None or account.password is None:
            raise HTTPException(status_code=404, detail="帐户或密码为空")
        try:
            db_account = Account(
                account=account.account,
                password=account.password,
                created_at=datetime.datetime.now(),
            )
            if account.pad_code is not None:
                current_proxy: ProxyResponse = await get_proxy_status(account.pad_code)
                db_account.code = current_proxy.code
                db_account.proxy_platform = current_proxy.proxy_platform
            db.add(db_account)
            await db.commit()
            await db.refresh(db_account)
            logger.success(f"{account.pad_code}: 账号上传成功")
            await update_proxies(pade_code=account.pad_code)
            await update_cloud_status(pad_code=account.pad_code, num_of_success=1)
            return db_account
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="账号已存在")


@router.get("/accounts", response_model=list[AccountResponse])
async def get_accounts() -> list[AccountResponse]:
    async with SessionLocal() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(Account).order_by(cast(ColumnElement[bool], Account.id))
        )
        accounts = result.scalars().all()
        return accounts


## 获取之后就会删除之前那条数据
@router.get("/account/unique", response_model=AccountResponse)
async def get_unique_account(
    delete: bool = Query(
        default=False, description="是否删除账号，False则将status改为1"
    ),
) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select

        stmt = (
            select(Account)
            .filter(cast(ColumnElement[bool], Account.status == 0))
            .with_for_update()
        )
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
            is_boned_secondary_email=account.is_boned_secondary_email,
            proxy_platform=account.proxy_platform,
        )

        if delete:
            await db.delete(account)
            logger.info(f"账号 {account.account} 已被删除")
        else:
            account.status = 1
        await db.commit()
        return account_data


@router.get("/accounts/details", response_class=HTMLResponse)
async def get_single_account_details(
    delete: bool = Query(
        default=False, description="是否删除账号，False则将status改为1"
    ),
):
    async with SessionLocal() as db:
        from sqlalchemy import select

        stmt = (
            select(Account)
            .filter(cast(ColumnElement[bool], Account.status == 0))
            .with_for_update()
        )
        result = await db.execute(stmt)
        account = result.scalars().first()
        if not account:
            # 如果账号不存在，返回404页面
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>账号不存在</title>
                    <style>
                        body {
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            margin: 0;
                            padding: 20px;
                            background-color: #f5f5f5;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                        }
                        .error-container {
                            background: white;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            padding: 40px;
                            text-align: center;
                            max-width: 500px;
                        }
                        .error-icon {
                            font-size: 4rem;
                            margin-bottom: 20px;
                        }
                        .back-btn {
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            color: white;
                            border: none;
                            border-radius: 25px;
                            padding: 10px 20px;
                            font-size: 1rem;
                            cursor: pointer;
                            margin-top: 20px;
                        }
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="error-icon">❌</div>
                        <h2>没有可用账号</h2>
                    </div>
                </body>
                </html>
                """,
                status_code=404,
            )

        # 构建HTML内容 - 单个账号展示
        html_content = """
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Google账号详情</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                .container {
                    max-width: 900px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    position: relative;
                }
                .header h1 {
                    margin: 0;
                    font-size: 2rem;
                }
                .back-btn {
                    position: absolute;
                    left: 20px;
                    top: 50%;
                    transform: translateY(-50%);
                    background: rgba(255,255,255,0.2);
                    color: white;
                    border: none;
                    border-radius: 25px;
                    padding: 8px 15px;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                .back-btn:hover {
                    background: rgba(255,255,255,0.3);
                }
                .account-container {
                    padding: 30px;
                }
                .account-card {
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }
                .account-info {
                    padding: 25px;
                    background: #fff;
                }
                .info-section {
                    margin-bottom: 25px;
                }
                .section-title {
                    font-size: 1.2rem;
                    font-weight: 600;
                    color: #495057;
                    margin-bottom: 15px;
                    border-bottom: 2px solid #667eea;
                    padding-bottom: 5px;
                }
                .info-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 15px;
                    margin-bottom: 15px;
                }
                .field-group {
                    display: flex;
                    flex-direction: column;
                }
                .field-label {
                    font-size: 0.9rem;
                    color: #6c757d;
                    margin-bottom: 5px;
                    font-weight: 500;
                }
                .field-value {
                    font-size: 1rem;
                    color: #495057;
                    word-break: break-all;
                    background: #f8f9fa;
                    padding: 10px 12px;
                    border-radius: 6px;
                    border: 1px solid #e9ecef;
                    min-height: 20px;
                }
                .image-container {
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                }
                .account-image {
                    max-width: 100%;
                    max-height: 500px;
                    width: auto;
                    height: auto;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                .account-image:hover {
                    transform: scale(1.02);
                }
                .no-image {
                    color: #6c757d;
                    font-style: italic;
                    padding: 40px;
                    font-size: 1.1rem;
                }
                .status-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-align: center;
                    display: inline-block;
                }
                .status-0 { background: #d4edda; color: #155724; }
                .status-1 { background: #fff3cd; color: #856404; }
                .status-2 { background: #f8d7da; color: #721c24; }
                .type-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-align: center;
                    background: #e2e3e5;
                    color: #495057;
                    display: inline-block;
                }
                .secondary-badge {
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 0.9rem;
                    font-weight: 500;
                    text-align: center;
                    display: inline-block;
                }
                .has-secondary { background: #d1ecf1; color: #0c5460; }
                .no-secondary { background: #f8d7da; color: #721c24; }
                
                /* 图片放大模态框样式 */
                .modal {
                    display: none;
                    position: fixed;
                    z-index: 1000;
                    left: 0;
                    top: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(0,0,0,0.9);
                    animation: fadeIn 0.3s;
                }
                
                .modal-content {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    max-width: 90vw;  /* 添加这行 */
                    max-height: 90vh; /* 添加这行 */
                    width: auto;
                    height: auto;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                    cursor: grab;
                    transition: transform 0.1s ease-out;
                    user-select: none;
                }
                
                .modal-content:active {
                    cursor: grabbing;
                }
                
                .close {
                    position: absolute;
                    top: 20px;
                    right: 35px;
                    color: #f1f1f1;
                    font-size: 40px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: color 0.3s;
                    z-index: 1001;
                }
                
                .close:hover,
                .close:focus {
                    color: #bbb;
                }
                
                /* 缩放控制按钮 */
                .zoom-controls {
                    position: absolute;
                    top: 20px;
                    left: 20px;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    z-index: 1001;
                }
                
                .zoom-btn {
                    background: rgba(0,0,0,0.6);
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    font-size: 18px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: background 0.2s;
                }
                
                .zoom-btn:hover {
                    background: rgba(0,0,0,0.8);
                }
                
                /* 缩放信息显示 */
                .zoom-info {
                    position: absolute;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: rgba(0,0,0,0.6);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 14px;
                    z-index: 1001;
                }
                
                @keyframes fadeIn {
                    from {opacity: 0;}
                    to {opacity: 1;}
                }
                
                .action-buttons {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    display: flex;
                    gap: 10px;
                }
                
                .action-btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 50px;
                    padding: 15px 20px;
                    font-size: 0.9rem;
                    cursor: pointer;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    transition: transform 0.2s;
                }
                
                .action-btn:hover {
                    transform: scale(1.05);
                }
                
                @media (max-width: 768px) {
                    .info-grid {
                        grid-template-columns: 1fr;
                    }
                    .action-buttons {
                        flex-direction: column;
                    }
                    .zoom-controls {
                        right: 20px;
                        left: auto;
                        flex-direction: row;
                        top: 70px;
                    }
                }
                
                .button-field {
                    display: flex;
                    gap: 8px;
                    padding: 8px;
                    background: transparent;
                    border: none;
                }
                
                .inline-btn {
                    border: none;
                    border-radius: 20px;
                    padding: 8px 16px;
                    font-size: 0.8rem;
                    cursor: pointer;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                    transition: all 0.2s ease;
                    color: white;
                    font-weight: 500;
                    flex: 1;
                }
                
                .inline-btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
                }
                
                .btn-warning {
                    background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
                }
            </style>
        </head>
        <body>
        """
        # 辅助邮箱状态
        secondary_class = (
            "has-secondary" if account.is_boned_secondary_email else "no-secondary"
        )
        secondary_text = "是" if account.is_boned_secondary_email else "否"

        # 格式化创建时间
        created_time = (
            account.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if account.created_at
            else "未知"
        )

        html_content += f"""
                <div class="account-container">
                    <div class="account-card">
                        <div class="account-info">
                            
                            <!-- 基本信息 -->
                            <div class="info-section">
                                <div class="info-grid">
                                    <div class="field-group">
                                        <div class="field-label">邮箱账号</div>
                                        <div class="field-value">{account.account or "未设置"}</div>
                                    </div>
                                    <div class="field-group">
                                        <div class="field-label">密码</div>
                                        <div class="field-value">{account.password or "未设置"}</div>
                                    </div>
                                    <div class="field-group">
                                        <div class="field-label">创建时间</div>
                                        <div class="field-value">{created_time}</div>
                                    </div>
                                    <div class="field-value button-field">
                                         <button class="inline-btn btn-warning" onclick="getCaptcha('{account.for_email}', '{account.for_password}')">获取验证码</button>
                                         <button class="inline-btn btn-warning" id="x-xx2200">刷新</button>
                                         
                                                 <div class="field-value button-field" id="show_captcha">
                                                 </div>
                                    </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 转发邮箱信息 -->
                            <div class="info-section">
                                <div class="info-grid">
                                    <div class="field-group">
                                        <div class="field-label">转发邮箱</div>
                                        <div class="field-value">{account.for_email or "未设置"}</div>
                                    </div>
                                    <div class="field-group">
                                        <div class="field-label">转发密码</div>
                                        <div class="field-value">{account.for_password or "未设置"}</div>
                                    </div>
                                    <div class="field-group">
                                        <div class="field-label">是否有辅助邮箱</div>
                                        <div class="secondary-badge {secondary_class}">{secondary_text}</div>
                                    </div>
                                </div>
                            </div>
                            <!-- 账号截图 -->
                            <div class="info-section">
                                <div class="image-container" style="display: flex;">
        """

        if account.image_base64:
            html_content += f"""
            <img src="data:image/jpeg;base64,{account.image_base64}" alt="账号截图" class="account-image">
            """
        else:
            html_content += """
                                    <div class="no-image">📷 暂无截图</div>
            """

        html_content += f"""
        <iframe src="http://foailbox.com:8888/email/message?email={account.for_email}&password={account.for_password}" style="width: 100%"></iframe>
"""
        html_content += """
                                </div>
                            </div>
                            
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 图片放大模态框 -->
            <div id="imageModal" class="modal">
                <div class="zoom-controls">
                    <button class="zoom-btn" onclick="zoomIn()" title="放大">+</button>
                    <button class="zoom-btn" onclick="zoomOut()" title="缩小">−</button>
                    <button class="zoom-btn" onclick="resetZoom()" title="重置">⟲</button>
                </div>
                <span class="close">&times;</span>
                <img class="modal-content" id="modalImage">
                <div class="zoom-info" id="zoomInfo">100%</div>
            </div>
            
            <script>
                // 图片缩放相关变量
                let currentZoom = 1;
                let minZoom = 0.1;
                let maxZoom = 5;
                let isDragging = false;
                let startX, startY, startLeft, startTop;
                let currentX = 0, currentY = 0;
                let initialX = 0, initialY = 0;
                
                // 图片点击放大功能
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImage');
                const closeBtn = document.getElementsByClassName('close')[0];
                const zoomInfo = document.getElementById('zoomInfo');
                
                // 为图片添加点击事件
                document.querySelectorAll('.account-image').forEach(img => {
                    img.onclick = function() {
                        modal.style.display = 'block';
                        modalImg.src = this.src;
                        resetZoom();
                        centerImage();
                    };
                    
                    // 图片加载错误处理
                    img.onerror = function() {
                        this.style.display = 'none';
                        this.parentElement.innerHTML = '<div class="no-image">📷 图片加载失败</div>';
                    };
                });
                
                // 关闭模态框
                if (closeBtn) {
                    closeBtn.onclick = function() {
                        modal.style.display = 'none';
                    };
                }
                
                // 点击模态框背景关闭
                modal.onclick = function(event) {
                    if (event.target === modal) {
                        modal.style.display = 'none';
                    }
                };
                
                // ESC键关闭模态框
                document.addEventListener('keydown', function(event) {
                    if (event.key === 'Escape' && modal.style.display === 'block') {
                        modal.style.display = 'none';
                    }
                });
                
                // 缩放功能
                function zoomIn() {
                    if (currentZoom < maxZoom) {
                        currentZoom = Math.min(currentZoom * 1.2, maxZoom);
                        updateZoom();
                    }
                }
                
                function zoomOut() {
                    if (currentZoom > minZoom) {
                        currentZoom = Math.max(currentZoom / 1.2, minZoom);
                        updateZoom();
                    }
                }
                
                function resetZoom() {
                    currentZoom = 1;
                    updateZoom();
                    centerImage();
                }
                
                function updateZoom() {
                    modalImg.style.transform = `translate(calc(-50% + ${currentX}px), calc(-50% + ${currentY}px)) scale(${currentZoom})`;
                    zoomInfo.textContent = Math.round(currentZoom * 100) + '%';
                }
                                
                function centerImage() {
                    currentX = 0;
                    currentY = 0;
                    modalImg.style.left = '50%';
                    modalImg.style.top = '50%';
                    modalImg.style.transform = 'translate(-50%, -50%)';
                }
                
                // 滚轮缩放
                modalImg.addEventListener('wheel', function(e) {
                    e.preventDefault();
                    
                    if (e.deltaY < 0) {
                        zoomIn();
                    } else {
                        zoomOut();
                    }
                });
                
                // 双击重置缩放
                modalImg.addEventListener('dblclick', function(e) {
                    e.preventDefault();
                    resetZoom();
                });
                
                // 拖拽功能
                modalImg.addEventListener('mousedown', function(e) {
                    if (currentZoom > 1) {
                        isDragging = true;
                        initialX = e.clientX - currentX;
                        initialY = e.clientY - currentY;
                        modalImg.style.cursor = 'grabbing';
                        e.preventDefault();
                    }
                });
                                
                document.addEventListener('mousemove', function(e) {
                    if (!isDragging) return;
                    
                    e.preventDefault();
                    currentX = e.clientX - initialX;
                    currentY = e.clientY - initialY;
                    
                    modalImg.style.transform = `translate(calc(-50% + ${currentX}px), calc(-50% + ${currentY}px)) scale(${currentZoom})`;
                });
                
                document.addEventListener('mouseup', function() {
                    if (isDragging) {
                        isDragging = false;
                        modalImg.style.cursor = 'grab';
                    }
                });
                
                // 触摸事件支持（移动端）
                let lastTouchDistance = 0;
                
                modalImg.addEventListener('touchstart', function(e) {
                    if (e.touches.length === 2) {
                        lastTouchDistance = Math.hypot(
                            e.touches[0].pageX - e.touches[1].pageX,
                            e.touches[0].pageY - e.touches[1].pageY
                        );
                    }
                }, { passive: true });
                
                modalImg.addEventListener('touchmove', function(e) {
                    if (e.touches.length === 2) {
                        e.preventDefault();
                        
                        const touchDistance = Math.hypot(
                            e.touches[0].pageX - e.touches[1].pageX,
                            e.touches[0].pageY - e.touches[1].pageY
                        );
                        
                        if (lastTouchDistance > 0) {
                            const scale = touchDistance / lastTouchDistance;
                            currentZoom = Math.max(minZoom, Math.min(maxZoom, currentZoom * scale));
                            updateZoom();
                        }
                        
                        lastTouchDistance = touchDistance;
                    }
                });
                
                async function getCaptcha(email, password) {
                    const showCaptchaDiv = document.querySelector('#show_captcha');
                    const url = `http://foailbox.com:8888/api/email/code?email=${email}&password=${password}&service=6024`;
                    
                    try {
                        showCaptchaDiv.innerText = '正在获取验证码...';
                        
                        const response = await fetch(url);
                        const data = await response.json();
                        
                        if (data && data.data) {
                            showCaptchaDiv.innerText = JSON.stringify(data['data']);
                        } else {
                            showCaptchaDiv.innerText = JSON.stringify(data['msg']);
                        }
                        console.log('验证码数据：', data);
                    } catch (error) {
                        console.error('获取验证码出错：', error);
                        showCaptchaDiv.innerText = '获取验证码失败：网络错误';
                    }
                }
                
                var x_refresh = document.querySelector('#x-xx2200');
                console.log(x_refresh);
                x_refresh.onclick = function() {
                    var iframe = document.querySelector('iframe');
                    iframe.src = iframe.src;
                }
            </script>
        </body>
        </html>
        """
        if delete:
            await db.delete(account)
            logger.info(f"账号 {account.account} 已删除")
        else:
            account.status = 1
        await db.commit()
        return HTMLResponse(content=html_content)


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select

        stmt = select(Account).filter(
            cast(ColumnElement[bool], Account.id == account_id)
        )
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail=f"{account_id}: 账号不存在")
        return account


@router.post("/update_forward", response_model=AccountResponse)
async def update_forward(forward: ForwardRequest) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select

        stmt = select(Account).filter(
            cast(ColumnElement[bool], Account.account == forward.account)
        )
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(
                status_code=404, detail=f"{forward.account}: 账号不存在"
            )
        account.for_email = forward.for_email
        account.for_password = forward.for_password
        account.image_base64 = forward.image_base64
        account.status = 0
        account.is_forward_email = True
        await db.commit()
        await db.refresh(account)
        await update_cloud_status(pad_code=forward.pad_code, forward_num=1)
        return account


@router.post("/update_secondary_mail", response_model=AccountResponse)
async def update_secondary_mail(secondary_mail: SecondaryEmail) -> AccountResponse:
    async with SessionLocal() as db:
        from sqlalchemy import select

        stmt = select(Account).filter(
            cast(ColumnElement[bool], Account.account == secondary_mail.account)
        )
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(
                status_code=404, detail=f"{secondary_mail.account}:账号不存在"
            )
        account.is_boned_secondary_email = secondary_mail.is_boned_secondary_email
        account.for_email = secondary_mail.for_email
        account.for_password = secondary_mail.for_password
        await db.commit()
        await db.refresh(account)
        await update_cloud_status(
            pad_code=secondary_mail.pad_code, secondary_email_num=1
        )
        return account


@router.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int, account_update: AccountUpdate
) -> AccountResponse:
    async with SessionLocal() as db:
        try:
            from sqlalchemy import select

            stmt = select(Account).filter(
                cast(ColumnElement[bool], Account.id == account_id)
            )
            result = await db.execute(stmt)
            db_account = result.scalars().first()
            if db_account is None:
                raise HTTPException(status_code=404, detail=f"{account_id}: 账号不存在")

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

        stmt = select(Account).filter(
            cast(ColumnElement[bool], Account.id == account_id)
        )
        result = await db.execute(stmt)
        account = result.scalars().first()
        if account is None:
            raise HTTPException(status_code=404, detail=f"{account_id}:账号不存在")

        await db.execute(
            delete(Account).filter(cast(ColumnElement[bool], Account.id == account_id))
        )
        await db.commit()
        logger.success(f"账号 {account_id} 删除成功")
        return {"detail": "账号删除成功"}
