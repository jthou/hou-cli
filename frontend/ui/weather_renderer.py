"""天气信息专用渲染器，使用 Rich Table 组件美化输出"""
import re
from typing import Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from frontend.ui.renderer import ContentRenderer


class WeatherRenderer(ContentRenderer):
    """天气信息专用渲染器，使用 Rich Table 美化表格输出"""
    
    def can_render(self, content: str) -> bool:
        """检测是否为天气相关内容"""
        # 检测天气相关的关键词和表格
        weather_keywords = [
            r'天气|温度|℃|°C|风向|湿度|AQI|PM2\.5|空气质量',
            r'穿衣建议|带伞建议|雾霾',
            r'未来.*周.*天气|天气预报'
        ]
        
        # 检测表格格式
        has_table = bool(re.search(r'\|.*\|', content, re.MULTILINE))
        
        # 检测天气关键词
        has_weather_keywords = any(
            re.search(keyword, content, re.IGNORECASE) 
            for keyword in weather_keywords
        )
        
        return has_table and has_weather_keywords
    
    def render(self, content: str, **kwargs) -> Any:
        """渲染天气信息，使用 Rich Table 美化表格"""
        console = Console()
        
        # 提取表格部分
        table_match = re.search(
            r'\|.*日期.*\|.*天气.*\|.*温度.*\|.*风向.*\|.*湿度.*\|.*\n.*\|.*-+.*\|.*\n(.*?)(?=\n##|\n\n\n|$)',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if table_match:
            # 解析表格数据
            table_rows = table_match.group(1).strip().split('\n')
            
            # 创建 Rich Table
            table = Table(
                title="[bold cyan]未来一周天气预报[/bold cyan]",
                show_header=True,
                header_style="bold magenta",
                border_style="cyan",
                title_style="bold cyan",
                box=None  # 使用简单边框
            )
            
            # 添加列（使用更美观的样式）
            table.add_column("日期", style="bold cyan", width=12, justify="center")
            table.add_column("天气", style="bold yellow", width=12, justify="center")
            table.add_column("最高温度", style="bold red", justify="center", width=12)
            table.add_column("最低温度", style="bold blue", justify="center", width=12)
            table.add_column("风向", style="bold green", width=18, justify="center")
            table.add_column("湿度", style="bold magenta", justify="center", width=10)
            
            # 解析并添加行
            for row in table_rows:
                if not row.strip() or not row.strip().startswith('|'):
                    continue
                
                # 解析表格行：| 1月3日 | ☀️ 晴 | 6°C | -4°C | 🍃 西北风1-3级 | 24% |
                cells = [cell.strip() for cell in row.split('|')[1:-1]]
                if len(cells) >= 6:
                    table.add_row(
                        cells[0],  # 日期
                        cells[1],  # 天气
                        cells[2],  # 最高温度
                        cells[3],  # 最低温度
                        cells[4],  # 风向
                        cells[5]   # 湿度
                    )
            
            # 替换原内容中的表格部分
            table_start = table_match.start()
            table_end = table_match.end()
            
            # 提取表格前后的内容
            before_table = content[:table_start].strip()
            after_table = content[table_end:].strip()
            
            # 组合渲染结果
            result_parts = []
            
            if before_table:
                # 渲染表格前的内容（使用 Markdown）
                result_parts.append(Markdown(before_table))
            
            # 添加表格
            result_parts.append(table)
            
            if after_table:
                # 渲染表格后的内容（使用 Markdown）
                result_parts.append(Markdown(after_table))
            
            # 返回组合结果（Rich 可以渲染多个对象）
            return result_parts
        else:
            # 如果没有找到表格，使用 Markdown 渲染
            return Markdown(content)

