// Token自动刷新管理
let tokenRefreshTimer = null;

async function checkAuthStatus() {
    const token = localStorage.getItem('access_token');
    const rememberMe = localStorage.getItem('remember_me');

    if (!token) {
        redirectToLogin();
        return;
    }

    try {
        const response = await fetch('/auth/verify', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            // Token无效或过期
            if (rememberMe === 'true') {
                // 尝试刷新token
                const refreshed = await refreshToken();
                if (!refreshed) {
                    redirectToLogin();
                }
            } else {
                redirectToLogin();
            }
        } else {
            // Token有效，设置自动刷新
            setupTokenRefresh();
        }
    } catch (error) {
        console.error('认证检查失败:', error);
        redirectToLogin();
    }
}

// 刷新Token
async function refreshToken() {
    const token = localStorage.getItem('access_token');

    if (!token) {
        return false;
    }

    try {
        const response = await fetch('/auth/refresh', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();

            // 更新token
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('token_expires_at', data.expires_at);
            localStorage.setItem('token_expires_in', data.expires_in);

            console.log('Token已自动刷新，新Token有效期：', data.expires_in / 3600, '小时');

            // 重新设置自动刷新
            setupTokenRefresh();

            return true;
        } else {
            return false;
        }
    } catch (error) {
        console.error('Token刷新失败:', error);
        return false;
    }
}

// 设置Token自动刷新
function setupTokenRefresh() {
    // 清除现有定时器
    if (tokenRefreshTimer) {
        clearTimeout(tokenRefreshTimer);
    }

    const expiresIn = parseInt(localStorage.getItem('token_expires_in') || '0');

    if (expiresIn > 0) {
        // 在过期前1小时自动刷新，如果小于1小时则在剩余时间的一半时刷新
        const refreshTime = expiresIn > 3600
            ? (expiresIn - 3600) * 1000  // 提前1小时
            : (expiresIn / 2) * 1000;     // 剩余时间的一半

        console.log(`Token将在 ${refreshTime / 1000 / 60} 分钟后自动刷新`);

        tokenRefreshTimer = setTimeout(async () => {
            console.log('开始自动刷新Token...');
            const refreshed = await refreshToken();
            if (!refreshed) {
                console.error('自动刷新Token失败');
                showTokenExpiredNotification();
            }
        }, refreshTime);
    }
}

// 显示Token即将过期提醒
function showTokenExpiredNotification() {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #f39c12;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        max-width: 350px;
    `;
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="font-size: 18px;">⚠️</span>
            <strong>登录即将过期</strong>
        </div>
        <div style="font-size: 14px; opacity: 0.9; margin-bottom: 10px;">
            您的登录状态即将过期，请重新登录以继续使用
        </div>
        <button onclick="window.location.href='/login'" 
                style="background: white; color: #f39c12; border: none; 
                       padding: 8px 16px; border-radius: 4px; cursor: pointer; 
                       font-weight: 600; width: 100%;">
            立即登录
        </button>
    `;
    document.body.appendChild(notification);
}

// 获取认证头
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

function redirectToLogin() {
    // 清除认证数据
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_expires_at');
    localStorage.removeItem('token_expires_in');
    // 不清除remember_me，以便用户下次登录时保持记住状态

    window.location.href = '/login';
}

function hideTableContent(tabName) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // 移除所有按钮的活跃状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 显示选中的标签内容
    const targetTab = document.getElementById(tabName + 'Tab');
    if (targetTab) {
        targetTab.classList.add('active');
    }

    if (typeof currentTab !== 'undefined') {
        currentTab = tabName;
    }
}

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    if (tokenRefreshTimer) {
        clearTimeout(tokenRefreshTimer);
    }
});