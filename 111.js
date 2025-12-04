// 超星学习通任务管理系统 - 前端交互脚本
// 版本: 2.2 (修复健康检查版)

// 配置
const CONFIG = {
    pollInterval: 5000,           // 轮询间隔（毫秒）
    autoRefreshInterval: 5000,    // 自动刷新间隔
    maxOutputLines: 500,          // 最大输出行数
    healthCheckInterval: 30000,   // 健康检查间隔（30秒）
    requestTimeout: 10000,        // 请求超时时间（10秒）
    serverUrls: {                 // 服务器地址配置
        remote: "http://154.36.158.140:5001",
        local: "http://127.0.0.1:5000",
        localhost: "http://localhost:5000"
    }
};

// 应用状态
const state = {
    currentServer: CONFIG.serverUrls.local,
    currentTaskId: null,
    tasks: {},
    autoRefreshEnabled: false,
    autoRefreshTimer: null,
    outputFilter: 'all',
    healthCheckTimer: null,
    serverOnline: false,
    isCheckingHealth: false
};

// DOM元素
const elements = {
    // 表单元素
    taskForm: document.getElementById('taskForm'),
    serverUrl: document.getElementById('serverUrl'),
    username: document.getElementById('username'),
    password: document.getElementById('password'),
    listId: document.getElementById('listId'),
    startBtn: document.getElementById('startBtn'),
    healthCheckBtn: document.getElementById('healthCheckBtn'),
    
    // 状态显示
    serverStatus: document.getElementById('serverStatus'),
    activeTasks: document.getElementById('activeTasks'),
    totalTasks: document.getElementById('totalTasks'),
    lastUpdate: document.getElementById('lastUpdate'),
    
    // 监控面板
    refreshBtn: document.getElementById('refreshBtn'),
    clearBtn: document.getElementById('clearBtn'),
    autoRefresh: document.getElementById('autoRefresh'),
    taskOutput: document.getElementById('taskOutput'),
    outputCount: document.getElementById('outputCount'),
    
    // 任务列表
    runningTasks: document.getElementById('runningTasks'),
    tasksTableBody: document.getElementById('tasksTableBody'),
    statusDetails: document.getElementById('statusDetails'),
    
    // Tab切换
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // 系统操作
    cleanupBtn: document.getElementById('cleanupBtn')
};

// ==================== Toast通知系统 ====================
class Toast {
    static show(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-times-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        toast.innerHTML = `
            <i class="toast-icon ${icons[type]}"></i>
            <div class="toast-content">
                <div class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">&times;</button>
        `;
        
        const container = document.getElementById('toastContainer');
        container.appendChild(toast);
        
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        });
        
        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateX(100%)';
                    setTimeout(() => toast.remove(), 300);
                }
            }, duration);
        }
        
        return toast;
    }
}

// ==================== API调用封装 ====================
class API {
    static async request(endpoint, options = {}) {
        const url = `${state.currentServer}${endpoint}`;
        console.log(`API请求: ${url}`);
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.requestTimeout);
            
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    ...options.headers
                },
                signal: controller.signal,
                ...options
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    if (errorData && errorData.message) {
                        errorMessage += `: ${errorData.message}`;
                    }
                } catch {
                    errorMessage += `: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error(`API请求失败: ${url}`, error);
            
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请检查网络连接');
            } else if (error.message.includes('Failed to fetch')) {
                throw new Error('无法连接到服务器，请检查地址和端口');
            } else {
                throw error;
            }
        }
    }
    
    static async runTask(username, password, listId) {
        console.log('启动任务:', { username, listId });
        return await this.request('/api/run', {
            method: 'POST',
            body: JSON.stringify({ 
                username: username,
                password: password,
                list_id: listId
            })
        });
    }
    
    static async getAllTasks() {
        return await this.request('/api/tasks');
    }
    
    static async getTaskStatus(taskId) {
        return await this.request(`/api/status/${taskId}`);
    }
    
    static async getTaskOutput(taskId) {
        return await this.request(`/api/output/${taskId}`);
    }
    
    static async stopTask(taskId) {
        return await this.request(`/api/stop/${taskId}`, {
            method: 'POST'
        });
    }
    
    static async healthCheck() {
        console.log(`执行健康检查: ${state.currentServer}`);
        
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            const xhr = new XMLHttpRequest();
            
            // 使用XMLHttpRequest，因为它更可靠
            xhr.timeout = 3000;
            xhr.open('GET', state.currentServer, true);
            
            xhr.onload = function() {
                const latency = Date.now() - startTime;
                console.log(`健康检查成功: HTTP ${xhr.status}, ${latency}ms`);
                
                if (xhr.status >= 200 && xhr.status < 500) {
                    resolve({
                        status: 'healthy',
                        message: `服务器在线 (HTTP ${xhr.status})`,
                        online: true,
                        latency: latency
                    });
                } else {
                    reject(new Error(`服务器返回错误状态: HTTP ${xhr.status}`));
                }
            };
            
            xhr.onerror = function() {
                const latency = Date.now() - startTime;
                console.log(`健康检查网络错误: ${latency}ms`);
                reject(new Error('无法连接到服务器'));
            };
            
            xhr.ontimeout = function() {
                console.log('健康检查超时');
                reject(new Error('连接超时'));
            };
            
            xhr.send();
        });
    }
    
    static async cleanupTasks() {
        return await this.request('/api/cleanup', {
            method: 'POST'
        });
    }
}

// ==================== 工具函数 ====================
class Utils {
    static formatTime(timestamp) {
        if (!timestamp) return '--:--:--';
        const date = new Date(timestamp * 1000);
        return date.toLocaleTimeString('zh-CN', { 
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    static formatDateTime(timestamp) {
        if (!timestamp) return '--:--:--';
        const date = new Date(timestamp * 1000);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }
    
    static formatDuration(seconds) {
        if (!seconds || seconds < 0) return '0秒';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        const parts = [];
        if (hours > 0) parts.push(`${hours}小时`);
        if (minutes > 0) parts.push(`${minutes}分`);
        if (secs > 0 || parts.length === 0) parts.push(`${secs}秒`);
        
        return parts.join('');
    }
    
    static shortenId(id) {
        if (!id || id.length <= 12) return id;
        return `${id.substring(0, 8)}...${id.substring(id.length - 4)}`;
    }
    
    static parseOutputLine(line) {
        if (typeof line !== 'string') {
            return { time: '', content: String(line) };
        }
        
        const timestampMatch = line.match(/^\[(\d{2}:\d{2}:\d{2})\]\s*/);
        if (timestampMatch) {
            return {
                time: timestampMatch[1],
                content: line.substring(timestampMatch[0].length)
            };
        }
        
        const timeMatch = line.match(/(\d{2}:\d{2}:\d{2})\s+(.*)/);
        if (timeMatch) {
            return {
                time: timeMatch[1],
                content: timeMatch[2]
            };
        }
        
        return { time: '', content: line };
    }
    
    static validatePhoneNumber(phone) {
        return /^1[3-9]\d{9}$/.test(phone);
    }
    
    static validateCourseList(list) {
        if (!list) return false;
        const courses = list.split(',').map(c => c.trim());
        return courses.length > 0 && courses.every(c => /^\d+$/.test(c));
    }
}

// ==================== 任务管理器 ====================
class TaskManager {
    static async refreshAllTasks() {
        if (!state.serverOnline) {
            console.log('服务器离线，跳过任务刷新');
            return;
        }
        
        try {
            const tasksData = await API.getAllTasks();
            state.tasks = {};
            
            elements.tasksTableBody.innerHTML = '';
            
            if (tasksData.tasks && tasksData.tasks.length > 0) {
                tasksData.tasks.forEach(task => {
                    state.tasks[task.task_id] = task;
                    TaskManager.addTaskToTable(task);
                });
            } else {
                elements.tasksTableBody.innerHTML = `
                    <tr>
                        <td colspan="4" class="empty-cell">暂无任务数据</td>
                    </tr>
                `;
            }
            
            TaskManager.updateRunningTasks();
            
            const activeCount = tasksData.tasks.filter(t => t.status === 'running').length;
            elements.activeTasks.textContent = activeCount;
            elements.totalTasks.textContent = tasksData.total || 0;
            elements.lastUpdate.textContent = Utils.formatTime(Date.now() / 1000);
            
            if (state.currentTaskId && state.tasks[state.currentTaskId]) {
                try {
                    const status = await API.getTaskStatus(state.currentTaskId);
                    TaskManager.showStatusDetails(status);
                    
                    if (status.running || status.output) {
                        await TaskManager.refreshTaskOutput(state.currentTaskId);
                    }
                } catch (error) {
                    console.warn('获取任务状态失败:', error);
                }
            }
            
        } catch (error) {
            console.error('刷新任务失败:', error);
            if (error.message.includes('无法连接到服务器') || error.message.includes('请求超时')) {
                state.serverOnline = false;
                updateServerStatus(false);
            }
        }
    }
    
    static addTaskToTable(task) {
        const row = document.createElement('tr');
        row.dataset.taskId = task.task_id;
        
        const statusClass = {
            running: 'status-running',
            completed: 'status-completed'
        }[task.status] || '';
        
        const statusText = {
            running: '运行中',
            completed: '已完成'
        }[task.status] || task.status;
        
        row.innerHTML = `
            <td>
                <div class="task-id" title="${task.task_id}">${Utils.shortenId(task.task_id)}</div>
                <button class="btn-icon select-task" title="选择此任务">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
            <td>
                <span class="task-status ${statusClass}">${statusText}</span>
            </td>
            <td>${Utils.formatTime(task.start_time)}</td>
            <td>
                <div class="task-actions">
                    <button class="btn-icon view-output" title="查看输出">
                        <i class="fas fa-terminal"></i>
                    </button>
                    ${task.status === 'running' ? `
                        <button class="btn-icon stop-task" title="停止任务">
                            <i class="fas fa-stop"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        `;
        
        elements.tasksTableBody.appendChild(row);
        
        const selectBtn = row.querySelector('.select-task');
        selectBtn.addEventListener('click', () => {
            TaskManager.selectTask(task.task_id);
        });
        
        const viewBtn = row.querySelector('.view-output');
        viewBtn.addEventListener('click', () => {
            TaskManager.selectTask(task.task_id);
            document.querySelector('[data-tab="output"]').click();
        });
        
        if (task.status === 'running') {
            const stopBtn = row.querySelector('.stop-task');
            stopBtn.addEventListener('click', async () => {
                if (confirm('确定要停止此任务吗？任务可能不会立即停止。')) {
                    try {
                        await API.stopTask(task.task_id);
                        Toast.show('已发送停止请求', 'info');
                        await TaskManager.refreshAllTasks();
                    } catch (error) {
                        Toast.show(`停止任务失败: ${error.message}`, 'error');
                    }
                }
            });
        }
    }
    
    static updateRunningTasks() {
        const runningTasks = Object.values(state.tasks).filter(t => t.status === 'running');
        
        if (runningTasks.length === 0) {
            elements.runningTasks.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-clock"></i>
                    <p>暂无运行中的任务</p>
                </div>
            `;
            return;
        }
        
        elements.runningTasks.innerHTML = runningTasks.map(task => `
            <div class="task-item running" data-task-id="${task.task_id}">
                <div class="task-info">
                    <div class="task-id" title="${task.task_id}">${Utils.shortenId(task.task_id)}</div>
                    <div class="task-status status-running">运行中</div>
                </div>
                <div class="task-actions">
                    <button class="btn-icon select-running-task" title="选择此任务">
                        <i class="fas fa-play-circle"></i>
                    </button>
                </div>
            </div>
        `).join('');
        
        document.querySelectorAll('.select-running-task').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const taskItem = e.target.closest('.task-item');
                const taskId = taskItem.dataset.taskId;
                TaskManager.selectTask(taskId);
            });
        });
    }
    
    static async refreshTaskStatus(taskId) {
        if (!state.serverOnline) return;
        
        try {
            const status = await API.getTaskStatus(taskId);
            
            if (state.currentTaskId === taskId) {
                TaskManager.showStatusDetails(status);
            }
            
        } catch (error) {
            console.error('刷新任务状态失败:', error);
        }
    }
    
    static async refreshTaskOutput(taskId) {
        if (!state.serverOnline) return;
        
        try {
            const outputData = await API.getTaskOutput(taskId);
            
            if (state.currentTaskId === taskId) {
                TaskManager.displayOutput(outputData.output || []);
            }
            
        } catch (error) {
            console.error('刷新任务输出失败:', error);
        }
    }
    
    static displayOutput(outputLines) {
        if (!outputLines || outputLines.length === 0) {
            elements.taskOutput.innerHTML = `
                <div class="output-placeholder">
                    <i class="fas fa-code"></i>
                    <p>暂无输出内容</p>
                </div>
            `;
            elements.outputCount.textContent = '0 条输出';
            return;
        }
        
        const filteredLines = outputLines.filter(line => {
            if (state.outputFilter === 'all') return true;
            return line.type === state.outputFilter;
        });
        
        const displayLines = filteredLines.slice(-CONFIG.maxOutputLines);
        
        elements.taskOutput.innerHTML = displayLines.map(line => {
            const { time, content } = Utils.parseOutputLine(line.content || '');
            const typeClass = line.type === 'stderr' ? 'stderr' : 'stdout';
            const icon = line.type === 'stderr' ? 'fas fa-exclamation-circle' : 'fas fa-info-circle';
            const timeHtml = time ? `<span class="output-time">[${time}]</span> ` : '';
            
            return `
                <div class="output-line ${typeClass}">
                    <i class="${icon} output-icon"></i>
                    ${timeHtml}
                    <span class="output-content">${content}</span>
                </div>
            `;
        }).join('');
        
        elements.outputCount.textContent = `${filteredLines.length} 条输出 (显示 ${displayLines.length} 条)`;
        
        elements.taskOutput.scrollTop = elements.taskOutput.scrollHeight;
    }
    
    static showStatusDetails(status) {
        if (!status) {
            elements.statusDetails.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle"></i>
                    <p>选择任务查看状态详情</p>
                </div>
            `;
            return;
        }
        
        const startTime = status.start_time ? Utils.formatDateTime(status.start_time) : '未知';
        const endTime = status.end_time ? Utils.formatDateTime(status.end_time) : '--:--:--';
        const duration = status.end_time 
            ? Utils.formatDuration(status.end_time - status.start_time)
            : Utils.formatDuration(Date.now() / 1000 - status.start_time);
        
        let resultHtml = '';
        if (status.last_result) {
            const stdoutLength = status.last_result.stdout ? status.last_result.stdout.length : 0;
            const stderrLength = status.last_result.stderr ? status.last_result.stderr.length : 0;
            
            resultHtml = `
                <div class="detail-item">
                    <div class="detail-label">
                        <i class="fas fa-check-circle"></i> 执行结果
                    </div>
                    <div class="detail-value">
                        返回码: ${status.last_result.returncode}<br>
                        标准输出长度: ${stdoutLength} 字符<br>
                        错误输出长度: ${stderrLength} 字符
                    </div>
                </div>
            `;
        }
        
        let errorHtml = '';
        if (status.last_error) {
            errorHtml = `
                <div class="detail-item">
                    <div class="detail-label">
                        <i class="fas fa-exclamation-triangle"></i> 错误信息
                    </div>
                    <div class="detail-value">
                        ${status.last_error.stderr || status.last_error.message || '未知错误'}
                    </div>
                </div>
            `;
        }
        
        elements.statusDetails.innerHTML = `
            <div class="detail-item">
                <div class="detail-label">
                    <i class="fas fa-info-circle"></i> 任务状态
                </div>
                <div class="detail-value">
                    ${status.running ? '🟢 运行中' : '🔵 已完成'}
                    ${status.last_error ? ' (有错误)' : ''}
                </div>
            </div>
            
            <div class="detail-item">
                <div class="detail-label">
                    <i class="fas fa-clock"></i> 运行时间
                </div>
                <div class="detail-value">
                    <strong>开始时间:</strong> ${startTime}<br>
                    <strong>结束时间:</strong> ${endTime}<br>
                    <strong>持续时间:</strong> ${duration}
                </div>
            </div>
            
            ${resultHtml}
            ${errorHtml}
        `;
    }
    
    static selectTask(taskId) {
        state.currentTaskId = taskId;
        const task = state.tasks[taskId];
        
        if (!task) {
            Toast.show('任务不存在或已过期', 'warning');
            return;
        }
        
        document.querySelectorAll('.task-item, tr').forEach(el => {
            el.classList.remove('selected');
        });
        
        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        if (taskElement) {
            taskElement.classList.add('selected');
        }
        
        TaskManager.refreshTaskStatus(taskId);
        
        Toast.show(`已选择任务 ${Utils.shortenId(taskId)}`, 'info');
    }
}

// ==================== 服务器健康检查 ====================
async function updateServerStatus(showToast = true) {
    if (state.isCheckingHealth) {
        console.log('健康检查正在进行中，跳过');
        return;
    }
    
    state.isCheckingHealth = true;
    
    const originalBtnText = elements.healthCheckBtn.innerHTML;
    elements.serverStatus.textContent = '检查中...';
    elements.serverStatus.className = 'status checking';
    elements.healthCheckBtn.innerHTML = '<span class="loading"></span> 检查中';
    elements.healthCheckBtn.disabled = true;
    
    try {
        const healthData = await API.healthCheck();
        
        state.serverOnline = true;
        elements.serverStatus.textContent = '在线';
        elements.serverStatus.className = 'status online';
        
        if (showToast) {
            Toast.show(healthData.message, 'success', 3000);
        }
        
        elements.startBtn.disabled = false;
        elements.startBtn.title = '';
        
        await TaskManager.refreshAllTasks();
        
    } catch (error) {
        console.error('健康检查失败:', error);
        
        state.serverOnline = false;
        elements.serverStatus.textContent = '离线';
        elements.serverStatus.className = 'status offline';
        
        if (showToast) {
            Toast.show(`服务器连接失败: ${error.message}`, 'error', 5000);
        }
        
        elements.startBtn.disabled = true;
        elements.startBtn.title = '服务器离线，无法启动任务';
        
        elements.tasksTableBody.innerHTML = `
            <tr>
                <td colspan="4" class="empty-cell">服务器离线，无法获取任务数据</td>
            </tr>
        `;
        elements.runningTasks.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-unlink"></i>
                <p>服务器连接已断开</p>
            </div>
        `;
        
    } finally {
        elements.healthCheckBtn.innerHTML = originalBtnText;
        elements.healthCheckBtn.disabled = false;
        state.isCheckingHealth = false;
    }
}

// ==================== 自动刷新控制 ====================
function startAutoRefresh() {
    stopAutoRefresh();
    if (state.serverOnline) {
        state.autoRefreshTimer = setInterval(() => {
            TaskManager.refreshAllTasks();
        }, CONFIG.autoRefreshInterval);
    }
}

function stopAutoRefresh() {
    if (state.autoRefreshTimer) {
        clearInterval(state.autoRefreshTimer);
        state.autoRefreshTimer = null;
    }
}

function startHealthCheckTimer() {
    if (state.healthCheckTimer) {
        clearInterval(state.healthCheckTimer);
    }
    
    state.healthCheckTimer = setInterval(() => {
        updateServerStatus(false);
    }, CONFIG.healthCheckInterval);
}

// ==================== 初始化函数 ====================
async function initialize() {
    console.log('初始化超星学习通任务管理系统...');
    
    // 1. 设置服务器地址选择器
    elements.serverUrl.addEventListener('change', async (e) => {
        state.currentServer = e.target.value;
        const selectedOption = e.target.selectedOptions[0];
        
        Toast.show(`切换到: ${selectedOption.text}`, 'info');
        await updateServerStatus(true);
        
        if (state.autoRefreshEnabled) {
            startAutoRefresh();
        }
    });
    
    // 2. 健康检查按钮
    elements.healthCheckBtn.addEventListener('click', async () => {
        await updateServerStatus(true);
    });
    
    // 3. 自动刷新控制
    elements.autoRefresh.addEventListener('change', (e) => {
        state.autoRefreshEnabled = e.target.checked;
        if (state.autoRefreshEnabled) {
            startAutoRefresh();
            Toast.show('已开启自动刷新', 'info');
        } else {
            stopAutoRefresh();
            Toast.show('已关闭自动刷新', 'info');
        }
    });
    
    // 4. 手动刷新
    elements.refreshBtn.addEventListener('click', async () => {
        if (!state.serverOnline) {
            Toast.show('服务器离线，无法刷新', 'warning');
            return;
        }
        
        await TaskManager.refreshAllTasks();
        Toast.show('已刷新任务列表', 'info');
    });
    
    // 5. 清空输出
    elements.clearBtn.addEventListener('click', () => {
        elements.taskOutput.innerHTML = `
            <div class="output-placeholder">
                <i class="fas fa-code"></i>
                <p>输出已清空</p>
            </div>
        `;
        elements.outputCount.textContent = '0 条输出';
        Toast.show('已清空输出窗口', 'info');
    });
    
    // 6. 清理旧任务
    elements.cleanupBtn.addEventListener('click', async () => {
        if (!state.serverOnline) {
            Toast.show('服务器离线，无法清理', 'warning');
            return;
        }
        
        if (confirm('确定要清理24小时前的旧任务记录吗？此操作不可撤销。')) {
            try {
                const result = await API.cleanupTasks();
                Toast.show(result.message, 'success');
                await TaskManager.refreshAllTasks();
            } catch (error) {
                Toast.show(`清理失败: ${error.message}`, 'error');
            }
        }
    });
    
    // 7. Tab切换
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            elements.tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${tabId}Tab`) {
                    content.classList.add('active');
                }
            });
            
            if (tabId === 'output' && state.currentTaskId) {
                TaskManager.refreshTaskOutput(state.currentTaskId);
            }
        });
    });
    
    // 8. 输出过滤
    document.querySelectorAll('input[name="outputType"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.outputFilter = e.target.value;
            if (state.currentTaskId) {
                TaskManager.refreshTaskOutput(state.currentTaskId);
            }
        });
    });
    
    // 9. 表单提交
    elements.taskForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // 直接检查服务器状态，不依赖state.serverOnline
        console.log('表单提交，检查服务器状态...');
        
        const username = elements.username.value.trim();
        const password = elements.password.value;
        const listId = elements.listId.value.trim();
        
        if (!username || !password || !listId) {
            Toast.show('请填写所有必填字段', 'warning');
            return;
        }
        
        if (!Utils.validatePhoneNumber(username)) {
            Toast.show('请输入正确的手机号格式 (11位数字)', 'warning');
            elements.username.focus();
            return;
        }
        
        if (!Utils.validateCourseList(listId)) {
            Toast.show('课程ID格式不正确，应为数字，多个用逗号分隔', 'warning');
            elements.listId.focus();
            return;
        }
        
        const originalText = elements.startBtn.innerHTML;
        elements.startBtn.innerHTML = '<span class="loading"></span> 启动中...';
        elements.startBtn.disabled = true;
        
        try {
            // 直接尝试运行任务，如果失败再检查服务器状态
            const result = await API.runTask(username, password, listId);
            
            Toast.show(`任务启动成功！任务ID: ${Utils.shortenId(result.task_id)}`, 'success');
            
            elements.password.value = '';
            
            // 更新服务器状态为在线
            state.serverOnline = true;
            elements.serverStatus.textContent = '在线';
            elements.serverStatus.className = 'status online';
            elements.startBtn.disabled = false;
            elements.startBtn.title = '';
            
            await TaskManager.refreshAllTasks();
            
            TaskManager.selectTask(result.task_id);
            
            document.querySelector('[data-tab="output"]').click();
            
        } catch (error) {
            console.error('启动任务失败:', error);
            
            // 如果任务启动失败，检查服务器状态
            Toast.show(`启动任务失败: ${error.message}`, 'error');
            
            // 更新服务器状态
            state.serverOnline = false;
            elements.serverStatus.textContent = '离线';
            elements.serverStatus.className = 'status offline';
            elements.startBtn.disabled = true;
            elements.startBtn.title = '服务器离线，无法启动任务';
            
        } finally {
            elements.startBtn.innerHTML = originalText;
            elements.startBtn.disabled = false;
        }
    });
    
    // 10. 初始健康检查
    await updateServerStatus(false);
    
    // 11. 启动定期健康检查
    startHealthCheckTimer();
    
    // 12. 初始任务刷新
    if (state.serverOnline) {
        await TaskManager.refreshAllTasks();
    }
    
    // 13. 开发环境预填充示例数据
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        setTimeout(() => {
            populateExampleData();
        }, 1000);
    }
    
    console.log('系统初始化完成');
}

// ==================== 开发辅助函数 ====================
function populateExampleData() {
    const isLocalDev = window.location.hostname === 'localhost' || 
                      window.location.hostname === '127.0.0.1';
    
    if (!isLocalDev) return;
    
    const exampleAccounts = [
        {
            username: '19837765338',
            password: 'Cyt2006820.',
            listId: '257040405',
            description: '示例账号1'
        },
        {
            username: '19087656626',
            password: '456456ggg',
            listId: '256597724',
            description: '示例账号2'
        }
    ];
    
    const example = exampleAccounts[Math.floor(Math.random() * exampleAccounts.length)];
    
    elements.username.value = example.username;
    elements.password.value = example.password;
    elements.listId.value = example.listId;
    
    Toast.show(`已填充${example.description}（仅开发环境）`, 'info', 3000);
}

// ==================== 页面生命周期管理 ====================
document.addEventListener('DOMContentLoaded', () => {
    Toast.show('系统正在初始化...', 'info', 2000);
    
    setTimeout(() => {
        initialize().catch(error => {
            console.error('系统初始化失败:', error);
            Toast.show(`系统初始化失败: ${error.message}`, 'error');
        });
    }, 500);
});

window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
    if (state.healthCheckTimer) {
        clearInterval(state.healthCheckTimer);
    }
});

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopAutoRefresh();
    } else if (state.autoRefreshEnabled && state.serverOnline) {
        startAutoRefresh();
        TaskManager.refreshAllTasks();
    }
});

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        if (state.serverOnline) {
            TaskManager.refreshAllTasks();
        }
    }
    
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'C') {
        e.preventDefault();
        elements.clearBtn.click();
    }
    
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        elements.cleanupBtn.click();
    }
    
    if (e.key === 'F5') {
        e.preventDefault();
        location.reload();
    }
});

// ==================== 调试工具 ====================
window.ChaoxingManager = {
    API,
    Utils,
    TaskManager,
    Toast,
    state,
    elements,
    updateServerStatus
};

// 添加调试函数
window.testConnection = async function() {
    console.log('测试服务器连接...');
    console.log('当前服务器:', state.currentServer);
    
    try {
        const response = await fetch(state.currentServer, {
            method: 'GET',
            headers: {
                'Accept': 'text/html,application/json'
            }
        });
        console.log('连接成功:', response.status, response.statusText);
        return true;
    } catch (error) {
        console.log('连接失败:', error.message);
        return false;
    }
};

console.log('超星学习通任务管理系统已加载');