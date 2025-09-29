document.addEventListener('DOMContentLoaded', function() {
    // 认证检查
    checkAuthStatus().then();

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
                isConnecting = false;
                reconnectAttempts = 0;
                updateConnectionStatus('connected');

                // 清除重连定时器
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }

                // 立即请求状态更新
                if (currentView === 'status') {
                    requestStatusUpdate();
                }
            };

            websocket.onmessage = function(event) {
                try {
                    const message = JSON.parse(event.data);
                    handleWebSocketMessage(message);
                } catch (error) {
                    console.error('❌ 解析WebSocket消息失败:', error);
                    console.log('原始消息:', event.data);
                }
            };

            websocket.onclose = function(event) {
                isConnecting = false;
                websocket = null;

                // 根据关闭代码决定是否重连
                if (event.code !== 1000 && currentView === 'status') { // 1000 = 正常关闭
                    updateConnectionStatus('disconnected');
                    attemptReconnect();
                } else {
                    updateConnectionStatus('disconnected');
                }
            };

            websocket.onerror = function(_error) {
                isConnecting = false;
                updateConnectionStatus('error');
            };

        } catch (error) {
            isConnecting = false;
            updateConnectionStatus('error');
            attemptReconnect();
        }
    }

    function handleWebSocketMessage(message) {
        const messageType = message.type;

        switch (messageType) {
            case 'status_update':
                if (currentView === 'status' && message.data) {
                    renderStatusTable(message.data);
                }
                break;

            case 'single_status_update':
                if (currentView === 'status' && message.data) {
                    updateSingleStatus(message.data);
                }
                break;

            case 'ping':
                // 响应服务器心跳
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({
                        type: 'pong',
                        client_time: new Date().toISOString()
                    }));
                    console.log('💓 响应服务器心跳');
                }
                break;

            case 'pong':
                // 服务器响应客户端心跳
                console.log('💓 收到服务器心跳响应');
                break;

            case 'error':
                console.error('❌ 服务器错误消息:', message.message);
                break;

            case 'config_updated':
                if (message.data) {
                    // 显示配置更新通知
                    showConfigUpdateNotification(message.data.message, message.data.updated_fields);

                    // 如果当前在状态监控页面，可能需要刷新状态
                    if (currentView === 'status') {
                        setTimeout(() => {
                            requestStatusUpdate();
                        }, 2000);
                    }
                }
                break;

            default:
                console.warn('⚠️  未知WebSocket消息类型:', messageType, message);
        }
    }

    function requestStatusUpdate() {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'subscribe_status',
                timestamp: new Date().toISOString()
            }));
        } else {
            fetchCloudStatus().then(r => {});
        }
    }

    function updateConnectionStatus(status) {
        if (!connectionStatus) return;

        const statusMap = {
            'connected': {
                text: '实时连接',
                class: 'status-success',
                icon: '🟢'
            },
            'connecting': {
                text: '连接中...',
                class: 'status-pending',
                icon: '🟡'
            },
            'reconnecting': {
                text: '重连中...',
                class: 'status-pending',
                icon: '🟡'
            },
            'disconnected': {
                text: '已断开',
                class: 'status-error',
                icon: '🔴'
            },
            'error': {
                text: '连接错误',
                class: 'status-error',
                icon: '❌'
            },
            'failed': {
                text: '连接失败',
                class: 'status-error',
                icon: '❌'
            }
        };

        const statusInfo = statusMap[status] || statusMap['disconnected'];
        connectionStatus.innerHTML = `
        <span class="${statusInfo.class}">
            ${statusInfo.icon} ${statusInfo.text}
        </span>
    `;
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
            updateConnectionStatus('failed');
            return;
        }

        if (reconnectInterval) {
            return; // 已经在重连中
        }

        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // 指数退避，最大30秒

        updateConnectionStatus('reconnecting');

        reconnectInterval = setTimeout(() => {
            reconnectAttempts++;
            reconnectInterval = null;
            initWebSocket();
        }, delay);
    }

// 更新单个状态行
    function updateSingleStatus(statusData) {
        if (!statusTableBody || !statusData.pad_code) {
            return;
        }

        const rows = statusTableBody.querySelectorAll('tr');
        let updated = false;

        for (const row of rows) {
            const padCodeCell = row.cells[0];
            if (padCodeCell && padCodeCell.textContent.trim() === statusData.pad_code) {
                // 更新状态列
                const statusCell = row.cells[1];
                if (statusCell && statusData.current_status) {
                    const oldStatus = statusCell.textContent;
                    statusCell.textContent = statusData.current_status;
                    statusCell.className = getStatusClass(statusData.current_status);

                    // 添加动画效果
                    statusCell.style.animation = 'highlight 2s ease-out';
                    setTimeout(() => {
                        statusCell.style.animation = '';
                    }, 2000);

                    updated = true;
                }
                break;
            }
        }

        if (!updated) {
            // 如果找不到对应行，请求完整更新
            requestFullStatusUpdate();
        }
    }

// 请求完整状态更新
    function requestFullStatusUpdate() {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'request_full_update',
                timestamp: new Date().toISOString()
            }));
        } else {
            fetchCloudStatus().then(r => {});
        }
    }

// 改进的状态表格渲染函数
    function renderStatusTable(statusData) {
        if (!statusTableBody) {
            return;
        }

        // 清空现有内容
        statusTableBody.innerHTML = '';

        if (!Array.isArray(statusData) || statusData.length === 0) {
            if (statusEmptyState) statusEmptyState.style.display = 'block';
            statusTableBody.innerHTML = '<tr><td colspan="10" style="text-align: center; padding: 20px; color: #666;">暂无状态数据</td></tr>';
            return;
        }

        if (statusEmptyState) statusEmptyState.style.display = 'none';

        // 使用文档片段提高性能
        const fragment = document.createDocumentFragment();

        statusData.forEach((status, index) => {
            const row = document.createElement('tr');
            row.style.animationDelay = `${index * 50}ms`; // 添加渐入动画

            // 根据状态设置样式
            const statusClass = getStatusClass(status.current_status);

            // 计算占比
            const totalRuns = status.number_of_run || 1;
            const forwardRatio = Math.round(((status.forward_num || 0) / totalRuns) * 100);
            const phoneRatio = Math.round(((status.phone_number_counts || 0) / totalRuns) * 100);
            const secondaryEmailRatio = Math.round(((status.secondary_email_num || 0) / totalRuns) * 100);

            // 为占比添加颜色样式
            const getRatioClass = (ratio) => {
                if (ratio >= 80) return 'ratio-high';
                if (ratio >= 50) return 'ratio-medium';
                if (ratio >= 20) return 'ratio-low';
                return 'ratio-none';
            };

            row.innerHTML = `
            <td title="${status.pad_code}">${status.pad_name || "未知设备"}</td>
            <td class="${statusClass}" title="${status.current_status || '未知'}">${status.current_status || '未知'}</td>
            <td title="运行次数">${status.number_of_run}</td>
            <td title="成功次数">${status.num_of_success}</td>
            <td title="error次数">${status.num_of_error}</td>
            <td title="其他错误">${status.num_other_error}</td>
            <td title="模板ID">${status.temple_id}</td>
            <td class="${getRatioClass(forwardRatio)}" title="转发邮箱: ${status.forward_num || 0}/${totalRuns}">${forwardRatio}%</td>
            <td class="${getRatioClass(phoneRatio)}" title="手机号: ${status.phone_number_counts || 0}/${totalRuns}">${phoneRatio}%</td>
            <td class="${getRatioClass(secondaryEmailRatio)}" title="辅助邮箱: ${status.secondary_email_num || 0}/${totalRuns}">${secondaryEmailRatio}%</td>
            <td title="国家">${status.country || '未设置'}</td>
            <td title="更新时间">${formatDateTime(status.updated_at)}</td>
            <td>
                <button class="status-btn" onclick="refreshSingleStatus('${status.pad_code}')" title="刷新该设备状态">
                    🔄
                </button>
            </td>
        `;

            fragment.appendChild(row);
        });

        statusTableBody.appendChild(fragment);
    }

// 视图切换函数 - 增强WebSocket管理
    function toggleView() {
        if (currentView === 'accounts') {
            currentView = 'status';
            if (accountsSection) accountsSection.style.display = 'none';
            if (statusSection) statusSection.style.display = 'block';
            if (toggleViewBtn) toggleViewBtn.textContent = '切换到账户管理';

            // 启动WebSocket连接并开始状态监控
            initWebSocket();

            // 如果WebSocket未能立即连接，使用HTTP作为备选
            setTimeout(() => {
                if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                    fetchCloudStatus().then(r => {});
                }
            }, 1000);

        } else {
            currentView = 'accounts';
            if (accountsSection) accountsSection.style.display = 'block';
            if (statusSection) statusSection.style.display = 'none';
            if (toggleViewBtn) toggleViewBtn.textContent = '切换到状态监控';
            closeWebSocket();
        }
    }

// 页面可见性变化处理 - 优化
    function handleVisibilityChange() {
        if (document.hidden) {
        } else {
            if (currentView === 'status') {
                if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                    initWebSocket();
                } else {
                    // 连接正常，请求最新状态
                    requestStatusUpdate();
                }
            }
        }
    }

// 添加状态行高亮动画的CSS
    const additionalStyles = `
    @keyframes highlight {
        0% { background-color: rgba(52, 152, 219, 0.3); }
        100% { background-color: transparent; }
    }
    
    .status-table-row {
        transition: background-color 0.3s ease;
    }
    
    .status-btn {
        min-width: 32px;
        padding: 4px 8px;
        font-size: 12px;
        background-color: var(--primary-color);
        border: none;
        color: white;
        border-radius: 3px;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .status-btn:hover {
        background-color: var(--primary-hover);
    }
    
    .connection-status {
        user-select: none;
        cursor: default;
    }
`;

// 将额外样式添加到页面
    if (!document.getElementById('additional-styles')) {
        const styleElement = document.createElement('style');
        styleElement.id = 'additional-styles';
        styleElement.textContent = additionalStyles;
        document.head.appendChild(styleElement);
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
                 new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
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
                new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
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
                new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
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

    async function refreshSingleStatus(padCode) {
        try {
            const response = await authenticatedFetch('/cloud_status', {
                method: 'POST',
                body: JSON.stringify({ pad_code: padCode })
            });

            if (response && response.ok) {
                if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                    await fetchCloudStatus();
                }
            }
        } catch (error) {
            console.error('刷新单个状态失败:', error);
        }
    }
    // ========== 设备管理功能 ==========
    let allCloudDevices = [];
    let currentConfiguredDevices = [];

// 显示设备管理器
    async function showDeviceManager() {
        document.getElementById('deviceManagerModal').style.display = 'flex';
        await loadDeviceManagerData();
    }

// 关闭设备管理器
    function closeDeviceManager() {
        document.getElementById('deviceManagerModal').style.display = 'none';
    }

// 加载设备管理数据
    async function loadDeviceManagerData() {
        try {
            // 并行获取云端设备和当前配置
            const [cloudResponse, configResponse] = await Promise.all([
                authenticatedFetch('/api/pad-codes/available'),
                authenticatedFetch('/api/pad-codes/current')
            ]);

            if (cloudResponse && cloudResponse.ok && configResponse && configResponse.ok) {
                const cloudData = await cloudResponse.json();
                const configData = await configResponse.json();

                allCloudDevices = cloudData.data || [];
                currentConfiguredDevices = configData.data || [];

                updateDeviceStats();
                renderDeviceList();
            }
        } catch (error) {
            console.error('加载设备数据失败:', error);
            showError('加载设备数据失败: ' + error.message);
        }
    }

// 更新统计信息
    function updateDeviceStats() {
        const configuredSet = new Set(currentConfiguredDevices);
        const notConfigured = allCloudDevices.filter(d => !configuredSet.has(d.padCode));

        document.getElementById('configuredCount').textContent = currentConfiguredDevices.length;
        document.getElementById('cloudTotalCount').textContent = allCloudDevices.length;
        document.getElementById('notConfiguredCount').textContent = notConfigured.length;
    }

// 渲染设备列表
    function renderDeviceList() {
        const tbody = document.getElementById('deviceListBody');
        const configuredSet = new Set(currentConfiguredDevices);

        tbody.innerHTML = allCloudDevices.map(device => {
            const isConfigured = configuredSet.has(device.padCode);
            const statusBadge = device.status === 1
                ? '<span style="color: #27ae60;">🟢 在线</span>'
                : '<span style="color: #e74c3c;">🔴 离线</span>';
            const configBadge = isConfigured
                ? '<span style="color: #27ae60;">✓</span>'
                : '<span style="color: #e74c3c;">✗</span>';

            return `
            <tr data-code="${device.padCode}" style="border-bottom: 1px solid #eee;">
                <td title="${device.padCode}" style="padding: 10px;">${device.padName}</td>
                <td style="padding: 10px;">${statusBadge}</td>
                <td style="padding: 10px; text-align: center;">${configBadge}</td>
                <td style="padding: 10px; text-align: center;">
                    ${isConfigured
                ? `<button onclick="removeDevice('${device.padCode}')" class="remove-btn" style="padding: 4px 8px; font-size: 12px;">移除</button>`
                : `<button onclick="addDevice('${device.padCode}')" class="add-btn" style="padding: 4px 8px; font-size: 12px;">添加</button>`
            }
                </td>
            </tr>
        `;
        }).join('');
    }

// 筛选设备列表
    function filterDeviceList() {
        const searchTerm = document.getElementById('deviceSearchInput').value.toLowerCase();
        const rows = document.querySelectorAll('#deviceListBody tr');

        rows.forEach(row => {
            const code = row.dataset.code.toLowerCase();
            row.style.display = code.includes(searchTerm) ? '' : 'none';
        });
    }

// 添加单个设备
    async function addDevice(padCode) {
        try {
            const response = await authenticatedFetch('/api/pad-codes/add', {
                method: 'POST',
                body: JSON.stringify({ selected_codes: [padCode] })
            });

            if (response && response.ok) {
                showSuccess('设备添加成功');
                await loadDeviceManagerData();
            }
        } catch (error) {
            showError('添加失败: ' + error.message);
        }
    }

// 移除单个设备
    async function removeDevice(padCode) {
        if (!confirm(`确定移除设备 ${padCode}?`)) return;

        try {
            const response = await authenticatedFetch('/api/pad-codes/remove', {
                method: 'DELETE',
                body: JSON.stringify({ selected_codes: [padCode] })
            });

            if (response && response.ok) {
                showSuccess('设备移除成功');
                await loadDeviceManagerData();
            }
        } catch (error) {
            showError('移除失败: ' + error.message);
        }
    }

// 同步所有设备
    async function syncAllDevices() {
        if (!confirm('确定导入所有云端设备?')) return;

        try {
            const response = await authenticatedFetch('/api/pad-codes/sync', {
                method: 'POST',
                body: JSON.stringify({ selected_codes: [] })
            });

            if (response && response.ok) {
                showSuccess('导入成功');
                await loadDeviceManagerData();
            }
        } catch (error) {
            showError('导入失败: ' + error.message);
        }
    }

// 同步在线设备
    async function syncOnlineDevices() {
        const onlineCodes = allCloudDevices
            .filter(d => d.status === 1)
            .map(d => d.padCode);

        if (onlineCodes.length === 0) {
            showError('没有在线设备');
            return;
        }

        if (!confirm(`确定导入 ${onlineCodes.length} 个在线设备?`)) return;

        try {
            const response = await authenticatedFetch('/api/pad-codes/add', {
                method: 'POST',
                body: JSON.stringify({ selected_codes: onlineCodes })
            });

            if (response && response.ok) {
                showSuccess('在线设备导入成功');
                await loadDeviceManagerData();
            }
        } catch (error) {
            showError('导入失败: ' + error.message);
        }
    }

// 移除无效设备
    async function removeInvalidDevices() {
        const cloudSet = new Set(allCloudDevices.map(d => d.padCode));
        const invalidCodes = currentConfiguredDevices.filter(code => !cloudSet.has(code));

        if (invalidCodes.length === 0) {
            showError('没有无效设备');
            return;
        }

        if (!confirm(`确定移除 ${invalidCodes.length} 个无效设备?\n\n${invalidCodes.join('\n')}`)) return;

        try {
            const response = await authenticatedFetch('/api/pad-codes/remove', {
                method: 'DELETE',
                body: JSON.stringify({ selected_codes: invalidCodes })
            });

            if (response && response.ok) {
                showSuccess('无效设备移除成功');
                await loadDeviceManagerData();
            }
        } catch (error) {
            showError('移除失败: ' + error.message);
        }
    }

// 显示成功消息
    function showSuccess(message) {
        const div = document.createElement('div');
        div.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        background: #27ae60; color: white; padding: 15px 20px;
        border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    `;
        div.textContent = message;
        document.body.appendChild(div);
        setTimeout(() => div.remove(), 3000);
    }
    // 在文件末尾添加以下函数

// 打开编辑设备配置弹窗
    function openEditDeviceModal(padCode) {
        // 从当前状态数据中查找设备信息
        const statusTableBody = document.getElementById('statusTableBody');
        const rows = statusTableBody.querySelectorAll('tr');

        let deviceData = null;
        for (const row of rows) {
            const padCodeCell = row.cells[0];
            if (padCodeCell && padCodeCell.getAttribute('data-pad-code') === padCode) {
                // 提取数据
                deviceData = {
                    padCode: padCode,
                    padName: padCodeCell.textContent.trim(),
                    templeId: row.getAttribute('data-temple-id'),
                    country: row.getAttribute('data-country'),
                    code: row.getAttribute('data-code'),
                    proxy: row.getAttribute('data-proxy'),
                    timeZone: row.getAttribute('data-time-zone'),
                    language: row.getAttribute('data-language'),
                    latitude: row.getAttribute('data-latitude'),
                    longitude: row.getAttribute('data-longitude'),
                    isSecondaryEmail: row.getAttribute('data-is-secondary-email') === 'true'
                };
                break;
            }
        }

        if (!deviceData) {
            showToast('未找到设备信息', 'error');
            return;
        }

        // 填充表单
        document.getElementById('editPadCode').value = deviceData.padCode;
        document.getElementById('editPadCodeDisplay').value = deviceData.padCode;
        document.getElementById('editPadName').value = deviceData.padName;
        document.getElementById('editTempleId').value = deviceData.templeId || '';
        document.getElementById('editCountry').value = deviceData.country || '';
        document.getElementById('editCode').value = deviceData.code || '';
        document.getElementById('editProxy').value = deviceData.proxy || '';
        document.getElementById('editTimeZone').value = deviceData.timeZone || '';
        document.getElementById('editLanguage').value = deviceData.language || '';
        document.getElementById('editLatitude').value = deviceData.latitude || '';
        document.getElementById('editLongitude').value = deviceData.longitude || '';
        document.getElementById('editIsSecondaryEmail').checked = deviceData.isSecondaryEmail;

        // 显示弹窗
        document.getElementById('editDeviceModal').style.display = 'flex';
    }

// 关闭编辑弹窗
    function closeEditDeviceModal() {
        document.getElementById('editDeviceModal').style.display = 'none';
        document.getElementById('editDeviceForm').reset();
    }

// 保存设备配置
    async function saveDeviceConfig() {
        const padCode = document.getElementById('editPadCode').value;
        const form = document.getElementById('editDeviceForm');

        // 表单验证
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const updateData = {
            temple_id: parseInt(document.getElementById('editTempleId').value),
            country: document.getElementById('editCountry').value.trim(),
            code: document.getElementById('editCode').value.trim(),
            proxy: document.getElementById('editProxy').value.trim(),
            time_zone: document.getElementById('editTimeZone').value.trim(),
            language: document.getElementById('editLanguage').value.trim(),
            latitude: parseFloat(document.getElementById('editLatitude').value),
            longitude: parseFloat(document.getElementById('editLongitude').value),
            is_secondary_email: document.getElementById('editIsSecondaryEmail').checked
        };

        try {
            showLoading(true);

            const response = await authenticatedFetch(`/cloud_status/${padCode}`, {
                method: 'PUT',
                headers: getAuthHeaders(),
                body: JSON.stringify(updateData)
            });

            if (!response || !response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '更新失败');
            }

            showToast(`设备 ${padCode} 配置更新成功`, 'success');
            closeEditDeviceModal();

            // 刷新状态列表
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                requestStatusUpdate();
            } else {
                await fetchCloudStatus();
            }

        } catch (error) {
            console.error('保存设备配置失败:', error);
            showToast('保存失败: ' + error.message, 'error');
        } finally {
            showLoading(false);
        }
    }

// 修改 renderStatusTable 函数，添加数据属性和编辑按钮
    function renderStatusTable(statusData) {
        if (!statusTableBody) {
            return;
        }

        statusTableBody.innerHTML = '';

        if (!Array.isArray(statusData) || statusData.length === 0) {
            if (statusEmptyState) statusEmptyState.style.display = 'block';
            statusTableBody.innerHTML = '<tr><td colspan="13" style="text-align: center; padding: 20px; color: #666;">暂无状态数据</td></tr>';
            return;
        }

        if (statusEmptyState) statusEmptyState.style.display = 'none';

        const fragment = document.createDocumentFragment();

        statusData.forEach((status, index) => {
            const row = document.createElement('tr');
            row.style.animationDelay = `${index * 50}ms`;

            // 添加数据属性
            row.setAttribute('data-temple-id', status.temple_id || '');
            row.setAttribute('data-country', status.country || '');
            row.setAttribute('data-code', status.code || '');
            row.setAttribute('data-proxy', status.proxy || '');
            row.setAttribute('data-time-zone', status.time_zone || '');
            row.setAttribute('data-language', status.language || '');
            row.setAttribute('data-latitude', status.latitude || '');
            row.setAttribute('data-longitude', status.longitude || '');
            row.setAttribute('data-is-secondary-email', status.is_secondary_email || false);

            const statusClass = getStatusClass(status.current_status);
            const totalRuns = status.number_of_run || 1;
            const forwardRatio = Math.round(((status.forward_num || 0) / totalRuns) * 100);
            const phoneRatio = Math.round(((status.phone_number_counts || 0) / totalRuns) * 100);
            const secondaryEmailRatio = Math.round(((status.secondary_email_num || 0) / totalRuns) * 100);

            const getRatioClass = (ratio) => {
                if (ratio >= 80) return 'ratio-high';
                if (ratio >= 50) return 'ratio-medium';
                if (ratio >= 20) return 'ratio-low';
                return 'ratio-none';
            };

            row.innerHTML = `
            <td title="${status.pad_code}" data-pad-code="${status.pad_code}">${status.pad_name || "未知设备"}</td>
            <td class="${statusClass}" title="${status.current_status || '未知'}">${status.current_status || '未知'}</td>
            <td title="运行次数">${status.number_of_run}</td>
            <td title="成功次数">${status.num_of_success}</td>
            <td title="error次数">${status.num_of_error}</td>
            <td title="其他错误">${status.num_other_error}</td>
            <td title="模板ID">${status.temple_id}</td>
            <td class="${getRatioClass(forwardRatio)}" title="转发邮箱: ${status.forward_num || 0}/${totalRuns}">${forwardRatio}%</td>
            <td class="${getRatioClass(phoneRatio)}" title="手机号: ${status.phone_number_counts || 0}/${totalRuns}">${phoneRatio}%</td>
            <td class="${getRatioClass(secondaryEmailRatio)}" title="辅助邮箱: ${status.secondary_email_num || 0}/${totalRuns}">${secondaryEmailRatio}%</td>
            <td title="国家">${status.country || '未设置'}</td>
            <td title="更新时间">${formatDateTime(status.updated_at)}</td>
            <td>
                <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                    <button class="status-btn" onclick="refreshSingleStatus('${status.pad_code}')" title="刷新该设备状态">
                        🔄
                    </button>
                    <button class="status-btn" onclick="openEditDeviceModal('${status.pad_code}')" title="编辑设备配置" style="background-color: var(--warning-color);">
                        ✏️
                    </button>
                </div>
            </td>
        `;

            fragment.appendChild(row);
        });

        statusTableBody.appendChild(fragment);
    }

// 添加 showToast 函数（如果还没有）
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-size: 14px;
        z-index: 10002;
        max-width: 300px;
        word-wrap: break-word;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        animation: slideInFromRight 0.3s ease-out;
    `;

        switch (type) {
            case 'success':
                toast.style.backgroundColor = '#27ae60';
                break;
            case 'error':
                toast.style.backgroundColor = '#e74c3c';
                break;
            case 'warning':
                toast.style.backgroundColor = '#f39c12';
                break;
            default:
                toast.style.backgroundColor = '#3498db';
        }

        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }
        }, 3000);

        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }
        });
    }

// 确保全局可访问
    window.openEditDeviceModal = openEditDeviceModal;
    window.closeEditDeviceModal = closeEditDeviceModal;
    window.saveDeviceConfig = saveDeviceConfig;

    window.refreshSingleStatus = refreshSingleStatus;
    window.showDeviceManager = showDeviceManager;
    window.closeDeviceManager = closeDeviceManager;
    window.syncAllDevices = syncAllDevices;
    window.syncOnlineDevices = syncOnlineDevices;
    window.removeInvalidDevices = removeInvalidDevices;
    window.filterDeviceList = filterDeviceList;
    window.addDevice = addDevice;
    window.removeDevice = removeDevice
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


function showConfigUpdateNotification(message, updatedFields) {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        max-width: 350px;
        animation: slideIn 0.3s ease-out;
    `;

    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="font-size: 18px;">⚙️</span>
            <strong>系统配置已更新</strong>
        </div>
        <div style="font-size: 14px; opacity: 0.9;">
            ${message}
        </div>
        <div style="font-size: 12px; opacity: 0.7; margin-top: 5px;">
            更新项目: ${updatedFields.join(', ')}
        </div>
    `;

    document.body.appendChild(notification);

    // 5秒后自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                notification.parentNode.removeChild(notification);
            }, 300);
        }
    }, 5000);

    // 点击移除
    notification.addEventListener('click', () => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                notification.parentNode.removeChild(notification);
            }, 300);
        }
    });
}

// 添加动画样式
const configNotificationStyles = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;

// 添加样式到页面
if (!document.getElementById('config-notification-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'config-notification-styles';
    styleElement.textContent = configNotificationStyles;
    document.head.appendChild(styleElement);
}