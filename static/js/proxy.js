let allProxyData = [];
let filteredProxyData = [];

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus().then(() => {
        loadProxyData();
        setupEventListeners();
    });
});

// 设置事件监听器
function setupEventListeners() {
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
    document.getElementById('searchInput').addEventListener('keyup', debounce(applyFilters, 300));
    document.getElementById('countryFilter').addEventListener('change', applyFilters);
    document.getElementById('languageFilter').addEventListener('change', applyFilters);
}

// 认证检查
async function checkAuthStatus() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login';
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
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('认证检查失败:', error);
        window.location.href = '/login';
    }
}

// 获取认证头
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// 加载代理数据
async function loadProxyData() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshIcon = document.getElementById('refreshIcon');
    const loadingOverlay = document.getElementById('loadingOverlay');

    try {
        // 设置加载状态
        refreshBtn.disabled = true;
        refreshIcon.classList.add('loading-spinner');
        loadingOverlay.style.display = 'flex';
        hideError();

        const response = await fetch('/proxy-collection', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP错误! 状态码: ${response.status}`);
        }

        allProxyData = await response.json();
        filteredProxyData = [...allProxyData];

        updateStatistics();
        updateFilterOptions();
        renderProxyTable();

    } catch (error) {
        console.error('加载代理数据失败:', error);
        showError('加载代理数据失败: ' + error.message);
    } finally {
        // 恢复状态
        refreshBtn.disabled = false;
        refreshIcon.classList.remove('loading-spinner');
        loadingOverlay.style.display = 'none';
    }
}

// 更新统计信息
function updateStatistics() {
    const statsCards = document.getElementById('statsCards');

    if (allProxyData.length === 0) {
        statsCards.innerHTML = '';
        return;
    }

    const uniqueCountries = new Set(allProxyData.map(p => p.country).filter(c => c)).size;
    const uniqueLanguages = new Set(allProxyData.map(p => p.language).filter(l => l)).size;
    const uniqueTimezones = new Set(allProxyData.map(p => p.time_zone).filter(t => t)).size;
    const avgLatitude = allProxyData.filter(p => p.latitude).reduce((sum, p) => sum + p.latitude, 0) / allProxyData.filter(p => p.latitude).length || 0;

    statsCards.innerHTML = `
            <div class="stat-card">
                <h3>${allProxyData.length}</h3>
                <p>代理记录总数</p>
            </div>
            <div class="stat-card">
                <h3>${uniqueCountries}</h3>
                <p>不同国家数量</p>
            </div>
            <div class="stat-card">
                <h3>${uniqueLanguages}</h3>
                <p>不同语言数量</p>
            </div>
            <div class="stat-card">
                <h3>${uniqueTimezones}</h3>
                <p>不同时区数量</p>
            </div>
        `;
}

// 更新筛选选项
function updateFilterOptions() {
    const countryFilter = document.getElementById('countryFilter');
    const languageFilter = document.getElementById('languageFilter');

    // 获取唯一的国家
    const countries = [...new Set(allProxyData.map(p => p.country).filter(c => c))].sort();
    countryFilter.innerHTML = '<option value="">所有国家</option>';
    countries.forEach(country => {
        const option = document.createElement('option');
        option.value = country;
        option.textContent = country;
        countryFilter.appendChild(option);
    });

    // 获取唯一的语言
    const languages = [...new Set(allProxyData.map(p => p.language).filter(l => l))].sort();
    languageFilter.innerHTML = '<option value="">所有语言</option>';
    languages.forEach(language => {
        const option = document.createElement('option');
        option.value = language;
        option.textContent = language;
        languageFilter.appendChild(option);
    });
}

// 渲染代理表格
function renderProxyTable() {
    const tableBody = document.getElementById('proxyTableBody');
    const emptyState = document.getElementById('emptyState');

    if (filteredProxyData.length === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    const rows = filteredProxyData.map(proxy => {
        const coordinates = proxy.latitude && proxy.longitude ?
            `${proxy.latitude.toFixed(4)}, ${proxy.longitude.toFixed(4)}` :
            '未设置';

        return `
                <tr>
                    <td>${proxy.id || ''}</td>
                    <td>${proxy.country || '未设置'}</td>
                    <td>${proxy.code || '未设置'}</td>
                    <td>${proxy.android_version || '未知'}</td>
                    <td>${proxy.temple_id || '未设置'}</td>
                    <td class="coordinates">${proxy.latitude ? proxy.latitude.toFixed(4) : '未设置'}</td>
                    <td class="coordinates">${proxy.longitude ? proxy.longitude.toFixed(4) : '未设置'}</td>
                    <td class="proxy-url" title="${proxy.proxy || ''}">${proxy.proxy || '未设置'}</td>
                    <td>${proxy.language || '未设置'}</td>
                    <td>${proxy.time_zone || '未设置'}</td>
                    <td>${formatDateTime(proxy.created_at)}</td>
                    <td>
                        <button class="delete-btn" onclick="deleteProxy(${proxy.id})">删除</button>
                    </td>
                </tr>
            `;
    }).join('');

    tableBody.innerHTML = rows;
}

// 应用筛选
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const countryFilter = document.getElementById('countryFilter').value;
    const languageFilter = document.getElementById('languageFilter').value;

    filteredProxyData = allProxyData.filter(proxy => {
        const matchesSearch = !searchTerm ||
            (proxy.country && proxy.country.toLowerCase().includes(searchTerm)) ||
            (proxy.code && proxy.code.toLowerCase().includes(searchTerm)) ||
            (proxy.proxy && proxy.proxy.toLowerCase().includes(searchTerm));

        const matchesCountry = !countryFilter || proxy.country === countryFilter;
        const matchesLanguage = !languageFilter || proxy.language === languageFilter;

        return matchesSearch && matchesCountry && matchesLanguage;
    });

    renderProxyTable();
}

// 重置筛选
function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('countryFilter').value = '';
    document.getElementById('languageFilter').value = '';
    filteredProxyData = [...allProxyData];
    renderProxyTable();
}

// 删除代理记录
async function deleteProxy(proxyId) {
    if (!confirm('确定要删除这条代理记录吗？此操作无法撤销。')) {
        return;
    }

    try {
        const response = await fetch(`/proxy-collection/${proxyId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`删除失败: ${response.status}`);
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        loadProxyData();

    } catch (error) {
        console.error('删除代理记录失败:', error);
        showError('删除失败: ' + error.message);
    }
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '未知';
    try {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    } catch (e) {
        return dateString;
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 显示错误信息
function showError(message) {
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorElement.style.display = 'flex';
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

// 隐藏错误信息
function hideError() {
    const errorElement = document.getElementById('error');
    errorElement.style.display = 'none';
}

// 显示成功信息
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: var(--success-color);
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 1000;
            max-width: 300px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        `;
    successDiv.textContent = message;
    document.body.appendChild(successDiv);

    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.parentNode.removeChild(successDiv);
        }
    }, 3000);
}