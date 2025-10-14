// ========== 全局变量声明 ==========
let allAccounts = [];
let filteredAccounts = [];
let currentPage = 1;
const pageSize = 50;
let totalPages = 0;
let isFetching = false;
let fetchMode = 'none';
let currentView = 'status';
let websocket = null;
let reconnectInterval = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let isConnecting = false;

// ========== 全局函数声明（需要被 HTML onclick 调用的函数）==========

// 显示添加设备弹窗
function showAddDeviceModal() {
    document.getElementById('addDeviceModal').style.display = 'flex';
    document.getElementById('addDeviceForm').reset();
}

// 关闭添加设备弹窗
function closeAddDeviceModal() {
    document.getElementById('addDeviceModal').style.display = 'none';
    document.getElementById('addDeviceForm').reset();
}

// 添加新设备
async function addNewDevice() {
    const form = document.getElementById('addDeviceForm');

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const padCode = document.getElementById('addPadCode').value.trim();
    const countryCode = document.getElementById('addCountryCode').value.trim();

    if (!padCode || !countryCode) {
        showToast('请填写所有必填项', 'error');
        return;
    }

    try {
        showLoading(true);

        const response = await authenticatedFetch('/add_cloud_status', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                pad_code: padCode,
                country_code: countryCode
            })
        });

        if (!response || !response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '添加失败');
        }

        const result = await response.json();
        showToast(result.msg || `设备 ${padCode} 添加成功`, 'success');
        closeAddDeviceModal();

        setTimeout(() => {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                requestStatusUpdate();
            } else {
                fetchCloudStatus();
            }
        }, 500);

    } catch (error) {
        console.error('添加设备失败:', error);
        showToast('添加失败: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 打开编辑设备配置弹窗
function openEditDeviceModal(padCode) {
    const statusTableBody = document.getElementById('statusTableBody');
    const rows = statusTableBody.querySelectorAll('tr');

    let deviceData = null;
    for (const row of rows) {
        const padCodeCell = row.cells[0];
        if (padCodeCell && padCodeCell.getAttribute('data-pad-code') === padCode) {
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
                isSecondaryEmail: row.getAttribute('data-is-secondary-email') === 'true',
                isRandomProxy: row.getAttribute('data-is-random-proxy') === 'true'
            };
            break;
        }
    }

    if (!deviceData) {
        showToast('未找到设备信息', 'error');
        return;
    }

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
    document.getElementById('editIsRandomProxy').checked = deviceData.isRandomProxy;

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
        is_secondary_email: document.getElementById('editIsSecondaryEmail').checked,
        is_random_proxy: document.getElementById('editIsRandomProxy').checked
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

// 删除云机设备
async function deleteCloudDevice(padCode) {
    const confirmation = confirm(
        `⚠️ 确定要删除设备 "${padCode}" 吗？\n\n` +
        `此操作将：\n` +
        `• 从状态监控列表中移除该设备\n` +
        `• 删除该设备的所有状态数据\n` +
        `• 此操作不可撤销\n\n` +
        `是否继续？`
    );

    if (!confirmation) {
        return;
    }

    try {
        showLoading(true);

        const response = await authenticatedFetch(`/cloud_status/${padCode}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response || !response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '删除失败');
        }

        const result = await response.json();
        showToast(result.message || `设备 ${padCode} 删除成功`, 'success');

        if (websocket && websocket.readyState === WebSocket.OPEN) {
            requestStatusUpdate();
        } else {
            await fetchCloudStatus();
        }

    } catch (error) {
        console.error('删除云机设备失败:', error);
        showToast('删除失败: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// 刷新单个状态
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

// 显示设备管理器
async function showDeviceManager() {
    document.getElementById('deviceManagerModal').style.display = 'flex';
    await loadDeviceManagerData();
}

// 关闭设备管理器
function closeDeviceManager() {
    document.getElementById('deviceManagerModal').style.display = 'none';
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

// ========== DOMContentLoaded 事件处理 ==========
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus().then();

    // DOM元素引用
    const elements = {
        fetchAllBtn: document.getElementById('fetchAll'),
        fetchPageBtn: document.getElementById('fetchPage'),
        fetchSingleBtn: document.getElementById('fetchSingle'),
        fetchSingleLockBtn: document.getElementById('fetchSingleLock'),
        accountIdInput: document.getElementById('accountId'),
        searchInput: document.getElementById('searchInput'),
        statusFilter: document.getElementById('statusFilter'),
        typeFilter: document.getElementById('typeFilter'),
        applyFiltersBtn: document.getElementById('applyFilters'),
        resetFiltersBtn: document.getElementById('resetFilters'),
        maskPasswordsCheck: document.getElementById('maskPasswords'),
        exportCSVBtn: document.getElementById('exportCSV'),
        accountsBody: document.getElementById('accountsBody'),
        loadingElement: document.getElementById('loading'),
        errorElement: document.getElementById('error'),
        errorMessage: document.getElementById('errorMessage'),
        emptyState: document.getElementById('emptyState'),
        tableContainer: document.getElementById('tableContainer'),
        pagination: document.getElementById('pagination'),
        firstPageBtn: document.getElementById('firstPage'),
        prevPageBtn: document.getElementById('prevPage'),
        nextPageBtn: document.getElementById('nextPage'),
        lastPageBtn: document.getElementById('lastPage'),
        pageNumbers: document.getElementById('pageNumbers'),
        paginationInfo: document.getElementById('paginationInfo'),
        progressBar: document.getElementById('progressBar'),
        statusTableBody: document.getElementById('statusTableBody'),
        toggleViewBtn: document.getElementById('toggleView'),
        accountsSection: document.getElementById('accountsSection'),
        statusSection: document.getElementById('statusSection'),
        logoutBtn: document.getElementById('logoutBtn'),
        refreshAllStatusBtn: document.getElementById('refreshAllStatus'),
        statusEmptyState: document.getElementById('statusEmptyState'),
        connectionStatus: document.getElementById('connectionStatus')
    };

    init();

    function init() {
        setupEventListeners();

        if (elements.accountsSection) elements.accountsSection.style.display = 'none';
        if (elements.statusSection) elements.statusSection.style.display = 'block';
        if (elements.toggleViewBtn) elements.toggleViewBtn.textContent = '切换到账户管理';

        initWebSocket();
        updateUI();
    }

    function setupEventListeners() {
        elements.fetchAllBtn && elements.fetchAllBtn.addEventListener('click', fetchAllAccounts);
        elements.fetchPageBtn && elements.fetchPageBtn.addEventListener('click', fetchAccountsByPage);
        elements.fetchSingleBtn && elements.fetchSingleBtn.addEventListener('click', fetchSingleAccount);
        elements.fetchSingleLockBtn && elements.fetchSingleLockBtn.addEventListener('click', fetchSingleAccountLocked);

        elements.firstPageBtn && elements.firstPageBtn.addEventListener('click', () => goToPage(1));
        elements.prevPageBtn && elements.prevPageBtn.addEventListener('click', () => goToPage(currentPage - 1));
        elements.nextPageBtn && elements.nextPageBtn.addEventListener('click', () => goToPage(currentPage + 1));
        elements.lastPageBtn && elements.lastPageBtn.addEventListener('click', () => goToPage(totalPages));

        elements.applyFiltersBtn && elements.applyFiltersBtn.addEventListener('click', applyFilters);
        elements.resetFiltersBtn && elements.resetFiltersBtn.addEventListener('click', resetFilters);
        elements.searchInput && elements.searchInput.addEventListener('keyup', debounce(applyFilters, 300));

        elements.maskPasswordsCheck && elements.maskPasswordsCheck.addEventListener('change', togglePasswordMask);
        elements.exportCSVBtn && elements.exportCSVBtn.addEventListener('click', exportToCSV);

        elements.tableContainer && elements.tableContainer.addEventListener('scroll', debounce(handleScroll, 200));

        elements.toggleViewBtn && elements.toggleViewBtn.addEventListener('click', toggleView);
        elements.logoutBtn && elements.logoutBtn.addEventListener('click', logout);
        elements.refreshAllStatusBtn && elements.refreshAllStatusBtn.addEventListener('click', requestStatusUpdate);

        document.addEventListener('visibilitychange', handleVisibilityChange);
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

                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }

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
                }
            };

            websocket.onclose = function(event) {
                isConnecting = false;
                websocket = null;

                if (event.code !== 1000 && currentView === 'status') {
                    updateConnectionStatus('disconnected');
                    attemptReconnect();
                } else {
                    updateConnectionStatus('disconnected');
                }
            };

            websocket.onerror = function() {
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
                if (websocket && websocket.readyState === WebSocket.OPEN) {
                    websocket.send(JSON.stringify({
                        type: 'pong',
                        client_time: new Date().toISOString()
                    }));
                }
                break;

            case 'config_updated':
                if (message.data) {
                    showConfigUpdateNotification(message.data.message, message.data.updated_fields);

                    if (currentView === 'status') {
                        setTimeout(() => {
                            requestStatusUpdate();
                        }, 2000);
                    }
                }
                break;

            default:
                console.warn('⚠️  未知WebSocket消息类型:', messageType);
        }
    }

    function requestStatusUpdate() {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'subscribe_status',
                timestamp: new Date().toISOString()
            }));
        } else {
            fetchCloudStatus();
        }
    }

    function updateConnectionStatus(status) {
        if (!elements.connectionStatus) return;

        const statusMap = {
            'connected': { text: '实时连接', class: 'status-success', icon: '🟢' },
            'connecting': { text: '连接中...', class: 'status-pending', icon: '🟡' },
            'reconnecting': { text: '重连中...', class: 'status-pending', icon: '🟡' },
            'disconnected': { text: '已断开', class: 'status-error', icon: '🔴' },
            'error': { text: '连接错误', class: 'status-error', icon: '❌' },
            'failed': { text: '连接失败', class: 'status-error', icon: '❌' }
        };

        const statusInfo = statusMap[status] || statusMap['disconnected'];
        elements.connectionStatus.innerHTML = `
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
            return;
        }

        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);

        updateConnectionStatus('reconnecting');

        reconnectInterval = setTimeout(() => {
            reconnectAttempts++;
            reconnectInterval = null;
            initWebSocket();
        }, delay);
    }

    function updateSingleStatus(statusData) {
        if (!elements.statusTableBody || !statusData.pad_code) {
            return;
        }

        const rows = elements.statusTableBody.querySelectorAll('tr');

        for (const row of rows) {
            const padCodeCell = row.cells[0];
            if (padCodeCell && padCodeCell.textContent.trim() === statusData.pad_code) {
                const statusCell = row.cells[1];
                if (statusCell && statusData.current_status) {
                    statusCell.textContent = statusData.current_status;
                    statusCell.className = getStatusClass(statusData.current_status);

                    statusCell.style.animation = 'highlight 2s ease-out';
                    setTimeout(() => {
                        statusCell.style.animation = '';
                    }, 2000);
                }
                break;
            }
        }
    }

    function requestFullStatusUpdate() {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({
                type: 'request_full_update',
                timestamp: new Date().toISOString()
            }));
        } else {
            fetchCloudStatus();
        }
    }

    function toggleView() {
        if (currentView === 'accounts') {
            currentView = 'status';
            if (elements.accountsSection) elements.accountsSection.style.display = 'none';
            if (elements.statusSection) elements.statusSection.style.display = 'block';
            if (elements.toggleViewBtn) elements.toggleViewBtn.textContent = '切换到账户管理';

            initWebSocket();

            setTimeout(() => {
                if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                    fetchCloudStatus();
                }
            }, 1000);

        } else {
            currentView = 'accounts';
            if (elements.accountsSection) elements.accountsSection.style.display = 'block';
            if (elements.statusSection) elements.statusSection.style.display = 'none';
            if (elements.toggleViewBtn) elements.toggleViewBtn.textContent = '切换到状态监控';
            closeWebSocket();
        }
    }

    function handleVisibilityChange() {
        if (document.hidden) {
            // 页面隐藏时不做处理
        } else {
            if (currentView === 'status') {
                if (!websocket || websocket.readyState !== WebSocket.OPEN) {
                    initWebSocket();
                } else {
                    requestStatusUpdate();
                }
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

    // 工具函数
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

    function updateProgress(progress) {
        if (elements.progressBar) {
            elements.progressBar.style.width = `${progress}%`;
        }
    }

    function showLoading(show = true) {
        if (show) {
            isFetching = true;
            if (elements.loadingElement) elements.loadingElement.style.display = 'flex';
            if (elements.errorElement) elements.errorElement.style.display = 'none';
        } else {
            isFetching = false;
            if (elements.loadingElement) elements.loadingElement.style.display = 'none';
            updateProgress(0);
        }
        updateUI();
    }

    function showError(message) {
        if (elements.errorMessage) elements.errorMessage.textContent = message;
        if (elements.errorElement) elements.errorElement.style.display = 'flex';
        console.error(message);
    }

    function updateUI() {
        if (elements.fetchAllBtn) elements.fetchAllBtn.disabled = isFetching;
        if (elements.fetchPageBtn) elements.fetchPageBtn.disabled = isFetching;
        if (elements.fetchSingleBtn) elements.fetchSingleBtn.disabled = isFetching || !elements.accountIdInput?.value;
        if (elements.fetchSingleLockBtn) elements.fetchSingleLockBtn.disabled = isFetching || !elements.accountIdInput?.value;
        if (elements.applyFiltersBtn) elements.applyFiltersBtn.disabled = isFetching;

        if (elements.firstPageBtn) elements.firstPageBtn.disabled = currentPage === 1 || isFetching;
        if (elements.prevPageBtn) elements.prevPageBtn.disabled = currentPage === 1 || isFetching;
        if (elements.nextPageBtn) elements.nextPageBtn.disabled = currentPage === totalPages || isFetching;
        if (elements.lastPageBtn) elements.lastPageBtn.disabled = currentPage === totalPages || isFetching;

        if (elements.pagination) {
            if (fetchMode === 'page' && filteredAccounts.length > 0) {
                elements.pagination.style.display = 'flex';
                updatePaginationUI();
            } else {
                elements.pagination.style.display = 'none';
            }
        }

        if (elements.emptyState && currentView === 'accounts') {
            if (filteredAccounts.length === 0 && !isFetching) {
                elements.emptyState.style.display = 'block';
            } else {
                elements.emptyState.style.display = 'none';
            }
        }
    }

    function updatePaginationUI() {
        if (!elements.pageNumbers) return;

        elements.pageNumbers.innerHTML = '';

        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);

        if (endPage - startPage < 4) {
            if (currentPage < 3) {
                endPage = Math.min(5, totalPages);
            } else {
                startPage = Math.max(1, totalPages - 4);
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.textContent = i.toString();
            pageBtn.className = i === currentPage ? 'active' : 'secondary';
            pageBtn.addEventListener('click', () => goToPage(i));
            elements.pageNumbers.appendChild(pageBtn);
        }

        if (elements.paginationInfo) {
            const startItem = (currentPage - 1) * pageSize + 1;
            const endItem = Math.min(currentPage * pageSize, filteredAccounts.length);
            elements.paginationInfo.textContent = `显示 ${startItem}-${endItem} 条，共 ${filteredAccounts.length} 条记录`;
        }
    }

    function goToPage(page) {
        if (page < 1 || page > totalPages || page === currentPage) return;

        currentPage = page;
        renderAccounts(getPaginatedAccounts());
        updateUI();
        if (elements.tableContainer) elements.tableContainer.scrollTo(0, 0);
    }

    function handleScroll() {
        if (fetchMode !== 'page' || isFetching || !elements.tableContainer) return;

        const { scrollTop, scrollHeight, clientHeight } = elements.tableContainer;
        const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;

        if (isNearBottom && currentPage < totalPages) {
            goToPage(currentPage + 1);
        }
    }

    function clearTable() {
        if (elements.accountsBody) elements.accountsBody.innerHTML = '';
    }

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

    function getPaginatedAccounts() {
        if (fetchMode === 'all') {
            return filteredAccounts;
        } else {
            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = startIndex + pageSize;
            return filteredAccounts.slice(startIndex, endIndex);
        }
    }

    function renderAccounts(accounts) {
        clearTable();

        if (!Array.isArray(accounts)) {
            accounts = [accounts];
        }

        if (accounts.length === 0) {
            return;
        }

        const fragment = document.createDocumentFragment();
        const maskPasswords = elements.maskPasswordsCheck?.checked || false;

        accounts.forEach(account => {
            const row = document.createElement('tr');

            const statusText = account.status === 1 ? '活跃' : '禁用';
            const statusClass = account.status === 1 ? 'status-active' : 'status-inactive';
            const typeClass = `type-${account.type}`;
            const code = account.code ? account.code : '无';
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

        if (elements.accountsBody) elements.accountsBody.appendChild(fragment);

        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                if (elements.accountIdInput) elements.accountIdInput.value = this.getAttribute('data-id');
                fetchSingleAccount();
            });
        });
    }

    async function fetchAllAccounts() {
        try {
            showLoading();
            clearTable();
            fetchMode = 'all';

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

            applyFilters(false);
            updateProgress(100);
        } catch (error) {
            showError(`获取全部账户失败: ${error.message}`);
            fetchMode = 'none';
        } finally {
            showLoading(false);
        }
    }

    async function fetchAccountsByPage() {
        try {
            showLoading();
            clearTable();
            fetchMode = 'page';
            currentPage = 1;

            const response = await authenticatedFetch(`/accounts`);

            if (!response || !response.ok) {
                throw new Error(`HTTP错误! 状态码: ${response?.status || 'unknown'}`);
            }

            allAccounts = await response.json();
            filteredAccounts = [...allAccounts];
            totalPages = Math.ceil(filteredAccounts.length / pageSize);

            applyFilters(false);
        } catch (error) {
            showError(`获取账户失败: ${error.message}`);
            fetchMode = 'none';
        } finally {
            showLoading(false);
        }
    }

    async function fetchSingleAccount() {
        const accountId = elements.accountIdInput?.value?.trim();

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
            fetchMode = 'none';
        } finally {
            showLoading(false);
        }
    }

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
            fetchMode = 'none';
        } finally {
            showLoading(false);
        }
    }

    function applyFilters(fetchData = true) {
        if (fetchData && fetchMode === 'none') {
            fetchAllAccounts();
            return;
        }

        const searchTerm = elements.searchInput?.value?.toLowerCase() || '';
        const statusValue = elements.statusFilter?.value || '';
        const typeValue = elements.typeFilter?.value || '';

        filteredAccounts = allAccounts.filter(account => {
            const matchesSearch =
                account.account.toLowerCase().includes(searchTerm) ||
                (account.code && account.code.toLowerCase().includes(searchTerm));

            const matchesStatus = statusValue === '' || account.status.toString() === statusValue;
            const matchesType = typeValue === '' || account.type.toString() === typeValue;

            return matchesSearch && matchesStatus && matchesType;
        });

        totalPages = Math.ceil(filteredAccounts.length / pageSize);
        currentPage = 1;

        renderAccounts(getPaginatedAccounts());
        updateUI();
    }

    function resetFilters() {
        if (elements.searchInput) elements.searchInput.value = '';
        if (elements.statusFilter) elements.statusFilter.value = '';
        if (elements.typeFilter) elements.typeFilter.value = '';
        applyFilters();
    }

    function togglePasswordMask() {
        renderAccounts(getPaginatedAccounts());
    }

    function exportToCSV() {
        if (filteredAccounts.length === 0) {
            showError('没有数据可导出');
            return;
        }

        try {
            const headers = ['ID', '账号', '密码', '类型', '状态', '代码', '创建时间'];

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

            const csvContent = [headers.join(','), ...rows].join('\n');

            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `账户数据_${new Date().toISOString().slice(0, 10)}.csv`;
            link.click();

            setTimeout(() => {
                URL.revokeObjectURL(url);
            }, 100);
        } catch (error) {
            showError(`导出CSV失败: ${error.message}`);
        }
    }

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

    function renderStatusTable(statusData) {
        if (!elements.statusTableBody) {
            return;
        }

        elements.statusTableBody.innerHTML = '';

        if (!Array.isArray(statusData) || statusData.length === 0) {
            if (elements.statusEmptyState) elements.statusEmptyState.style.display = 'block';
            elements.statusTableBody.innerHTML = '<tr><td colspan="14" style="text-align: center; padding: 20px; color: #666;">暂无状态数据</td></tr>';
            return;
        }

        if (elements.statusEmptyState) elements.statusEmptyState.style.display = 'none';

        const fragment = document.createDocumentFragment();

        statusData.forEach((status, index) => {
            const row = document.createElement('tr');
            row.style.animationDelay = `${index * 50}ms`;

            row.setAttribute('data-temple-id', status.temple_id || '');
            row.setAttribute('data-country', status.country || '');
            row.setAttribute('data-code', status.code || '');
            row.setAttribute('data-proxy', status.proxy || '');
            row.setAttribute('data-time-zone', status.time_zone || '');
            row.setAttribute('data-language', status.language || '');
            row.setAttribute('data-latitude', status.latitude || '');
            row.setAttribute('data-longitude', status.longitude || '');
            row.setAttribute('data-is-secondary-email', status.is_secondary_email || false);
            row.setAttribute('data-is-random-proxy', status.is_random_proxy || false);

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
                <td title="运行次数">${status.number_of_run - 1}</td>
                <td title="成功次数">${status.num_of_success}</td>
                <td title="error次数">${status.num_of_error}</td>
                <td title="其他错误">${status.num_other_error}</td>
                <td title="模板ID">${status.temple_id || "未设置"}</td>
                <td class="${getRatioClass(forwardRatio)}" title="转发邮箱: ${status.forward_num || 0}/${totalRuns}">${forwardRatio}%</td>
                <td class="${getRatioClass(phoneRatio)}" title="手机号: ${status.phone_number_counts || 0}/${totalRuns}">${phoneRatio}%</td>
                <td class="${getRatioClass(secondaryEmailRatio)}" title="辅助邮箱: ${status.secondary_email_num || 0}/${totalRuns}">${secondaryEmailRatio}%</td>
                <td title="国家">${status.country || '未设置'}</td>
                <td title="更新时间">${formatDateTime(status.updated_at)}</td>
                <td title="随机代理状态">${status.is_random_proxy ? '✓ 启用' : '✗ 关闭'}</td>
                <td>
                    <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                        <button class="status-btn" onclick="refreshSingleStatus('${status.pad_code}')" title="刷新该设备状态">
                            🔄
                        </button>
                        <button class="status-btn" onclick="openEditDeviceModal('${status.pad_code}')" title="编辑设备配置" style="background-color: var(--warning-color);">
                            ✏️
                        </button>
                        <button class="status-btn" onclick="deleteCloudDevice('${status.pad_code}')" title="删除该设备" style="background-color: var(--danger-color);">
                            🗑️
                        </button>
                    </div>
                </td>
            `;

            fragment.appendChild(row);
        });

        elements.statusTableBody.appendChild(fragment);
    }

    // 设备管理相关变量和函数
    let allCloudDevices = [];
    let currentConfiguredDevices = [];

    async function loadDeviceManagerData() {
        try {
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

    function updateDeviceStats() {
        const configuredSet = new Set(currentConfiguredDevices);
        const notConfigured = allCloudDevices.filter(d => !configuredSet.has(d.padCode));

        const configuredCountEl = document.getElementById('configuredCount');
        const cloudTotalCountEl = document.getElementById('cloudTotalCount');
        const notConfiguredCountEl = document.getElementById('notConfiguredCount');

        if (configuredCountEl) configuredCountEl.textContent = currentConfiguredDevices.length;
        if (cloudTotalCountEl) cloudTotalCountEl.textContent = allCloudDevices.length;
        if (notConfiguredCountEl) notConfiguredCountEl.textContent = notConfigured.length;
    }

    function renderDeviceList() {
        const tbody = document.getElementById('deviceListBody');
        if (!tbody) return;

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

    // 将内部函数暴露到全局作用域（仅用于内部调用）
    window.requestStatusUpdate = requestStatusUpdate;
    window.fetchCloudStatus = fetchCloudStatus;
    window.loadDeviceManagerData = loadDeviceManagerData;
});

// ========== 辅助函数 ==========

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

function showConfigUpdateNotification(message, updatedFields) {
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

    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                notification.parentNode.removeChild(notification);
            }, 300);
        }
    }, 5000);

    notification.addEventListener('click', () => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                notification.parentNode.removeChild(notification);
            }, 300);
        }
    });
}

// 添加CSS动画
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

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

    @keyframes slideInFromRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes highlight {
        0% { background-color: rgba(52, 152, 219, 0.3); }
        100% { background-color: transparent; }
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

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
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