// 设置页面初始化
export const settingsModule = {
    initSettingsPages() {
        const checkBackendBtn = document.getElementById('checkBackendBtn');
        if (checkBackendBtn) {
            checkBackendBtn.addEventListener('click', () => {
                this.checkBackendConnection();
            });
        }

        const refreshStorageBtn = document.getElementById('refreshStorageBtn');
        if (refreshStorageBtn) {
            refreshStorageBtn.addEventListener('click', () => {
                this.loadStorageConfig();
            });
        }
    }
};
