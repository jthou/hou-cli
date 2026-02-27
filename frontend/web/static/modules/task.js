// 任务管理（普通任务 + 定时任务）
export const taskModule = {
    // 初始化任务统计卡片
    initTaskStats() {
        // 默认显示普通任务的统计卡片
        this.updateStats(false); // false表示普通任务
        this.updateToolbar(false);
    },
    initTaskManagement() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.getAttribute('data-tab');
                this.switchTaskTab(tab);
            });
        });

        const createTaskBtn = document.getElementById('createTaskBtn');
        if (createTaskBtn) createTaskBtn.addEventListener('click', () => this.showCreateTaskModal());

        const createScheduledTaskBtn = document.getElementById('createScheduledTaskBtn');
        if (createScheduledTaskBtn) {
            createScheduledTaskBtn.addEventListener('click', () => this.showCreateScheduledTaskModal());
        }

        const refreshTasksBtn = document.getElementById('refreshTasksBtn');
        if (refreshTasksBtn) refreshTasksBtn.addEventListener('click', () => this.loadTasks());

        const refreshScheduledTasksBtn = document.getElementById('refreshScheduledTasksBtn');
        if (refreshScheduledTasksBtn) {
            refreshScheduledTasksBtn.addEventListener('click', () => this.loadScheduledTasks());
        }

        const cleanupStaleTasksBtn = document.getElementById('cleanupStaleTasksBtn');
        if (cleanupStaleTasksBtn) cleanupStaleTasksBtn.addEventListener('click', () => this.cleanupStaleTasks());

        const statusFilter = document.getElementById('taskStatusFilter');
        if (statusFilter) statusFilter.addEventListener('change', () => this.loadTasks());

        const scheduledTaskFilter = document.getElementById('scheduledTaskFilter');
        if (scheduledTaskFilter) {
            scheduledTaskFilter.addEventListener('change', () => this.loadScheduledTasks());
        }

        const searchInput = document.getElementById('taskSearchInput');
        if (searchInput) searchInput.addEventListener('input', () => this.filterTasks());

        const scheduledTaskSearchInput = document.getElementById('scheduledTaskSearchInput');
        if (scheduledTaskSearchInput) {
            scheduledTaskSearchInput.addEventListener('input', () => this.filterScheduledTasks());
        }
    },

    switchTaskTab(tab) {
        // 更新标签页激活状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tab);
        });

        const isScheduled = tab === 'scheduled';
        
        // 动态更新内容
        this.updateTaskView(isScheduled);
        
        // 切换创建按钮
        document.getElementById('createTaskBtn').style.display = isScheduled ? 'none' : 'inline-block';
        document.getElementById('createScheduledTaskBtn').style.display = isScheduled ? 'inline-block' : 'none';

        // 加载对应数据
        this.loadHeartbeatStatus();
        if (isScheduled) {
            this.loadScheduledTasks();
        } else {
            this.loadTasks();
        }
    },
    
    updateTaskView(isScheduled) {
        // 更新统计区域
        this.updateStats(isScheduled);
        
        // 更新工具栏
        this.updateToolbar(isScheduled);
        
        // 更新任务列表容器
        const taskList = document.getElementById('taskListContainer');
        if (taskList) {
            taskList.innerHTML = '<div class="empty-state">加载中...</div>';
        }
    },
    
    updateStats(isScheduled) {
        const container = document.getElementById('taskStatsContainer');
        if (!container) return;
        
        const statsConfig = isScheduled ? this.scheduledStatsConfig : this.normalStatsConfig;
        
        container.innerHTML = statsConfig.map(stat => `
            <div class="stat-card ${stat.class || ''}">
                <span class="stat-number" id="${stat.id}">0</span>
                <span class="stat-label">${stat.label}</span>
            </div>
        `).join('');
    },
    
    updateToolbar(isScheduled) {
        const filterSelect = document.getElementById('taskStatusFilter');
        const extraActionButton = document.getElementById('extraActionBtn');
        
        if (!filterSelect || !extraActionButton) return;
        
        // 更新筛选选项
        const options = isScheduled ? this.scheduledFilterOptions : this.normalFilterOptions;
        filterSelect.innerHTML = options.map(opt => 
            `<option value="${opt.value}">${opt.label}</option>`
        ).join('');
        
        // 控制额外按钮显示
        if (isScheduled) {
            extraActionButton.style.display = 'none';
        } else {
            extraActionButton.style.display = 'inline-block';
            extraActionButton.textContent = '清理超时';
            extraActionButton.onclick = () => this.cleanupStaleTasks();
        }
    },

    async loadHeartbeatStatus() {
        const dotEl = document.getElementById('heartbeatDot');
        const runningEl = document.getElementById('heartbeatRunning');
        const lastEl = document.getElementById('heartbeatLast');
        const uptimeEl = document.getElementById('heartbeatUptime');
        const metricsEl = document.getElementById('heartbeatMetrics');
        if (!runningEl) return;

        try {
            const res = await fetch('/api/heartbeat/status');
            const data = await res.json();
            if (!data.success || !data.status) {
                if (runningEl) runningEl.textContent = '获取失败';
                return;
            }
            const s = data.status;
            if (dotEl) dotEl.className = 'heartbeat-dot ' + (s.is_running ? 'heartbeat-ok' : 'heartbeat-stop');
            runningEl.textContent = s.is_running ? '运行中' : '已停止';
            lastEl.textContent = s.last_heartbeat ? new Date(s.last_heartbeat).toLocaleTimeString('zh-CN') : '-';
            const uptime = s.uptime_seconds || 0;
            uptimeEl.textContent = uptime >= 3600
                ? `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`
                : uptime >= 60 ? `${Math.floor(uptime / 60)}m` : `${uptime}s`;
            const m = s.metrics || {};
            metricsEl.textContent = m.cpu_percent != null && m.memory_percent != null
                ? `${(m.cpu_percent || 0).toFixed(1)}% / ${(m.memory_percent || 0).toFixed(1)}%`
                : '-';
        } catch (e) {
            runningEl.textContent = '请求失败';
        }
    },

    async loadTasks() {
        this.loadHeartbeatStatus();
        const taskList = document.getElementById('taskListContainer');
        if (!taskList) return;

        taskList.innerHTML = '<div class="empty-state">加载中...</div>';

        try {
            const statusFilter = document.getElementById('taskStatusFilter');
            const status = statusFilter ? statusFilter.value : '';

            let url = '/api/task-queue/tasks?limit=100&offset=0';
            if (status) url += `&status=${status}`;

            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            if (data.success && data.tasks) {
                this.updateTasksDisplay(data.tasks);
                this.updateTasksStats(data.tasks);
            } else {
                taskList.innerHTML = '<div class="empty-state">加载任务失败</div>';
            }
        } catch (error) {
            console.error('加载任务失败:', error);
            taskList.innerHTML = `<div class="empty-state">加载失败: ${error.message}</div>`;
        }
    },

    updateTasksDisplay(tasks) {
        const taskList = document.getElementById('taskListContainer');
        if (!taskList) return;

        if (tasks.length === 0) {
            taskList.innerHTML = '<div class="empty-state">暂无任务</div>';
            return;
        }

        const searchInput = document.getElementById('taskSearchInput');
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';

        const filteredTasks = tasks.filter(task => {
            if (!searchTerm) return true;
            const taskName = (task.task_name || '').toLowerCase();
            const taskId = (task.task_id || '').toLowerCase();
            return taskName.includes(searchTerm) || taskId.includes(searchTerm);
        });

        if (filteredTasks.length === 0) {
            taskList.innerHTML = '<div class="empty-state">没有匹配的任务</div>';
            return;
        }

        taskList.innerHTML = filteredTasks.map(task => {
            const statusClass = this.getTaskStatusClass(task.status);
            const priorityClass = this.getTaskPriorityClass(task.priority);
            const progress = task.progress || 0;

            return `
                <div class="task-item" data-task-id="${task.task_id}">
                    <div class="task-header">
                        <div class="task-title">
                            <span class="task-name">${this.escapeHtml(task.task_name || '未命名任务')}</span>
                            <span class="task-id">#${task.task_id}</span>
                        </div>
                        <div class="task-actions">
                            <span class="task-status-tag ${statusClass}">${this.getTaskStatusText(task.status)}</span>
                            <span class="task-priority-tag ${priorityClass}">${this.getTaskPriorityText(task.priority)}</span>
                            ${task.status === 'running' || task.status === 'queued' ?
                                `<button class="btn-small btn-danger" onclick="app.cancelTask('${task.task_id}')">取消</button>` : ''}
                        </div>
                    </div>
                    <div class="task-body">
                        <div class="task-info">
                            <div class="task-info-item">
                                <span class="info-label">类型:</span>
                                <span class="info-value">${this.escapeHtml(task.task_type || 'unknown')}</span>
                            </div>
                            <div class="task-info-item">
                                <span class="info-label">创建时间:</span>
                                <span class="info-value">${this.formatDateTime(task.created_at)}</span>
                            </div>
                            ${task.started_at ? `
                            <div class="task-info-item">
                                <span class="info-label">开始时间:</span>
                                <span class="info-value">${this.formatDateTime(task.started_at)}</span>
                            </div>` : ''}
                            ${task.completed_at ? `
                            <div class="task-info-item">
                                <span class="info-label">完成时间:</span>
                                <span class="info-value">${this.formatDateTime(task.completed_at)}</span>
                            </div>` : ''}
                            ${task.retries_attempted > 0 ? `
                            <div class="task-info-item">
                                <span class="info-label">重试次数:</span>
                                <span class="info-value">${task.retries_attempted}/${task.max_retries || 3}</span>
                            </div>` : ''}
                        </div>
                        ${task.status === 'running' ? `
                        <div class="task-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${progress}%"></div>
                            </div>
                            <span class="progress-text">${progress}%</span>
                        </div>` : ''}
                        ${task.error_message ? `
                        <div class="task-error">
                            <strong>错误:</strong> ${this.escapeHtml(task.error_message)}
                        </div>` : ''}
                    </div>
                    <div class="task-footer">
                        <button class="btn-small btn-secondary" onclick="app.viewTaskDetail('${task.task_id}')">查看详情</button>
                    </div>
                </div>
            `;
        }).join('');
    },

    updateTasksStats(tasks) {
        const stats = { total: tasks.length, pending: 0, running: 0, completed: 0, failed: 0 };

        tasks.forEach(task => {
            if (task.status === 'pending' || task.status === 'queued') stats.pending++;
            else if (task.status === 'running') stats.running++;
            else if (task.status === 'completed') stats.completed++;
            else if (task.status === 'failed') stats.failed++;
        });

        const ids = ['totalTasksCount', 'pendingTasksCount', 'runningTasksCount', 'completedTasksCount', 'failedTasksCount'];
        const keys = ['total', 'pending', 'running', 'completed', 'failed'];
        keys.forEach((key, i) => {
            const el = document.getElementById(ids[i]);
            if (el) el.textContent = stats[key];
        });
    },

    filterTasks() {
        this.loadTasks();
    },

    async showCreateTaskModal() {
        let taskTypes = [];
        try {
            const response = await fetch('/api/task-queue/task-types');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.task_types) taskTypes = data.task_types;
            } else {
                console.warn('获取任务类型失败:', response.status, await response.text());
            }
        } catch (error) {
            console.error('加载任务类型失败:', error);
        }
        // 后端不可用时的兜底列表（与 task_handlers.TASK_TYPES 保持一致）
        if (taskTypes.length === 0) {
            taskTypes = [
                { type: 'video_download', name: '视频下载', description: '从 Bilibili、YouTube 等平台下载视频', metadata_schema: { url: { type: 'string', required: true, description: '视频链接', placeholder: '如：https://...' } } },
                { type: 'weather_query', name: '天气查询', description: '查询指定地点的天气预报', metadata_schema: { location: { type: 'string', required: true, description: '城市名称', placeholder: '如：北京、上海、深圳' }, query_type: { type: 'string', required: false, description: '查询类型', enum: [{ value: 'current', label: '实时天气' }, { value: 'forecast', label: '天气预报' }], default: 'current' } } },
                { type: 'speech_to_text', name: '语音转文字', description: '使用 Whisper 将音频文件转成文字或字幕', metadata_schema: { input_file: { type: 'string', required: true, description: '音频文件路径', placeholder: '如：/Users/xx/audio.mp3' } } },
                { type: 'video_extract_audio', name: '视频提取音频', description: '从本地视频文件中提取音频轨并保存为音频文件', metadata_schema: { input_file: { type: 'string', required: true, description: '本地视频文件路径', placeholder: '如：/Users/xx/video.mp4' } } }
            ];
        }

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'createTaskModal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>创建新任务</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="taskTypeSelect">任务类型 <span class="required">*</span></label>
                        <select id="taskTypeSelect" class="form-control">
                            <option value="">请选择任务类型</option>
                            ${taskTypes.map(type => `
                                <option value="${type.type}" data-schema='${JSON.stringify(type.metadata_schema || {})}'>
                                    ${type.name} - ${type.description}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="taskNameInput">任务名称</label>
                        <input type="text" id="taskNameInput" class="form-control" placeholder="留空将根据类型和参数自动生成">
                    </div>
                    <div class="form-group">
                        <label for="taskPrioritySelect">优先级</label>
                        <select id="taskPrioritySelect" class="form-control">
                            <option value="1">低 (1)</option>
                            <option value="2" selected>普通 (2)</option>
                            <option value="3">高 (3)</option>
                            <option value="4">紧急 (4)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="taskMaxRetriesInput">最大重试次数</label>
                        <input type="number" id="taskMaxRetriesInput" class="form-control" value="3" min="0" max="10">
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="taskAutoQueue" checked>
                            自动入队
                        </label>
                    </div>
                    <div id="taskMetadataFields" class="form-group">
                        <label>任务参数</label>
                        <div id="metadataInputs"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal').remove()">取消</button>
                    <button class="btn-primary" onclick="app.submitCreateTask()">创建任务</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        const taskTypeSelect = document.getElementById('taskTypeSelect');
        const metadataInputs = document.getElementById('metadataInputs');

        taskTypeSelect.addEventListener('change', () => {
            const selectedOption = taskTypeSelect.options[taskTypeSelect.selectedIndex];
            if (selectedOption.value) {
                const schema = JSON.parse(selectedOption.getAttribute('data-schema') || '{}');
                this.renderMetadataFields(schema, metadataInputs);
            } else {
                metadataInputs.innerHTML = '';
            }
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    renderMetadataFields(schema, container) {
        container.innerHTML = '';

        if (!schema || Object.keys(schema).length === 0) {
            container.innerHTML = '<p class="form-hint">此任务类型无需额外参数</p>';
            return;
        }

        for (const [key, field] of Object.entries(schema)) {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'metadata-field';

            const label = document.createElement('label');
            label.textContent = field.description || key;
            if (field.required) label.innerHTML += ' <span class="required">*</span>';

            let input;
            if (field.enum && Array.isArray(field.enum)) {
                // 枚举：渲染下拉选择
                input = document.createElement('select');
                input.className = 'form-control';
                const defaultVal = field.default || (field.enum[0] && field.enum[0].value);
                input.innerHTML = field.enum.map(opt => {
                    const val = opt.value ?? opt;
                    const lab = opt.label ?? opt;
                    const sel = val === defaultVal ? ' selected' : '';
                    return `<option value="${this.escapeHtml(String(val))}"${sel}>${this.escapeHtml(String(lab))}</option>`;
                }).join('');
            } else if (field.type === 'array') {
                input = document.createElement('textarea');
                input.placeholder = field.placeholder || '请输入JSON数组，例如: ["item1", "item2"]';
                input.rows = 3;
            } else if (field.type === 'object') {
                input = document.createElement('textarea');
                input.placeholder = field.placeholder || '请输入JSON对象，例如: {"key": "value"}';
                input.rows = 3;
            } else if (field.type === 'integer') {
                input = document.createElement('input');
                input.type = 'number';
                input.step = '1';
                if (field.placeholder) input.placeholder = field.placeholder;
            } else {
                input = document.createElement('input');
                input.type = 'text';
                if (field.placeholder) input.placeholder = field.placeholder;
            }

            input.className = 'form-control';
            input.name = `metadata_${key}`;
            input.id = `metadata_${key}`;
            input.required = field.required || false;

            fieldDiv.appendChild(label);
            fieldDiv.appendChild(input);
            container.appendChild(fieldDiv);
        }
    },

    async submitCreateTask() {
        const taskType = document.getElementById('taskTypeSelect').value;
        const taskName = document.getElementById('taskNameInput').value;
        const priority = parseInt(document.getElementById('taskPrioritySelect').value);
        const maxRetries = parseInt(document.getElementById('taskMaxRetriesInput').value) || 3;
        const autoQueue = document.getElementById('taskAutoQueue').checked;

        if (!taskType) {
            alert('请选择任务类型');
            return;
        }

        const metadata = {};
        document.querySelectorAll('#metadataInputs input, #metadataInputs textarea, #metadataInputs select').forEach(input => {
            const key = input.name.replace('metadata_', '');
            let value = input.value.trim();

            if (value) {
                if (input.tagName === 'TEXTAREA') {
                    try {
                        value = JSON.parse(value);
                    } catch (e) {}
                } else if (input.type === 'number') {
                    value = parseFloat(value);
                }
                metadata[key] = value;
            }
        });

        const payload = {
            task_type: taskType,
            priority,
            max_retries: maxRetries,
            metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
            auto_queue: autoQueue
        };
        if (taskName) payload.task_name = taskName;
        await this.createTask(payload);

        const modal = document.getElementById('createTaskModal');
        if (modal) modal.remove();
    },

    async createTask(taskData) {
        try {
            const response = await fetch('/api/task-queue/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(taskData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            if (result.success) {
                alert('任务创建成功: ' + result.task_id);
                this.loadTasks();
            } else {
                alert('任务创建失败: ' + (result.message || '未知错误'));
            }
        } catch (error) {
            console.error('创建任务失败:', error);
            alert('创建任务失败: ' + error.message);
        }
    },

    async cancelTask(taskId) {
        if (!confirm('确定要取消这个任务吗？')) return;

        try {
            const response = await fetch(`/api/task-queue/tasks/${taskId}/cancel`, { method: 'POST' });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const result = await response.json();
            if (result.success) {
                alert('任务已取消');
                this.loadTasks();
            } else {
                alert('取消任务失败: ' + (result.message || '未知错误'));
            }
        } catch (error) {
            console.error('取消任务失败:', error);
            alert('取消任务失败: ' + error.message);
        }
    },

    async viewTaskDetail(taskId) {
        try {
            const response = await fetch(`/api/task-queue/tasks/${taskId}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            if (data.success && data.task) {
                const task = data.task;
                this.showTaskDetailModal(task);
            } else {
                alert('获取任务详情失败');
            }
        } catch (error) {
            console.error('获取任务详情失败:', error);
            alert('获取任务详情失败: ' + error.message);
        }
    },

    showTaskDetailModal(task) {
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'taskDetailModal';
        
        // 生成任务基本信息
        const basicInfo = `
            <div class="task-detail-section">
                <h3>基本信息</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">任务ID:</span>
                        <span class="detail-value">${this.escapeHtml(task.task_id)}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">任务名称:</span>
                        <span class="detail-value">${this.escapeHtml(task.task_name || '未命名')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">任务类型:</span>
                        <span class="detail-value">${this.escapeHtml(task.task_type || '-')}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">状态:</span>
                        <span class="detail-value">
                            <span class="task-status-tag ${this.getTaskStatusClass(task.status)}">
                                ${this.getTaskStatusText(task.status)}
                            </span>
                        </span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">优先级:</span>
                        <span class="detail-value">
                            <span class="task-priority-tag ${this.getTaskPriorityClass(task.priority)}">
                                ${this.getTaskPriorityText(task.priority)}
                            </span>
                        </span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">创建时间:</span>
                        <span class="detail-value">${this.formatDateTime(task.created_at)}</span>
                    </div>
                    ${task.started_at ? `
                    <div class="detail-item">
                        <span class="detail-label">开始时间:</span>
                        <span class="detail-value">${this.formatDateTime(task.started_at)}</span>
                    </div>` : ''}
                    ${task.completed_at ? `
                    <div class="detail-item">
                        <span class="detail-label">完成时间:</span>
                        <span class="detail-value">${this.formatDateTime(task.completed_at)}</span>
                    </div>` : ''}
                    ${task.duration ? `
                    <div class="detail-item">
                        <span class="detail-label">耗时:</span>
                        <span class="detail-value">${task.duration.toFixed(1)}s</span>
                    </div>` : ''}
                    ${task.progress !== undefined ? `
                    <div class="detail-item">
                        <span class="detail-label">进度:</span>
                        <span class="detail-value">${task.progress}%</span>
                    </div>` : ''}
                    ${task.retry_count > 0 ? `
                    <div class="detail-item">
                        <span class="detail-label">重试次数:</span>
                        <span class="detail-value">${task.retry_count}/${task.max_retries || 3}</span>
                    </div>` : ''}
                </div>
            </div>
        `;

        // 生成错误信息（如果有）
        const errorSection = task.error ? `
            <div class="task-detail-section error-section">
                <h3>错误信息</h3>
                <div class="error-message">
                    ${this.escapeHtml(task.error)}
                </div>
            </div>
        ` : '';

        // 生成执行结果（如果有）
        let resultSection = '';
        if (task.result && task.status === 'completed') {
            resultSection = `
                <div class="task-detail-section">
                    <h3>执行结果</h3>
                    ${this.renderTaskResult(task.result)}
                </div>
            `;
        }

        // 生成元数据（如果有）
        const metadataSection = task.metadata ? `
            <div class="task-detail-section">
                <h3>任务参数</h3>
                <pre class="metadata-display">${JSON.stringify(task.metadata, null, 2)}</pre>
            </div>
        ` : '';

        modal.innerHTML = `
            <div class="modal-content task-detail-modal">
                <div class="modal-header">
                    <h2>任务详情</h2>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    ${basicInfo}
                    ${errorSection}
                    ${resultSection}
                    ${metadataSection}
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary" onclick="this.closest('.modal').remove()">关闭</button>
                    ${task.status === 'running' || task.status === 'queued' ? 
                        `<button class="btn-danger" onclick="app.cancelTask('${task.task_id}'); this.closest('.modal').remove()">取消任务</button>` : ''}
                </div>
            </div>
        `;

        // 添加到页面并显示
        document.body.appendChild(modal);
        
        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    renderTaskResult(result) {
        // 根据任务类型渲染不同的结果
        if (result.status === 'success') {
            if (result.location && result.query_type === 'forecast') {
                // 天气预报结果
                return this.renderWeatherForecastResult(result);
            } else if (result.location && result.query_type === 'current') {
                // 实时天气结果
                return this.renderCurrentWeatherResult(result);
            } else if (result.data) {
                // 通用数据结果
                return this.renderGenericDataResult(result);
            }
        }
        
        // 默认显示原始JSON
        return `
            <div class="result-json">
                <pre>${JSON.stringify(result, null, 2)}</pre>
            </div>
        `;
    },

    renderWeatherForecastResult(result) {
        const forecastData = result.result?.forecast;
        if (!forecastData || !forecastData.daily) {
            return `<div class="result-error">天气预报数据格式不正确</div>`;
        }

        const dailyForecasts = forecastData.daily.slice(0, 5); // 只显示前5天
        
        return `
            <div class="weather-forecast-result">
                <div class="forecast-summary">
                    <h4>${this.escapeHtml(result.summary)}</h4>
                    <p>数据来源: ${forecastData.refer?.sources?.join(', ') || '未知'}</p>
                </div>
                <div class="forecast-days">
                    ${dailyForecasts.map(day => `
                        <div class="forecast-day">
                            <div class="day-header">
                                <span class="date">${day.fxDate}</span>
                                <span class="temp-range">${day.tempMin}°C ~ ${day.tempMax}°C</span>
                            </div>
                            <div class="weather-info">
                                <div class="day-weather">
                                    <span class="weather-icon">☀️</span>
                                    <span class="weather-text">${this.escapeHtml(day.textDay)}</span>
                                </div>
                                <div class="night-weather">
                                    <span class="weather-icon">🌙</span>
                                    <span class="weather-text">${this.escapeHtml(day.textNight)}</span>
                                </div>
                            </div>
                            <div class="wind-info">
                                <span>风力: ${this.escapeHtml(day.windDirDay)} ${day.windScaleDay}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <details class="raw-data-details">
                    <summary>查看原始数据</summary>
                    <pre class="raw-json">${JSON.stringify(forecastData, null, 2)}</pre>
                </details>
            </div>
        `;
    },

    renderCurrentWeatherResult(result) {
        const weatherData = result.result?.current_weather;
        if (!weatherData) {
            return `<div class="result-error">实时天气数据格式不正确</div>`;
        }

        return `
            <div class="current-weather-result">
                <div class="weather-summary">
                    <h4>${this.escapeHtml(result.summary)}</h4>
                </div>
                <div class="weather-details">
                    <div class="weather-item">
                        <span class="label">温度:</span>
                        <span class="value">${weatherData.temp || '-'}°C</span>
                    </div>
                    <div class="weather-item">
                        <span class="label">天气:</span>
                        <span class="value">${this.escapeHtml(weatherData.text || '-')}</span>
                    </div>
                    <div class="weather-item">
                        <span class="label">湿度:</span>
                        <span class="value">${weatherData.humidity || '-'}%</span>
                    </div>
                    <div class="weather-item">
                        <span class="label">风向:</span>
                        <span class="value">${this.escapeHtml(weatherData.windDir || '-')}</span>
                    </div>
                    <div class="weather-item">
                        <span class="label">风力:</span>
                        <span class="value">${weatherData.windScale || '-'}</span>
                    </div>
                </div>
                <details class="raw-data-details">
                    <summary>查看原始数据</summary>
                    <pre class="raw-json">${JSON.stringify(weatherData, null, 2)}</pre>
                </details>
            </div>
        `;
    },

    renderGenericDataResult(result) {
        return `
            <div class="generic-result">
                <div class="result-summary">
                    <h4>${this.escapeHtml(result.summary)}</h4>
                </div>
                <div class="result-data">
                    <pre>${JSON.stringify(result.data, null, 2)}</pre>
                </div>
            </div>
        `;
    },

    async cleanupStaleTasks() {
        if (!confirm('确定要清理超时任务吗？')) return;

        try {
            const response = await fetch('/api/task-queue/cleanup?max_idle_minutes=30', { method: 'POST' });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const result = await response.json();
            if (result.success) {
                alert(`清理完成，共清理了 ${result.cleaned_count} 个超时任务`);
                this.loadTasks();
            } else {
                alert('清理失败: ' + (result.message || '未知错误'));
            }
        } catch (error) {
            console.error('清理超时任务失败:', error);
            alert('清理失败: ' + error.message);
        }
    },

    // 定时任务（占位实现，待后续完善）
    async loadScheduledTasks() {
        // 先更新视图为定时任务模式
        this.updateTaskView(true);
        
        const listEl = document.getElementById('taskListContainer');
        if (!listEl) return;

        listEl.innerHTML = '<div class="empty-state">加载中...</div>';

        try {
            const filter = document.getElementById('scheduledTaskFilter');
            const filterVal = filter ? filter.value : '';
            const activeOnly = filterVal === 'active';

            const url = `/api/task-queue/scheduled-tasks?active_only=${activeOnly}`;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

            const data = await response.json();
            let tasks = data.scheduled_tasks || data.tasks || [];
            if (filterVal === 'inactive') {
                tasks = tasks.filter(t => !t.is_active);
            }
            if (data.success) {
                this.updateScheduledTasksDisplay(tasks);
                this.updateScheduledTasksStats(tasks);
            } else {
                listEl.innerHTML = '<div class="empty-state">暂无定时任务</div>';
            }
        } catch (error) {
            console.error('加载定时任务失败:', error);
            listEl.innerHTML = `<div class="empty-state">加载失败: ${error.message}</div>`;
        }
    },

    updateScheduledTasksDisplay(tasks) {
        const listEl = document.getElementById('taskListContainer');
        if (!listEl) return;

        const searchInput = document.getElementById('scheduledTaskSearchInput');
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const nameOrId = t => (t.task_name || t.name || '') + (t.schedule_id || '');

        const filtered = searchTerm
            ? tasks.filter(t => nameOrId(t).toLowerCase().includes(searchTerm))
            : tasks;

        if (filtered.length === 0) {
            listEl.innerHTML = '<div class="empty-state">暂无定时任务</div>';
            return;
        }

        listEl.innerHTML = filtered.map(t => {
            let cfg = t.schedule_config || {};
            if (typeof cfg === 'string') { try { cfg = JSON.parse(cfg); } catch { cfg = {}; } }
            const cronOrInterval = t.schedule_type === 'cron'
                ? (cfg.cron_expression || JSON.stringify(cfg))
                : (cfg.interval_seconds ? `每 ${cfg.interval_seconds} 秒` : JSON.stringify(cfg));
            const statusClass = t.is_active ? 'status-completed' : 'status-cancelled';
            return `
            <div class="task-item" data-schedule-id="${t.schedule_id}">
                <div class="task-header">
                    <div class="task-title">
                        <span class="task-name">${this.escapeHtml(t.task_name || t.name || '未命名')}</span>
                        <span class="task-id">#${t.schedule_id}</span>
                    </div>
                    <div class="task-actions">
                        <span class="task-status-tag ${statusClass}">${t.is_active ? '激活' : '已禁用'}</span>
                    </div>
                </div>
                <div class="task-body">
                    <div class="task-info">
                        <div class="task-info-item">
                            <span class="info-label">类型</span>
                            <span class="info-value">${this.escapeHtml(t.task_type || '-')}</span>
                        </div>
                        <div class="task-info-item">
                            <span class="info-label">调度</span>
                            <span class="info-value">${this.escapeHtml(cronOrInterval)}</span>
                        </div>
                    </div>
                </div>
                <div class="task-footer">
                    <button class="btn-small" onclick="app.toggleScheduledTask('${t.schedule_id}', ${!t.is_active})">${t.is_active ? '禁用' : '启用'}</button>
                    <button class="btn-small btn-danger" onclick="app.deleteScheduledTask('${t.schedule_id}')">删除</button>
                </div>
            </div>
        `;
        }).join('');
    },

    updateScheduledTasksStats(tasks) {
        const total = tasks.length;
        const active = tasks.filter(t => t.is_active).length;

        const totalEl = document.getElementById('totalScheduledTasksCount');
        const activeEl = document.getElementById('activeScheduledTasksCount');
        const inactiveEl = document.getElementById('inactiveScheduledTasksCount');

        if (totalEl) totalEl.textContent = total;
        if (activeEl) activeEl.textContent = active;
        if (inactiveEl) inactiveEl.textContent = total - active;
    },

    filterScheduledTasks() {
        this.loadScheduledTasks();
    },

    async showCreateScheduledTaskModal() {
        alert('创建定时任务功能待实现');
    },

    async toggleScheduledTask(scheduleId, isActive) {
        try {
            const response = await fetch(`/api/task-queue/scheduled-tasks/${scheduleId}/toggle`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_active: isActive })
            });
            if (response.ok) this.loadScheduledTasks();
        } catch (e) {
            console.error('切换定时任务失败:', e);
        }
    },

    async deleteScheduledTask(scheduleId) {
        if (!confirm('确定删除此定时任务？')) return;
        try {
            const response = await fetch(`/api/task-queue/scheduled-tasks/${scheduleId}`, { method: 'DELETE' });
            if (response.ok) this.loadScheduledTasks();
        } catch (e) {
            console.error('删除定时任务失败:', e);
        }
    },

    // 辅助方法
    getTaskStatusClass(status) {
        const map = {
            'pending': 'status-pending', 'queued': 'status-queued', 'running': 'status-running',
            'completed': 'status-completed', 'failed': 'status-failed', 'cancelled': 'status-cancelled',
            'retrying': 'status-retrying'
        };
        return map[status] || 'status-unknown';
    },

    getTaskStatusText(status) {
        const map = {
            'pending': '待处理', 'queued': '已入队', 'running': '运行中',
            'completed': '已完成', 'failed': '失败', 'cancelled': '已取消', 'retrying': '重试中'
        };
        return map[status] || status;
    },

    getTaskPriorityClass(priority) {
        if (priority === 1) return 'priority-low';
        if (priority === 3) return 'priority-high';
        if (priority === 4) return 'priority-urgent';
        return 'priority-normal';
    },

    getTaskPriorityText(priority) {
        const map = { 1: '低', 2: '普通', 3: '高', 4: '紧急' };
        return map[priority] || '普通';
    },
    
    // 配置数据
    normalStatsConfig: [
        { id: 'totalTasksCount', label: '总任务', class: '' },
        { id: 'pendingTasksCount', label: '待处理', class: 'stat-wait' },
        { id: 'runningTasksCount', label: '运行中', class: 'stat-run' },
        { id: 'completedTasksCount', label: '已完成', class: 'stat-done' },
        { id: 'failedTasksCount', label: '失败', class: 'stat-fail' }
    ],

    scheduledStatsConfig: [
        { id: 'totalScheduledTasksCount', label: '总定时任务', class: '' },
        { id: 'activeScheduledTasksCount', label: '激活中', class: 'stat-done' },
        { id: 'inactiveScheduledTasksCount', label: '已禁用', class: 'stat-wait' }
    ],

    normalFilterOptions: [
        { value: '', label: '全部状态' },
        { value: 'pending', label: '待处理' },
        { value: 'queued', label: '已入队' },
        { value: 'running', label: '运行中' },
        { value: 'completed', label: '已完成' },
        { value: 'failed', label: '失败' },
        { value: 'cancelled', label: '已取消' }
    ],

    scheduledFilterOptions: [
        { value: '', label: '全部' },
        { value: 'active', label: '激活中' },
        { value: 'inactive', label: '已禁用' }
    ]
};
