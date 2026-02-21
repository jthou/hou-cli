// 后端连接状态
export const backendStatusModule = {
    async checkBackendConnection() {
        const statusEl = document.getElementById('backendConnectionStatus');
        if (statusEl) {
            statusEl.textContent = '检查中...';
            statusEl.className = 'status-indicator-text checking';
        }
        try {
            const response = await fetch('/api/backend-url');
            const data = await response.json();
            this.backendUrl = data.backend_url;
            const backendUrlElements = document.querySelectorAll('#backendUrl, #aboutBackendUrl, #footerBackendUrl');
            backendUrlElements.forEach(el => {
                if (el) el.textContent = data.backend_url;
            });
            const healthResponse = await fetch('/health');
            if (healthResponse.ok) {
                this.updateStatus('已连接', 'connected');
                if (statusEl) {
                    statusEl.textContent = '已连接';
                    statusEl.className = 'status-indicator-text connected';
                }
            } else {
                this.updateStatus('不可用', 'disconnected');
                if (statusEl) {
                    statusEl.textContent = '不可用';
                    statusEl.className = 'status-indicator-text disconnected';
                }
            }
        } catch (error) {
            console.error('检查后端连接失败:', error);
            this.updateStatus('连接失败', 'disconnected');
            if (statusEl) {
                statusEl.textContent = '连接失败';
                statusEl.className = 'status-indicator-text disconnected';
            }
        }
    },

    updateStatus(text, status) {
        const statusText = document.getElementById('statusText');
        const statusIndicator = document.getElementById('statusIndicator');
        if (statusText) statusText.textContent = text;
        if (statusIndicator) statusIndicator.className = 'status-indicator ' + (status || '');
    }
};
