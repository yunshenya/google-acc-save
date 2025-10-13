document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    const loginBtn = document.getElementById('loginBtn');
    const loginText = document.getElementById('loginText');
    const errorMessage = document.getElementById('errorMessage');

    // 检查是否已经登录
    checkAuthStatus().then(r => {});

    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        if (!username || !password) {
            showError('请填写用户名和密码');
            return;
        }

        try {
            setLoading(true);
            hideError();

            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({username, password})
            });

            const data = await response.json();

            if (response.ok) {
                // 保存token和过期信息
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('token_expires_at', data.expires_at);
                localStorage.setItem('token_expires_in', data.expires_in);

                // 设置"记住我"标记
                // 在登录成功后
                const rememberMe = document.getElementById('rememberMe').checked;
                localStorage.setItem('remember_me', rememberMe ? 'true' : 'false');

                console.log('登录成功，Token有效期：', data.expires_in / 3600, '小时');

                // 跳转到主页
                window.location.href = '/';
            } else {
                showError(data.detail || '登录失败');
            }
        } catch (error) {
            showError('网络错误，请稍后重试');
            console.error('登录错误:', error);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        loginBtn.disabled = isLoading;
        if (isLoading) {
            loginText.innerHTML = '<span class="loading"></span>登录中...';
        } else {
            loginText.innerHTML = '登录';
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    function hideError() {
        errorMessage.style.display = 'none';
    }

    async function checkAuthStatus() {
        const token = localStorage.getItem('access_token');
        const rememberMe = localStorage.getItem('remember_me');

        if (token && rememberMe === 'true') {
            try {
                const response = await fetch('/auth/verify', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    // 已经登录，跳转到主页
                    window.location.href = '/';
                } else {
                    // Token过期或无效，清除本地存储
                    clearAuthData();
                }
            } catch (error) {
                // Token 无效，清除本地存储
                clearAuthData();
            }
        }
    }

    function clearAuthData() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('token_expires_at');
        localStorage.removeItem('token_expires_in');
        localStorage.removeItem('remember_me');
    }
});