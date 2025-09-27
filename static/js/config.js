let currentConfig = {};
let currentTab = 'basic';

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus().then(() => {
        loadConfig();
        setupEventListeners();
        loadEnvVars();
    });
});

// 设置事件监听器
function setupEventListeners() {
    document.getElementById('saveBtn').addEventListener('click', saveConfig);
    document.getElementById('resetBtn').addEventListener('click', resetConfig);
    document.getElementById('validateBtn').addEventListener('click', validateConfig);
    document.getElementById('backupBtn').addEventListener('click', createBackup);
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

    // 如果切换到环境变量标签，加载环境变量
    if (tabName === 'environment') {
        loadEnvVars();
    }

    // 如果切换到备份标签，加载备份列表
    if (tabName === 'backup') {
        loadBackups();
    }
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

// 加载配置
async function loadConfig() {
    showLoading(true);
    try {
        const response = await fetch('/api/config', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP错误! 状态码: ${response.status}`);
        }

        currentConfig = await response.json();
        populateForm(currentConfig);
        hideMessages();

    } catch (error) {
        console.error('加载配置失败:', error);
        showError('加载配置失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 填充表单
function populateForm(config) {
    // 基础配置
    populateArrayInput('padCodesContainer', config.pad_codes, 'pad_code');
    document.getElementById('primaryPackage').value = config.package_names.primary || '';
    document.getElementById('secondaryPackage').value = config.package_names.secondary || '';
    populateArrayInput('templeIdsContainer', config.temple_ids, 'temple_id');

    // 代理配置
    const proxy = config.default_proxy;
    document.getElementById('proxyCountry').value = proxy.country || '';
    document.getElementById('proxyCode').value = proxy.code || '';
    document.getElementById('proxyUrl').value = proxy.proxy || '';
    document.getElementById('proxyTimezone').value = proxy.time_zone || '';
    document.getElementById('proxyLanguage').value = proxy.language || '';
    document.getElementById('proxyLatitude').value = proxy.latitude || '';
    document.getElementById('proxyLongitude').value = proxy.longitude || '';

    // 应用URL
    const urls = config.app_urls;
    document.getElementById('clashUrl').value = urls.clash || '';
    document.getElementById('scriptUrl').value = urls.script || '';
    document.getElementById('script2Url').value = urls.script2 || '';
    document.getElementById('chromeUrl').value = urls.chrome || '';

    // 超时配置
    const timeouts = config.timeouts;
    document.getElementById('globalTimeout').value = timeouts.global_timeout || '';
    document.getElementById('checkTaskTimeout').value = timeouts.check_task_timeout || '';

    // 调试模式
    document.getElementById('debugMode').checked = config.debug || false;

    // 安全配置
    document.getElementById('jwtSecretKey').value = config.jwt_secret_key || '';
    document.getElementById('adminUsername').value = config.admin_credentials.username || '';
    document.getElementById('adminPassword').value = config.admin_credentials.password || '';
    document.getElementById('databaseUrl').value = config.database_url || '';
}

// 填充数组输入
function populateArrayInput(containerId, values, inputName) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';

    if (values && values.length > 0) {
        values.forEach((value, index) => {
            addArrayItem(container, value, inputName, index);
        });
    } else {
        addArrayItem(container, '', inputName, 0);
    }
}

// 添加数组项
function addArrayItem(container, value, inputName, index) {
    const div = document.createElement('div');
    div.className = 'array-item';
    div.innerHTML = `
            <input type="${inputName === 'temple_id' ? 'number' : 'text'}"
                   value="${value}"
                   placeholder="${inputName === 'temple_id' ? '模板ID' : '设备代码'}"
                   name="${inputName}">
            <button type="button" class="remove-btn" onclick="removeArrayItem(this)">移除</button>
        `;
    container.appendChild(div);
}

// 添加设备代码
function addPadCode() {
    const container = document.getElementById('padCodesContainer');
    addArrayItem(container, '', 'pad_code', container.children.length);
}

// 添加模板ID
function addTempleId() {
    const container = document.getElementById('templeIdsContainer');
    addArrayItem(container, '', 'temple_id', container.children.length);
}

// 移除数组项
function removeArrayItem(button) {
    const container = button.parentElement.parentElement;
    button.parentElement.remove();

    // 确保至少有一个输入框
    if (container.children.length === 0) {
        const inputName = container.id.includes('temple') ? 'temple_id' : 'pad_code';
        addArrayItem(container, '', inputName, 0);
    }
}

// 收集表单数据
function collectFormData() {
    const formData = {};

    // 设备代码
    const padCodes = Array.from(document.querySelectorAll('input[name="pad_code"]'))
        .map(input => input.value.trim())
        .filter(value => value !== '');
    if (padCodes.length > 0) {
        formData.pad_codes = padCodes;
    }

    // 包名
    const primaryPackage = document.getElementById('primaryPackage').value.trim();
    const secondaryPackage = document.getElementById('secondaryPackage').value.trim();
    if (primaryPackage || secondaryPackage) {
        formData.package_names = {};
        if (primaryPackage) formData.package_names.primary = primaryPackage;
        if (secondaryPackage) formData.package_names.secondary = secondaryPackage;
    }

    // 模板ID
    const templeIds = Array.from(document.querySelectorAll('input[name="temple_id"]'))
        .map(input => parseInt(input.value.trim()))
        .filter(value => !isNaN(value));
    if (templeIds.length > 0) {
        formData.temple_ids = templeIds;
    }

    // 默认代理
    const proxyData = {
        country: document.getElementById('proxyCountry').value.trim(),
        code: document.getElementById('proxyCode').value.trim(),
        proxy: document.getElementById('proxyUrl').value.trim(),
        time_zone: document.getElementById('proxyTimezone').value.trim(),
        language: document.getElementById('proxyLanguage').value.trim(),
        latitude: parseFloat(document.getElementById('proxyLatitude').value) || 0,
        longitude: parseFloat(document.getElementById('proxyLongitude').value) || 0
    };
    if (Object.values(proxyData).some(v => v !== '' && v !== 0)) {
        formData.default_proxy = proxyData;
    }

    // 应用URL
    const urlData = {
        clash: document.getElementById('clashUrl').value.trim(),
        script: document.getElementById('scriptUrl').value.trim(),
        script2: document.getElementById('script2Url').value.trim(),
        chrome: document.getElementById('chromeUrl').value.trim()
    };
    if (Object.values(urlData).some(v => v !== '')) {
        formData.app_urls = urlData;
    }

    // 超时配置
    const timeoutData = {
        global_timeout: parseInt(document.getElementById('globalTimeout').value) || undefined,
        check_task_timeout: parseInt(document.getElementById('checkTaskTimeout').value) || undefined
    };
    if (timeoutData.global_timeout || timeoutData.check_task_timeout) {
        formData.timeouts = timeoutData;
    }

    // 调试模式
    formData.debug = document.getElementById('debugMode').checked;

    // 安全配置
    const jwtKey = document.getElementById('jwtSecretKey').value.trim();
    if (jwtKey) {
        formData.jwt_secret_key = jwtKey;
    }

    const adminUsername = document.getElementById('adminUsername').value.trim();
    const adminPassword = document.getElementById('adminPassword').value.trim();
    if (adminUsername || adminPassword) {
        formData.admin_credentials = {};
        if (adminUsername) formData.admin_credentials.username = adminUsername;
        if (adminPassword) formData.admin_credentials.password = adminPassword;
    }

    const dbUrl = document.getElementById('databaseUrl').value.trim();
    if (dbUrl) {
        formData.database_url = dbUrl;
    }

    return formData;
}

// 保存配置
async function saveConfig() {
    if (!confirm('确定要保存这些配置更改吗？\n\n更改将立即生效并持久化到.env文件，可能影响系统运行。')) {
        return;
    }

    showLoading(true);
    try {
        const formData = collectFormData();

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '保存失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载配置
        setTimeout(() => {
            loadConfig();
        }, 1000);

    } catch (error) {
        console.error('保存配置失败:', error);
        showError('保存配置失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 重置配置
async function resetConfig() {
    if (!confirm('确定要重置所有配置为默认值吗？\n\n这将覆盖当前的所有配置更改并持久化！')) {
        return;
    }

    showLoading(true);
    try {
        const response = await fetch('/api/config/reset', {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '重置失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载配置
        setTimeout(() => {
            loadConfig();
        }, 1000);

    } catch (error) {
        console.error('重置配置失败:', error);
        showError('重置配置失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 验证配置
async function validateConfig() {
    showLoading(true);
    try {
        const response = await fetch('/api/config/validate', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '验证失败');
        }

        const result = await response.json();
        showValidationResult(result);

    } catch (error) {
        console.error('验证配置失败:', error);
        showError('验证配置失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 显示验证结果
function showValidationResult(result) {
    const statusDiv = document.getElementById('validationStatus');
    statusDiv.style.display = 'block';

    let statusClass, statusText;
    if (result.valid) {
        statusClass = 'validation-valid';
        statusText = '✅ 配置验证通过！所有配置项都是有效的。';
    } else {
        statusClass = 'validation-invalid';
        statusText = '❌ 配置验证失败！发现以下错误：';
    }

    let content = `<div class="${statusClass}"><strong>${statusText}</strong>`;

    if (result.errors && result.errors.length > 0) {
        content += '<ul class="validation-list">';
        result.errors.forEach(error => {
            content += `<li>❌ ${error}</li>`;
        });
        content += '</ul>';
    }

    if (result.warnings && result.warnings.length > 0) {
        content += '<div class="validation-warnings" style="margin-top: 10px;"><strong>⚠️ 警告：</strong>';
        content += '<ul class="validation-list">';
        result.warnings.forEach(warning => {
            content += `<li>⚠️ ${warning}</li>`;
        });
        content += '</ul></div>';
    }

    content += '</div>';
    statusDiv.innerHTML = content;

    // 3秒后自动隐藏验证成功消息
    if (result.valid && (!result.warnings || result.warnings.length === 0)) {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 3000);
    }
}

// 环境变量管理
async function loadEnvVars() {
    try {
        const response = await fetch('/api/config/env-vars', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('获取环境变量失败');
        }

        const envVars = await response.json();
        renderEnvVarTable(envVars);

    } catch (error) {
        console.error('加载环境变量失败:', error);
        showError('加载环境变量失败: ' + error.message);
    }
}

function renderEnvVarTable(envVars) {
    const tbody = document.getElementById('envVarTableBody');
    tbody.innerHTML = '';

    envVars.forEach(envVar => {
        const row = document.createElement('tr');
        row.className = envVar.is_system ? 'system-var' : 'custom-var';

        row.innerHTML = `
                <td>${envVar.key}</td>
                <td style="font-family: monospace; max-width: 200px; overflow: hidden; text-overflow: ellipsis;">${envVar.value}</td>
                <td>
                    <span style="padding: 2px 6px; border-radius: 3px; font-size: 11px; color: white; background-color: ${envVar.is_system ? '#ffc107' : '#17a2b8'};">
                        ${envVar.is_system ? '系统' : '自定义'}
                    </span>
                </td>
                <td>
                    ${envVar.is_system ?
            '<span style="color: #666;">受保护</span>' :
            `<button class="remove-btn" onclick="deleteEnvVar('${envVar.key}')">删除</button>`
        }
                </td>
            `;
        tbody.appendChild(row);
    });
}

// 添加环境变量
async function addEnvVar() {
    const key = document.getElementById('newEnvKey').value.trim();
    const value = document.getElementById('newEnvValue').value.trim();

    if (!key || !value) {
        showError('请输入变量名和变量值');
        return;
    }

    try {
        const response = await fetch('/api/config/env-var', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ key, value })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '添加失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 清空输入框
        document.getElementById('newEnvKey').value = '';
        document.getElementById('newEnvValue').value = '';

        // 重新加载环境变量列表
        loadEnvVars();

    } catch (error) {
        console.error('添加环境变量失败:', error);
        showError('添加环境变量失败: ' + error.message);
    }
}

// 删除环境变量
async function deleteEnvVar(key) {
    if (!confirm(`确定要删除环境变量 "${key}" 吗？`)) {
        return;
    }

    try {
        const response = await fetch('/api/config/env-var', {
            method: 'DELETE',
            headers: getAuthHeaders(),
            body: JSON.stringify({ key })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '删除失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载环境变量列表
        loadEnvVars();

    } catch (error) {
        console.error('删除环境变量失败:', error);
        showError('删除环境变量失败: ' + error.message);
    }
}

// 备份管理
async function createBackup() {
    showLoading(true);
    try {
        const response = await fetch('/api/config/backup', {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '备份失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载备份列表
        loadBackups();

    } catch (error) {
        console.error('创建备份失败:', error);
        showError('创建备份失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function loadBackups() {
    try {
        const response = await fetch('/api/config/backups', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('获取备份列表失败');
        }

        const backups = await response.json();
        renderBackupList(backups);

    } catch (error) {
        console.error('加载备份列表失败:', error);
        showError('加载备份列表失败: ' + error.message);
    }
}

function renderBackupList(backups) {
    const container = document.getElementById('backupList');

    if (backups.length === 0) {
        container.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">暂无备份文件</p>';
        return;
    }

    container.innerHTML = backups.map(backup => `
        <div class="backup-item">
            <div class="backup-info">
                <h4>${backup.filename}</h4>
                <p>创建时间: ${new Date(backup.created_at * 1000).toLocaleString()}</p>
                <p>文件大小: ${(backup.size / 1024).toFixed(2)} KB</p>
            </div>
            <div class="backup-actions">
                <button class="secondary" onclick="restoreBackup('${backup.filename}')" title="从此备份恢复配置">恢复</button>
                <button class="remove-btn" onclick="deleteBackup('${backup.filename}')" title="删除此备份文件">删除</button>
            </div>
        </div>
    `).join('');
}

async function restoreBackup(filename) {
    if (!confirm(`确定要从备份 "${filename}" 恢复配置吗？\n\n这将覆盖当前所有配置！`)) {
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`/api/config/restore/${filename}`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '恢复失败');
        }

        const result = await response.json();
        showSuccess(result.message);

        // 重新加载配置
        setTimeout(() => {
            loadConfig();
        }, 1000);

    } catch (error) {
        console.error('恢复备份失败:', error);
        showError('恢复备份失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

async function deleteBackup(filename) {
    if (!confirm(`确定要删除备份文件 "${filename}" 吗？\n\n此操作无法撤销！`)) {
        return;
    }

    showLoading(true);
    try {
        const response = await fetch(`/api/config/backup/${filename}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '删除失败');
        }

        const result = await response.json();
        showSuccess(result.message || '备份文件删除成功');

        // 重新加载备份列表
        await loadBackups();

    } catch (error) {
        console.error('删除备份失败:', error);
        showError('删除备份失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// 危险操作确认
function confirmReset() {
    if (confirm('⚠️ 警告：这将重置所有配置为默认值！\n\n确定要继续吗？')) {
        resetConfig();
    }
}

async function clearAllEnvVars() {
    if (!confirm('⚠️ 警告：这将删除所有自定义环境变量！\n\n确定要继续吗？')) {
        return;
    }

    // 这里可以实现批量删除自定义环境变量的逻辑
    // 为简化，暂时提示用户手动删除
    showError('请手动删除需要移除的自定义环境变量');
}

// 显示/隐藏加载状态
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';

    // 禁用/启用按钮
    const buttons = document.querySelectorAll('button');
    buttons.forEach(btn => {
        btn.disabled = show;
    });
}

// 显示错误消息
function showError(message) {
    hideMessages();
    const errorElement = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorElement.style.display = 'flex';
}

// 显示成功消息
function showSuccess(message) {
    hideMessages();
    const successElement = document.getElementById('success');
    const successMessage = document.getElementById('successMessage');
    successMessage.textContent = message;
    successElement.style.display = 'flex';

    // 3秒后自动隐藏
    setTimeout(() => {
        successElement.style.display = 'none';
    }, 3000);
}

// 隐藏所有消息
function hideMessages() {
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
    document.getElementById('validationStatus').style.display = 'none';
}

// 全局错误处理
window.addEventListener('error', function(e) {
    console.error('全局错误:', e.error);
    showError('发生未知错误，请刷新页面重试');
});