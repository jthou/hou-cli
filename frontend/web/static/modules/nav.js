// 导航、侧边栏、页面切换
export const navModule = {
    initNavigation() {
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
    },

    initSidebarToggle() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');

        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });
        }
    },

    navigateToPage(page) {
        const navItems = document.querySelectorAll('.nav-item');
        navItems.forEach(item => {
            if (item.getAttribute('data-page') === page) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        const pages = document.querySelectorAll('.page');
        pages.forEach(p => p.style.display = 'none');

        const targetPage = document.getElementById(`page-${page}`);
        if (targetPage) {
            targetPage.style.display = 'flex';
        }

        const pageTitles = {
            'tasks': '任务管理',
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

        this.currentPage = page;

        if (page === 'settings-general') {
            // 常规设置页面 - 无需加载数据
        } else if (page === 'settings-storage') {
            this.loadStorageConfig();
        } else if (page === 'settings-tests') {
            this.loadTestStatus();
            this.loadTestHistory();
        } else if (page === 'settings-backend') {
            this.checkBackendConnection();
        } else if (page === 'tasks') {
            this.loadTasks();
        }

        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
    }
};
