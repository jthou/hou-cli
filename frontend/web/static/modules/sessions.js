// 会话管理
export const sessionsModule = {
    initSessions() {
        const newSessionBtn = document.getElementById('newSessionBtn');
        if (newSessionBtn) {
            newSessionBtn.addEventListener('click', () => this.createNewSession());
        }

        this.loadSessions();
    },

    createNewSession() {
        this.sessionId = this.generateSessionId();
        const sessionIdElements = document.querySelectorAll('#sessionId');
        sessionIdElements.forEach(el => el.textContent = this.sessionId);

        const messages = document.getElementById('messages');
        if (messages) messages.innerHTML = '';

        this.navigateToPage('chat');

        if (this.ws) this.ws.close();
        this.connectWebSocket();
    },

    async loadSessions() {
        const sessionsList = document.getElementById('sessionsList');
        if (sessionsList) {
            sessionsList.innerHTML = `
                <div class="empty-state">
                    <p>暂无会话记录</p>
                </div>
            `;
        }
    }
};
