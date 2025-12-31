import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from dynamic_prompt import *
import pytest

@pytest.mark.skip(reason="太慢了")
def test_dynamic_prompt():
    question = "中英人寿2023年各渠道的销售业绩是多少？"
    response = dynamic_prompt(question)
    assert response is not None

def test_dynamic_prompt_with_wikipedia():
    question = "北京的面积是多少？"
    print(question)
    response = dynamic_prompt_with_wikipedia(question)
    assert response is not None

def test_dynamic_prompt_with_wikipedia_and_math():
    question = "北京的面积加上上海的面积是多少？"
    print(question)
    response = dynamic_prompt_with_wikipedia(question)
    assert response is not None


if __name__ == "__main__":
    pytest.main()