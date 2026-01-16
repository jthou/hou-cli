"""交互式执行器（前端）

处理用户确认、密码输入等交互操作
"""
from typing import Optional
from dataclasses import dataclass
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.text import Text

# 导入风险级别（需要从后端同步定义，或使用字符串）
# 为了简化，这里使用字符串常量
RISK_LEVEL_SAFE = "safe"
RISK_LEVEL_LOW = "low"
RISK_LEVEL_MEDIUM = "medium"
RISK_LEVEL_HIGH = "high"
RISK_LEVEL_CRITICAL = "critical"


@dataclass
class ConfirmationResult:
    """确认结果"""
    approved: bool
    password: Optional[str] = None
    modified_code: Optional[str] = None


class InteractiveExecutor:
    """交互式执行器（前端）
    
    处理用户确认、密码输入等交互操作
    """
    
    def __init__(self, console: Console):
        """初始化交互式执行器
        
        Args:
            console: Rich Console 实例
        """
        self.console = console
    
    def request_confirmation(
        self,
        code: str,
        risk_level: str,
        reason: str
    ) -> ConfirmationResult:
        """请求用户确认
        
        Args:
            code: 代码内容
            risk_level: 风险级别 (safe/low/medium/high/critical)
            reason: 风险原因
            
        Returns:
            确认结果
        """
        # 显示代码和警告
        warning = self._get_warning(risk_level)
        
        # 构建确认面板内容
        panel_content = [
            Text("⚠️  危险操作确认", style="bold yellow"),
            "",
            f"检测到危险操作：{reason}",
            f"风险级别：{risk_level.upper()}",
            "",
            Text("代码内容：", style="bold"),
            ""
        ]
        
        # 显示代码（带语法高亮）
        # 尝试从代码推断语言（简单检测）
        language = self._detect_language(code)
        code_syntax = Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=False,
            word_wrap=True
        )
        panel_content.append(code_syntax)
        panel_content.append("")
        
        if warning:
            panel_content.append(Text(f"警告：{warning}", style="bold yellow"))
            panel_content.append("")
        
        self.console.print(Panel(
            *panel_content,
            title="确认执行",
            border_style="yellow",
            padding=(1, 1)
        ))
        
        # 获取用户选择
        if risk_level == RISK_LEVEL_HIGH:
            # 高风险需要明确确认和密码
            approved = Confirm.ask(
                "是否执行此操作？(需要输入密码)",
                default=False,
                console=self.console
            )
            
            if approved:
                password = self.get_password_input()
                return ConfirmationResult(
                    approved=True,
                    password=password
                )
            else:
                return ConfirmationResult(approved=False)
        elif risk_level == RISK_LEVEL_MEDIUM:
            # 中风险需要明确确认
            approved = Confirm.ask(
                "是否执行此操作？",
                default=False,
                console=self.console
            )
            return ConfirmationResult(approved=approved)
        elif risk_level == RISK_LEVEL_LOW:
            # 低风险简单确认
            approved = Confirm.ask(
                "是否执行此操作？",
                default=True,
                console=self.console
            )
            return ConfirmationResult(approved=approved)
        else:
            # 安全操作或严重风险不应该调用此方法
            return ConfirmationResult(approved=False)
    
    def get_password_input(self, prompt: str = "Password") -> str:
        """获取密码输入（隐藏显示）
        
        Args:
            prompt: 提示文本
            
        Returns:
            密码字符串
        """
        password = Prompt.ask(
            prompt,
            password=True,  # Rich 支持隐藏输入
            console=self.console
        )
        
        # 不存储、不记录密码
        return password
    
    def handle_interactive_input(
        self,
        prompt: str,
        is_password: bool = False
    ) -> str:
        """处理交互式输入
        
        Args:
            prompt: 提示文本
            is_password: 是否为密码输入
            
        Returns:
            用户输入
        """
        if is_password:
            return self.get_password_input(prompt)
        else:
            return Prompt.ask(
                prompt,
                console=self.console
            )
    
    def _get_warning(self, risk_level: str) -> str:
        """获取警告信息
        
        Args:
            risk_level: 风险级别
            
        Returns:
            警告文本
        """
        warnings = {
            RISK_LEVEL_HIGH: "此操作需要管理员权限，可能影响系统安全",
            RISK_LEVEL_MEDIUM: "此操作可能修改或删除文件",
            RISK_LEVEL_LOW: "此操作相对安全，但仍需确认"
        }
        return warnings.get(risk_level, "")
    
    def _detect_language(self, code: str) -> str:
        """简单检测代码语言
        
        Args:
            code: 代码内容
            
        Returns:
            语言名称
        """
        code_lower = code.lower().strip()
        
        # 简单的启发式检测
        if code_lower.startswith("#!/bin/bash") or code_lower.startswith("#!/usr/bin/bash"):
            return "bash"
        elif code_lower.startswith("#!/bin/zsh") or code_lower.startswith("#!/usr/bin/zsh"):
            return "zsh"
        elif code_lower.startswith("#!/usr/bin/env python"):
            return "python"
        elif "sudo" in code_lower or "apt" in code_lower or "yum" in code_lower:
            return "bash"
        elif "input(" in code_lower or "print(" in code_lower:
            return "python"
        else:
            return "python"  # 默认




