document.addEventListener('DOMContentLoaded', function() {
    // 认证检查
    checkAuthStatus().then(r => {});

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
    const connectionStatus = document.getElementById('connectionStatus');

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
    let websocket = null;
    let reconnectInterval = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    let isConnecting = false;

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
        refreshAllStatusBtn && refreshAllStatusBtn.addEventListener('click', requestStatusUpdate);

        // 页面可见性变化时重连WebSocket
        document.addEventListener('visibilitychange', handleVisibilityChange);

        // 页面卸载前关闭WebSocket
        window.addEventListener('beforeunload', closeWebSocket);
    }

    // WebSocket相关函数
    function initWebSocket() {
        if (isConnecting || (websocket && websocket.readyState === WebSocket.OPEN)) {
            return;
        }

        isConnecting = true;
        updateConnectionStatus('connecting');
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            websocket = new WebSocket(wsUrl);

            websocket.onopen = function() {
                console.log('WebSocket连接已建立');
                isConnecting = false;
                reconnectAttempts = 0;
                updateConnectionStatus('connected');

                // 清除重连定时器
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }

                // 订阅状态更新
                if (currentView === 'status') {
                    requestStatusUpdate();
                }
            };

            websocket.onmessage = function(event) {
                try {
                    const message = JSON.parse(event.data);
                    handleWebSocketMessage(message);
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };

            websocket.onclose = function(event) {
                console.log('WebSocket连接已关闭:', event.code, event.reason);
                isConnecting = false;
                websocket = null;
                updateConnectionStatus('disconnected');

                // 如果不是主动关闭且在状态监控页面，尝试重连
                if (event.code !== 1000 && currentView === 'status') {
                    attemptReconnect();
                }
            };

            websocket.onerror = function(error) {
                console.error('WebSocket错误:', error);
                isConnecting = false;
                updateConnectionStatus('error');
            };

        } catch (error) {
            console.error('创建WebSocket连接失败:', error);
            isConnecting = false;
            updateConnectionStatus('error');
            attemptReconnect();
        }
    }

    function closeWebSocket() {
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }

        if (websocket) {
            websocket.close(1000, '页面关闭');
            websocket = null;
        }
        updateConnectionStatus('disconnected');
    }

    function attemptReconnect() {
        if (reconnectAttempts >= maxReconnectAttempts) {
            console.log('达到最大重连次数，停止重连');
            updateConnectionStatus('failed');
            return;
        }

        if (reconnectInterval) {
            return; // 已经在重连中
        }

        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // 指数退避，最大30秒
        console.log(`${delay}ms后尝试重连... (${reconnectAttempts + 1}/${maxReconnectAttempts})`);

        updateConnectionStatus('reconnecting');

        reconnectInterval = setTimeout(() => {
            reconnectAttempts++;
            reconnectInterval = null;
            initWebSocket();
        }, delay);
    }

    function handleWebSocketMessage(message) {
        switch (message.type) {
            case 'status_update':
                if (currentView === 'status') {
                    renderStatusTable(message.data);
                }
                break;

            case 'single_status_update':
                if (currentView === 'status') {
                    updateSingleStatus(message.data);
                }
                break;

            case 'pong':
                // 心跳响应
                break;

            default:
                console.log('未知WebSocket消息类型:', message.type);
        }
    }

    function requestStatusUpdate() {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'subscribe_status'
            }));
        } else {
            // WebSocket未连接，回退到HTTP请求
            fetchCloudStatus();
        }
    }

    function updateConnectionStatus(status) {
        if (!connectionStatus) return;

        const statusMap = {
            'connected': { text: '实时连接', class: 'status-success', icon: '●' },
            'connecting': { text: '连接中...', class: 'status-pending', icon: '◐' },
            'reconnecting': { text: '重连中...', class: 'status-pending', icon: '◑' },
            'disconnected': { text: '已断开', class: 'status-error', icon: '○' },
            'error': { text: '连接错误', class: 'status-error', icon: '✗' },
            'failed': { text: '连接失败', class: 'status-error', icon: '✗' }
        };

        const statusInfo = statusMap[status] || statusMap['disconnected'];
        connectionStatus.innerHTML = `
            <span class="${statusInfo.class}">
                ${statusInfo.icon} ${statusInfo.text}
            </span>
        `;
    }

    function handleVisibilityChange() {
        if (document.hidden) {
            // 页面隐藏时暂停WebSocket心跳
        } else {
            // 页面显示时恢复连接
            if (currentView === 'status' && (!websocket || websocket.readyState !== WebSocket.OPEN)) {
                initWebSocket();
            }
        }
    }

    // 更新单个状态行
    function updateSingleStatus(statusData) {
        const rows = statusTableBody.querySelectorAll('tr');
        for (const row of rows) {
            const padCodeCell = row.cells[0];
            if (padCodeCell && padCodeCell.textContent === statusData.pad_code) {
                // 更新状态
                const statusCell = row.cells[1];
                if (statusCell) {
                    statusCell.textContent = statusData.current_status;
                    statusCell.className = getStatusClass(statusData.current_status);
                }

                // 如果有运行次数等数据更新，也需要重新计算占比
                if (statusData.number_of_run !== undefined) {
                    // 重新获取完整状态数据并重新渲染整行
                    requestStatusUpdate();
                }
                break;
            }
        }
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

            }
        } catch (error) {
            console.error('认证检查失败:', error);
            redirectToLogin();

        }
    }

    function redirectToLogin() {
        window.location.href = '/login';
    }

    function logout() {
        localStorage.removeItem('access_token');
        closeWebSocket();
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

    // 实时状态功能 - 改为WebSocket优先，HTTP作为fallback
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
            statusTableBody.innerHTML = '<tr><td colspan="10" style="text-align: center;">暂无状态数据</td></tr>';
            return;
        }

        if (statusEmptyState) statusEmptyState.style.display = 'none';

        statusData.forEach(status => {
            const row = document.createElement('tr');

            // 根据状态设置样式
            const statusClass = getStatusClass(status.current_status);

            // 计算占比
            const totalRuns = status.number_of_run || 1; // 避免除零
            const forwardRatio = totalRuns > 0 ? Math.round((status.forward_num || 0) / totalRuns * 100) : 0;
            const phoneRatio = totalRuns > 0 ? Math.round((status.phone_number_counts || 0) / totalRuns * 100) : 0;
            const secondaryEmailRatio = totalRuns > 0 ? Math.round((status.secondary_email_num || 0) / totalRuns * 100) : 0;

            // 为占比添加颜色样式
            const getRatioClass = (ratio) => {
                if (ratio >= 80) return 'ratio-high';
                if (ratio >= 50) return 'ratio-medium';
                if (ratio >= 20) return 'ratio-low';
                return 'ratio-none';
            };

            row.innerHTML = `
            <td>${status.pad_code}</td>
            <td class="${statusClass}">${status.current_status || '未知'}</td>
            <td>${status.number_of_run}</td>
            <td>${status.temple_id}</td>
            <td class="${getRatioClass(forwardRatio)}">${forwardRatio}%</td>
            <td class="${getRatioClass(phoneRatio)}">${phoneRatio}%</td>
            <td class="${getRatioClass(secondaryEmailRatio)}">${secondaryEmailRatio}%</td>
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
            // 启动WebSocket连接并开始状态监控
            initWebSocket();
        } else {
            currentView = 'accounts';
            if (accountsSection) accountsSection.style.display = 'block';
            if (statusSection) statusSection.style.display = 'none';
            if (toggleViewBtn) toggleViewBtn.textContent = '切换到状态监控';
            // 关闭WebSocket连接
            closeWebSocket();
        }
    }

    async function refreshSingleStatus(padCode) {
        try {
            const response = await authenticatedFetch('/cloud_status', {
                method: 'POST',
                body: JSON.stringify({ pad_code: padCode })
            });

            if (response && response.ok) {
                // WebSocket优先，如果WebSocket连接正常，状态会自动更新
                // 如果WebSocket未连接，则手动刷新
                if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                    fetchCloudStatus();
                }
            }
        } catch (error) {
            console.error('刷新单个状态失败:', error);
        }
    }

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

            .connection-status {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
                padding: 8px 12px;
                border-radius: 4px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                min-width: 120px;
            }

            .connection-status .status-success {
                color: #27ae60;
                font-weight: 500;
            }

            .connection-status .status-pending {
                color: #f39c12;
                font-weight: 500;
            }

            .connection-status .status-error {
                color: #e74c3c;
                font-weight: 500;
            }

            .connection-status .status-info {
                color: #6c757d;
                font-weight: 500;
            }

            .status-running::after {
                content: '';
                display: inline-block;
                width: 6px;
                height: 6px;
                margin-left: 8px;
                background-color: var(--primary-color);
                border-radius: 50%;
                animation: blink 1s infinite;
            }

            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0.3; }
            }

            /* WebSocket连接状态指示器动画 */
            .connection-status .status-pending::before {
                content: '';
                display: inline-block;
                width: 12px;
                height: 12px;
                margin-right: 4px;
                border: 2px solid #f39c12;
                border-top-color: transparent;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            .connection-status .status-success::before {
                content: '';
                display: inline-block;
                width: 8px;
                height: 8px;
                margin-right: 4px;
                background-color: #27ae60;
                border-radius: 50%;
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% {
                    transform: scale(1);
                    opacity: 1;
                }
                50% {
                    transform: scale(1.2);
                    opacity: 0.7;
                }
                100% {
                    transform: scale(1);
                    opacity: 1;
                }
            }

            /* 表格行的状态样式 */
            .status-success {
                color: var(--success-color);
                font-weight: bold;
            }

            .status-error {
                color: var(--danger-color);
                font-weight: bold;
            }

            .status-running {
                color: var(--primary-color);
                font-weight: bold;
                position: relative;
            }

            .status-pending {
                color: var(--warning-color);
                font-weight: bold;
            }

            .status-info {
                color: var(--dark-gray);
                font-weight: 500;
            }

            /* 响应式优化 */
            @media (max-width: 768px) {
                .connection-status {
                    font-size: 12px;
                    padding: 6px 10px;
                    min-width: 100px;
                }
                
                .status-controls {
                    flex-direction: column;
                    gap: 10px;
                    align-items: stretch;
                }
                
                .status-controls button {
                    width: 100%;
                }
            }
        `;
document.head.appendChild(style);