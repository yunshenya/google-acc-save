document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
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


    // 状态变量
    let allAccounts = [];
    let filteredAccounts = [];
    let currentPage = 1;
    const pageSize = 50;
    let totalPages = 0;
    let isFetching = false;
    let fetchMode = 'none'; // 'all', 'page', 'single'

    // 初始化
    init();

    function init() {
        setupEventListeners();
        updateUI();
    }

    function setupEventListeners() {
        // 获取数据按钮
        fetchAllBtn.addEventListener('click', fetchAllAccounts);
        fetchPageBtn.addEventListener('click', fetchAccountsByPage);
        fetchSingleBtn.addEventListener('click', fetchSingleAccount);
        fetchSingleLockBtn.addEventListener('click', fetchSingleAccountLocked);

        // 分页控制
        firstPageBtn.addEventListener('click', () => goToPage(1));
        prevPageBtn.addEventListener('click', () => goToPage(currentPage - 1));
        nextPageBtn.addEventListener('click', () => goToPage(currentPage + 1));
        lastPageBtn.addEventListener('click', () => goToPage(totalPages));

        // 筛选和搜索
        applyFiltersBtn.addEventListener('click', applyFilters);
        resetFiltersBtn.addEventListener('click', resetFilters);
        searchInput.addEventListener('keyup', debounce(applyFilters, 300));

        // 其他功能
        maskPasswordsCheck.addEventListener('change', togglePasswordMask);
        exportCSVBtn.addEventListener('click', exportToCSV);

        // 监听滚动事件实现无限滚动
        tableContainer.addEventListener('scroll', debounce(handleScroll, 200));
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
        progressBar.style.width = `${progress}%`;
    }

    // 显示加载状态
    function showLoading() {
        isFetching = true;
        loadingElement.style.display = 'flex';
        errorElement.style.display = 'none';
        updateUI();
    }

    // 隐藏加载状态
    function hideLoading() {
        isFetching = false;
        loadingElement.style.display = 'none';
        updateProgress(0);
        updateUI();
    }

    // 显示错误信息
    function showError(message) {
        errorMessage.textContent = message;
        errorElement.style.display = 'flex';
        console.error(message);
    }

    // 更新UI状态
    function updateUI() {
        // 禁用/启用按钮
        fetchAllBtn.disabled = isFetching;
        fetchPageBtn.disabled = isFetching;
        fetchSingleBtn.disabled = isFetching || !accountIdInput.value;
        fetchSingleLockBtn.disabled = isFetching || !accountIdInput.value;
        applyFiltersBtn.disabled = isFetching;

        // 分页控制
        firstPageBtn.disabled = currentPage === 1 || isFetching;
        prevPageBtn.disabled = currentPage === 1 || isFetching;
        nextPageBtn.disabled = currentPage === totalPages || isFetching;
        lastPageBtn.disabled = currentPage === totalPages || isFetching;

        // 只有在分页模式下才显示分页控件
        if (fetchMode === 'page' && filteredAccounts.length > 0) {
            pagination.style.display = 'flex';
            updatePaginationUI();
        } else {
            pagination.style.display = 'none';
        }

        // 显示/隐藏空状态
        if (filteredAccounts.length === 0 && !isFetching) {
            emptyState.style.display = 'block';
        } else {
            emptyState.style.display = 'none';
        }
    }

    // 更新分页UI
    function updatePaginationUI() {
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
        const startItem = (currentPage - 1) * pageSize + 1;
        const endItem = Math.min(currentPage * pageSize, filteredAccounts.length);
        paginationInfo.textContent = `显示 ${startItem}-${endItem} 条，共 ${filteredAccounts.length} 条记录`;
    }

    // 跳转到指定页
    function goToPage(page) {
        if (page < 1 || page > totalPages || page === currentPage) return;

        currentPage = page;
        renderAccounts(getPaginatedAccounts());
        updateUI();
        tableContainer.scrollTo(0, 0);
    }

    // 处理滚动事件
    function handleScroll() {
        if (fetchMode !== 'page' || isFetching) return;

        const { scrollTop, scrollHeight, clientHeight } = tableContainer;
        const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;

        if (isNearBottom && currentPage < totalPages) {
            goToPage(currentPage + 1);
        }
    }

    // 清空表格
    function clearTable() {
        accountsBody.innerHTML = '';
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
        const maskPasswords = maskPasswordsCheck.checked;

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

        accountsBody.appendChild(fragment);

        // 添加查看按钮事件
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                accountIdInput.value = this.getAttribute('data-id');
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

            const response = await fetch(`/accounts`);
            updateProgress(30);

            if (!response.ok) {
                new Error(`HTTP错误! 状态码: ${response.status}`);
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
            const response = await fetch(`/accounts`);

            if (!response.ok) {
                new Error(`HTTP错误! 状态码: ${response.status}`);
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
        const accountId = accountIdInput.value.trim();

        if (!accountId) {
            showError('请输入账户ID');
            return;
        }

        try {
            showLoading();
            clearTable();
            fetchMode = 'single';

            const response = await fetch(`/accounts/${accountId}`);

            if (!response.ok) {
                new Error(`HTTP错误! 状态码: ${response.status}`);
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
        const accountId = accountIdInput.value.trim();

        if (!accountId) {
            showError('请输入账户ID');
            return;
        }

        try {
            showLoading();
            clearTable();
            fetchMode = 'single';

            const response = await fetch(`/account/${accountId}`);

            if (!response.ok) {
                new Error(`HTTP错误! 状态码: ${response.status}`);
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

        const searchTerm = searchInput.value.toLowerCase();
        const statusValue = statusFilter.value;
        const typeValue = typeFilter.value;

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
        searchInput.value = '';
        statusFilter.value = '';
        typeFilter.value = '';
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