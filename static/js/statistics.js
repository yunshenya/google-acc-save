let growthChart = null;
let refreshInterval = null;
let currentChart = 'total'; // 'total' 或 'average'
let chartData = null;

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus().then(() => {
        loadStatistics().then(r => {});
        // 每5分钟自动刷新一次
        refreshInterval = setInterval(loadStatistics, 5 * 60 * 1000);
    });
});

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

// 获取认证头
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// 加载统计数据
async function loadStatistics() {
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshIcon = document.getElementById('refreshIcon');

    try {
        // 设置加载状态
        refreshBtn.disabled = true;
        refreshIcon.classList.add('loading-spinner');

        // 并行请求两个接口
        const [growthResponse, summaryResponse] = await Promise.all([
            fetch('/api/statistics/hourly-growth', {
                headers: getAuthHeaders()
            }),
            fetch('/api/statistics/overall-summary', {
                headers: getAuthHeaders()
            })
        ]);

        if (!growthResponse.ok || !summaryResponse.ok) {
            new Error('获取统计数据失败');
        }

        chartData = await growthResponse.json();
        const summaryData = await summaryResponse.json();

        // 更新页面内容
        updateSummaryCards(chartData.summary, summaryData);
        updateChart(chartData);
        updateMetrics(summaryData);
        updateTimeRange(chartData.summary.time_range);

    } catch (error) {
        console.error('加载统计数据失败:', error);
        showError('加载统计数据失败: ' + error.message);
    } finally {
        // 恢复按钮状态
        refreshBtn.disabled = false;
        refreshIcon.classList.remove('loading-spinner');
    }
}

// 切换图表视图
function switchChart(type) {
    currentChart = type;

    // 更新按钮状态
    document.getElementById('totalTab').classList.toggle('active', type === 'total');
    document.getElementById('avgTab').classList.toggle('active', type === 'average');

    // 更新图表
    if (chartData) {
        updateChart(chartData);
    }
}

// 更新摘要卡片
function updateSummaryCards(chartSummary, overallSummary) {
    const container = document.getElementById('statsSummary');
    container.innerHTML = `
                <div class="summary-card">
                    <h3>${chartSummary.total_devices}</h3>
                    <p>总设备数</p>
                    <div class="subtitle">活跃设备数量</div>
                </div>
                <div class="summary-card">
                    <h3>${chartSummary.total_accounts_24h}</h3>
                    <p>24小时新增账号</p>
                    <div class="subtitle">所有设备总计</div>
                </div>
                <div class="summary-card">
                    <h3>${chartSummary.avg_per_device_24h}</h3>
                    <p>平均每设备24小时</p>
                    <div class="subtitle">账号增长数</div>
                </div>
                <div class="summary-card">
                    <h3>${chartSummary.avg_per_device_per_hour}</h3>
                    <p>平均每设备每小时</p>
                    <div class="subtitle">账号增长率</div>
                </div>
                <div class="summary-card">
                    <h3>${overallSummary.total_accounts}</h3>
                    <p>历史总账号数</p>
                    <div class="subtitle">所有时间累计</div>
                </div>
            `;
}

// 更新图表
function updateChart(data) {
    const ctx = document.getElementById('growthChart').getContext('2d');
    const chartTitle = document.getElementById('chartTitle');

    // 销毁现有图表
    if (growthChart) {
        growthChart.destroy();
    }

    let chartDataset, title, yAxisTitle;

    if (currentChart === 'total') {
        chartDataset = data.total_accounts_data;
        title = '过去24小时总账号增长趋势';
        yAxisTitle = '账号总数';
    } else {
        chartDataset = data.avg_per_device_data;
        title = '过去24小时平均每设备账号增长趋势';
        yAxisTitle = '平均账号数/设备';
    }

    chartTitle.textContent = title;

    growthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.time_points,
            datasets: [{
                label: currentChart === 'total' ? '总账号数' : '平均每设备账号数',
                data: chartDataset,
                borderColor: currentChart === 'total' ? '#3498db' : '#e74c3c',
                backgroundColor: (currentChart === 'total' ? '#3498db' : '#e74c3c') + '20',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: currentChart === 'total' ? '#3498db' : '#e74c3c',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    cornerRadius: 6,
                    callbacks: {
                        title: function(context) {
                            return '时间: ' + context[0].label;
                        },
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y + (currentChart === 'total' ? ' 个' : ' 个/设备');
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '时间',
                        color: '#666',
                        font: {
                            size: 12
                        }
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        color: '#666'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yAxisTitle,
                        color: '#666',
                        font: {
                            size: 12
                        }
                    },
                    beginAtZero: true,
                    ticks: {
                        precision: currentChart === 'total' ? 0 : 2,
                        color: '#666'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

// 更新详细指标
function updateMetrics(data) {
    // 设备效率指标
    const deviceMetrics = document.getElementById('deviceMetrics');
    deviceMetrics.innerHTML = `
                <div class="metric-row">
                    <span class="metric-label">总设备数</span>
                    <span class="metric-value">${data.total_devices}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">平均每设备总账号</span>
                    <span class="metric-value positive">${data.avg_total_per_device}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">平均每设备24小时</span>
                    <span class="metric-value positive">${data.avg_24h_per_device}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">平均每设备每小时(24h)</span>
                    <span class="metric-value">${data.avg_per_device_per_hour_24h}</span>
                </div>
            `;

    // 时间周期统计
    const timeMetrics = document.getElementById('timeMetrics');
    timeMetrics.innerHTML = `
                <div class="metric-row">
                    <span class="metric-label">1小时新增</span>
                    <span class="metric-value positive">${data.accounts_1h} (${data.avg_1h_per_device}/设备)</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">24小时新增</span>
                    <span class="metric-value positive">${data.accounts_24h} (${data.avg_24h_per_device}/设备)</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">7天新增</span>
                    <span class="metric-value positive">${data.accounts_7d} (${data.avg_7d_per_device}/设备)</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">历史总计</span>
                    <span class="metric-value">${data.total_accounts} (${data.avg_total_per_device}/设备)</span>
                </div>
            `;

    // 如果有时间信息，添加到时间指标中
    if (data.first_account_time || data.last_account_time) {
        timeMetrics.innerHTML += `
                    <div class="metric-row">
                        <span class="metric-label">首个账号时间</span>
                        <span class="metric-value">${formatDateTime(data.first_account_time)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">最新账号时间</span>
                        <span class="metric-value">${formatDateTime(data.last_account_time)}</span>
                    </div>
                `;
    }
}

// 更新时间范围显示
function updateTimeRange(timeRange) {
    const element = document.getElementById('timeRange');
    if (element) {
        element.textContent = '统计时间范围: ' + timeRange;
    }
}

// 格式化日期时间
function formatDateTime(dateString) {
    if (!dateString) return '暂无';

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

// 显示错误信息
function showError(message) {
    // 创建简单的错误提示
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background-color: #e74c3c;
                color: white;
                padding: 15px 20px;
                border-radius: 5px;
                z-index: 1000;
                max-width: 300px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            `;
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);

    // 5秒后自动移除
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}