// WebSocket 聊天、消息、后端连接
export const chatModule = {
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
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    },

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
                this.updateStatus('后端已连接', 'connected');
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
            if (statusEl) {
                statusEl.textContent = '连接失败';
                statusEl.className = 'status-indicator-text disconnected';
            }
        }
    },

    updateStatus(text, status) {
        const statusText = document.getElementById('statusText');
        const statusIndicator = document.getElementById('statusIndicator');

        statusText.textContent = text;
        statusIndicator.className = 'status-indicator ' + (status || '');
    },

    sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();

        if (!message) return;

        if (!this.isConnected) {
            this.addMessage('系统', 'WebSocket 未连接，请稍候...', 'error');
            return;
        }

        if (this.isStreaming) {
            this.addMessage('系统', '正在处理上一个消息，请稍候...', 'error');
            return;
        }

        this.addMessage('你', message, 'user');
        messageInput.value = '';

        this.isStreaming = true;
        this.disableInput(true);

        const assistantMsgId = this.addMessage('助手', '', 'assistant', true);

        this.ws.send(JSON.stringify({
            message: message,
            session_id: this.sessionId
        }));
    },

    handleMessage(data) {
        if (data.type === 'chunk') {
            this.appendToLastAssistantMessage(data.content);
        } else if (data.type === 'done') {
            this.isStreaming = false;
            this.disableInput(false);
            this.removeStreamingIndicator();
        } else if (data.type === 'error') {
            this.addMessage('系统', data.content, 'error');
            this.isStreaming = false;
            this.disableInput(false);
        }
    },

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

        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        return messageId;
    },

    appendToLastAssistantMessage(content) {
        const messages = document.querySelectorAll('.message.assistant');
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            const contentDiv = lastMessage.querySelector('.message-content');
            if (contentDiv) {
                contentDiv.textContent += content;
                const messagesContainer = document.getElementById('messages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    },

    removeStreamingIndicator() {
        document.querySelectorAll('.message.streaming').forEach(msg => {
            msg.classList.remove('streaming');
        });
    },

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
};
