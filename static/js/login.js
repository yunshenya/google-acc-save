document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');
    const loginBtn = document.getElementById('loginBtn');
    const loginText = document.getElementById('loginText');
    const errorMessage = document.getElementById('errorMessage');

    // 检查是否已经登录
    checkAuthStatus();

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
                // 保存token
                localStorage.setItem('access_token', data.access_token);

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
        if (token) {
            try {
                const response = await fetch('/auth/verify', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    // 已经登录，跳转到主页
                    window.location.href = '/';
                }
            } catch (error) {
                // Token 无效，清除本地存储
                localStorage.removeItem('access_token');
            }
        }
    }
});