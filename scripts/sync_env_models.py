#!/usr/bin/env python3
"""
同步 .env 文件中的模型配置部分，使其与 env.example 保持一致的结构和格式

使用方法：
    python scripts/sync_env_models.py

功能：
    1. 读取 env.example 中的模型配置部分（包括注释和说明）
    2. 保留 .env 中已设置的实际值（API Key 等敏感信息）
    3. 更新 .env 中的模型列表说明，使其与 env.example 一致
"""

import os
import re
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
ENV_EXAMPLE = PROJECT_ROOT / "env.example"
ENV_FILE = PROJECT_ROOT / ".env"


def extract_model_sections(content: str) -> dict:
    """提取模型配置部分"""
    sections = {}
    current_section = None
    current_lines = []
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        # 检测模型配置部分的开始
        if re.search(r'# (OpenAI|Anthropic|Google|xAI|Perplexity) 服务模型名称', line):
            # 保存之前的章节
            if current_section:
                sections[current_section] = current_lines
            
            # 开始新章节
            if 'OpenAI' in line:
                current_section = 'OPENAI'
            elif 'Anthropic' in line:
                current_section = 'ANTHROPIC'
            elif 'Google' in line:
                current_section = 'GOOGLE'
            elif 'xAI' in line:
                current_section = 'XAI'
            elif 'Perplexity' in line:
                current_section = 'PERPLEXITY'
            
            current_lines = [line]
        elif current_section:
            current_lines.append(line)
            # 检测章节结束（下一个主要配置项）
            if line.strip() and not line.startswith('#') and not line.startswith(' ') and 'MODEL=' not in line:
                if not line.startswith('OPENAI_') and not line.startswith('ANTHROPIC_') and \
                   not line.startswith('GOOGLE_') and not line.startswith('XAI_') and \
                   not line.startswith('PERPLEXITY_'):
                    sections[current_section] = current_lines
                    current_section = None
                    current_lines = []
    
    # 保存最后一个章节
    if current_section:
        sections[current_section] = current_lines
    
    return sections


def get_current_model_value(env_content: str, model_key: str) -> str:
    """从 .env 文件中获取当前模型值"""
    pattern = rf'^{model_key}=(.+)$'
    match = re.search(pattern, env_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def update_env_file(env_example_content: str, env_content: str) -> str:
    """更新 .env 文件内容"""
    # 提取 env.example 中的模型配置部分
    example_sections = extract_model_sections(env_example_content)
    
    # 获取当前 .env 中的模型值
    current_values = {
        'OPENAI': get_current_model_value(env_content, 'OPENAI_MODEL'),
        'ANTHROPIC': get_current_model_value(env_content, 'ANTHROPIC_MODEL'),
        'GOOGLE': get_current_model_value(env_content, 'GOOGLE_MODEL'),
        'XAI': get_current_model_value(env_content, 'XAI_MODEL'),
        'PERPLEXITY': get_current_model_value(env_content, 'PERPLEXITY_MODEL'),
    }
    
    # 构建新的 .env 内容
    lines = env_content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # 检测模型配置部分的开始
        if re.search(r'# (OpenAI|Anthropic|Google|xAI|Perplexity) 服务模型名称', line):
            section_type = None
            if 'OpenAI' in line:
                section_type = 'OPENAI'
            elif 'Anthropic' in line:
                section_type = 'ANTHROPIC'
            elif 'Google' in line:
                section_type = 'GOOGLE'
            elif 'xAI' in line:
                section_type = 'XAI'
            elif 'Perplexity' in line:
                section_type = 'PERPLEXITY'
            
            if section_type and section_type in example_sections:
                # 添加 env.example 中的完整配置（包括注释）
                new_lines.extend(example_sections[section_type])
                
                # 更新模型值（如果 .env 中有设置）
                model_key = f'{section_type}_MODEL'
                if current_values[section_type]:
                    # 找到 MODEL= 行并更新
                    for j, example_line in enumerate(example_sections[section_type]):
                        if f'{model_key}=' in example_line:
                            new_lines[-len(example_sections[section_type]) + j] = f'{model_key}={current_values[section_type]}'
                
                # 跳过 .env 中旧的模型配置部分
                while i < len(lines) and not (
                    lines[i].strip() and 
                    not lines[i].startswith('#') and 
                    not lines[i].startswith(' ') and
                    'MODEL=' not in lines[i] and
                    not any(lines[i].startswith(prefix) for prefix in ['OPENAI_', 'ANTHROPIC_', 'GOOGLE_', 'XAI_', 'PERPLEXITY_'])
                ):
                    if f'{section_type}_MODEL=' in lines[i]:
                        i += 1
                        break
                    i += 1
                continue
        
        new_lines.append(line)
        i += 1
    
    return '\n'.join(new_lines)


def main():
    """主函数"""
    if not ENV_EXAMPLE.exists():
        print(f"错误：{ENV_EXAMPLE} 不存在")
        return 1
    
    if not ENV_FILE.exists():
        print(f"错误：{ENV_FILE} 不存在")
        return 1
    
    # 读取文件
    print(f"读取 {ENV_EXAMPLE}...")
    with open(ENV_EXAMPLE, 'r', encoding='utf-8') as f:
        env_example_content = f.read()
    
    print(f"读取 {ENV_FILE}...")
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # 备份原文件
    backup_file = ENV_FILE.with_suffix('.env.backup')
    print(f"备份原文件到 {backup_file}...")
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    # 更新 .env 文件
    print("更新 .env 文件...")
    new_content = update_env_file(env_example_content, env_content)
    
    # 写入新内容
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ 完成！已更新 {ENV_FILE}")
    print(f"   备份文件：{backup_file}")
    print("\n提示：请检查更新后的 .env 文件，确保配置正确。")
    
    return 0


if __name__ == '__main__':
    exit(main())

