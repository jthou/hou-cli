# 代码执行器设计：最大化吸收 OpenClaw 优点

> 在保留 hou-cli 现有架构的前提下，选择性吸收 OpenClaw 的 exec/process、安全增强、流式输出等能力。

---

## 一、设计原则

1. **兼容现有**：不破坏 `CodeExecutorTool`、`SecureExecutor`、`RiskDetector`、`AutoCodeExecutor` 的对外接口
2. **渐进增强**：分阶段实现，每阶段可独立交付
3. **无重依赖**：不引入 Pi Agent、Docker、Mac App
4. **保留优势**：保留风险分级、多语言、AutoCodeExecutor、黑名单智能检测

---

## 二、目标能力矩阵

| 能力 | 当前 | 目标 | 来源 |
|------|------|------|------|
| 一次性代码执行 | ✅ | ✅ 保留 | hou-cli |
| 风险分级 | ✅ | ✅ 保留 | hou-cli |
| AutoCodeExecutor | ✅ | ✅ 保留 | hou-cli |
| 混淆检测 | ❌ | ✅ 新增 | OpenClaw |
| Preflight（shell 注入） | ❌ | ✅ 新增 | OpenClaw |
| 流式输出 | ❌ | ✅ 新增 | OpenClaw |
| 后台执行 | ❌ | ✅ 新增 | OpenClaw |
| process 管理 | ❌ | ✅ 新增 | OpenClaw |
| allowlist + approval | ⚠️ 部分 | ✅ 完善 | OpenClaw |
| PTY 支持 | ❌ | ⚠️ 可选 | OpenClaw |
| Docker 沙箱 | ❌ | ⏸️ 暂缓 | OpenClaw |

> **allowlist + approval 必要性**：无审批时，大模型要删文件只能「全拒」或「全放」——全拒则用户无法通过 AI 删文件，全放则危险。allowlist 允许常见安全模式免审，approval 让用户对危险操作（rm、chmod 等）显式确认后执行。

---

## 三、架构设计

### 3.1 整体结构

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Agent 层                                                                 │
│  execute_code (保留)  │  exec (新增)  │  process (新增)                    │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────────┐
│  执行层 (backend/infrastructure/execution/)                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │ SecureExecutor  │  │ ProcessRegistry │  │ ObfuscationDet  │          │
│  │ (保留+增强)      │  │ (新增)          │  │ PreflightCheck  │          │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘          │
│  ┌────────────────────┐  ┌──────────────────┐                            │
│  │ AllowlistEvaluator │  │ ApprovalManager  │                            │
│  │ (新增)             │  │ (新增)           │                            │
│  └────────────────────┘  └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 工具职责划分

| 工具 | 职责 | 与现有关系 |
|------|------|------------|
| **execute_code** | 一次性执行脚本（同步等待），保留现有行为 | 保留，内部增强 |
| **exec** | 执行 shell 命令，支持后台、流式、超时 | 新增 |
| **process** | 管理 exec 启动的后台会话：list/poll/log/kill | 新增 |

**设计决策**：`execute_code` 与 `exec` 并存
- `execute_code`：面向「脚本代码块」，多语言、风险分级、AutoCodeExecutor 使用
- `exec`：面向「shell 命令」，支持后台、流式、更接近 OpenClaw exec

---

### 3.3 支持的语言

> **当前范围**：暂时仅支持 **python** 和 **zsh**，其他语言（bash、powershell、batch）后续再扩展。

#### 3.3.1 execute_code

| 语言 | Linux | macOS | 说明 |
|------|-------|-------|------|
| **python** | ✅ python3/python | ✅ python3/python | -c 执行 |
| **zsh** | ✅ zsh | ✅ zsh（系统默认） | -c 执行 |

**暂不支持**：bash、powershell、batch（后续按需扩展）

**别名映射**（AutoCodeExecutor 提取代码块时）：
- `shell`、`sh`、`bash` → `zsh`（统一用 zsh 执行）

#### 3.3.2 exec

| 类型 | 默认 | 说明 |
|------|------|------|
| **shell** | zsh（Linux/macOS） | 执行 `command` 字符串，使用 zsh -c |

exec 不接收 `language`，直接通过 zsh 执行命令。

#### 3.3.3 各模块对 language 的依赖

| 模块 | 使用 language | 说明 |
|------|---------------|------|
| ObfuscationDetector | ✅ | 区分 python 与 shell 的混淆模式 |
| PreflightCheck | ✅ | 仅对 python/node 脚本做 shell 变量注入检测 |
| AllowlistEvaluator | ✅ | 部分模式按 language 区分（如 zsh rm vs python os.remove） |
| RiskDetector | ✅ | 已有 |
| ProcessRegistry | ❌ | 与 language 无关 |

---

## 四、模块设计

### 4.1 混淆检测（ObfuscationDetector）

**文件**：`backend/infrastructure/execution/obfuscation_detector.py`

**职责**：检测 base64|eval|xxd|printf 等混淆模式，防止绕过黑名单

```python
# 接口
class ObfuscationDetector:
    def detect(self, code: str, language: str) -> ObfuscationResult:
        """返回 detected: bool, reasons: List[str], matched_patterns: List[str]"""
```

**模式**（借鉴 OpenClaw）：
- `base64 -d | sh`
- `eval $(base64 ...)`
- `xxd -r | bash`
- `printf \\x... | sh`
- `curl | sh`
- Python: `eval(base64.b64decode(...))`、`os.system(base64...)`

**集成**：在 `SecureExecutor` 和 `exec` 工具执行前调用

---

### 4.2 Preflight 检查（ShellBleedCheck）

**文件**：`backend/infrastructure/execution/preflight.py`

**职责**：检测 Python/Node 脚本中的 shell 变量注入（如 `$PATH`）

```python
# 接口
def validate_script_for_shell_bleed(command: str, workdir: Path) -> None:
    """
    解析 command 中的 python file.py / node file.js，
    读取文件内容，检测 $VAR 模式，若存在则 raise ValueError
    """
```

**集成**：在 `exec` 执行前、`execute_code` 写入临时文件后调用（仅当 language 为 python 且 code 来自文件时可选）

---

### 4.3 进程注册表（ProcessRegistry）

**文件**：`backend/infrastructure/execution/process_registry.py`

**职责**：管理 exec 启动的后台进程

```python
@dataclass
class ProcessSession:
    id: str
    command: str
    pid: Optional[int]
    cwd: str
    started_at: float
    aggregated: str      # 聚合输出
    tail: str            # 尾部 N 字符
    exited: bool
    exit_code: Optional[int]
    backgrounded: bool

class ProcessRegistry:
    def add(self, session: ProcessSession) -> None
    def get(self, session_id: str) -> Optional[ProcessSession]
    def list_running(self, scope_key: Optional[str] = None) -> List[ProcessSession]
    def mark_backgrounded(self, session_id: str) -> None
    def append_output(self, session_id: str, stdout: str, stderr: str) -> None
    def tail(self, session_id: str, max_chars: int) -> str
```

**LRU 清理**：finished 会话保留 N 分钟，超时自动清理

---

### 4.4 exec 工具

**文件**：`backend/core/agent/tools/builtin/exec_tool.py`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| command | string | shell 命令 |
| workdir | string? | 工作目录 |
| timeout | int? | 超时秒数 |
| background | bool? | 是否立即后台 |
| yield_ms | int? | 运行 N 毫秒后后台 |
| pty | bool? | 是否使用 PTY（可选实现） |
| approval_token | string? | 用户确认后获得的 token |
| approval_id | string? | 待审批请求 ID（返回 requires_approval 时） |

**流程**：
1. ObfuscationDetector.detect()
2. Preflight（若可解析出脚本文件）
3. AllowlistEvaluator.evaluate()：若命中 allowlist → 直接执行
4. 否则 RiskDetector.detect_risk()：CRITICAL 拒绝，MEDIUM/HIGH 需 approval
5. 若需 approval 且无 `approval_token` → 返回 `requires_approval`，等待用户确认
6. 用户确认后，携带 `approval_token` 重新调用 → 执行
7. 启动子进程，输出写入 ProcessRegistry
5. 若 background 或 yield_ms 到期 → mark_backgrounded，返回 session_id
6. 否则等待完成，返回 aggregated

**流式**：通过 `progress_callback` 或新增 `on_update` 回调传递增量输出

---

### 4.5 process 工具

**文件**：`backend/core/agent/tools/builtin/process_tool.py`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| action | string | list \| poll \| log \| kill \| remove |
| session_id | string? | 会话 ID（list 以外必填） |
| offset | int? | log 分页偏移 |
| limit | int? | log 行数 |

**action 语义**：
- `list`：返回运行中会话列表
- `poll`：等待新输出或退出，返回 tail
- `log`：返回 aggregated 或分页片段
- `kill`：终止进程
- `remove`：从 registry 移除（仅限已退出）

---

### 4.6 execute_code 增强

**保留**：现有接口、RiskDetector、多语言、AutoCodeExecutor

**增强**：
1. 执行前调用 `ObfuscationDetector.detect()`，若 detected 则拒绝
2. 集成 allowlist + approval（见 4.7），新增参数 `approval_token`、`approval_id`
3. 可选：`progress_callback` 支持流式输出
4. 可选：新增参数 `stream: bool`，为 True 时通过 callback 流式返回

---

### 4.7 Allowlist + Approval（重要）

**问题**：无审批时，大模型要删文件只能「全拒」或「全放」——全拒则用户无法通过 AI 删文件，全放则危险。

**设计**：allowlist 允许常见安全模式免审，approval 让用户对危险操作显式确认后执行。

#### 4.7.1 AllowlistEvaluator

**文件**：`backend/infrastructure/execution/allowlist.py`

**职责**：评估命令是否命中 allowlist，命中则免审执行

```python
# 配置示例（YAML/JSON 或 .env）
# EXEC_ALLOWLIST 或 config 中定义
ALLOWLIST_PATTERNS = [
    {"pattern": r"^ls\s+", "description": "列出目录"},
    {"pattern": r"^cat\s+[\w./-]+$", "description": "读取文件"},
    {"pattern": r"^rm\s+[\w./-]+$", "description": "删除单文件（非 -rf）"},
    {"pattern": r"^rm\s+-rf\s+/tmp/[\w./-]*$", "description": "删除 /tmp 下目录"},
    {"pattern": r"^rm\s+-rf\s+\./[\w./-]*$", "description": "删除当前目录下"},
    # 可扩展：按 workdir、正则、命令+参数组合
]

class AllowlistEvaluator:
    def evaluate(self, command: str, workdir: str, language: str) -> AllowlistResult:
        """返回 satisfied: bool, matched_pattern: Optional[str]"""
```

**策略**：命中 allowlist → 直接执行；未命中 → 走 RiskDetector + approval

#### 4.7.2 ApprovalManager

**文件**：`backend/infrastructure/execution/approval.py`

**职责**：管理待审批请求，签发 approval_token，校验 token 有效性

```python
# 待审批请求（可持久化到内存/Redis/文件，支持重启恢复）
@dataclass
class PendingApproval:
    id: str
    command: str
    workdir: str
    language: str
    risk_level: str
    reason: str
    created_at: float
    expires_at: float  # 超时未审批则失效

class ApprovalManager:
    def create_pending(self, ...) -> PendingApproval
    def approve(self, approval_id: str, user_id: Optional[str] = None) -> str  # 返回 token
    def reject(self, approval_id: str) -> None
    def verify_token(self, token: str) -> Optional[PendingApproval]  # 校验并消费 token
```

#### 4.7.3 工具参数扩展

**execute_code / exec** 新增可选参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| approval_token | string? | 用户确认后获得的 token，携带则跳过审批直接执行 |
| approval_id | string? | 待审批请求 ID（返回 requires_approval 时一并返回） |

#### 4.7.4 流程

```
1. LLM 调用 execute_code(code="rm -rf ./build", language="zsh")
2. ObfuscationDetector → 通过
3. AllowlistEvaluator → 未命中（或命中则直接执行）
4. RiskDetector → MEDIUM（rm）
5. 无 approval_token → 返回：
   {
     "success": False,
     "requires_approval": True,
     "approval_id": "ap_xxx",
     "message": "需要用户确认：删除操作",
     "preview": {"command": "rm -rf ./build", "risk_level": "medium"}
   }
6. 前端展示确认弹窗，用户点击「确认」
7. 前端/后端调用 ApprovalManager.approve(approval_id) → 获得 token
8. 重新调用 execute_code(..., approval_token=token) → 执行
```

#### 4.7.5 与现有 RiskDetector 的关系

- **保留** RiskDetector 的 CRITICAL 直接拒绝、SAFE 直接执行
- **增强** MEDIUM/HIGH：现有返回 `requires_confirmation`，改为统一走 ApprovalManager，前端展示确认 UI 后携带 token 重试
- **allowlist** 作为前置：命中则跳过 RiskDetector 的 MEDIUM/HIGH 审批

---

## 五、执行层增强

### 5.1 SubprocessExecutor 流式支持

**修改**：`backend/infrastructure/execution/executor.py`

```python
async def execute(
    self,
    request: ExecutionRequest,
    on_stdout: Optional[Callable[[str], None]] = None,
    on_stderr: Optional[Callable[[str], None]] = None,
) -> ExecutionResult:
    """
    若 on_stdout/on_stderr 非空，则使用 create_subprocess_exec + 逐行读取，
    否则保持现有 communicate() 行为
    """
```

### 5.2 新增 RunExecProcess

**文件**：`backend/infrastructure/execution/run_exec.py`

**职责**：封装「启动进程 + 输出聚合 + 超时 + 后台」逻辑，供 exec 工具调用

```python
async def run_exec_process(
    command: str,
    workdir: str,
    env: Optional[Dict[str, str]] = None,
    timeout_sec: Optional[int] = None,
    use_pty: bool = False,
    on_update: Optional[Callable[[str], None]] = None,
) -> RunResult:
    """
    RunResult: session_id, promise (Future), session (ProcessSession)
    输出实时 append 到 ProcessRegistry，并调用 on_update
    """
```

---

## 六、安全增强汇总

| 层级 | 增强项 | 位置 |
|------|--------|------|
| 执行前 | ObfuscationDetector | SecureExecutor、exec |
| 执行前 | Preflight（shell bleed） | exec（解析到脚本文件时） |
| 执行前 | **AllowlistEvaluator** | execute_code、exec |
| 执行前 | **ApprovalManager** | 需审批时 |
| 执行前 | RiskDetector（保留） | execute_code、exec |
| 执行前 | 黑名单（保留） | SecureExecutor |
| 执行中 | 超时、resource 限制（保留） | SubprocessExecutor |

---

## 七、实施阶段

### 阶段 1：安全增强（低成本）

| 任务 | 文件 | 工作量 |
|------|------|--------|
| ObfuscationDetector | `obfuscation_detector.py` | 小 |
| 集成到 SecureExecutor | `secure_executor.py` | 小 |
| 集成到 CodeExecutorTool | `code_executor_tool.py` | 小 |
| Preflight（可选） | `preflight.py` | 小 |

### 阶段 2：allowlist + approval

| 任务 | 文件 | 工作量 |
|------|------|--------|
| AllowlistEvaluator | `allowlist.py` | 中 |
| ApprovalManager | `approval.py` | 中 |
| 集成到 execute_code | `code_executor_tool.py` | 小 |
| 前端确认 UI | 已有 `interactive_executor.py`，需完善与后端对接 | 中 |
| 确认 API | `POST /api/execution/approve` | 小 |

### 阶段 3：exec + process

| 任务 | 文件 | 工作量 |
|------|------|--------|
| ProcessRegistry | `process_registry.py` | 中 |
| run_exec_process | `run_exec.py` | 中 |
| exec 工具（含 allowlist+approval） | `exec_tool.py` | 中 |
| process 工具 | `process_tool.py` | 中 |
| 注册到 agent_tools_registry | `agent_tools_registry.py` | 小 |

### 阶段 4：流式输出

| 任务 | 文件 | 工作量 |
|------|------|--------|
| SubprocessExecutor 流式 | `executor.py` | 中 |
| execute_code 支持 stream | `code_executor_tool.py` | 小 |
| exec 的 on_update | `exec_tool.py` | 小 |

### 阶段 5：PTY（可选）

| 任务 | 文件 | 工作量 |
|------|------|--------|
| PTY 支持 | `run_exec.py`、`executor.py` | 中 |
| exec 参数 pty | `exec_tool.py` | 小 |

---

## 八、配置与开关

```python
# 可选：.env 或 config
EXEC_BACKGROUND_ENABLED = True      # 是否允许后台
EXEC_MAX_YIELD_MS = 120_000        # yield_ms 上限
EXEC_DEFAULT_TIMEOUT_SEC = 1800
PROCESS_SESSION_TTL_MINUTES = 30   # 已退出会话保留时间
OBFUSCATION_DETECTION_ENABLED = True
PREFLIGHT_SHELL_BLEED_ENABLED = True
EXEC_ALLOWLIST_ENABLED = True      # 是否启用 allowlist
EXEC_APPROVAL_TIMEOUT_SEC = 120    # 审批请求超时
APPROVAL_STORAGE = "memory"        # memory | file | redis
```

---

## 九、与 OpenClaw 的对应关系

| OpenClaw | hou-cli 设计 |
|----------|--------------|
| exec 工具 | exec 工具（新增） |
| process 工具 | process 工具（新增） |
| ProcessSession / bash-process-registry | ProcessRegistry |
| runExecProcess | run_exec_process |
| detectCommandObfuscation | ObfuscationDetector |
| validateScriptFileForShellBleed | preflight.validate_script_for_shell_bleed |
| host=sandbox/gateway/node | 仅 gateway（本地），无 Docker/Node |
| allowlist / approval | AllowlistEvaluator + ApprovalManager，与 RiskDetector 协同 |
| PTY | 可选实现 |

---

## 十、向后兼容

- `execute_code`：行为不变，仅增加混淆检测
- `AutoCodeExecutor`：不变
- `SecureExecutor`：新增混淆检测，可配置关闭
- 现有调用方无需修改

---

## 十一、测试方案

### 11.1 测试分层

| 层级 | 范围 | 工具 | 目标 |
|------|------|------|------|
| 单元测试 | 单模块 | pytest | 逻辑正确、边界条件 |
| 集成测试 | 多模块协作 | pytest | 流程贯通、工具调用 |
| 端到端测试 | 全链路 | pytest + Mock LLM | 用户视角、审批流程 |

### 11.2 单元测试

#### 11.2.1 ObfuscationDetector

**文件**：`backend/infrastructure/execution/tests/test_obfuscation_detector.py`

| 用例 | 输入 | 预期 |
|------|------|------|
| base64_pipe_sh | `echo xxx \| base64 -d \| sh` | detected=True |
| eval_base64 | `eval $(echo xxx \| base64 -d)` | detected=True |
| xxd_pipe_bash | `xxd -r \| bash` | detected=True |
| curl_pipe_sh | `curl url \| sh` | detected=True |
| python_eval_b64 | `eval(base64.b64decode(...))` | detected=True |
| safe_ls | `ls -la` | detected=False |
| safe_rm_simple | `rm ./tmp.txt` | detected=False |

#### 11.2.2 PreflightCheck

**文件**：`backend/infrastructure/execution/tests/test_preflight.py`

| 用例 | 场景 | 预期 |
|------|------|------|
| python_shell_var | 脚本含 `$PATH` | raise ValueError |
| python_os_environ | 脚本含 `os.environ.get("PATH")` | 通过 |
| node_process_env | 脚本含 `process.env.PATH` | 通过 |
| node_shell_var | 脚本含 `$HOME` | raise ValueError |
| no_script_file | 命令非 python/node 文件 | 通过 |

#### 11.2.3 AllowlistEvaluator

**文件**：`backend/infrastructure/execution/tests/test_allowlist.py`

| 用例 | 输入 | 预期 |
|------|------|------|
| match_ls | `ls -la /tmp` | satisfied=True |
| match_rm_tmp | `rm -rf /tmp/foo` | satisfied=True |
| match_rm_rel | `rm -rf ./build` | satisfied=True |
| no_match_rm_root | `rm -rf /` | satisfied=False |
| no_match_rm_rf_etc | `rm -rf /etc` | satisfied=False |

#### 11.2.4 ApprovalManager

**文件**：`backend/infrastructure/execution/tests/test_approval.py`

| 用例 | 操作 | 预期 |
|------|------|------|
| create_and_approve | create → approve | token 有效，verify 通过 |
| create_and_reject | create → reject | verify 返回 None |
| verify_consumes | approve → verify 两次 | 第二次返回 None（token 已消费） |
| expired | create → 等待超时 → approve | 拒绝或 token 无效 |
| wrong_token | verify("invalid") | 返回 None |

#### 11.2.5 ProcessRegistry

**文件**：`backend/infrastructure/execution/tests/test_process_registry.py`

| 用例 | 操作 | 预期 |
|------|------|------|
| add_get | add → get | 返回相同 session |
| list_running | add 多个 → list_running | 仅返回未退出的 |
| mark_backgrounded | add → mark_backgrounded | backgrounded=True |
| append_output | add → append_output | aggregated 正确累积 |
| tail | append 大量 → tail(100) | 返回最后 100 字符 |
| lru_cleanup | 添加大量 finished → 触发清理 | 超过 TTL 的已移除 |

### 11.3 集成测试

#### 11.3.1 execute_code 增强

**文件**：`backend/core/agent/tools/tests/test_code_executor_tool.py`（扩展现有）

| 用例 | 场景 | 预期 |
|------|------|------|
| obfuscation_rejected | code 含 base64\|sh | success=False, error 含「混淆」 |
| allowlist_skip_approval | rm -rf ./build 且命中 allowlist | 直接执行成功 |
| approval_required | rm -rf ./build 未命中 allowlist | requires_approval=True |
| approval_token_execute | 携带有效 approval_token | 执行成功 |
| approval_token_invalid | 携带无效 token | success=False |

#### 11.3.2 exec 工具

**文件**：`backend/core/agent/tools/tests/test_exec_tool.py`（新建）

| 用例 | 场景 | 预期 |
|------|------|------|
| sync_execute | command="echo hi" | 返回 aggregated 含 "hi" |
| timeout | command="sleep 10", timeout=1 | 超时终止 |
| background | background=True | 返回 session_id，可 process.poll |
| workdir | workdir=/tmp | cwd 正确 |
| allowlist_skip | ls /tmp 命中 allowlist | 直接执行成功 |
| approval_flow | rm 未命中 → 返回 approval_id | requires_approval=True |

#### 11.3.3 process 工具

**文件**：`backend/core/agent/tools/tests/test_process_tool.py`（新建）

| 用例 | 场景 | 预期 |
|------|------|------|
| list_empty | 无后台进程 | 返回空列表 |
| list_after_exec | exec background 后 list | 含 1 条 |
| poll_running | 对运行中 session poll | 返回 tail |
| poll_exited | 对已退出 session poll | 返回 exit_code |
| log_pagination | log offset=0 limit=10 | 返回分页片段 |
| kill | kill 运行中 session | 进程终止 |
| remove_exited | remove 已退出 | 从 registry 移除 |

### 11.4 端到端测试

**文件**：`tests/integration/test_code_execution_approval.py`（新建）

| 用例 | 流程 | 预期 |
|------|------|------|
| e2e_approval_flow | 1) LLM 调用 execute_code(rm) 2) 返回 requires_approval 3) 调用 approve API 4) 携带 token 重试 | 执行成功 |
| e2e_allowlist_no_approval | LLM 调用 execute_code(ls) | 直接执行，无需确认 |
| e2e_obfuscation_blocked | LLM 输出含 base64\|sh 的代码 | 被拒绝，不执行 |

### 11.5 测试数据与 Mock

| 类型 | 策略 |
|------|------|
| 真实命令 | 使用 `echo`、`ls`、`pwd` 等安全命令 |
| 危险命令 | 仅测试「拒绝」逻辑，不实际执行 |
| 审批 API | Mock 或内存 ApprovalManager，不依赖 Redis |
| LLM | Mock 工具调用参数，不调用真实 API |

### 11.6 测试执行命令

```bash
# 单元测试
pytest backend/infrastructure/execution/tests/test_obfuscation_detector.py -v
pytest backend/infrastructure/execution/tests/test_preflight.py -v
pytest backend/infrastructure/execution/tests/test_allowlist.py -v
pytest backend/infrastructure/execution/tests/test_approval.py -v
pytest backend/infrastructure/execution/tests/test_process_registry.py -v

# 集成测试
pytest backend/core/agent/tools/tests/test_code_executor_tool.py -v
pytest backend/core/agent/tools/tests/test_exec_tool.py -v
pytest backend/core/agent/tools/tests/test_process_tool.py -v

# 端到端
pytest tests/integration/test_code_execution_approval.py -v

# 全量执行
pytest backend/infrastructure/execution/tests/ backend/core/agent/tools/tests/test_*_tool.py tests/integration/test_code_execution_approval.py -v
```

### 11.7 与实施阶段的对应

| 实施阶段 | 测试先行 |
|----------|----------|
| 阶段 1 安全增强 | test_obfuscation_detector, test_preflight |
| 阶段 2 allowlist+approval | test_allowlist, test_approval, test_code_executor_tool 扩展 |
| 阶段 3 exec+process | test_process_registry, test_exec_tool, test_process_tool |
| 阶段 4 流式 | 在 test_exec_tool 中增加流式断言 |
| 阶段 5 PTY | 在 test_exec_tool 中增加 pty 可选（需环境支持） |
