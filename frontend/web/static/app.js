// Web 前端应用
class ChatApp {
    constructor() {
        this.ws = null;
        this.sessionId = this.generateSessionId();
        this.isConnected = false;
        this.isStreaming = false;
        this.currentPage = 'chat';
        this.backendUrl = null;  // 缓存后端 URL
        
        this.init();
    }
    
    generateSessionId() {
        return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    }
    
    init() {
        // 更新会话 ID 显示
        const sessionIdElements = document.querySelectorAll('#sessionId');
        sessionIdElements.forEach(el => el.textContent = this.sessionId);
        
        // 初始化导航
        this.initNavigation();
        
        // 初始化侧边栏切换（移动端）
        this.initSidebarToggle();
        
        // 绑定事件
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        
        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // 连接 WebSocket（仅在聊天页面）
        if (this.currentPage === 'chat') {
            this.connectWebSocket();
            this.checkBackendConnection();
        }
        
        // 初始化会话管理
        this.initSessions();
        
        // 初始化测试审计
        this.initTestAudit();
        // 初始化设置页面
        this.initSettingsPages();
    }
    
    initNavigation() {
        // 处理普通导航项
        const navItems = document.querySelectorAll('.nav-item[data-page]');
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const page = item.getAttribute('data-page');
                if (page) {
                    this.navigateToPage(page);
                }
            });
        });
        
        // 处理可展开的导航组
        const navGroupToggles = document.querySelectorAll('.nav-group-toggle');
        navGroupToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const group = toggle.getAttribute('data-group');
                const submenu = document.getElementById(`${group}-submenu`);
                if (submenu) {
                    submenu.classList.toggle('open');
                    const arrow = toggle.querySelector('.nav-arrow');
                    if (arrow) {
                        arrow.textContent = submenu.classList.contains('open') ? '▲' : '▼';
                    }
                }
            });
        });
    }
    
    initSidebarToggle() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });
        }
    }
    
    navigateToPage(page) {
        // 更新导航状态
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            if (item.getAttribute('data-page') === page) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        
        // 隐藏所有页面
        const pages = document.querySelectorAll('.page');
        pages.forEach(p => p.style.display = 'none');
        
        // 显示目标页面
        const targetPage = document.getElementById(`page-${page}`);
        if (targetPage) {
            targetPage.style.display = 'flex';
        }
        
        // 更新页面标题
        const pageTitles = {
            'chat': '聊天',
            'sessions': '会话管理',
            'settings-general': '常规设置',
            'settings-storage': '存储配置',
            'settings-tests': '测试审计',
            'settings-backend': '后端服务',
            'about': '关于'
        };
        const pageTitle = document.getElementById('pageTitle');
        if (pageTitle) {
            pageTitle.textContent = pageTitles[page] || '页面';
        }
        
        // 更新当前页面
        this.currentPage = page;
        
        // 如果是聊天页面，确保 WebSocket 连接
        if (page === 'chat' && !this.isConnected) {
            this.connectWebSocket();
            this.checkBackendConnection();
        }
        
        // 根据不同的设置页面加载相应数据（完全独立，互不影响）
        if (page === 'settings-general') {
            // 常规设置页面 - 无需加载数据
        } else if (page === 'settings-storage') {
            // 存储配置页面 - 仅加载存储配置
            this.loadStorageConfig();
        } else if (page === 'settings-tests') {
            // 测试审计页面 - 加载测试状态和历史
            this.loadTestStatus();
            this.loadTestHistory();
        } else if (page === 'settings-backend') {
            // 后端服务页面 - 仅检查后端连接
            this.checkBackendConnection();
        }
        
        // 关闭移动端侧边栏
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
    }
    
    async loadStorageConfig() {
        // 显示加载状态
        const loadingElements = [
            'storageDataDir', 'sqliteStatus', 'sqliteDbDir', 'sqliteDefaultDb', 
            'sqliteSize', 'sqliteDatabases', 'chromadbStatus', 'chromadbDataDir',
            'chromadbSize', 'chromadbCollectionCount', 'chromadbCollections'
        ];
        loadingElements.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '加载中...';
        });
        
        try {
            // 通过 Web 前端代理访问后端 API（避免 CORS 问题）
            const response = await fetch('/api/storage/config', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('存储配置数据:', data);
            
            if (data.success) {
                this.updateStorageDisplay(data);
            } else {
                this.showStorageError(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载存储配置失败:', error);
            const errorMsg = error.message || '无法连接到后端服务';
            this.showStorageError(errorMsg);
        }
    }
    
    async getBackendUrl() {
        // 优先使用已保存的后端 URL
        if (this.backendUrl) {
            return this.backendUrl;
        }
        
        try {
            const response = await fetch('/api/backend-url');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (data.backend_url) {
                this.backendUrl = data.backend_url;
                return data.backend_url;
            }
            throw new Error('No backend_url in response');
        } catch (error) {
            console.error('获取后端 URL 失败:', error);
            // 尝试从页面中获取后端 URL（如果已经加载过）
            const backendUrlEl = document.getElementById('backendUrl');
            if (backendUrlEl && backendUrlEl.textContent) {
                const url = backendUrlEl.textContent.trim();
                this.backendUrl = url;
                return url;
            }
            // 最后尝试默认端口
            return 'http://127.0.0.1:8000';
        }
    }
    
    updateStorageDisplay(config) {
        // 更新数据目录
        const dataDirEl = document.getElementById('storageDataDir');
        if (dataDirEl) dataDirEl.textContent = config.data_dir;
        
        // 更新 SQLite 信息
        const sqlite = config.sqlite;
        const sqliteStatusEl = document.getElementById('sqliteStatus');
        if (sqliteStatusEl) {
            sqliteStatusEl.textContent = sqlite.enabled ? '已启用' : '未启用';
            sqliteStatusEl.className = sqlite.enabled ? 'status-enabled' : 'status-disabled';
        }
        
        const sqliteDbDirEl = document.getElementById('sqliteDbDir');
        if (sqliteDbDirEl) sqliteDbDirEl.textContent = sqlite.db_dir;
        
        const sqliteDefaultDbEl = document.getElementById('sqliteDefaultDb');
        if (sqliteDefaultDbEl) {
            sqliteDefaultDbEl.textContent = sqlite.default_db_path;
        }
        
        const sqliteSizeEl = document.getElementById('sqliteSize');
        if (sqliteSizeEl) {
            sqliteSizeEl.textContent = sqlite.default_db_exists 
                ? `${sqlite.default_db_size_mb} MB` 
                : '数据库文件不存在';
        }
        
        // 更新数据库文件列表
        const sqliteDatabasesEl = document.getElementById('sqliteDatabases');
        if (sqliteDatabasesEl) {
            if (sqlite.databases && sqlite.databases.length > 0) {
                sqliteDatabasesEl.innerHTML = sqlite.databases.map(db => `
                    <div class="database-item">
                        <span class="db-name">${db.name}</span>
                        <span class="db-size">${db.size_mb} MB</span>
                    </div>
                `).join('');
            } else {
                sqliteDatabasesEl.innerHTML = '<div class="empty-state"><p>暂无数据库文件</p></div>';
            }
        }
        
        // 更新 ChromaDB 信息
        const chromadb = config.chromadb;
        const chromadbStatusEl = document.getElementById('chromadbStatus');
        if (chromadbStatusEl) {
            chromadbStatusEl.textContent = chromadb.enabled ? '已启用' : '未启用';
            chromadbStatusEl.className = chromadb.enabled ? 'status-enabled' : 'status-disabled';
        }
        
        const chromadbDataDirEl = document.getElementById('chromadbDataDir');
        if (chromadbDataDirEl) chromadbDataDirEl.textContent = chromadb.data_dir;
        
        const chromadbSizeEl = document.getElementById('chromadbSize');
        if (chromadbSizeEl) {
            chromadbSizeEl.textContent = chromadb.exists 
                ? `${chromadb.size_mb} MB` 
                : '数据目录不存在';
        }
        
        const chromadbCollectionCountEl = document.getElementById('chromadbCollectionCount');
        if (chromadbCollectionCountEl) {
            chromadbCollectionCountEl.textContent = `${chromadb.collection_count} 个集合`;
        }
        
        // 更新集合列表
        const chromadbCollectionsEl = document.getElementById('chromadbCollections');
        if (chromadbCollectionsEl) {
            if (chromadb.collections && chromadb.collections.length > 0) {
                chromadbCollectionsEl.innerHTML = chromadb.collections.map(col => `
                    <div class="collection-item">
                        <span class="collection-name">${col.name}</span>
                        <span class="collection-count">${col.count} 条记录</span>
                    </div>
                `).join('');
            } else {
                chromadbCollectionsEl.innerHTML = '<div class="empty-state"><p>暂无集合</p></div>';
            }
        }
    }
    
    showStorageError(error) {
        const elements = [
            'storageDataDir', 'sqliteStatus', 'sqliteDbDir', 'sqliteDefaultDb', 
            'sqliteSize', 'sqliteDatabases', 'chromadbStatus', 'chromadbDataDir',
            'chromadbSize', 'chromadbCollectionCount', 'chromadbCollections'
        ];
        elements.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = `错误: ${error}`;
        });
    }
    
    initSettingsPages() {
        // 绑定后端连接检查按钮（仅在后端服务页面）
        const checkBackendBtn = document.getElementById('checkBackendBtn');
        if (checkBackendBtn) {
            checkBackendBtn.addEventListener('click', () => {
                this.checkBackendConnection();
            });
        }
        
        // 绑定刷新存储信息按钮（仅在存储配置页面）
        const refreshStorageBtn = document.getElementById('refreshStorageBtn');
        if (refreshStorageBtn) {
            refreshStorageBtn.addEventListener('click', () => {
                this.loadStorageConfig();
            });
        }
    }
    
    initTestAudit() {
        // 绑定测试相关按钮（只读模式，不运行测试）
        const refreshTestStatusBtn = document.getElementById('refreshTestStatusBtn');
        const refreshTestHistoryBtn = document.getElementById('refreshTestHistoryBtn');
        
        if (refreshTestStatusBtn) {
            refreshTestStatusBtn.addEventListener('click', () => {
                this.loadTestStatus();
            });
        }
        
        if (refreshTestHistoryBtn) {
            refreshTestHistoryBtn.addEventListener('click', () => {
                this.loadTestHistory();
            });
        }
    }
    
    async loadTestHistory() {
        const historyListEl = document.getElementById('testHistoryList');
        const historyCountEl = document.getElementById('testHistoryCount');
        
        if (historyListEl) {
            historyListEl.innerHTML = '<div class="empty-state">加载中...</div>';
        }
        
        try {
            const response = await fetch('/api/tests/history?limit=20');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success && data.runs) {
                this.updateTestHistoryDisplay(data.runs);
                if (historyCountEl) {
                    historyCountEl.textContent = data.runs.length;
                }
            } else if (data.success === false) {
                // 如果后端返回错误，显示错误信息
                console.error('测试历史API返回错误:', data.error || '未知错误');
                if (historyListEl) {
                    historyListEl.innerHTML = `<div class="empty-state">加载失败: ${data.error || '未知错误'}</div>`;
                }
                if (historyCountEl) {
                    historyCountEl.textContent = '0';
                }
            } else {
                if (historyListEl) {
                    historyListEl.innerHTML = '<div class="empty-state">暂无测试历史记录</div>';
                }
                if (historyCountEl) {
                    historyCountEl.textContent = '0';
                }
            }
        } catch (error) {
            console.error('加载测试历史失败:', error);
            if (historyListEl) {
                historyListEl.innerHTML = `<div class="empty-state">加载失败: ${error.message}</div>`;
            }
        }
    }
    
    updateTestHistoryDisplay(runs) {
        const historyListEl = document.getElementById('testHistoryList');
        if (!historyListEl) return;
        
        if (runs.length === 0) {
            historyListEl.innerHTML = '<div class="empty-state">暂无测试历史记录</div>';
            return;
        }
        
        historyListEl.innerHTML = runs.map(run => {
            const startTime = new Date(run.started_at);
            const timeStr = startTime.toLocaleString('zh-CN');
            const successClass = run.success ? 'test-passed' : 'test-failed';
            const durationStr = run.duration ? `${run.duration.toFixed(2)}s` : '-';
            
            return `
                <div class="test-history-item" data-run-id="${run.run_id}">
                    <div class="test-history-header">
                        <span class="test-history-time">${timeStr}</span>
                        <span class="test-history-status ${successClass}">${run.success ? '成功' : '失败'}</span>
                    </div>
                    <div class="test-history-stats">
                        <span>总计: ${run.total_tests}</span>
                        <span class="test-passed">通过: ${run.passed}</span>
                        <span class="test-failed">失败: ${run.failed}</span>
                        <span class="test-skipped">跳过: ${run.skipped}</span>
                        <span>成功率: ${run.success_rate.toFixed(1)}%</span>
                        <span>耗时: ${durationStr}</span>
                    </div>
                    ${run.test_path ? `<div class="test-history-path">路径: ${run.test_path}</div>` : ''}
                </div>
            `;
        }).join('');
        
        // 绑定点击事件查看详情
        historyListEl.querySelectorAll('.test-history-item').forEach(item => {
            item.addEventListener('click', () => {
                const runId = item.getAttribute('data-run-id');
                this.loadTestRunDetail(runId);
            });
        });
    }
    
    async loadTestRunDetail(runId) {
        try {
            const response = await fetch(`/api/tests/history/${runId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success && data.run) {
                this.displayTestRunDetail(data.run);
            }
        } catch (error) {
            console.error('加载测试运行详情失败:', error);
            alert(`加载测试详情失败: ${error.message}`);
        }
    }
    
    displayTestRunDetail(run) {
        // 显示当前测试结果区域
        const currentTestSection = document.getElementById('currentTestSection');
        if (currentTestSection) {
            currentTestSection.style.display = 'block';
        }
        
        // 更新运行信息
        const runIdEl = document.getElementById('currentTestRunId');
        const runTimeEl = document.getElementById('currentTestRunTime');
        if (runIdEl) runIdEl.textContent = `运行 ID: ${run.run_id}`;
        if (runTimeEl) {
            const startTime = new Date(run.started_at);
            runTimeEl.textContent = `运行时间: ${startTime.toLocaleString('zh-CN')}`;
        }
        
        // 更新测试结果列表
        const resultsListEl = document.getElementById('testResultsList');
        if (resultsListEl && run.test_results) {
            if (run.test_results.length > 0) {
                resultsListEl.innerHTML = run.test_results.map(test => {
                    let statusClass = '';
                    if (test.status === 'passed') statusClass = 'status-passed';
                    else if (test.status === 'failed') statusClass = 'status-failed';
                    else if (test.status === 'skipped') statusClass = 'status-skipped';
                    else if (test.status === 'error') statusClass = 'status-error';
                    
                    return `
                        <div class="test-result-item">
                            <span class="test-name">${test.name}</span>
                            <span class="test-file">${test.file}</span>
                            <span class="test-status ${statusClass}">${test.status.toUpperCase()}</span>
                        </div>
                    `;
                }).join('');
            } else {
                resultsListEl.innerHTML = '<div class="empty-state">暂无测试结果</div>';
            }
        }
        
        // 更新测试输出
        const outputContainer = document.getElementById('testOutputContainer');
        const testOutput = document.getElementById('testOutput');
        if (testOutput && run.output) {
            testOutput.textContent = run.output;
            if (outputContainer) {
                outputContainer.style.display = 'block';
            }
        }
        
        // 更新测试状态显示
        this.updateTestStatusDisplay({
            total_tests: run.total_tests,
            passed: run.passed,
            failed: run.failed,
            skipped: run.skipped,
            errors: run.errors,
            success_rate: run.success_rate,
            last_run_time: run.started_at
        });
    }
    
    async loadTestStatus() {
        try {
            const response = await fetch('/api/tests/status');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success && data.status) {
                this.updateTestStatusDisplay(data.status);
            }
        } catch (error) {
            console.error('加载测试状态失败:', error);
            this.updateTestStatusDisplay({
                total_tests: 0,
                passed: 0,
                failed: 0,
                skipped: 0,
                errors: 0,
                success_rate: 0
            });
        }
    }
    
    updateTestStatusDisplay(status) {
        const totalEl = document.getElementById('testTotal');
        const passedEl = document.getElementById('testPassed');
        const failedEl = document.getElementById('testFailed');
        const skippedEl = document.getElementById('testSkipped');
        const successRateEl = document.getElementById('testSuccessRate');
        const lastRunTimeEl = document.getElementById('testLastRunTime');
        
        if (totalEl) totalEl.textContent = status.total_tests || 0;
        if (passedEl) passedEl.textContent = status.passed || 0;
        if (failedEl) failedEl.textContent = status.failed || 0;
        if (skippedEl) skippedEl.textContent = status.skipped || 0;
        if (successRateEl) {
            const rate = status.success_rate || 0;
            successRateEl.textContent = `${rate.toFixed(1)}%`;
            successRateEl.className = `test-value ${rate === 100 ? 'test-passed' : rate >= 80 ? 'test-warning' : 'test-failed'}`;
        }
        if (lastRunTimeEl) {
            if (status.last_run_time) {
                try {
                    const startTime = new Date(status.last_run_time);
                    lastRunTimeEl.textContent = startTime.toLocaleString('zh-CN');
                } catch (e) {
                    lastRunTimeEl.textContent = status.last_run_time || '-';
                }
            } else {
                lastRunTimeEl.textContent = '-';
            }
        }
    }
    
    updateTestStatus(status) {
        // 兼容旧方法名
        this.updateTestStatusDisplay(status);
    }
    
    async runAllTests() {
        const runBtn = document.getElementById('runAllTestsBtn');
        const resultsList = document.getElementById('testResultsList');
        const outputContainer = document.getElementById('testOutputContainer');
        const testOutput = document.getElementById('testOutput');
        const verboseCheckbox = document.getElementById('testVerboseCheckbox');
        const coverageCheckbox = document.getElementById('testCoverageCheckbox');
        
        // 禁用按钮
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.textContent = '运行中...';
        }
        
        // 清空结果
        if (resultsList) {
            resultsList.innerHTML = '<div class="test-loading">正在运行测试...</div>';
        }
        
        if (outputContainer) {
            outputContainer.style.display = 'none';
        }
        
        try {
            const response = await fetch('/api/tests/run', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    test_path: null,  // 运行所有测试
                    verbose: verboseCheckbox ? verboseCheckbox.checked : false,
                    coverage: coverageCheckbox ? coverageCheckbox.checked : false
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // 保存运行 ID（如果有）
            if (result.run_id) {
                console.log('测试运行 ID:', result.run_id);
            }
            
            // 更新状态
            this.updateTestStatusDisplay({
                total_tests: result.total_tests || 0,
                passed: result.passed || 0,
                failed: result.failed || 0,
                skipped: result.skipped || 0,
                errors: result.errors || 0,
                success_rate: result.total_tests > 0 
                    ? ((result.passed || 0) / result.total_tests * 100) 
                    : 0,
                last_run_time: new Date().toISOString()
            });
            
            // 刷新测试历史
            if (typeof this.loadTestHistory === 'function') {
                this.loadTestHistory();
            }
            
            // 如果有 run_id，显示当前测试结果
            if (result.run_id && typeof this.loadTestRunDetail === 'function') {
                this.loadTestRunDetail(result.run_id);
            } else {
                // 显示测试结果列表
                if (resultsList) {
                    if (result.test_results && result.test_results.length > 0) {
                        resultsList.innerHTML = result.test_results.map(test => {
                            let statusClass = '';
                            if (test.status === 'passed') statusClass = 'status-passed';
                            else if (test.status === 'failed') statusClass = 'status-failed';
                            else if (test.status === 'skipped') statusClass = 'status-skipped';
                            else if (test.status === 'error') statusClass = 'status-error';
                            
                            return `
                                <div class="test-result-item">
                                    <span class="test-name">${test.name}</span>
                                    <span class="test-file">${test.file}</span>
                                    <span class="test-status ${statusClass}">${test.status.toUpperCase()}</span>
                                </div>
                            `;
                        }).join('');
                    } else {
                        resultsList.innerHTML = '<div class="empty-state">暂无测试结果</div>';
                    }
                }
                
                // 显示输出
                if (testOutput && (result.output || result.error)) {
                    testOutput.textContent = result.output || result.error || '';
                    if (outputContainer) {
                        outputContainer.style.display = 'block';
                    }
                }
            }
            
        } catch (error) {
            console.error('运行测试失败:', error);
            if (resultsList) {
                resultsList.innerHTML = `<div class="test-error">运行测试失败: ${error.message}</div>`;
            }
        } finally {
            // 恢复按钮
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.textContent = '运行所有测试';
            }
        }
    }
    
    initSessions() {
        const newSessionBtn = document.getElementById('newSessionBtn');
        if (newSessionBtn) {
            newSessionBtn.addEventListener('click', () => {
                this.createNewSession();
            });
        }
        
        // 加载会话列表
        this.loadSessions();
    }
    
    createNewSession() {
        this.sessionId = this.generateSessionId();
        const sessionIdElements = document.querySelectorAll('#sessionId');
        sessionIdElements.forEach(el => el.textContent = this.sessionId);
        
        // 清空消息
        const messages = document.getElementById('messages');
        if (messages) {
            messages.innerHTML = '';
        }
        
        // 切换到聊天页面
        this.navigateToPage('chat');
        
        // 重新连接 WebSocket
        if (this.ws) {
            this.ws.close();
        }
        this.connectWebSocket();
    }
    
    async loadSessions() {
        // TODO: 从后端加载会话列表
        const sessionsList = document.getElementById('sessionsList');
        if (sessionsList) {
            // 暂时显示空状态
            sessionsList.innerHTML = `
                <div class="empty-state">
                    <p>暂无会话记录</p>
                </div>
            `;
        }
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket 连接已建立');
            this.isConnected = true;
            this.updateStatus('已连接', 'connected');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket 错误:', error);
            this.updateStatus('连接错误', 'disconnected');
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket 连接已关闭');
            this.isConnected = false;
            this.updateStatus('已断开', 'disconnected');
            
            // 尝试重连
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    async checkBackendConnection() {
        // 更新后端连接状态显示
        const statusEl = document.getElementById('backendConnectionStatus');
        if (statusEl) {
            statusEl.textContent = '检查中...';
            statusEl.className = 'status-indicator-text checking';
        }
        
        try {
            const response = await fetch('/api/backend-url');
            const data = await response.json();
            
            // 保存后端 URL 到实例变量，供其他方法使用
            this.backendUrl = data.backend_url;
            
            // 更新所有后端 URL 显示
            const backendUrlElements = document.querySelectorAll('#backendUrl, #aboutBackendUrl, #footerBackendUrl');
            backendUrlElements.forEach(el => {
                if (el) el.textContent = data.backend_url;
            });
            
            // 检查后端健康状态
            const healthResponse = await fetch(`${data.backend_url}/health`);
            if (healthResponse.ok) {
                this.updateStatus('后端已连接', 'connected');
                // 更新后端服务页面的状态显示
                if (statusEl) {
                    statusEl.textContent = '已连接';
                    statusEl.className = 'status-indicator-text connected';
                }
            } else {
                this.updateStatus('后端不可用', 'disconnected');
                if (statusEl) {
                    statusEl.textContent = '不可用';
                    statusEl.className = 'status-indicator-text disconnected';
                }
            }
        } catch (error) {
            console.error('检查后端连接失败:', error);
            this.updateStatus('后端连接失败', 'disconnected');
            // 更新后端服务页面的状态显示
            if (statusEl) {
                statusEl.textContent = '连接失败';
                statusEl.className = 'status-indicator-text disconnected';
            }
        }
    }
    
    updateStatus(text, status) {
        const statusText = document.getElementById('statusText');
        const statusIndicator = document.getElementById('statusIndicator');
        
        statusText.textContent = text;
        statusIndicator.className = 'status-indicator ' + (status || '');
    }
    
    sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) {
            return;
        }
        
        if (!this.isConnected) {
            this.addMessage('系统', 'WebSocket 未连接，请稍候...', 'error');
            return;
        }
        
        if (this.isStreaming) {
            this.addMessage('系统', '正在处理上一个消息，请稍候...', 'error');
            return;
        }
        
        // 添加用户消息
        this.addMessage('你', message, 'user');
        
        // 清空输入框
        messageInput.value = '';
        
        // 发送消息
        this.isStreaming = true;
        this.disableInput(true);
        
        // 创建助手消息容器
        const assistantMsgId = this.addMessage('助手', '', 'assistant', true);
        
        // 通过 WebSocket 发送
        this.ws.send(JSON.stringify({
            message: message,
            session_id: this.sessionId
        }));
    }
    
    handleMessage(data) {
        if (data.type === 'chunk') {
            // 追加内容到助手消息
            this.appendToLastAssistantMessage(data.content);
        } else if (data.type === 'done') {
            // 流式响应完成
            this.isStreaming = false;
            this.disableInput(false);
            this.removeStreamingIndicator();
        } else if (data.type === 'error') {
            // 错误消息
            this.addMessage('系统', data.content, 'error');
            this.isStreaming = false;
            this.disableInput(false);
        }
    }
    
    addMessage(role, content, type = 'assistant', isStreaming = false) {
        const messagesContainer = document.getElementById('messages');
        const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        
        const messageDiv = document.createElement('div');
        messageDiv.id = messageId;
        messageDiv.className = `message ${type} ${isStreaming ? 'streaming' : ''}`;
        
        const header = document.createElement('div');
        header.className = 'message-header';
        header.innerHTML = `
            <span><strong>${role}</strong></span>
            <span>${new Date().toLocaleTimeString()}</span>
        `;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;
        
        messageDiv.appendChild(header);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        
        // 滚动到底部
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageId;
    }
    
    appendToLastAssistantMessage(content) {
        const messages = document.querySelectorAll('.message.assistant');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            const contentDiv = lastMessage.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.textContent += content;
                
                // 滚动到底部
                const messagesContainer = document.getElementById('messages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    }
    
    removeStreamingIndicator() {
        const streamingMessages = document.querySelectorAll('.message.streaming');
        streamingMessages.forEach(msg => {
            msg.classList.remove('streaming');
        });
    }
    
    disableInput(disabled) {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        
        messageInput.disabled = disabled;
        sendButton.disabled = disabled;
        
        if (disabled) {
            sendButton.textContent = '发送中...';
        } else {
            sendButton.textContent = '发送';
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatApp();
    
    // 绑定刷新存储信息按钮
    const refreshStorageBtn = document.getElementById('refreshStorageBtn');
    if (refreshStorageBtn) {
        refreshStorageBtn.addEventListener('click', () => {
            app.loadStorageConfig();
        });
    }
});

