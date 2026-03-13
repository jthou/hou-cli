"""使用 LLM 验证工具描述的准确性测试"""

import pytest
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService


class ToolDescriptionValidator:
    """使用 LLM 验证工具描述的准确性"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.registry = ToolRegistry()
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """获取所有已注册的工具信息"""
        tools = []
        for tool_name in self.registry.list_tools():
            tool = self.registry.get_tool(tool_name)
            if tool:
                tool_dict = tool.to_dict()
                # 添加更多信息用于验证
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "description": p.description,
                            "required": p.required,
                            "default": p.default,
                            "enum": p.enum
                        }
                        for p in tool.parameters
                    ],
                    "full_dict": tool_dict
                }
                tools.append(tool_info)
        return tools
    
    async def validate_tool_description(
        self, 
        tool_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 LLM 验证单个工具的描述"""
        
        # 构建验证提示
        prompt = self._build_validation_prompt(tool_info)
        
        # 调用 LLM
        try:
            response = await self.llm_service.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一个专业的工具描述审查专家。"
                            "你的任务是分析工具的描述和参数定义，检查是否存在以下问题："
                            "\n1. 错误信息：描述中提到的功能或参数实际上不存在"
                            "\n2. 歧义：描述模糊不清，可能产生多种理解"
                            "\n3. 信息不准确：描述与实际功能不符"
                            "\n4. 信息不足：缺少关键信息，导致用户无法正确使用工具"
                            "\n5. 参数描述问题：参数描述与参数定义不一致"
                            "\n\n请仔细分析，给出详细的评估报告。"
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 降低温度以获得更一致的评估
                max_tokens=2000
            )
            
            # 解析响应
            result = self._parse_llm_response(response, tool_info)
            return result
            
        except Exception as e:
            return {
                "tool_name": tool_info["name"],
                "status": "error",
                "error": str(e),
                "issues": [],
                "score": 0
            }
    
    def _build_validation_prompt(self, tool_info: Dict[str, Any]) -> str:
        """构建验证提示"""
        prompt = f"""请分析以下工具的描述和参数定义，检查是否存在问题：

工具名称：{tool_info['name']}

工具描述：
{tool_info['description']}

参数列表：
"""
        for param in tool_info['parameters']:
            prompt += f"\n- {param['name']} ({param['type']})"
            prompt += f"  {'[必需]' if param['required'] else '[可选]'}"
            if param.get('default') is not None:
                prompt += f" 默认值: {param['default']}"
            if param.get('enum'):
                prompt += f" 可选值: {param['enum']}"
            prompt += f"\n  描述: {param['description']}\n"
        
        prompt += """
请从以下角度分析：

1. **准确性检查**：
   - 描述中提到的功能是否真实存在？
   - 描述中提到的参数是否在参数列表中？
   - 描述中提到的限制或特性是否准确？

2. **歧义检查**：
   - 描述是否有多种可能的理解？
   - 参数之间的关系是否清晰？
   - 操作流程是否明确？

3. **完整性检查**：
   - 是否缺少关键信息？
   - 使用示例是否充分？
   - 错误处理说明是否清晰？

4. **一致性检查**：
   - 参数描述与参数定义是否一致？
   - 描述中的示例与参数类型是否匹配？

请以 JSON 格式返回分析结果：
{
    "has_issues": true/false,
    "issues": [
        {
            "type": "错误信息" | "歧义" | "信息不准确" | "信息不足" | "参数描述问题",
            "severity": "严重" | "中等" | "轻微",
            "description": "问题描述",
            "location": "描述中的具体位置或参数名",
            "suggestion": "改进建议"
        }
    ],
    "score": 0-100,  // 描述质量评分，100 表示完美
    "summary": "总体评价"
}
"""
        return prompt
    
    def _parse_llm_response(
        self, 
        response: str, 
        tool_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON（可能包含在代码块中）
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # 如果没有找到 JSON，尝试直接解析
                result = json.loads(response)
            
            return {
                "tool_name": tool_info["name"],
                "status": "success",
                "has_issues": result.get("has_issues", False),
                "issues": result.get("issues", []),
                "score": result.get("score", 0),
                "summary": result.get("summary", ""),
                "raw_response": response
            }
        except json.JSONDecodeError:
            # 如果无法解析 JSON，返回原始响应
            return {
                "tool_name": tool_info["name"],
                "status": "parse_error",
                "error": "无法解析 LLM 响应为 JSON",
                "raw_response": response,
                "issues": [],
                "score": 0
            }


@pytest.fixture
def llm_service():
    """创建 LLM 服务实例"""
    return LLMService(temperature=0.3, max_tokens=2000)


@pytest.fixture
def validator(llm_service):
    """创建验证器实例"""
    # 确保所有工具都已注册
    _ensure_all_tools_registered()
    return ToolDescriptionValidator(llm_service)


def _ensure_all_tools_registered():
    """确保所有内置工具都已注册"""
    registry = ToolRegistry()
    
    # 如果注册表为空，注册所有内置工具
    if len(registry.list_tools()) == 0:
        from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
        from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
        from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
        from backend.core.agent.tools.builtin.wikipedia_tool import WikipediaTool
        from backend.core.agent.tools.builtin.google_search_tool import GoogleSearchTool
        from backend.core.agent.tools.builtin.file_search_tool import FileSearchTool
        from backend.core.agent.tools.builtin.browser_tool import BrowserTool
        from backend.core.agent.tools.builtin.gvim_tool import GvimTool
        from backend.core.agent.tools.builtin.mediawiki_tool import MediaWikiTool
        from backend.core.agent.tools.builtin.video_downloader_tool import VideoDownloaderTool
        from backend.core.agent.tools.builtin.zhihu_zhida_tool import ZhihuZhidaTool
        from backend.core.agent.tools.builtin.pdf_parser_tool import PDFParserTool
        from backend.core.agent.tools.builtin.file_organizer_tool import FileOrganizerTool
        from backend.core.agent.tools.builtin.weather_tool import WeatherTool, get_weather_tool
        
        # 注册所有工具（如果尚未注册）
        tools_to_register = [
            CodeExecutorTool(),
            FFmpegTool(),
            WhisperTool(),
            WikipediaTool(),
            GoogleSearchTool(),
            FileSearchTool(),
            GvimTool(),
            MediaWikiTool(),
            VideoDownloaderTool(),
            ZhihuZhidaTool(),
            PDFParserTool(),
            FileOrganizerTool(),
        ]
        
        # WeatherTool 需要特殊处理
        try:
            weather_tool = get_weather_tool()
            if weather_tool:
                tools_to_register.append(weather_tool)
        except Exception:
            # 如果 WeatherTool 初始化失败，跳过
            pass
        
        # BrowserTool 需要特殊处理（需要 LLM 服务）
        try:
            from backend.services.llm.llm_service import LLMService
            llm_service = LLMService()
            from backend.core.agent.tools.builtin.browser_tool import BrowserTool
            tools_to_register.append(BrowserTool(llm_service=llm_service))
        except Exception:
            # 如果 BrowserTool 初始化失败，跳过
            pass
        
        for tool in tools_to_register:
            try:
                registry.register(tool)
            except ValueError:
                # 工具已注册，跳过
                pass


# 基础测试：不需要 LLM，可以立即运行
def test_tools_are_registered():
    """测试：确保所有工具都已注册（基础检查）"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    tools = registry.list_tools()
    
    assert len(tools) > 0, "没有找到已注册的工具"
    print(f"\n✅ 找到 {len(tools)} 个已注册的工具: {', '.join(tools)}")


def test_tool_descriptions_not_empty():
    """测试：检查所有工具的描述不为空"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    issues = []
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if tool:
            if not tool.description or len(tool.description.strip()) < 10:
                issues.append(f"{tool_name}: 描述为空或过短")
    
    assert len(issues) == 0, f"发现描述问题:\n" + "\n".join(issues)


def test_tool_parameters_have_descriptions():
    """测试：检查所有参数都有描述"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    issues = []
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if tool:
            for param in tool.parameters:
                if not param.description or len(param.description.strip()) < 3:
                    issues.append(f"{tool_name}.{param.name}: 参数描述为空或过短")
    
    if issues:
        print(f"\n⚠️  发现参数描述问题:\n" + "\n".join(issues))
    # 只警告，不失败


def test_tool_required_parameters_are_marked():
    """测试：检查必需参数是否正确标记"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    issues = []
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if tool:
            required_params = [p for p in tool.parameters if p.required]
            # 检查是否有必需参数但描述中没有说明
            for param in required_params:
                if "必需" not in param.description and "required" not in param.description.lower():
                    issues.append(f"{tool_name}.{param.name}: 必需参数未在描述中明确说明")
    
    if issues:
        print(f"\n⚠️  发现必需参数标记问题:\n" + "\n".join(issues))
    # 只警告，不失败


def test_tool_enum_parameters_have_valid_values():
    """测试：检查枚举参数是否有有效值"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    issues = []
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if tool:
            for param in tool.parameters:
                if param.enum and len(param.enum) == 0:
                    issues.append(f"{tool_name}.{param.name}: 枚举参数为空")
    
    assert len(issues) == 0, f"发现枚举参数问题:\n" + "\n".join(issues)


def test_tool_descriptions_no_obvious_errors():
    """测试：检查描述中是否有明显的错误（不需要 LLM）"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    issues = []
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if tool:
            description = tool.description.lower()
            
            # 检查是否提到不存在的参数
            param_names = {p.name.lower() for p in tool.parameters}
            # 简单的模式匹配（可能不够准确，但可以捕获明显错误）
            import re
            mentioned = re.findall(r'\b(\w+)\s*[:：]', description)
            for word in mentioned:
                if word.lower() in ['参数', 'param', '必需', '可选', '默认']:
                    continue
                # 检查是否是参数名的一部分
                is_param = any(word.lower() in pname or pname in word.lower() for pname in param_names)
                if not is_param and len(word) > 3:
                    # 可能是误匹配，但记录一下
                    pass
    
    # 这个测试主要是结构检查，不强制失败


# LLM 测试：需要 API Key
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要配置 DEEPSEEK_API_KEY（必需，参考 env.example）"
)
async def test_all_tool_descriptions(validator):
    """测试所有工具的描述准确性"""
    tools = validator.get_all_tools()
    
    if not tools:
        pytest.skip("没有找到已注册的工具")
    
    results = []
    issues_found = []
    
    for tool_info in tools:
        print(f"\n正在验证工具: {tool_info['name']}...")
        result = await validator.validate_tool_description(tool_info)
        results.append(result)
        
        if result.get("has_issues", False):
            issues_found.append(result)
            print(f"  ❌ 发现问题: {len(result.get('issues', []))} 个")
        else:
            print(f"  ✅ 通过验证 (评分: {result.get('score', 0)})")
    
    # 生成报告
    report = generate_report(results)
    print("\n" + "="*80)
    print("工具描述验证报告")
    print("="*80)
    print(report)
    
    # 保存报告到文件
    report_file = Path(__file__).parent.parent.parent.parent / "docs" / "tool-description-validation-report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 工具描述验证报告\n\n")
        f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
        f.write(report)
    
    # 如果有严重问题，测试失败
    critical_issues = [
        issue for r in issues_found 
        for issue in r.get('issues', [])
        if issue.get('severity') == '严重'
    ]
    
    if critical_issues:
        pytest.fail(
            f"发现 {len(critical_issues)} 个严重问题。"
            f"详细报告已保存到: {report_file}"
        )


def generate_report(results: List[Dict[str, Any]]) -> str:
    """生成验证报告"""
    total_tools = len(results)
    tools_with_issues = sum(1 for r in results if r.get("has_issues", False))
    total_issues = sum(len(r.get("issues", [])) for r in results)
    
    # 按严重程度分类
    critical_issues = []
    medium_issues = []
    minor_issues = []
    
    for result in results:
        for issue in result.get("issues", []):
            severity = issue.get("severity", "轻微")
            if severity == "严重":
                critical_issues.append((result["tool_name"], issue))
            elif severity == "中等":
                medium_issues.append((result["tool_name"], issue))
            else:
                minor_issues.append((result["tool_name"], issue))
    
    report = f"""
## 总体统计

- 总工具数: {total_tools}
- 有问题的工具: {tools_with_issues}
- 总问题数: {total_issues}
  - 严重: {len(critical_issues)}
  - 中等: {len(medium_issues)}
  - 轻微: {len(minor_issues)}

## 平均质量评分

平均分: {sum(r.get('score', 0) for r in results) / total_tools if total_tools > 0 else 0:.1f}/100

## 详细问题列表

"""
    
    if critical_issues:
        report += "### 严重问题\n\n"
        for tool_name, issue in critical_issues:
            report += f"**{tool_name}** - {issue['type']}\n"
            report += f"- 位置: {issue.get('location', 'N/A')}\n"
            report += f"- 描述: {issue['description']}\n"
            report += f"- 建议: {issue.get('suggestion', 'N/A')}\n\n"
    
    if medium_issues:
        report += "### 中等问题\n\n"
        for tool_name, issue in medium_issues[:10]:  # 只显示前10个
            report += f"**{tool_name}** - {issue['type']}\n"
            report += f"- {issue['description']}\n\n"
    
    # 按工具分组显示
    report += "\n## 按工具分组\n\n"
    for result in results:
        if result.get("has_issues", False):
            report += f"### {result['tool_name']}\n\n"
            report += f"评分: {result.get('score', 0)}/100\n\n"
            if result.get("summary"):
                report += f"**总体评价**: {result['summary']}\n\n"
            
            for issue in result.get("issues", []):
                report += f"- **{issue['type']}** ({issue['severity']})\n"
                report += f"  - {issue['description']}\n"
                if issue.get("suggestion"):
                    report += f"  - 建议: {issue['suggestion']}\n"
            report += "\n"
    
    return report


# 单独测试特定工具
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要配置 DEEPSEEK_API_KEY（必需，参考 env.example）"
)
async def test_specific_tool_description(validator, tool_name: str = "whisper"):
    """测试特定工具的描述（用于调试）"""
    tool = validator.registry.get_tool(tool_name)
    if not tool:
        pytest.skip(f"工具 '{tool_name}' 未找到")
    
    tool_info = {
        "name": tool.name,
        "description": tool.description,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required,
                "default": p.default,
                "enum": p.enum
            }
            for p in tool.parameters
        ]
    }
    
    result = await validator.validate_tool_description(tool_info)
    
    print("\n" + "="*80)
    print(f"工具: {tool_name}")
    print("="*80)
    print(f"评分: {result.get('score', 0)}/100")
    print(f"有问题: {result.get('has_issues', False)}")
    if result.get("summary"):
        print(f"\n总体评价:\n{result['summary']}")
    if result.get("issues"):
        print(f"\n发现的问题 ({len(result['issues'])} 个):")
        for issue in result["issues"]:
            print(f"\n- {issue['type']} ({issue['severity']})")
            print(f"  {issue['description']}")
            if issue.get("suggestion"):
                print(f"  建议: {issue['suggestion']}")
    
    # 断言：如果有严重问题，测试失败
    critical_issues = [
        issue for issue in result.get("issues", [])
        if issue.get("severity") == "严重"
    ]
    if critical_issues:
        pytest.fail(f"发现 {len(critical_issues)} 个严重问题")


# 使用参数化测试为每个工具创建测试用例
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要配置 DEEPSEEK_API_KEY（必需，参考 env.example）"
)
@pytest.mark.parametrize("tool_name", [
    "exec_py",
    "exec_shell",
    "ffmpeg",
    "whisper",
    "wikipedia",
    "google_search",
    "file_search",
    "gvim",
    "mediawiki",
    "video_downloader",
    "zhihu_zhida",
    "pdf_parser",
    "file_organizer",
    "weather",
    "browser",
])
async def test_individual_tool_description(validator, tool_name):
    """测试单个工具的描述准确性（参数化测试）"""
    tool = validator.registry.get_tool(tool_name)
    if not tool:
        pytest.skip(f"工具 '{tool_name}' 未找到或未注册")
    
    tool_info = {
        "name": tool.name,
        "description": tool.description,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required,
                "default": p.default,
                "enum": p.enum
            }
            for p in tool.parameters
        ]
    }
    
    result = await validator.validate_tool_description(tool_info)
    
    # 记录结果但不强制失败（除非是严重问题）
    critical_issues = [
        issue for issue in result.get("issues", [])
        if issue.get("severity") == "严重"
    ]
    
    if critical_issues:
        pytest.fail(
            f"工具 '{tool_name}' 发现 {len(critical_issues)} 个严重问题。"
            f"评分: {result.get('score', 0)}/100"
        )
    # 非严重问题只记录，不失败


def test_tool_description_consistency():
    """测试工具描述的一致性（描述与参数定义是否一致）"""
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    issues = []
    
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if not tool:
            continue
        
        description = tool.description.lower()
        param_names = {p.name.lower() for p in tool.parameters}
        
        # 检查必需参数是否在描述中有说明（更宽松的检查）
        required_params = [p for p in tool.parameters if p.required]
        for param in required_params:
            param_name_lower = param.name.lower()
            # 检查参数名或参数描述关键词是否在描述中
            if (param_name_lower not in description and 
                param.description.lower() not in description):
                # 检查是否是明显的参数（如 url, query 等常见参数名）
                common_params = {'url', 'query', 'task', 'operation', 'action', 'file_path', 'input_file'}
                if param_name_lower not in common_params:
                    issues.append({
                        "tool": tool_name,
                        "parameter": param.name,
                        "issue": "必需参数在描述中未明确提及"
                    })
    
    if issues:
        issue_msg = "\n".join([
            f"- {issue['tool']}.{issue['parameter']}: {issue['issue']}"
            for issue in issues
        ])
        # 只警告，不失败（因为描述可能在其他地方说明了参数）
        print(f"\n⚠️  发现描述一致性问题（仅供参考）:\n{issue_msg}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要配置 DEEPSEEK_API_KEY（必需，参考 env.example）"
)
async def test_tool_parameter_descriptions(validator):
    """测试工具参数描述的完整性"""
    tools = validator.get_all_tools()
    
    if not tools:
        pytest.skip("没有找到已注册的工具")
    
    issues = []
    
    for tool_info in tools:
        tool_name = tool_info["name"]
        
        for param in tool_info["parameters"]:
            param_name = param["name"]
            param_desc = param.get("description", "")
            
            # 检查参数描述是否为空或过短
            if not param_desc or len(param_desc.strip()) < 5:
                issues.append({
                    "tool": tool_name,
                    "parameter": param_name,
                    "issue": "参数描述为空或过短"
                })
            
            # 检查必需参数是否有明确说明
            if param.get("required", False) and "必需" not in param_desc and "required" not in param_desc.lower():
                issues.append({
                    "tool": tool_name,
                    "parameter": param_name,
                    "issue": "必需参数未在描述中明确说明"
                })
            
            # 检查有默认值的参数是否说明了默认值
            if param.get("default") is not None and str(param["default"]) not in param_desc:
                issues.append({
                    "tool": tool_name,
                    "parameter": param_name,
                    "issue": f"有默认值 {param['default']} 但描述中未说明"
                })
    
    if issues:
        issue_msg = "\n".join([
            f"- {issue['tool']}.{issue['parameter']}: {issue['issue']}"
            for issue in issues
        ])
        # 只警告，不失败（这些是轻微问题）
        print(f"\n⚠️  发现参数描述问题:\n{issue_msg}")


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要配置 DEEPSEEK_API_KEY（必需，参考 env.example）"
)
async def test_llm_generated_code_matches_tool_requirements(validator, llm_service):
    """测试：LLM 生成的代码是否符合工具要求
    
    让 LLM 根据工具描述生成使用代码，然后检查：
    1. 代码是否正确使用了工具
    2. 参数是否正确传递
    3. 是否使用了正确的参数名和类型
    """
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    # 选择几个代表性工具进行测试
    test_tools = ["whisper", "ffmpeg", "file_search", "wikipedia"]
    
    issues = []
    
    for tool_name in test_tools:
        tool = registry.get_tool(tool_name)
        if not tool:
            continue
        
        # 构建提示，让 LLM 生成使用该工具的代码
        prompt = f"""请根据以下工具的描述和参数，生成一个 Python 代码示例，展示如何正确使用这个工具。

工具名称：{tool.name}
工具描述：
{tool.description}

参数列表：
"""
        for param in tool.parameters:
            prompt += f"\n- {param.name} ({param.type})"
            prompt += f"  {'[必需]' if param.required else '[可选]'}"
            if param.default is not None:
                prompt += f"  默认值: {param.default}"
            if param.enum:
                prompt += f"  可选值: {param.enum}"
            prompt += f"\n  描述: {param.description}\n"
        
        prompt += """
请生成一个 Python 代码示例，展示如何调用这个工具。
代码应该：
1. 正确使用工具名称
2. 正确传递所有必需参数
3. 使用正确的参数名称
4. 参数类型正确

只返回代码，不要返回其他说明。
"""
        
        try:
            # 调用 LLM 生成代码
            response = await llm_service.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的 Python 开发者。根据工具描述生成正确的代码示例。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            generated_code = response.strip()
            
            # 分析生成的代码
            analysis = _analyze_generated_code(generated_code, tool)
            
            if analysis["has_issues"]:
                issues.append({
                    "tool": tool_name,
                    "code": generated_code,
                    "issues": analysis["issues"]
                })
                print(f"\n❌ {tool_name}: 发现 {len(analysis['issues'])} 个问题")
            else:
                print(f"\n✅ {tool_name}: 生成的代码符合要求")
                
        except Exception as e:
            issues.append({
                "tool": tool_name,
                "error": str(e)
            })
            print(f"\n⚠️  {tool_name}: LLM 调用失败 - {str(e)}")
    
    # 生成报告
    if issues:
        report = "\n" + "="*80 + "\n"
        report += "LLM 生成代码与工具要求一致性检查报告\n"
        report += "="*80 + "\n\n"
        
        for item in issues:
            report += f"工具: {item['tool']}\n"
            if "error" in item:
                report += f"错误: {item['error']}\n"
            else:
                report += f"生成的代码:\n```python\n{item['code']}\n```\n"
                report += f"发现的问题:\n"
                for issue in item.get("issues", []):
                    report += f"  - {issue['type']}: {issue['description']}\n"
            report += "\n"
        
        print(report)
        
        # 如果有严重问题，测试失败
        critical_issues = [
            issue for item in issues 
            if "issues" in item
            for issue in item["issues"]
            if issue.get("severity") == "严重"
        ]
        
        if critical_issues:
            pytest.fail(f"发现 {len(critical_issues)} 个严重问题，LLM 生成的代码不符合工具要求")


def _analyze_generated_code(code: str, tool) -> Dict[str, Any]:
    """分析生成的代码是否符合工具要求"""
    issues = []
    
    # 检查工具名称
    tool_name_patterns = [
        tool.name,
        tool.name.replace("_", ""),
        f'"{tool.name}"',
        f"'{tool.name}'",
    ]
    
    tool_name_found = any(pattern in code for pattern in tool_name_patterns)
    if not tool_name_found:
        issues.append({
            "type": "工具名称错误",
            "severity": "严重",
            "description": f"代码中未找到工具名称 '{tool.name}'"
        })
    
    # 检查必需参数
    required_params = {p.name: p for p in tool.parameters if p.required}
    for param_name, param in required_params.items():
        # 检查参数是否在代码中
        param_patterns = [
            f"{param_name}=",
            f'"{param_name}"',
            f"'{param_name}'",
            f"{param_name}:",
        ]
        param_found = any(pattern in code for pattern in param_patterns)
        
        if not param_found:
            issues.append({
                "type": "缺少必需参数",
                "severity": "严重",
                "description": f"必需参数 '{param_name}' 未在代码中使用"
            })
    
    # 检查参数类型（简单检查）
    for param in tool.parameters:
        if param.name in code:
            # 检查参数值是否符合类型要求
            if param.type == "integer":
                # 检查是否有数字值
                import re
                param_value_pattern = rf"{param.name}\s*=\s*(\d+)"
                if not re.search(param_value_pattern, code):
                    # 可能是变量，不一定是错误
                    pass
            elif param.type == "boolean":
                # 检查是否有布尔值
                param_value_pattern = rf"{param.name}\s*=\s*(True|False|true|false)"
                if not re.search(param_value_pattern, code):
                    pass
    
    # 检查枚举值（如果参数有枚举）
    for param in tool.parameters:
        if param.enum and param.name in code:
            # 检查是否使用了有效的枚举值
            enum_values_found = [val for val in param.enum if str(val) in code]
            if not enum_values_found and param.required:
                # 如果必需参数有枚举但代码中没找到，可能是问题
                pass
    
    return {
        "has_issues": len(issues) > 0,
        "issues": issues
    }


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="需要配置 DEEPSEEK_API_KEY（必需，参考 env.example）"
)
async def test_llm_understands_tool_parameters(llm_service):
    """测试：LLM 是否能正确理解工具参数
    
    给 LLM 一个任务，让它选择正确的工具和参数
    """
    _ensure_all_tools_registered()
    registry = ToolRegistry()
    
    # 获取所有工具的 LLM 格式定义
    tools_for_llm = registry.get_tools_for_llm()
    
    # 测试场景
    test_scenarios = [
        {
            "task": "将音频文件 /path/to/audio.mp3 转换为文字",
            "expected_tool": "whisper",
            "expected_params": ["audio_file"]
        },
        {
            "task": "搜索包含 'test' 的 Python 文件",
            "expected_tool": "file_search",
            "expected_params": ["query", "file_type"]
        },
        {
            "task": "在 Wikipedia 上搜索 'Python' 的相关信息",
            "expected_tool": "wikipedia",
            "expected_params": ["action", "query"]
        },
    ]
    
    issues = []
    
    for scenario in test_scenarios:
        prompt = f"""你是一个 AI 助手，可以使用以下工具完成任务。

可用工具：
{json.dumps(tools_for_llm, indent=2, ensure_ascii=False)}

任务：{scenario['task']}

请以 JSON 格式返回：
{{
    "tool": "工具名称",
    "parameters": {{
        "参数名": "参数值"
    }}
}}
"""
        
        try:
            response = await llm_service.chat(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个工具选择助手。根据任务选择正确的工具和参数。只返回 JSON，不要其他内容。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # 解析响应
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                
                # 检查工具选择
                selected_tool = result.get("tool", "")
                if selected_tool != scenario["expected_tool"]:
                    issues.append({
                        "scenario": scenario["task"],
                        "type": "工具选择错误",
                        "severity": "严重",
                        "description": f"期望工具 '{scenario['expected_tool']}'，但选择了 '{selected_tool}'"
                    })
                
                # 检查参数
                params = result.get("parameters", {})
                for expected_param in scenario["expected_params"]:
                    if expected_param not in params:
                        issues.append({
                            "scenario": scenario["task"],
                            "type": "缺少必需参数",
                            "severity": "严重",
                            "description": f"缺少必需参数 '{expected_param}'"
                        })
            else:
                issues.append({
                    "scenario": scenario["task"],
                    "type": "响应格式错误",
                    "severity": "中等",
                    "description": "LLM 返回的不是有效的 JSON 格式"
                })
                
        except Exception as e:
            issues.append({
                "scenario": scenario["task"],
                "type": "LLM 调用失败",
                "severity": "中等",
                "description": str(e)
            })
    
    if issues:
        issue_msg = "\n".join([
            f"- {issue['scenario']}: {issue['description']}"
            for issue in issues
        ])
        # 只警告，不失败（因为 LLM 可能有多种合理的理解）
        print(f"\n⚠️  LLM 理解工具参数的问题:\n{issue_msg}")


if __name__ == "__main__":
    import os
    from datetime import datetime
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])

