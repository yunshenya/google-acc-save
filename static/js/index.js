document.addEventListener('DOMContentLoaded', function() {
    // 认证检查
    checkAuthStatus();

    // DOM元素 - 原有元素
    const fetchAllBtn = document.getElementById('fetchAll');
    const fetchPageBtn = document.getElementById('fetchPage');
    const fetchSingleBtn = document.getElementById('fetchSingle');
    const fetchSingleLockBtn = document.getElementById('fetchSingleLock');
    const accountIdInput = document.getElementById('accountId');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const typeFilter = document.getElementById('typeFilter');
    const applyFiltersBtn = document.getElementById('applyFilters');
    const resetFiltersBtn = document.getElementById('resetFilters');
    const maskPasswordsCheck = document.getElementById('maskPasswords');
    const exportCSVBtn = document.getElementById('exportCSV');
    const accountsBody = document.getElementById('accountsBody');
    const loadingElement = document.getElementById('loading');
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');
    const pagination = document.getElementById('pagination');
    const firstPageBtn = document.getElementById('firstPage');
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');
    const lastPageBtn = document.getElementById('lastPage');
    const pageNumbers = document.getElementById('pageNumbers');
    const paginationInfo = document.getElementById('paginationInfo');
    const progressBar = document.getElementById('progressBar');

    // DOM元素 - 新增元素
    const statusTableBody = document.getElementById('statusTableBody');
    const toggleViewBtn = document.getElementById('toggleView');
    const accountsSection = document.getElementById('accountsSection');
    const statusSection = document.getElementById('statusSection');
    const logoutBtn = document.getElementById('logoutBtn');
    const refreshAllStatusBtn = document.getElementById('refreshAllStatus');
    const statusEmptyState = document.getElementById('statusEmptyState');

    // 状态变量
    let allAccounts = [];
    let filteredAccounts = [];
    let currentPage = 1;
    const pageSize = 50;
    let totalPages = 0;
    let isFetching = false;
    let fetchMode = 'none'; // 'all', 'page', 'single'

    // 新增状态变量
    let currentView = 'accounts'; // 'accounts' or 'status'
    let statusUpdateInterval = null;

    // 初始化
    init();

    function init() {
        setupEventListeners();
        updateUI();
    }

    function setupEventListeners() {
        // 获取数据按钮
        fetchAllBtn && fetchAllBtn.addEventListener('click', fetchAllAccounts);
        fetchPageBtn && fetchPageBtn.addEventListener('click', fetchAccountsByPage);
        fetchSingleBtn && fetchSingleBtn.addEventListener('click', fetchSingleAccount);
        fetchSingleLockBtn && fetchSingleLockBtn.addEventListener('click', fetchSingleAccountLocked);

        // 分页控制
        firstPageBtn && firstPageBtn.addEventListener('click', () => goToPage(1));
        prevPageBtn && prevPageBtn.addEventListener('click', () => goToPage(currentPage - 1));
        nextPageBtn && nextPageBtn.addEventListener('click', () => goToPage(currentPage + 1));
        lastPageBtn && lastPageBtn.addEventListener('click', () => goToPage(totalPages));

        // 筛选和搜索
        applyFiltersBtn && applyFiltersBtn.addEventListener('click', applyFilters);
        resetFiltersBtn && resetFiltersBtn.addEventListener('click', resetFilters);
        searchInput && searchInput.addEventListener('keyup', debounce(applyFilters, 300));

        // 其他功能
        maskPasswordsCheck && maskPasswordsCheck.addEventListener('change', togglePasswordMask);
        exportCSVBtn && exportCSVBtn.addEventListener('click', exportToCSV);

        // 监听滚动事件实现无限滚动
        tableContainer && tableContainer.addEventListener('scroll', debounce(handleScroll, 200));

        // 新增事件监听器
        toggleViewBtn && toggleViewBtn.addEventListener('click', toggleView);
        logoutBtn && logoutBtn.addEventListener('click', logout);
        refreshAllStatusBtn && refreshAllStatusBtn.addEventListener('click', fetchCloudStatus);
    }

    // 认证相关函数
    function getAuthToken() {
        return localStorage.getItem('access_token');
    }

    function getAuthHeaders() {
        const token = getAuthToken();
        return token ? {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        } : {
            'Content-Type': 'application/json'
        };
    }

    async function checkAuthStatus() {
        const token = getAuthToken();
        if (!token) {
            redirectToLogin();
            return;
        }

        try {
            const response = await fetch('/auth/verify', {
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                redirectToLogin();
                return;
            }
        } catch (error) {
            console.error('认证检查失败:', error);
            redirectToLogin();
            return;
        }
    }

    function redirectToLogin() {
        window.location.href = '/login';
    }

    function logout() {
        localStorage.removeItem('access_token');
        redirectToLogin();
    }

    // 修改所有的 fetch 请求以包含认证头
    async function authenticatedFetch(url, options = {}) {
        const headers = getAuthHeaders();

        const response = await fetch(url, {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        });

        if (response.status === 401) {
            redirectToLogin();
            return;
        }

        return response;
    }

    // 防抖函数
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func.apply(context, args);
            }, wait);
        };
    }

    // 显示加载进度
    function updateProgress(progress) {
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    // 显示加载状态
    function showLoading() {
        isFetching = true;
        if (loadingElement) loadingElement.style.display = 'flex';
        if (errorElement) errorElement.style.display = 'none';
        updateUI();
    }

    // 隐藏加载状态
    function hideLoading() {
        isFetching = false;
        if (loadingElement) loadingElement.style.display = 'none';
        updateProgress(0);
        updateUI();
    }

    // 显示错误信息
    function showError(message) {
        if (errorMessage) errorMessage.textContent = message;
        if (errorElement) errorElement.style.display = 'flex';
        console.error(message);
    }

    // 更新UI状态
    function updateUI() {
        // 禁用/启用按钮
        if (fetchAllBtn) fetchAllBtn.disabled = isFetching;
        if (fetchPageBtn) fetchPageBtn.disabled = isFetching;
        if (fetchSingleBtn) fetchSingleBtn.disabled = isFetching || !accountIdInput?.value;
        if (fetchSingleLockBtn) fetchSingleLockBtn.disabled = isFetching || !accountIdInput?.value;
        if (applyFiltersBtn) applyFiltersBtn.disabled = isFetching;

        // 分页控制
        if (firstPageBtn) firstPageBtn.disabled = currentPage === 1 || isFetching;
        if (prevPageBtn) prevPageBtn.disabled = currentPage === 1 || isFetching;
        if (nextPageBtn) nextPageBtn.disabled = currentPage === totalPages || isFetching;
        if (lastPageBtn) lastPageBtn.disabled = currentPage === totalPages || isFetching;

        // 只有在分页模式下才显示分页控件
        if (pagination) {
            if (fetchMode === 'page' && filteredAccounts.length > 0) {
                pagination.style.display = 'flex';
                updatePaginationUI();
            } else {
                pagination.style.display = 'none';
            }
        }

        // 显示/隐藏空状态
        if (emptyState && currentView === 'accounts') {
            if (filteredAccounts.length === 0 && !isFetching) {
                emptyState.style.display = 'block';
            } else {
                emptyState.style.display = 'none';
            }
        }
    }

    // 更新分页UI
    function updatePaginationUI() {
        if (!pageNumbers) return;

        // 清空页码按钮
        pageNumbers.innerHTML = '';

        // 计算显示的页码范围
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        // 确保显示5个页码
        if (endPage - startPage < 4) {
            if (currentPage < 3) {
                endPage = Math.min(5, totalPages);
            } else {
                startPage = Math.max(1, totalPages - 4);
            }
        }

        // 添加页码按钮
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.textContent = i.toString();
            pageBtn.className = i === currentPage ? 'active' : 'secondary';
            pageBtn.addEventListener('click', () => goToPage(i));
            pageNumbers.appendChild(pageBtn);
        }

        // 更新分页信息
        if (paginationInfo) {
            const startItem = (currentPage - 1) * pageSize + 1;
            const endItem = Math.min(currentPage * pageSize, filteredAccounts.length);
            paginationInfo.textContent = `显示 ${startItem}-${endItem} 条，共 ${filteredAccounts.length} 条记录`;
        }
    }

    // 跳转到指定页
    function goToPage(page) {
        if (page < 1 || page > totalPages || page === currentPage) return;

        currentPage = page;
        renderAccounts(getPaginatedAccounts());
        updateUI();
        if (tableContainer) tableContainer.scrollTo(0, 0);
    }

    // 处理滚动事件
    function handleScroll() {
        if (fetchMode !== 'page' || isFetching || !tableContainer) return;

        const { scrollTop, scrollHeight, clientHeight } = tableContainer;
        const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;

        if (isNearBottom && currentPage < totalPages) {
            goToPage(currentPage + 1);
        }
    }

    // 清空表格
    function clearTable() {
        if (accountsBody) accountsBody.innerHTML = '';
    }

    // 格式化日期时间
    function formatDateTime(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (e) {
            return dateString;
        }
    }

    // 获取分页数据
    function getPaginatedAccounts() {
        if (fetchMode === 'all') {
            return filteredAccounts;
        } else {
            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = startIndex + pageSize;
            return filteredAccounts.slice(startIndex, endIndex);
        }
    }

    // 渲染账户数据到表格
    function renderAccounts(accounts) {
        clearTable();

        // 如果accounts不是数组，转换为数组
        if (!Array.isArray(accounts)) {
            accounts = [accounts];
        }

        if (accounts.length === 0) {
            return;
        }

        // 使用文档片段提高性能
        const fragment = document.createDocumentFragment();
        const maskPasswords = maskPasswordsCheck?.checked || false;

        accounts.forEach(account => {
            const row = document.createElement('tr');

            // 状态显示
            const statusText = account.status === 1 ? '活跃' : '禁用';
            const statusClass = account.status === 1 ? 'status-active' : 'status-inactive';

            // 类型显示
            const typeClass = `type-${account.type}`;

            // 代码显示（可能为null）
            const code = account.code ? account.code : '无';

            // 密码显示
            const passwordDisplay = maskPasswords ?
                '<span class="password-mask">••••••••</span>' :
                account.password;

            row.innerHTML = `
                        <td>${account.id}</td>
                        <td>${account.account}</td>
                        <td>${passwordDisplay}</td>
                        <td class="${typeClass}">${account.type}</td>
                        <td class="${statusClass}">${statusText}</td>
                        <td>${code}</td>
                        <td>${formatDateTime(account.created_at)}</td>
                        <td>
                            <button class="view-btn" data-id="${account.id}">查看</button>
                        </td>
                    `;

            fragment.appendChild(row);
        });

        if (accountsBody) accountsBody.appendChild(fragment);

        // 添加查看按钮事件
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                if (accountIdInput) accountIdInput.value = this.getAttribute('data-id');
                fetchSingleAccount().then(() => {});
            });
        });
    }

    // 获取全部账户
    async function fetchAllAccounts() {
        try {
            showLoading();
            clearTable();
            fetchMode = 'all';

            // 模拟分块加载进度
            updateProgress(10);

            const response = await authenticatedFetch(`/accounts`);
            updateProgress(30);

            if (!response || !response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
            }

            const data = await response.json();
            updateProgress(70);

            allAccounts = data;
            filteredAccounts = [...allAccounts];
            totalPages = Math.ceil(filteredAccounts.length / pageSize);

            applyFilters(false); // 应用当前筛选但不重新获取数据
            updateProgress(100);
        } catch (error) {
            showError(`获取全部账户失败: ${error.message}`);
            console.error('获取全部账户失败:', error);
            fetchMode = 'none';
        } finally {
            hideLoading();
        }
    }

    // 分页获取账户
    async function fetchAccountsByPage() {
        try {
            showLoading();
            clearTable();
            fetchMode = 'page';
            currentPage = 1;

            // 这里假设后端支持分页参数，如果实际不支持，需要在前端处理
            const response = await authenticatedFetch(`/accounts`);

            if (!response || !response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
            }

            allAccounts = await response.json();
            filteredAccounts = [...allAccounts];
            totalPages = Math.ceil(filteredAccounts.length / pageSize);

            applyFilters(false); // 应用当前筛选但不重新获取数据
        } catch (error) {
            showError(`获取账户失败: ${error.message}`);
            console.error('获取账户失败:', error);
            fetchMode = 'none';
        } finally {
            hideLoading();
        }
    }

    // 获取单个账户（不加锁）
    async function fetchSingleAccount() {
        const accountId = accountIdInput?.value?.trim();

        if (!accountId) {
            showError('请输入账户ID');
            return;
        }

        try {
            showLoading();
            clearTable();
            fetchMode = 'single';

            const response = await authenticatedFetch(`/accounts/${accountId}`);

            if (!response || !response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
            }

            const data = await response.json();
            allAccounts = [data];
            filteredAccounts = [...allAccounts];

            renderAccounts(filteredAccounts);
        } catch (error) {
            showError(`获取单个账户失败: ${error.message}`);
            console.error('获取单个账户失败:', error);
            fetchMode = 'none';
        } finally {
            hideLoading();
        }
    }

    // 获取单个账户（加锁）
    async function fetchSingleAccountLocked() {
        const accountId = accountIdInput?.value?.trim();

        if (!accountId) {
            showError('请输入账户ID');
            return;
        }

        try {
            showLoading();
            clearTable();
            fetchMode = 'single';

            const response = await authenticatedFetch(`/account/unique`);

            if (!response || !response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
            }

            const data = await response.json();
            allAccounts = [data];
            filteredAccounts = [...allAccounts];

            renderAccounts(filteredAccounts);
        } catch (error) {
            showError(`获取单个账户(加锁)失败: ${error.message}`);
            console.error('获取单个账户(加锁)失败:', error);
            fetchMode = 'none';
        } finally {
            hideLoading();
        }
    }

    // 应用筛选条件
    function applyFilters(fetchData = true) {
        if (fetchData && fetchMode === 'none') {
            fetchAllAccounts().then(() => {});
            return;
        }

        const searchTerm = searchInput?.value?.toLowerCase() || '';
        const statusValue = statusFilter?.value || '';
        const typeValue = typeFilter?.value || '';

        filteredAccounts = allAccounts.filter(account => {
            // 搜索条件
            const matchesSearch =
                account.account.toLowerCase().includes(searchTerm) ||
                (account.code && account.code.toLowerCase().includes(searchTerm));

            // 状态筛选
            const matchesStatus = statusValue === '' || account.status.toString() === statusValue;

            // 类型筛选
            const matchesType = typeValue === '' || account.type.toString() === typeValue;

            return matchesSearch && matchesStatus && matchesType;
        });

        totalPages = Math.ceil(filteredAccounts.length / pageSize);
        currentPage = 1;

        renderAccounts(getPaginatedAccounts());
        updateUI();
    }

    // 重置筛选条件
    function resetFilters() {
        if (searchInput) searchInput.value = '';
        if (statusFilter) statusFilter.value = '';
        if (typeFilter) typeFilter.value = '';
        applyFilters();
    }

    // 切换密码显示
    function togglePasswordMask() {
        renderAccounts(getPaginatedAccounts());
    }

    // 导出为CSV
    function exportToCSV() {
        if (filteredAccounts.length === 0) {
            showError('没有数据可导出');
            return;
        }

        try {
            // CSV标题行
            const headers = ['ID', '账号', '密码', '类型', '状态', '代码', '创建时间'];

            // CSV数据行
            const rows = filteredAccounts.map(account => {
                return [
                    account.id,
                    account.account,
                    account.password,
                    account.type,
                    account.status === 1 ? '活跃' : '禁用',
                    account.code || '',
                    formatDateTime(account.created_at)
                ].map(field => `"${field.toString().replace(/"/g, '""')}"`).join(',');
            });

            // 合并为完整CSV
            const csvContent = [headers.join(','), ...rows].join('\n');

            // 创建下载链接
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `账户数据_${new Date().toISOString().slice(0, 10)}.csv`;
            link.click();

            // 清理
            setTimeout(() => {
                URL.revokeObjectURL(url);
            }, 100);
        } catch (error) {
            showError(`导出CSV失败: ${error.message}`);
            console.error('导出CSV失败:', error);
        }
    }

    // 实时状态功能
    async function fetchCloudStatus() {
        try {
            const response = await authenticatedFetch('/cloud_status');
            if (!response || !response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
            }
            const statusData = await response.json();
            renderStatusTable(statusData);
        } catch (error) {
            console.error('获取状态失败:', error);
            showError(`获取云机状态失败: ${error.message}`);
        }
    }

    function renderStatusTable(statusData) {
        if (!statusTableBody) return;

        statusTableBody.innerHTML = '';

        if (!Array.isArray(statusData) || statusData.length === 0) {
            if (statusEmptyState) statusEmptyState.style.display = 'block';
            statusTableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">暂无状态数据</td></tr>';
            return;
        }

        if (statusEmptyState) statusEmptyState.style.display = 'none';

        statusData.forEach(status => {
            const row = document.createElement('tr');

            // 根据状态设置样式
            const statusClass = getStatusClass(status.current_status);

            row.innerHTML = `
                <td>${status.pad_code}</td>
                <td class="${statusClass}">${status.current_status || '未知'}</td>
                <td>${status.number_of_run}</td>
                <td>${status.temple_id}</td>
                <td>${status.phone_number_counts}</td>
                <td>${status.country || '未设置'}</td>
                <td>${formatDateTime(status.updated_at)}</td>
                <td>
                    <button class="status-btn" onclick="refreshSingleStatus('${status.pad_code}')">刷新</button>
                </td>
            `;

            statusTableBody.appendChild(row);
        });
    }

    function getStatusClass(status) {
        if (!status) return '';

        const statusLower = status.toLowerCase();
        if (statusLower.includes('成功') || statusLower.includes('完成')) {
            return 'status-success';
        } else if (statusLower.includes('失败') || statusLower.includes('错误')) {
            return 'status-error';
        } else if (statusLower.includes('进行中') || statusLower.includes('安装中') || statusLower.includes('启动中')) {
            return 'status-running';
        } else if (statusLower.includes('等待') || statusLower.includes('准备')) {
            return 'status-pending';
        }
        return 'status-info';
    }

    function toggleView() {
        if (currentView === 'accounts') {
            currentView = 'status';
            if (accountsSection) accountsSection.style.display = 'none';
            if (statusSection) statusSection.style.display = 'block';
            if (toggleViewBtn) toggleViewBtn.textContent = '切换到账户管理';
            startStatusUpdates();
        } else {
            currentView = 'accounts';
            if (accountsSection) accountsSection.style.display = 'block';
            if (statusSection) statusSection.style.display = 'none';
            if (toggleViewBtn) toggleViewBtn.textContent = '切换到状态监控';
            stopStatusUpdates();
        }
    }

    function startStatusUpdates() {
        fetchCloudStatus(); // 立即获取一次
        statusUpdateInterval = setInterval(fetchCloudStatus, 3000); // 每3秒更新一次
    }

    function stopStatusUpdates() {
        if (statusUpdateInterval) {
            clearInterval(statusUpdateInterval);
            statusUpdateInterval = null;
        }
    }

    async function refreshSingleStatus(padCode) {
        try {
            const response = await authenticatedFetch('/cloud_status', {
                method: 'POST',
                body: JSON.stringify({ pad_code: padCode })
            });

            if (response && response.ok) {
                fetchCloudStatus(); // 刷新整个状态表
            }
        } catch (error) {
            console.error('刷新单个状态失败:', error);
        }
    }

    // 页面卸载时清理定时器
    window.addEventListener('beforeunload', function() {
        stopStatusUpdates();
    });

    // 将 refreshSingleStatus 函数暴露到全局，以便在 HTML 中使用
    window.refreshSingleStatus = refreshSingleStatus;
});

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            button.active {
                background-color: #2c3e50;
                color: white;
            }

            .view-btn {
                padding: 4px 8px;
                font-size: 12px;
                min-width: auto;
                background-color: #7f8c8d;
            }

            .view-btn:hover {
                background-color: #34495e;
            }
        `;
document.head.appendChild(style);