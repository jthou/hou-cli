#!/usr/bin/env python3
"""测试命令补全功能"""
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

class TestCompleter(Completer):
    """测试补全器"""
    
    def __init__(self):
        self.commands = ['list', 'search', 'show', 'delete', 'switch', 'restore', 'summary', 'clear', 'help']
    
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        # 只处理以 / 开头的命令
        if not text.startswith('/'):
            return
        
        # 提取命令部分
        command_part = text[1:].strip()
        
        if not command_part:
            # 输入了 /，显示所有命令
            for cmd in self.commands:
                yield Completion(
                    f"/{cmd}",
                    start_position=-1,
                    display=f"/{cmd}",
                    display_meta=f"Command: {cmd}"
                )
        else:
            # 输入了部分命令
            partial = command_part.split()[0].lower()
            for cmd in self.commands:
                if cmd.startswith(partial):
                    yield Completion(
                        cmd,
                        start_position=-len(partial),
                        display=f"/{cmd}",
                        display_meta=f"Command: {cmd}"
                    )

def main():
    print("测试命令补全功能")
    print("=" * 50)
    print("输入 '/' 然后按 Tab 查看所有命令")
    print("输入 '/l' 然后按 Tab 应该补全为 '/list'")
    print("输入 'exit' 退出")
    print("=" * 50)
    
    completer = TestCompleter()
    session = PromptSession(
        completer=completer,
        complete_style='multi-column',
        complete_in_thread=False,
    )
    
    while True:
        try:
            text = session.prompt("▸ ")
            if text.lower() in ['exit', 'quit']:
                break
            print(f"你输入了: {text}")
        except KeyboardInterrupt:
            break
        except EOFError:
            break

if __name__ == '__main__':
    main()

