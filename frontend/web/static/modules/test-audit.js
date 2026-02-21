// 测试审计 - 历史、状态、运行
export const testAuditModule = {
    initTestAudit() {
        const refreshTestStatusBtn = document.getElementById('refreshTestStatusBtn');
        const refreshTestHistoryBtn = document.getElementById('refreshTestHistoryBtn');

        if (refreshTestStatusBtn) {
            refreshTestStatusBtn.addEventListener('click', () => this.loadTestStatus());
        }

        if (refreshTestHistoryBtn) {
            refreshTestHistoryBtn.addEventListener('click', () => this.loadTestHistory());
        }
    },

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
                if (historyCountEl) historyCountEl.textContent = data.runs.length;
            } else if (data.success === false) {
                console.error('测试历史API返回错误:', data.error || '未知错误');
                if (historyListEl) {
                    historyListEl.innerHTML = `<div class="empty-state">加载失败: ${data.error || '未知错误'}</div>`;
                }
                if (historyCountEl) historyCountEl.textContent = '0';
            } else {
                if (historyListEl) {
                    historyListEl.innerHTML = '<div class="empty-state">暂无测试历史记录</div>';
                }
                if (historyCountEl) historyCountEl.textContent = '0';
            }
        } catch (error) {
            console.error('加载测试历史失败:', error);
            if (historyListEl) {
                historyListEl.innerHTML = `<div class="empty-state">加载失败: ${error.message}</div>`;
            }
        }
    },

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

        historyListEl.querySelectorAll('.test-history-item').forEach(item => {
            item.addEventListener('click', () => {
                const runId = item.getAttribute('data-run-id');
                this.loadTestRunDetail(runId);
            });
        });
    },

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
    },

    displayTestRunDetail(run) {
        const currentTestSection = document.getElementById('currentTestSection');
        if (currentTestSection) currentTestSection.style.display = 'block';

        const runIdEl = document.getElementById('currentTestRunId');
        const runTimeEl = document.getElementById('currentTestRunTime');
        if (runIdEl) runIdEl.textContent = `运行 ID: ${run.run_id}`;
        if (runTimeEl) {
            const startTime = new Date(run.started_at);
            runTimeEl.textContent = `运行时间: ${startTime.toLocaleString('zh-CN')}`;
        }

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

        const outputContainer = document.getElementById('testOutputContainer');
        const testOutput = document.getElementById('testOutput');
        if (testOutput && run.output) {
            testOutput.textContent = run.output;
            if (outputContainer) outputContainer.style.display = 'block';
        }

        this.updateTestStatusDisplay({
            total_tests: run.total_tests,
            passed: run.passed,
            failed: run.failed,
            skipped: run.skipped,
            errors: run.errors,
            success_rate: run.success_rate,
            last_run_time: run.started_at
        });
    },

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
                total_tests: 0, passed: 0, failed: 0, skipped: 0, errors: 0, success_rate: 0
            });
        }
    },

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
    },

    updateTestStatus(status) {
        this.updateTestStatusDisplay(status);
    },

    async runAllTests() {
        const runBtn = document.getElementById('runAllTestsBtn');
        const resultsList = document.getElementById('testResultsList');
        const outputContainer = document.getElementById('testOutputContainer');
        const testOutput = document.getElementById('testOutput');
        const verboseCheckbox = document.getElementById('testVerboseCheckbox');
        const coverageCheckbox = document.getElementById('testCoverageCheckbox');

        if (runBtn) {
            runBtn.disabled = true;
            runBtn.textContent = '运行中...';
        }

        if (resultsList) {
            resultsList.innerHTML = '<div class="test-loading">正在运行测试...</div>';
        }

        if (outputContainer) outputContainer.style.display = 'none';

        try {
            const response = await fetch('/api/tests/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    test_path: null,
                    verbose: verboseCheckbox ? verboseCheckbox.checked : false,
                    coverage: coverageCheckbox ? coverageCheckbox.checked : false
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.run_id) console.log('测试运行 ID:', result.run_id);

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

            if (typeof this.loadTestHistory === 'function') this.loadTestHistory();

            if (result.run_id && typeof this.loadTestRunDetail === 'function') {
                this.loadTestRunDetail(result.run_id);
            } else {
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

                if (testOutput && (result.output || result.error)) {
                    testOutput.textContent = result.output || result.error || '';
                    if (outputContainer) outputContainer.style.display = 'block';
                }
            }
        } catch (error) {
            console.error('运行测试失败:', error);
            if (resultsList) {
                resultsList.innerHTML = `<div class="test-error">运行测试失败: ${error.message}</div>`;
            }
        } finally {
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.textContent = '运行所有测试';
            }
        }
    }
};
