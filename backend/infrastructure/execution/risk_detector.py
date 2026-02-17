"""风险检测模块

检测代码中的危险操作，评估风险级别
"""
import re
from enum import Enum
from typing import Tuple, Optional


class RiskLevel(Enum):
    """风险级别"""
    SAFE = "safe"           # 安全操作，自动执行
    LOW = "low"             # 低风险，简单确认
    MEDIUM = "medium"       # 中风险，需要明确确认
    HIGH = "high"           # 高风险，需要密码确认
    CRITICAL = "critical"   # 严重风险，禁止执行


class RiskDetector:
    """风险检测器
    
    检测代码中的危险操作，返回风险级别和原因
    """
    
    # 风险规则：命令 -> 风险级别
    RISK_RULES = {
        # 高风险操作（需要密码确认）
        "sudo": RiskLevel.HIGH,
        "su": RiskLevel.HIGH,
        "rm -rf": RiskLevel.HIGH,
        "rm -r -f": RiskLevel.HIGH,
        "format": RiskLevel.HIGH,
        "dd": RiskLevel.HIGH,
        "mkfs": RiskLevel.HIGH,
        "fdisk": RiskLevel.HIGH,
        
        # 中风险操作（需要明确确认）
        "rm ": RiskLevel.MEDIUM,
        "del ": RiskLevel.MEDIUM,
        "chmod": RiskLevel.MEDIUM,
        "chown": RiskLevel.MEDIUM,
        "chgrp": RiskLevel.MEDIUM,
        "killall": RiskLevel.MEDIUM,
        "pkill": RiskLevel.MEDIUM,
        
        # 低风险操作（简单确认）
        "cp ": RiskLevel.LOW,
        "mv ": RiskLevel.LOW,
        "mkdir": RiskLevel.LOW,
        "touch": RiskLevel.LOW,
        
        # 安全操作（自动执行）
        "ls": RiskLevel.SAFE,
        "cat": RiskLevel.SAFE,
        "echo": RiskLevel.SAFE,
        "print": RiskLevel.SAFE,
        "pwd": RiskLevel.SAFE,
        "cd": RiskLevel.SAFE,
    }
    
    # 严重风险操作（禁止执行）
    CRITICAL_PATTERNS = [
        r"rm\s+-rf\s+/",  # rm -rf /
        r"dd\s+if=/dev/",  # dd if=/dev/
        r"format\s+c:",  # format c:
        r":\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # fork bomb
    ]
    
    # 受限路径
    RESTRICTED_PATHS = [
        "/etc", "/sys", "/proc", "/dev", "/root",
        "C:\\Windows\\System32", "C:\\Windows\\SysWOW64"
    ]
    
    def detect_risk(self, code: str, language: str) -> Tuple[RiskLevel, str]:
        """检测代码风险级别
        
        Args:
            code: 代码内容
            language: 代码语言
            
        Returns:
            (风险级别, 原因)
        """
        code_lower = code.lower()
        
        # 1. 检查严重风险（禁止执行）
        for pattern in self.CRITICAL_PATTERNS:
            if re.search(pattern, code_lower):
                return RiskLevel.CRITICAL, f"检测到严重危险操作: {pattern}"
        
        # 2. 检查受限路径
        for restricted_path in self.RESTRICTED_PATHS:
            if restricted_path.lower() in code_lower:
                return RiskLevel.CRITICAL, f"禁止访问受限路径: {restricted_path}"
        
        # 3. 检查风险规则
        max_risk = RiskLevel.SAFE
        detected_commands = []
        
        for command, risk_level in self.RISK_RULES.items():
            # 使用单词边界匹配，避免误匹配
            pattern = r'\b' + re.escape(command) + r'\b'
            if re.search(pattern, code_lower):
                if risk_level.value > max_risk.value:
                    max_risk = risk_level
                detected_commands.append(command)
        
        if max_risk != RiskLevel.SAFE:
            reason = f"检测到危险操作: {', '.join(detected_commands)}"
            return max_risk, reason
        
        # 4. 默认安全
        return RiskLevel.SAFE, ""
    
    def requires_confirmation(self, risk_level: RiskLevel) -> bool:
        """判断是否需要用户确认
        
        Args:
            risk_level: 风险级别
            
        Returns:
            是否需要确认
        """
        return risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
    
    def requires_password(self, risk_level: RiskLevel) -> bool:
        """判断是否需要密码确认
        
        Args:
            risk_level: 风险级别
            
        Returns:
            是否需要密码
        """
        return risk_level == RiskLevel.HIGH
    
    def is_allowed(self, risk_level: RiskLevel) -> bool:
        """判断是否允许执行
        
        Args:
            risk_level: 风险级别
            
        Returns:
            是否允许执行
        """
        return risk_level != RiskLevel.CRITICAL









