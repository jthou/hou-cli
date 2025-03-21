# use pytest to test the functions code generation
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from deepseek_r1 import *

def test_make_deepseek_client_raises_value_error():
    with pytest.raises(ValueError, match="DeepSeek API key is not set."):
        make_deepseek_client()

def test_make_deepseek_client():
    # set the deepseek api key in the environment
    os.environ['DEEPSEEK_API_KEY'] = 'sk-1649ff7085b8400281c27ae816e752aa'
    client = make_deepseek_client()
    # assert the client is not None
    assert client is not None

@pytest.mark.skip(reason="不能老测，费钱！")
def test_get_deepseek_response():
    # set the deepseek api key in the environment
    os.environ['DEEPSEEK_API_KEY'] = 'sk-1649ff7085b8400281c27ae816e752aa'
    client = make_deepseek_client()
    # test with a simple prompt
    prompt = "中国的首都是哪里？请用中文回答"
    response = get_deepseek_response(prompt, client)
    # assert the response contains the capital of France
    print(response)
    assert "北京" in response

def test_get_deepseek_14b_local_response():
    prompt = "中国的首都是哪里？请用中文回答"
    response = get_deepseek_14b_local_response(prompt)
    # assert the response contains the capital of France
    print(response)
    assert "北京" in response

def test_get_deepseek_14b_local_response_stream():
    prompt = "中国的首都是哪里？请用中文回答"
    response = get_deepseek_14b_local_response_stream(prompt)


if __name__ == "__main__":
    pytest.main()