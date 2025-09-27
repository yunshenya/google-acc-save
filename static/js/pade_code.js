let availablePadCodes = [];
let currentPadCodes = [];
let filteredAvailableCodes = [];
let selectedCodes = new Set();
let currentTab = 'available';

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', async function() {
    checkAuthStatus().then(() => {
        loadAvailablePadCodes();
        loadCurrentPadCodes();
        setupEventListeners();
        initializeAdvancedFeatures();
    });
});

// 设置事件监听器
function setupEventListeners() {
    // 原有事件监听器
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
    document.getElementById('searchInput').addEventListener('keyup', debounce(applyFilters, 300));
    document.getElementById('statusFilter').addEventListener('change', applyFilters);
    document.getElementById('configFilter').addEventListener('change', applyFilters);

    // 选择相关事件
    document.getElementById('selectAll').addEventListener('change', toggleSelectAll);
    document.getElementById('selectNotInConfig').addEventListener('click', selectNotInConfig);
    document.getElementById('selectOnlineOnly').addEventListener('click', selectOnlineOnly);

    // 新增事件监听器
    document.getElementById('selectOfflineOnly').addEventListener('click', selectOfflineOnly);
    document.getElementById('selectByAndroidVersion').addEventListener('click', selectByAndroidVersion);
    document.getElementById('headerSelectAll').addEventListener('change', toggleSelectAllFromHeader);

    // 当前配置筛选
    document.getElementById('applyCurrentFilters').addEventListener('click', applyCurrentFilters);
    document.getElementById('resetCurrentFilters').addEventListener('click', resetCurrentFilters);
    document.getElementById('currentSearchInput').addEventListener('keyup', debounce(applyCurrentFilters, 300));
}

// 初始化高级功能
function initializeAdvancedFeatures() {
    // 监听选择变化以更新UI
    document.addEventListener('selectionChanged', updateSelectionUI);

    // 键盘快捷键
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // 初始化表格样式
    initializeTableStyles();
}

// 处理键盘快捷键
async function handleKeyboardShortcuts(event) {
    if (event.ctrlKey || event.metaKey) {
        switch(event.key) {
            case 'a':
                event.preventDefault();
                selectAllVisible();
                break;
            case 'd':
                event.preventDefault();
                clearSelection();
                break;
            case 'i':
                event.preventDefault();
                if (selectedCodes.size > 0) {
                    await importSelectedDevices('add');
                }
                break;
        }
    }
}

// 切换标签页
function switchTab(tabName) {
    // 隐藏所有标签内容
    hideTableContent(tabName);

    // 根据标签页加载对应数据
    if (tabName === 'current') {
        loadCurrentPadCodes().then(r => {});
    } else if (tabName === 'compare') {
        loadComparison().then(r => {});
    }

    // 清空选择
    clearSelection();
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
            new Error(`HTTP错误! 状态码: ${response.status}`);
        }

        const result = await response.json();
        availablePadCodes = result.data || [];
        filteredAvailableCodes = [...availablePadCodes];

        updateStatsCards(result.summary);
        renderAvailableTable();
        updateSelectedCount();
        updateAndroidVersionFilter();

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
        <div class="stat-card fade-in-up">
            <h3>${summary.total_available}</h3>
            <p>云端可用设备</p>
        </div>
        <div class="stat-card fade-in-up" style="animation-delay: 0.1s;">
            <h3>${summary.total_in_config}</h3>
            <p>当前配置设备</p>
        </div>
        <div class="stat-card fade-in-up" style="animation-delay: 0.2s;">
            <h3>${summary.not_in_config}</h3>
            <p>未配置设备</p>
        </div>
        <div class="stat-card fade-in-up" style="animation-delay: 0.3s;">
            <h3>${summary.config_not_available}</h3>
            <p>配置中但云端不可用</p>
        </div>
    `;
}

// 更新Android版本筛选器
function updateAndroidVersionFilter() {
    const versions = [...new Set(availablePadCodes
        .map(pad => pad.androidVersion)
        .filter(v => v)
    )].sort();

    const select = document.getElementById('androidVersionSelect');
    if (select) {
        select.innerHTML = '<option value="">所有版本</option>';
        versions.forEach(version => {
            const option = document.createElement('option');
            option.value = version;
            option.textContent = `Android ${version}`;
            select.appendChild(option);
        });
    }
}

// 渲染可用设备表格 - 增强版
function renderAvailableTable() {
    const tableBody = document.getElementById('availableTableBody');
    const emptyState = document.getElementById('availableEmptyState');

    if (filteredAvailableCodes.length === 0) {
        tableBody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    tableBody.innerHTML = filteredAvailableCodes.map((pad, index) => {
        const isSelected = selectedCodes.has(pad.padCode);
        const statusBadge = pad.status === 1 ?
            '<span class="status-badge status-active">在线</span>' :
            '<span class="status-badge status-inactive">离线</span>';

        const configBadge = pad.isInConfig ?
            '<span class="config-status in-config">已配置</span>' :
            '<span class="config-status not-in-config">未配置</span>';

        // 设备行的CSS类
        const rowClasses = [
            'device-row',
            isSelected ? 'selected' : '',
            pad.isInConfig ? 'configured' : '',
            pad.status === 1 ? 'online' : 'offline'
        ].filter(cls => cls).join(' ');

        return `
            <tr class="${rowClasses}" data-pad-code="${pad.padCode}" style="animation-delay: ${index * 50}ms;">
                <td class="checkbox-cell">
                    <input type="checkbox" ${isSelected ? 'checked' : ''}
                           onchange="toggleSelection('${pad.padCode}')"
                           value="${pad.padCode}">
                </td>
                <td title="${pad.padCode}" class="device-tooltip" data-tooltip="设备代码: ${pad.padCode}">
                    <strong>${pad.padCode}</strong>
                </td>
                <td>${pad.padName || '未命名'}</td>
                <td>${statusBadge}</td>
                <td>${configBadge}</td>
                <td>
                    <span class="device-tooltip" data-tooltip="Android版本: ${pad.androidVersion || '未知'}">
                        Android ${pad.androidVersion || '未知'}
                    </span>
                </td>
                <td class="device-info">
                    设备IP: ${pad.deviceIp || '未知'}<br>
                    Pad IP: ${pad.padIp || '未知'}
                </td>
                <td>${pad.goodName || '未设置'}</td>
                <td class="expiration-time">${pad.signExpirationTime || '未知'}</td>
                <td>${formatTimestamp(pad.bootTime)}</td>
                <td>
                    <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                        ${!pad.isInConfig ?
            `<button class="single-action-btn import-btn" onclick="importSingleDevice('${pad.padCode}')" title="导入此设备">
                                ➕
                            </button>` :
            `<button class="single-action-btn remove-btn" onclick="removeSingleDevice('${pad.padCode}')" title="移除此设备">
                                ➖
                            </button>`
        }
                        <button class="single-action-btn secondary" onclick="showDeviceDetails('${pad.padCode}')" title="查看详情">
                            👁️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    // 添加渐入动画
    const rowElements = tableBody.querySelectorAll('tr');
    rowElements.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(20px)';
        setTimeout(() => {
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, index * 50);
    });
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
            <tr class="device-row">
                <td class="checkbox-cell">
                    <input type="checkbox" value="${code}" onchange="toggleCurrentSelection('${code}')">
                </td>
                <td title="${code}"><strong>${code}</strong></td>
                <td>${cloudStatus}</td>
                <td>
                    <button class="single-action-btn remove-btn" onclick="removeSingleCode('${code}')" title="移除此设备">
                        🗑️ 移除
                    </button>
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
    updateRowStyles();

    // 触发选择变化事件
    document.dispatchEvent(new CustomEvent('selectionChanged', {
        detail: { selectedCount: selectedCodes.size }
    }));
}

// 从表头切换全选
function toggleSelectAllFromHeader() {
    const headerCheckbox = document.getElementById('headerSelectAll');
    const mainCheckbox = document.getElementById('selectAll');

    mainCheckbox.checked = headerCheckbox.checked;
    toggleSelectAll();
}

// 切换全选
function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const headerCheckbox = document.getElementById('headerSelectAll');
    const checkboxes = document.querySelectorAll('#availableTableBody input[type="checkbox"]');

    // 同步表头复选框
    if (headerCheckbox) {
        headerCheckbox.checked = selectAllCheckbox.checked;
    }

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
    updateRowStyles();
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
    showToast('已选择所有未配置的设备', 'success');
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
    showToast('已选择所有在线设备', 'success');
}

// 选择离线设备
function selectOfflineOnly() {
    selectedCodes.clear();
    filteredAvailableCodes.forEach(pad => {
        if (pad.status === 0) {
            selectedCodes.add(pad.padCode);
        }
    });
    renderAvailableTable();
    updateSelectedCount();
    updateBulkActions();
    showToast('已选择所有离线设备', 'success');
}

// 按Android版本选择
function selectByAndroidVersion() {
    // 获取所有Android版本
    const versions = [...new Set(filteredAvailableCodes
        .map(pad => pad.androidVersion)
        .filter(v => v)
    )].sort();

    if (versions.length === 0) {
        showToast('没有找到Android版本信息', 'warning');
        return;
    }

    // 创建简单的选择对话框
    const version = prompt(`请选择Android版本:\n${versions.map((v, i) => `${i + 1}. Android ${v}`).join('\n')}\n\n请输入版本号:`);

    if (version) {
        selectedCodes.clear();
        filteredAvailableCodes.forEach(pad => {
            if (pad.androidVersion === version) {
                selectedCodes.add(pad.padCode);
            }
        });
        renderAvailableTable();
        updateSelectedCount();
        updateBulkActions();
        showToast(`已选择所有 Android ${version} 设备`, 'success');
    }
}

// 清空选择
function clearSelection() {
    selectedCodes.clear();
    renderAvailableTable();
    updateSelectedCount();
    updateBulkActions();
}

// 选择所有可见设备
function selectAllVisible() {
    filteredAvailableCodes.forEach(pad => {
        selectedCodes.add(pad.padCode);
    });
    renderAvailableTable();
    updateSelectedCount();
    updateBulkActions();
    showToast('已选择所有可见设备', 'success');
}

// 更新选择计数
function updateSelectedCount() {
    const countElement = document.getElementById('selectedCount');
    const bulkCountElement = document.getElementById('bulkSelectedCount');

    if (countElement) {
        countElement.textContent = `已选择: ${selectedCodes.size}`;
    }
    if (bulkCountElement) {
        bulkCountElement.textContent = selectedCodes.size;
    }
}

// 更新批量操作区域
function updateBulkActions() {
    const bulkActions = document.getElementById('bulkActions');
    if (selectedCodes.size > 0) {
        bulkActions.classList.add('show');
        bulkActions.style.animation = 'slideInFromRight 0.3s ease-out';
    } else {
        bulkActions.classList.remove('show');
    }
}

// 更新行样式
function updateRowStyles() {
    const rows = document.querySelectorAll('#availableTableBody tr');
    rows.forEach(row => {
        const padCode = row.dataset.padCode;
        const checkbox = row.querySelector('input[type="checkbox"]');

        if (padCode && selectedCodes.has(padCode)) {
            row.classList.add('selected');
            if (checkbox) checkbox.checked = true;
        } else {
            row.classList.remove('selected');
            if (checkbox) checkbox.checked = false;
        }
    });
}

// 更新选择UI
function updateSelectionUI(event) {
    const selectedCount = event.detail.selectedCount;

    // 更新全选复选框状态
    const selectAllCheckbox = document.getElementById('selectAll');
    const headerCheckbox = document.getElementById('headerSelectAll');

    if (selectedCount === 0) {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = false;
        if (headerCheckbox) {
            headerCheckbox.indeterminate = false;
            headerCheckbox.checked = false;
        }
    } else if (selectedCount === filteredAvailableCodes.length) {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = true;
        if (headerCheckbox) {
            headerCheckbox.indeterminate = false;
            headerCheckbox.checked = true;
        }
    } else {
        selectAllCheckbox.indeterminate = true;
        if (headerCheckbox) {
            headerCheckbox.indeterminate = true;
        }
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

    // 清空当前选择中不在筛选结果中的项
    const visibleCodes = new Set(filteredAvailableCodes.map(pad => pad.padCode));
    selectedCodes.forEach(code => {
        if (!visibleCodes.has(code)) {
            selectedCodes.delete(code);
        }
    });

    renderAvailableTable();
    updateSelectedCount();
    updateBulkActions();
}

// 重置筛选
function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('configFilter').value = '';
    filteredAvailableCodes = [...availablePadCodes];
    renderAvailableTable();
}

// 增强的导入功能
async function importSelectedDevices(mode = 'add') {
    if (selectedCodes.size === 0) {
        showError('请先选择要导入的设备');
        return;
    }

    const actionText = mode === 'add' ? '添加' : '同步';
    const selectedArray = Array.from(selectedCodes);

    if (!confirm(`确定要${actionText}选中的 ${selectedCodes.size} 个设备代码吗？`)) {
        return;
    }

    try {
        showImportProgress(0, `正在${actionText}设备...`);

        const endpoint = mode === 'add' ? '/api/pad-codes/add' : '/api/pad-codes/sync';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: selectedArray
            })
        });

        showImportProgress(50, `处理服务器响应...`);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `${actionText}失败`);
        }

        const result = await response.json();
        showImportProgress(80, `更新界面...`);

        // 成功动画
        selectedArray.forEach(code => {
            const row = document.querySelector(`tr[data-pad-code="${code}"]`);
            if (row) {
                row.classList.add('import-success');
            }
        });

        showImportProgress(100, `${actionText}完成！`);

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);

            // 重新加载数据
            selectedCodes.clear();
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error(`${actionText}失败:`, error);
        showError(`${actionText}失败: ` + error.message);
    }
}

// 导入单个设备
async function importSingleDevice(padCode) {
    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/add', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: [padCode]
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '导入失败');
        }

        const result = await response.json();
        showToast(`设备 ${padCode} 导入成功`, 'success');

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('导入单个设备失败:', error);
        showError('导入失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 移除单个设备
async function removeSingleDevice(padCode) {
    if (!confirm(`确定要移除设备代码 "${padCode}" 吗？`)) {
        return;
    }

    try {
        showLoading(true);

        const response = await fetch('/api/pad-codes/remove', {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: [padCode]
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '移除失败');
        }

        const result = await response.json();
        showToast(`设备 ${padCode} 移除成功`, 'success');

        // 重新加载数据
        await loadAvailablePadCodes();
        await loadCurrentPadCodes();

    } catch (error) {
        console.error('移除单个设备失败:', error);
        showError('移除失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 显示设备详情
function showDeviceDetails(padCode) {
    const device = availablePadCodes.find(pad => pad.padCode === padCode);
    if (!device) {
        showError('未找到设备信息');
        return;
    }

    const detailsHtml = `
        <div class="device-details-modal">
            <h4>📱 设备详细信息</h4>
            <div class="device-details-grid">
                <div class="detail-item">
                    <strong>设备代码:</strong> ${device.padCode}
                </div>
                <div class="detail-item">
                    <strong>设备名称:</strong> ${device.padName || '未命名'}
                </div>
                <div class="detail-item">
                    <strong>状态:</strong> ${device.status === 1 ? '🟢 在线' : '🔴 离线'}
                </div>
                <div class="detail-item">
                    <strong>配置状态:</strong> ${device.isInConfig ? '✅ 已配置' : '❌ 未配置'}
                </div>
                <div class="detail-item">
                    <strong>Android版本:</strong> ${device.androidVersion || '未知'}
                </div>
                <div class="detail-item">
                    <strong>设备IP:</strong> ${device.deviceIp || '未知'}
                </div>
                <div class="detail-item">
                    <strong>Pad IP:</strong> ${device.padIp || '未知'}
                </div>
                <div class="detail-item">
                    <strong>CVM状态:</strong> ${device.cvmStatus || '未知'}
                </div>
                <div class="detail-item">
                    <strong>配置名称:</strong> ${device.goodName || '未设置'}
                </div>
                <div class="detail-item">
                    <strong>到期时间:</strong> ${device.signExpirationTime || '未知'}
                </div>
                <div class="detail-item">
                    <strong>启动时间:</strong> ${formatTimestamp(device.bootTime)}
                </div>
            </div>
        </div>
    `;

    showModal('设备详情', detailsHtml);
}

// 高级导入选项
function showAdvancedImportDialog() {
    document.getElementById('advancedImportModal').style.display = 'flex';
    updateAndroidVersionFilter();
}

function closeAdvancedImportDialog() {
    document.getElementById('advancedImportModal').style.display = 'none';
}

// 执行高级导入
async function executeAdvancedImport() {
    const onlineOnly = document.getElementById('onlineOnlyCheck').checked;
    const androidVersion = document.getElementById('androidVersionSelect').value;
    const importMode = document.getElementById('importModeSelect').value;
    const excludeConfigured = document.getElementById('excludeConfiguredCheck').checked;

    // 根据条件筛选设备
    let devicesToImport = availablePadCodes.filter(pad => {
        if (onlineOnly && pad.status !== 1) return false;
        if (androidVersion && pad.androidVersion !== androidVersion) return false;
        return !(excludeConfigured && pad.isInConfig);

    });

    if (devicesToImport.length === 0) {
        showError('根据选择的条件，没有找到符合要求的设备');
        return;
    }

    const deviceCodes = devicesToImport.map(pad => pad.padCode);

    if (!confirm(`根据选择的条件，将${importMode === 'add' ? '添加' : '替换为'} ${deviceCodes.length} 个设备，确定继续吗？`)) {
        return;
    }

    closeAdvancedImportDialog();

    try {
        showImportProgress(0, '开始高级导入...');

        const endpoint = importMode === 'add' ? '/api/pad-codes/add' : '/api/pad-codes/replace';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: deviceCodes
            })
        });

        showImportProgress(70, '处理服务器响应...');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '高级导入失败');
        }

        const result = await response.json();
        showImportProgress(100, '高级导入完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);

            // 重新加载数据
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('高级导入失败:', error);
        showError('高级导入失败: ' + error.message);
    }
}

// 仅导入在线设备
async function importOnlineOnly() {
    const onlineCodes = filteredAvailableCodes
        .filter(pad => pad.status === 1 && !pad.isInConfig)
        .map(pad => pad.padCode);

    if (onlineCodes.length === 0) {
        showError('没有未配置的在线设备可导入');
        return;
    }

    if (!confirm(`确定要导入 ${onlineCodes.length} 个在线设备吗？`)) {
        return;
    }

    try {
        showImportProgress(0, '导入在线设备...');

        const response = await fetch('/api/pad-codes/add', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: onlineCodes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '导入失败');
        }

        const result = await response.json();
        showImportProgress(100, '在线设备导入完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('导入在线设备失败:', error);
        showError('导入在线设备失败: ' + error.message);
    }
}

// 按Android版本导入
async function importByAndroidVersion() {
    const versions = [...new Set(filteredAvailableCodes
        .map(pad => pad.androidVersion)
        .filter(v => v)
    )].sort();

    if (versions.length === 0) {
        showError('没有找到Android版本信息');
        return;
    }

    const version = prompt(`请选择要导入的Android版本:\n${versions.map((v, i) => `${i + 1}. Android ${v}`).join('\n')}\n\n请输入版本号:`);

    if (!version) return;

    const versionCodes = filteredAvailableCodes
        .filter(pad => pad.androidVersion === version && !pad.isInConfig)
        .map(pad => pad.padCode);

    if (versionCodes.length === 0) {
        showError(`没有找到 Android ${version} 的未配置设备`);
        return;
    }

    if (!confirm(`确定要导入 ${versionCodes.length} 个 Android ${version} 设备吗？`)) {
        return;
    }

    try {
        showImportProgress(0, `导入 Android ${version} 设备...`);

        const response = await fetch('/api/pad-codes/add', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                selected_codes: versionCodes
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '导入失败');
        }

        const result = await response.json();
        showImportProgress(100, `Android ${version} 设备导入完成！`);

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('按版本导入失败:', error);
        showError('按版本导入失败: ' + error.message);
    }
}

// 移除选中的设备代码
async function removeSelectedCodes() {
    if (selectedCodes.size === 0) {
        showError('请先选择要移除的设备');
        return;
    }

    if (!confirm(`确定要从配置中移除选中的 ${selectedCodes.size} 个设备吗？`)) {
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
    if (!confirm('确定要导入所有云端可用的设备代码吗？这将添加所有云端设备到配置中。')) {
        return;
    }

    try {
        showImportProgress(0, '导入所有可用设备...');

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
        showImportProgress(100, '所有设备导入完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('同步失败:', error);
        showError('同步失败: ' + error.message);
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
        showImportProgress(0, '同步在线设备...');

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
        showImportProgress(100, '在线设备同步完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('同步在线设备失败:', error);
        showError('同步在线设备失败: ' + error.message);
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
        showImportProgress(0, '同步未配置设备...');

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
        showImportProgress(100, '未配置设备同步完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('同步未配置设备失败:', error);
        showError('同步未配置设备失败: ' + error.message);
    }
}

// 当前配置筛选
function applyCurrentFilters() {
    const searchTerm = document.getElementById('currentSearchInput').value.toLowerCase();

    if (searchTerm) {
        const filteredCodes = currentPadCodes.filter(code =>
            code.toLowerCase().includes(searchTerm)
        );

        // 临时渲染筛选结果
        const tableBody = document.getElementById('currentTableBody');
        const rows = filteredCodes.map(code => {
            const cloudDevice = availablePadCodes.find(pad => pad.padCode === code);
            const cloudStatus = cloudDevice ?
                (cloudDevice.status === 1 ?
                    '<span class="status-badge status-active">云端在线</span>' :
                    '<span class="status-badge status-inactive">云端离线</span>') :
                '<span class="status-badge status-unknown">云端不存在</span>';

            return `
                <tr class="device-row">
                    <td class="checkbox-cell">
                        <input type="checkbox" value="${code}" onchange="toggleCurrentSelection('${code}')">
                    </td>
                    <td title="${code}"><strong>${code}</strong></td>
                    <td>${cloudStatus}</td>
                    <td>
                        <button class="single-action-btn remove-btn" onclick="removeSingleCode('${code}')" title="移除此设备">
                            🗑️ 移除
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        tableBody.innerHTML = rows;
    } else {
        renderCurrentTable();
    }
}

function resetCurrentFilters() {
    document.getElementById('currentSearchInput').value = '';
    renderCurrentTable();
}

// 切换当前配置选择
function toggleCurrentSelection(code) {
    // 当前配置的选择逻辑
    const checkbox = document.querySelector(`input[value="${code}"]`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
    }
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
        <div class="comparison-card fade-in-up">
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

        <div class="comparison-card fade-in-up" style="animation-delay: 0.1s;">
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

        <div class="comparison-card fade-in-up" style="animation-delay: 0.2s;">
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
        syncRecommendations.classList.add('fade-in-up');
        syncRecommendations.style.animationDelay = '0.3s';

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
        showImportProgress(0, '添加云端设备...');

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
        showImportProgress(100, '云端设备添加完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);

            // 重新加载数据
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
            await loadComparison();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('添加失败:', error);
        showError('添加失败: ' + error.message);
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
        showImportProgress(0, '移除无效设备...');

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
        showImportProgress(100, '无效设备移除完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);

            // 重新加载数据
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
            await loadComparison();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('移除失败:', error);
        showError('移除失败: ' + error.message);
    }
}

// 自动同步
async function autoSync() {
    if (!confirm('确定要执行自动同步吗？\n\n这将：\n1. 添加云端存在但本地未配置的设备\n2. 移除本地配置但云端不存在的设备')) {
        return;
    }

    try {
        showImportProgress(0, '开始自动同步...');

        // 获取最新对比数据
        const compareResponse = await fetch('/api/pad-codes/compare', {
            headers: getAuthHeaders()
        });
        const compareData = await compareResponse.json();

        let successMessages = [];

        // 先添加新设备
        if (compareData.only_in_cloud.codes.length > 0) {
            showImportProgress(25, '添加云端新设备...');

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
            showImportProgress(75, '移除无效设备...');

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

        showImportProgress(100, '自动同步完成！');

        setTimeout(async () => {
            hideImportProgress();

            if (successMessages.length > 0) {
                showSuccess('自动同步完成！\n' + successMessages.join('\n'));
            }

            // 重新加载数据
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
            await loadComparison();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('自动同步失败:', error);
        showError('自动同步失败: ' + error.message);
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
        showImportProgress(0, '替换配置中...');

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
        showImportProgress(100, '配置替换完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess(result.message);

            // 重新加载数据
            selectedCodes.clear();
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('替换失败:', error);
        showError('替换失败: ' + error.message);
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
        showImportProgress(0, '清空配置中...');

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

        showImportProgress(100, '配置清空完成！');

        setTimeout(async () => {
            hideImportProgress();
            showSuccess('所有设备代码已清空');

            // 重新加载数据
            selectedCodes.clear();
            await loadAvailablePadCodes();
            await loadCurrentPadCodes();
        }, 1000);

    } catch (error) {
        hideImportProgress();
        console.error('清空失败:', error);
        showError('清空失败: ' + error.message);
    }
}

// 初始化表格样式
function initializeTableStyles() {
    // 为表格添加响应式处理
    const tables = document.querySelectorAll('.pad-table');
    tables.forEach(table => {
        table.addEventListener('scroll', function() {
            const scrollLeft = this.scrollLeft;
            const headers = this.querySelectorAll('thead th');
            headers.forEach(header => {
                header.style.transform = `translateX(${scrollLeft}px)`;
            });
        });
    });
}

// 显示导入进度
function showImportProgress(percentage, message) {
    let progressDiv = document.getElementById('importProgress');
    if (!progressDiv) {
        progressDiv = document.createElement('div');
        progressDiv.id = 'importProgress';
        progressDiv.className = 'import-progress slide-in';
        document.body.appendChild(progressDiv);
    }

    progressDiv.innerHTML = `
        <h4>🔄 导入进度</h4>
        <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${percentage}%"></div>
        </div>
        <div class="progress-text">${message} (${percentage}%)</div>
    `;
}

// 隐藏导入进度
function hideImportProgress() {
    const progressDiv = document.getElementById('importProgress');
    if (progressDiv) {
        progressDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (progressDiv.parentNode) {
                progressDiv.parentNode.removeChild(progressDiv);
            }
        }, 300);
    }
}

// 显示模态对话框
function showModal(title, content) {
    const modalHtml = `
        <div class="modal" id="dynamicModal" style="display: flex;">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" onclick="closeDynamicModal()">&times;</button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
                <div class="modal-footer">
                    <button onclick="closeDynamicModal()" class="secondary">关闭</button>
                </div>
            </div>
        </div>
    `;

    // 移除现有模态框
    const existingModal = document.getElementById('dynamicModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 添加新模态框
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// 关闭动态模态框
function closeDynamicModal() {
    const modal = document.getElementById('dynamicModal');
    if (modal) {
        modal.remove();
    }
}

// 显示Toast提示
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} slide-in`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-size: 14px;
        z-index: 1002;
        max-width: 300px;
        word-wrap: break-word;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;

    // 根据类型设置颜色
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

    // 3秒后自动移除
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

    // 点击移除
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
    const loadingOverlay = document.getElementById('loadingOverlay');

    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }

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
    errorElement.classList.add('slide-in');

    setTimeout(() => {
        errorElement.style.display = 'none';
        errorElement.classList.remove('slide-in');
    }, 5000);
}

// 显示成功信息
function showSuccess(message) {
    hideMessages();
    const successElement = document.getElementById('success');
    const successMessage = document.getElementById('successMessage');
    successMessage.textContent = message;
    successElement.style.display = 'flex';
    successElement.classList.add('slide-in');

    setTimeout(() => {
        successElement.style.display = 'none';
        successElement.classList.remove('slide-in');
    }, 3000);
}

// 隐藏所有消息
function hideMessages() {
    const errorElement = document.getElementById('error');
    const successElement = document.getElementById('success');

    if (errorElement) {
        errorElement.style.display = 'none';
        errorElement.classList.remove('slide-in');
    }
    if (successElement) {
        successElement.style.display = 'none';
        successElement.classList.remove('slide-in');
    }
}

// 添加CSS样式到页面
const additionalStyles = `
    .device-details-modal {
        max-width: 100%;
    }
    
    .device-details-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        margin-top: 15px;
    }
    
    .detail-item {
        padding: 8px 12px;
        background: #f8f9fa;
        border-radius: 4px;
        border-left: 3px solid var(--primary-color);
    }
    
    .detail-item strong {
        color: var(--text-color);
        margin-right: 8px;
    }
    
    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #f1f3f4;
    }
    
    .metric-row:last-child {
        border-bottom: none;
    }
    
    .metric-label {
        color: var(--dark-gray);
        font-size: 14px;
    }
    
    .metric-value {
        font-weight: bold;
        color: var(--text-color);
    }
    
    .metric-value.positive {
        color: var(--success-color);
    }
    
    .code-list {
        max-height: 200px;
        overflow-y: auto;
        background: #f8f9fa;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #e9ecef;
    }
    
    .code-item {
        padding: 2px 0;
        font-family: monospace;
        font-size: 12px;
        color: var(--text-color);
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

// 将样式添加到页面
if (!document.getElementById('enhanced-pade-code-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'enhanced-pade-code-styles';
    styleElement.textContent = additionalStyles;
    document.head.appendChild(styleElement);
}