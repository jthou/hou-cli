// 存储配置
export const storageModule = {
    async loadStorageConfig() {
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
            const response = await fetch('/api/storage/config', {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.success) {
                this.updateStorageDisplay(data);
            } else {
                this.showStorageError(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载存储配置失败:', error);
            this.showStorageError(error.message || '无法连接到后端服务');
        }
    },

    async getBackendUrl() {
        if (this.backendUrl) return this.backendUrl;

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
            const backendUrlEl = document.getElementById('backendUrl');
            if (backendUrlEl && backendUrlEl.textContent) {
                const url = backendUrlEl.textContent.trim();
                this.backendUrl = url;
                return url;
            }
            return 'http://127.0.0.1:8000';
        }
    },

    updateStorageDisplay(config) {
        const dataDirEl = document.getElementById('storageDataDir');
        if (dataDirEl) dataDirEl.textContent = config.data_dir;

        const sqlite = config.sqlite;
        const sqliteStatusEl = document.getElementById('sqliteStatus');
        if (sqliteStatusEl) {
            sqliteStatusEl.textContent = sqlite.enabled ? '已启用' : '未启用';
            sqliteStatusEl.className = sqlite.enabled ? 'status-enabled' : 'status-disabled';
        }

        const sqliteDbDirEl = document.getElementById('sqliteDbDir');
        if (sqliteDbDirEl) sqliteDbDirEl.textContent = sqlite.db_dir;

        const sqliteDefaultDbEl = document.getElementById('sqliteDefaultDb');
        if (sqliteDefaultDbEl) sqliteDefaultDbEl.textContent = sqlite.default_db_path;

        const sqliteSizeEl = document.getElementById('sqliteSize');
        if (sqliteSizeEl) {
            sqliteSizeEl.textContent = sqlite.default_db_exists
                ? `${sqlite.default_db_size_mb} MB`
                : '数据库文件不存在';
        }

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
    },

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
};
