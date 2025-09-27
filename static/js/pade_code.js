let availablePadCodes = [];
let currentPadCodes = [];
let filteredAvailableCodes = [];
let selectedCodes = new Set();
let currentTab = 'available';

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus().then(() => {
        loadAvailablePadCodes();
        loadCurrentPadCodes();
        setupEventListeners();
    });
});

// 设置事件监听器
function setupEventListeners() {
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
    document.getElementById('searchInput').addEventListener('keyup', debounce(applyFilters, 300));
    document.getElementById('statusFilter').addEventListener('change', applyFilters);
    document.getElementById('configFilter').addEventListener('change', applyFilters);

    document.getElementById('selectAll').addEventListener('change', toggleSelectAll);
    document.getElementById('selectNotInConfig').addEventListener('click', selectNotInConfig);
    document.getElementById('selectOnlineOnly').addEventListener('click', selectOnlineOnly);

    document.getElementById('applyCurrentFilters').addEventListener('click', applyCurrentFilters);
    document.getElementById('resetCurrentFilters').addEventListener('click', resetCurrentFilters);
    document.getElementById('currentSearchInput').addEventListener('keyup', debounce(applyCurrentFilters, 300));
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

// 切换标签页
function switchTab(tabName) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // 移除所有按钮的活跃状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 显示选中的标签内容
    document.getElementById(tabName + 'Tab').classList.add('active');

    // 激活对应按钮
    event.target.classList.add('active');

    currentTab = tabName;

    // 根据标签页加载对应数据
    if (tabName === 'current') {
        loadCurrentPadCodes();
    } else if (tabName === 'compare') {
        loadComparison();
    }
}

// 加载云端可用设备
async function loadAvailablePadCodes() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshIcon = document.getElementById('refreshIcon');
    const loadingOverlay = document.getElementById('loadingOverlay');

    try {
        refreshBtn.disabled = true;
        refreshIcon.classList.add('loading-spinner');
        loadingOverlay.style.display = 'flex';
        hideMessages();

        const response = await fetch('/api/pad-codes/available', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP错误! 状态码: ${response.status}`);
        }

        const result = await response.json();
        availablePadCodes = result.data || [];
        filteredAvailableCodes = [...availablePadCodes];

        updateStatsCards(result.summary);
        renderAvailableTable();
        updateSelectedCount();

    } catch (error) {
        console.error('加载云端设备失败:', error);
        showError('加载云端设备失败: ' + error.message);
    } finally {
        refreshBtn.disabled = false;
        refreshIcon.classList.remove('loading-spinner');
        loadingOverlay.style.display = 'none';
    }
}

// 加载当前配置
async function loadCurrentPadCodes() {
    try {
        const response = await fetch('/api/pad-codes/current', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`获取当前配置失败: ${response.status}`);
        }

        const result = await response.json();
        currentPadCodes = result.data || [];
        renderCurrentTable();

    } catch (error) {
        console.error('加载当前配置失败:', error);
        showError('加载当前配置失败: ' + error.message);
    }
}

// 更新统计卡片
function updateStatsCards(summary) {
    const statsCards = document.getElementById('statsCards');

    if (!summary) {
        statsCards.innerHTML = '';
        return;
    }

    statsCards.innerHTML = `
            <div class="stat-card">
                <h3>${summary.total_available}</h3>
                <p>云端可用设备</p>
            </div>
            <div class="stat-card">
                <h3>${summary.total_in_config}</h3>
                <p>当前配置设备</p>
            </div>
            <div class="stat-card">
                <h3>${summary.not_in_config}</h3>
                <p>未配置设备</p>
            </div>
            <div class="stat-card">
                <h3>${summary.config_not_available}</h3>
                <p>配置中但云端不可用</p>
            </div>
        `;
}

// 渲染可用设备表格
function renderAvailableTable() {
    const tableBody = document.getElementById('availableTableBody');
    const emptyState = document.getElementById('availableEmptyState');

    if (filteredAvailableCodes.length === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    const rows = filteredAvailableCodes.map(pad => {
        const isSelected = selectedCodes.has(pad.padCode);
        const statusBadge = pad.status === 1 ?
            '<span class="status-badge status-active">在线</span>' :
            '<span class="status-badge status-inactive">离线</span>';

        const configBadge = pad.isInConfig ?
            '<span class="config-status in-config">已配置</span>' :
            '<span class="config-status not-in-config">未配置</span>';

        return `
                <tr>
                    <td class="checkbox-cell">
                        <input type="checkbox" ${isSelected ? 'checked' : ''}
                               onchange="toggleSelection('${pad.padCode}')"
                               value="${pad.padCode}">
                    </td>
                    <td title="${pad.padCode}">${pad.padCode}</td>
                    <td>${pad.padName || '未命名'}</td>
                    <td>${statusBadge}</td>
                    <td>${configBadge}</td>
                    <td>Android ${pad.androidVersion || '未知'}</td>
                    <td class="device-info">
                        设备IP: ${pad.deviceIp || '未知'}<br>
                        Pad IP: ${pad.padIp || '未知'}
                    </td>
                    <td>${pad.goodName || '未设置'}</td>
                    <td class="expiration-time">${pad.signExpirationTime || '未知'}</td>
                    <td>${formatTimestamp(pad.bootTime)}</td>
                </tr>
            `;
    }).join('');

    tableBody.innerHTML = rows;
}

// 渲染当前配置表格
function renderCurrentTable() {
    const tableBody = document.getElementById('currentTableBody');
    const emptyState = document.getElementById('currentEmptyState');

    if (currentPadCodes.length === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    const rows = currentPadCodes.map(code => {
        const cloudDevice = availablePadCodes.find(pad => pad.padCode === code);
        const cloudStatus = cloudDevice ?
            (cloudDevice.status === 1 ?
                '<span class="status-badge status-active">云端在线</span>' :
                '<span class="status-badge status-inactive">云端离线</span>') :
            '<span class="status-badge status-unknown">云端不存在</span>';

        return `
                <tr>
                    <td class="checkbox-cell">
                        <input type="checkbox" value="${code}" onchange="toggleCurrentSelection('${code}')">
                    </td>
                    <td title="${code}">${code}</td>
                    <td>${cloudStatus}</td>
                    <td>
                        <button class="remove-btn" onclick="removeSingleCode('${code}')">移除</button>
                    </td>
                </tr>
            `;
    }).join('');

    tableBody.innerHTML = rows;
}

// 切换选择状态
function toggleSelection(padCode) {
    if (selectedCodes.has(padCode)) {
        selectedCodes.delete(padCode);
    } else {
        selectedCodes.add(padCode);
    }
    updateSelectedCount();
    updateBulkActions();
}

// 切换全选
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const checkboxes = document.querySelectorAll('#availableTableBody input[type="checkbox"]');

    if (selectAllCheckbox.checked) {
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
            selectedCodes.add(checkbox.value);
        });
    } else {
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
            selectedCodes.delete(checkbox.value);
        });
    }

    updateSelectedCount();
    updateBulkActions();
}

// 选择未配置的设备
function selectNotInConfig() {
    selectedCodes.clear();
    filteredAvailableCodes.forEach(pad => {
        if (!pad.isInConfig) {
            selectedCodes.add(pad.padCode);
        }
    });
    renderAvailableTable();
    updateSelectedCount();
    updateBulkActions();
}

// 选择在线设备
function selectOnlineOnly() {
    selectedCodes.clear();
    filteredAvailableCodes.forEach(pad => {
        if (pad.status === 1) {
            selectedCodes.add(pad.padCode);
        }
    });
    renderAvailableTable();
    updateSelectedCount();
    updateBulkActions();
}

// 更新选择计数
function updateSelectedCount() {
    const countElement = document.getElementById('selectedCount');
    if (countElement) {
        countElement.textContent = `已选择: ${selectedCodes.size}`;
    }
}

// 更新批量操作区域
function updateBulkActions() {
    const bulkActions = document.getElementById('bulkActions');
    if (selectedCodes.size > 0) {
        bulkActions.classList.add('show');
    } else {
        bulkActions.classList.remove('show');
    }
}

// 应用筛选
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const configFilter = document.getElementById('configFilter').value;

    filteredAvailableCodes = availablePadCodes.filter(pad => {
        const matchesSearch = !searchTerm ||
            (pad.padCode && pad.padCode.toLowerCase().includes(searchTerm)) ||
            (pad.padName && pad.padName.toLowerCase().includes(searchTerm)) ||
            (pad.deviceIp && pad.deviceIp.toLowerCase().includes(searchTerm)) ||
            (pad.padIp && pad.padIp.toLowerCase().includes(searchTerm));

        const matchesStatus = !statusFilter || pad.status.toString() === statusFilter;
        const matchesConfig = !configFilter || pad.isInConfig.toString() === configFilter;

        return matchesSearch && matchesStatus && matchesConfig;
    });

    renderAvailableTable();
}

// 重置筛选
function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('configFilter').value = '';
    filteredAvailableCodes = [...availablePadCodes];
    renderAvailableTable();
}

// 同步选中的设备代码
async function syncSelectedCodes() {
    if (selectedCodes.size === 0) {
        showError('请先选择要同步的设备');
        return;
    }

    if (!confirm(`确定要同步选中的 ${selectedCodes.size} 个设备代码吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/sync', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: Array.from(selectedCodes)
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '同步失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        selectedCodes.clear();
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('同步失败:', error);
        showError('同步失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 添加选中的设备代码
async function addSelectedCodes() {
    if (selectedCodes.size === 0) {
        showError('请先选择要添加的设备');
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/add', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: Array.from(selectedCodes)
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '添加失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        selectedCodes.clear();
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('添加失败:', error);
        showError('添加失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 移除选中的设备代码
async function removeSelectedCodes() {
    if (selectedCodes.size === 0) {
        showError('请先选择要移除的设备');
        return;
    }

    if (!confirm(`确定要从配置中移除选中的 ${selectedCodes.size} 个设备代码吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/remove', {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: Array.from(selectedCodes)
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '移除失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        selectedCodes.clear();
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('移除失败:', error);
        showError('移除失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 同步所有可用设备
async function syncAllAvailable() {
    if (!confirm('确定要同步所有云端可用的设备代码吗？这将添加所有云端设备到配置中。')) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/sync', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: []  // 空数组表示同步所有
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '同步失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('同步失败:', error);
        showError('同步失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 仅同步在线设备
async function syncOnlineOnly() {
    const onlineCodes = availablePadCodes
        .filter(pad => pad.status === 1)
        .map(pad => pad.padCode);

    if (onlineCodes.length === 0) {
        showError('没有在线的设备可同步');
        return;
    }

    if (!confirm(`确定要同步 ${onlineCodes.length} 个在线设备吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/sync', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: onlineCodes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '同步失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('同步在线设备失败:', error);
        showError('同步在线设备失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 仅同步未配置设备
async function syncNotInConfig() {
    const notConfiguredCodes = availablePadCodes
        .filter(pad => !pad.isInConfig)
        .map(pad => pad.padCode);

    if (notConfiguredCodes.length === 0) {
        showError('没有未配置的设备可同步');
        return;
    }

    if (!confirm(`确定要同步 ${notConfiguredCodes.length} 个未配置的设备吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/add', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: notConfiguredCodes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '同步失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('同步未配置设备失败:', error);
        showError('同步未配置设备失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 当前配置筛选
function applyCurrentFilters() {
    const searchTerm = document.getElementById('currentSearchInput').value.toLowerCase();
    // 这里可以添加当前配置的筛选逻辑
    renderCurrentTable();
}

function resetCurrentFilters() {
    document.getElementById('currentSearchInput').value = '';
    renderCurrentTable();
}

// 切换当前配置选择
function toggleCurrentSelection(code) {
    // 当前配置的选择逻辑
}

// 从配置中移除选中设备
async function removeSelectedFromConfig() {
    const checkboxes = document.querySelectorAll('#currentTableBody input[type="checkbox"]:checked');
    const selectedCurrentCodes = Array.from(checkboxes).map(cb => cb.value);

    if (selectedCurrentCodes.length === 0) {
        showError('请先选择要移除的设备');
        return;
    }

    if (!confirm(`确定要从配置中移除选中的 ${selectedCurrentCodes.length} 个设备吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/remove', {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: selectedCurrentCodes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '移除失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('移除失败:', error);
        showError('移除失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 移除单个设备代码
async function removeSingleCode(code) {
    if (!confirm(`确定要移除设备代码 "${code}" 吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/remove', {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: [code]
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '移除失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('移除失败:', error);
        showError('移除失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 验证当前配置有效性
async function validateCurrentConfig() {
    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/compare', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('验证失败');
        }

        const result = await response.json();

        let message = `配置验证结果：\n`;
        message += `云端总设备: ${result.cloud_total}\n`;
        message += `本地配置: ${result.local_total}\n`;
        message += `有效配置: ${result.in_both}\n`;
        message += `无效配置: ${result.only_in_local.count}\n`;
        message += `可添加设备: ${result.only_in_cloud.count}`;

        if (result.only_in_local.count > 0) {
            message += `\n\n无效设备代码: ${result.only_in_local.codes.join(', ')}`;
        }

        alert(message);

    } catch (error) {
        console.error('验证失败:', error);
        showError('验证失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 加载对比数据
async function loadComparison() {
    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/compare', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('获取对比数据失败');
        }

        const result = await response.json();
        renderComparisonData(result);

    } catch (error) {
        console.error('加载对比数据失败:', error);
        showError('加载对比数据失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 渲染对比数据
function renderComparisonData(data) {
    const comparisonGrid = document.getElementById('comparisonGrid');
    const syncRecommendations = document.getElementById('syncRecommendations');

    comparisonGrid.innerHTML = `
            <div class="comparison-card">
                <h4>📊 统计总览</h4>
                <div class="metric-row">
                    <span class="metric-label">云端总设备</span>
                    <span class="metric-value">${data.cloud_total}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">本地配置设备</span>
                    <span class="metric-value">${data.local_total}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">有效配置</span>
                    <span class="metric-value positive">${data.in_both}</span>
                </div>
            </div>

            <div class="comparison-card">
                <h4>🆕 可添加设备 (${data.only_in_cloud.count})</h4>
                <div class="code-list">
                    ${data.only_in_cloud.codes.length > 0 ?
        data.only_in_cloud.codes.map(code =>
            `<div class="code-item">${code}</div>`
        ).join('') :
        '<div class="code-item">无</div>'
    }
                </div>
                ${data.only_in_cloud.count > 0 ?
        `<button onclick="addCloudOnlyCodes()" class="add-btn" style="margin-top: 10px;">添加这些设备</button>` :
        ''
    }
            </div>

            <div class="comparison-card">
                <h4>⚠️ 无效配置 (${data.only_in_local.count})</h4>
                <div class="code-list">
                    ${data.only_in_local.codes.length > 0 ?
        data.only_in_local.codes.map(code =>
            `<div class="code-item">${code}</div>`
        ).join('') :
        '<div class="code-item">无</div>'
    }
                </div>
                ${data.only_in_local.count > 0 ?
        `<button onclick="removeInvalidCodes()" class="remove-btn" style="margin-top: 10px;">移除这些设备</button>` :
        ''
    }
            </div>
        `;

    // 显示同步建议
    if (data.only_in_cloud.count > 0 || data.only_in_local.count > 0) {
        syncRecommendations.style.display = 'block';
        syncRecommendations.innerHTML = `
                <h4>🔄 同步建议</h4>
                <p>
                    建议您：
                    ${data.only_in_cloud.count > 0 ? `添加 ${data.only_in_cloud.count} 个云端新设备到配置中；` : ''}
                    ${data.only_in_local.count > 0 ? `移除 ${data.only_in_local.count} 个无效的配置设备。` : ''}
                </p>
                <div style="margin-top: 10px;">
                    ${data.only_in_cloud.count > 0 && data.only_in_local.count > 0 ?
            `<button onclick="autoSync()" class="add-btn">🔄 自动同步（添加新设备+移除无效设备）</button>` :
            ''
        }
                </div>
            `;
    } else {
        syncRecommendations.style.display = 'none';
    }
}

// 添加仅云端存在的设备
async function addCloudOnlyCodes() {
    // 重新获取最新的对比数据
    const response = await fetch('/api/pad-codes/compare', {
        headers: getAuthHeaders()
    });
    const data = await response.json();

    if (data.only_in_cloud.codes.length === 0) {
        showError('没有可添加的设备');
        return;
    }

    if (!confirm(`确定要添加 ${data.only_in_cloud.codes.length} 个云端设备到配置中吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/add', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: data.only_in_cloud.codes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '添加失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();
        await loadComparison();

    } catch (error) {
        console.error('添加失败:', error);
        showError('添加失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 移除无效的设备代码
async function removeInvalidCodes() {
    // 重新获取最新的对比数据
    const response = await fetch('/api/pad-codes/compare', {
        headers: getAuthHeaders()
    });
    const data = await response.json();

    if (data.only_in_local.codes.length === 0) {
        showError('没有无效的设备需要移除');
        return;
    }

    if (!confirm(`确定要移除 ${data.only_in_local.codes.length} 个无效的设备代码吗？\n\n这些设备在云端不存在：\n${data.only_in_local.codes.join('\n')}`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/remove', {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: data.only_in_local.codes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '移除失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();
        await loadComparison();

    } catch (error) {
        console.error('移除失败:', error);
        showError('移除失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 自动同步
async function autoSync() {
    if (!confirm('确定要执行自动同步吗？\n\n这将：\n1. 添加云端存在但本地未配置的设备\n2. 移除本地配置但云端不存在的设备')) {
        return;
    }

    try {
        showLoading(true);

        // 获取最新对比数据
        const compareResponse = await fetch('/api/pad-codes/compare', {
            headers: getAuthHeaders()
        });
        const compareData = await compareResponse.json();

        let successMessages = [];

        // 先添加新设备
        if (compareData.only_in_cloud.codes.length > 0) {
            const addResponse = await fetch('/api/pad-codes/add', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    selected_codes: compareData.only_in_cloud.codes
                })
            });

            if (addResponse.ok) {
                const addResult = await addResponse.json();
                successMessages.push(`添加: ${addResult.message}`);
            }
        }

        // 再移除无效设备
        if (compareData.only_in_local.codes.length > 0) {
            const removeResponse = await fetch('/api/pad-codes/remove', {
                method: 'DELETE',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    selected_codes: compareData.only_in_local.codes
                })
            });

            if (removeResponse.ok) {
                const removeResult = await removeResponse.json();
                successMessages.push(`移除: ${removeResult.message}`);
            }
        }

        if (successMessages.length > 0) {
            showSuccess('自动同步完成！\n' + successMessages.join('\n'));
        }

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();
        await loadComparison();

    } catch (error) {
        console.error('自动同步失败:', error);
        showError('自动同步失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 危险操作：用云端代码完全替换本地配置
async function replaceWithCloudCodes() {
    if (!confirm('⚠️ 危险操作警告！\n\n这将用云端的所有设备代码完全替换当前配置，原有配置将丢失！\n\n确定要继续吗？')) {
        return;
    }

    if (!confirm('最后确认：您确定要用云端设备代码完全替换当前配置吗？\n\n此操作不可撤销！')) {
        return;
    }

    try {
        showLoading(true);

        const cloudCodes = availablePadCodes.map(pad => pad.padCode);

        const response = await fetch('/api/pad-codes/replace', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: cloudCodes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '替换失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载数据
        selectedCodes.clear();
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('替换失败:', error);
        showError('替换失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 危险操作：清空所有设备代码
async function clearAllCodes() {
    if (!confirm('⚠️ 危险操作警告！\n\n这将清空所有设备代码配置！\n\n确定要继续吗？')) {
        return;
    }

    if (!confirm('最后确认：您确定要清空所有设备代码吗？\n\n此操作不可撤销！')) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/replace', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: []
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '清空失败');
        }

        showSuccess('所有设备代码已清空');

        // 重新加载数据
        selectedCodes.clear();
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('清空失败:', error);
        showError('清空失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 格式化时间戳
function formatTimestamp(timestamp) {
    if (!timestamp) return '未知';
    try {
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        });
    } catch (e) {
        return '无效时间';
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

// 显示/隐藏加载状态
function showLoading(show) {
    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => {
        btn.disabled = show;
    });
}

// 显示错误信息
function showError(message) {
    hideMessages();
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorElement.style.display = 'flex';

    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 5000);
}

// 显示成功信息
function showSuccess(message) {
    hideMessages();
    const successElement = document.getElementById('success');
    const successMessage = document.getElementById('successMessage');
    successMessage.textContent = message;
    successElement.style.display = 'flex';

    setTimeout(() => {
        successElement.style.display = 'none';
    }, 3000);
}

// 隐藏所有消息
function hideMessages() {
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
}