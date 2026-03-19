# Agent 记忆

## Learned User Preferences

- 有明确指令的兜底设计，代码中一定要注明时间、理由、方法
- 没有明确指令的情况下，不要搞任何兜底
- 交付结果、闭环测试、主动排查、测试优先；禁止只给建议让用户自己实施

## Learned Workspace Facts

- 漫画生成：TheTurbo.ai 网关模型均不可用（返回 model does not exist），改用百炼平台
- 百炼漫画需 LiteLLM 代理：`make litellm-comic-proxy`，配置 `litellm_settings.drop_params: true` 以兼容 Claude Agent SDK 的 reasoning_effort/context_management 参数
