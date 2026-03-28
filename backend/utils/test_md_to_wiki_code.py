#!/usr/bin/env python3
"""md_to_wiki 代码块转换测试"""
from backend.utils.md_to_wiki import md_to_wiki


def test_code_block_to_syntaxhighlight():
    md = """## 标题

这是一段文字，包含 ```python
def foo():
    **bold** 和 *italic* 不应被转换
    return True
```

正文继续。
"""
    out = md_to_wiki(md)
    assert '<syntaxhighlight lang="python">' in out
    assert "**bold**" in out
    assert "*italic*" in out
    assert "'''bold'''" not in out  # 不应被 emphasis 破坏
    assert "''italic''" not in out


def test_code_block_no_lang():
    md = """``` 
plain text
```
"""
    out = md_to_wiki(md)
    assert '<syntaxhighlight lang="text">' in out
    assert "plain text" in out


def test_markdown_image_to_wiki_file_defaults():
    out = md_to_wiki("![](Foo.png)\n![ cap ]( Bar.jpg )")
    assert "[[File:Foo.png|500px|center|frame]]" in out
    assert "[[File:Bar.jpg|500px|center|frame|cap]]" in out


if __name__ == "__main__":
    test_code_block_to_syntaxhighlight()
    test_code_block_no_lang()
    print("OK")
