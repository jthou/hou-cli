// Web 前端应用 - 入口，组合各功能模块
import { utilsModule } from './modules/utils.js';
import { navModule } from './modules/nav.js';
import { storageModule } from './modules/storage.js';
import { settingsModule } from './modules/settings.js';
import { testAuditModule } from './modules/test-audit.js';
import { taskModule } from './modules/task.js';
import { backendStatusModule } from './modules/backend-status.js';

class ChatApp {
    constructor() {
        this.currentPage = 'tasks';
        this.backendUrl = null;

        this.init();
    }

    init() {
        this.initNavigation();
        this.initSidebarToggle();
        this.checkBackendConnection();
        this.initTestAudit();
        this.initSettingsPages();
        this.initTaskManagement();
        // 初始化普通任务的统计卡片
        this.initTaskStats();
        this.loadTasks();
    }
}

// 合并所有模块方法到 ChatApp 原型
Object.assign(ChatApp.prototype, utilsModule, navModule, storageModule, settingsModule, testAuditModule, taskModule, backendStatusModule);

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ChatApp();
});
