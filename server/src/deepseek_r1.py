import sys
import os
from openai import OpenAI

def make_deepseek_client():
    # get api key from environment variable
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        raise ValueError("DeepSeek API key is not set.")
        return None

    base_url = "https://api.deepseek.com"
    return OpenAI(api_key=api_key, base_url=base_url)

def get_deepseek_response(prompt, client):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

from ollama import chat
from ollama import ChatResponse
def get_deepseek_14b_local_response(prompt):
    response = chat(model='deepseek-r1:14b', messages=[
    {
        'role': 'user',
        'content': prompt,
        'stream': False
    }
    ])

    return response['message']['content']

def get_deepseek_14b_local_response_stream(prompt):
    stream = chat(
        model='deepseek-r1:14b',
        messages=[{'role': 'user', 'content': prompt}],
        stream=True,
    )

    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)