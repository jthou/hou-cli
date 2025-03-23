
from langchain_ollama import OllamaLLM
from langchain.chat_models import ChatOllama
from langchain import PromptTemplate, LLMChain
from langchain.agents import load_tools, initialize_agent, AgentType


def dynamic_prompt(question):
    llm = OllamaLLM(model="deepseek-r1:14b")  # 使用新的 OllamaLLM 类

    # 定义提示模板，但注意必须构造 PromptTemplate 对象
    prompt_template = PromptTemplate(
        template="""
        Question: {question}
        请一步一步的思考，然后给出答案。用中文回答，回答的时候请列出详细的步骤。
        Answer: 
        """,
        input_variables=["question"]  # 声明模板中用到的变量
    )

    # 创建 LLM Chain
    llm_chain = LLMChain(prompt=prompt_template, llm=llm, verbose=True)

    # 运行链以生成答案
    response = llm_chain.run({"question": question})
    print(response)
    return response

def dynamic_prompt_with_wikipedia(question):
    llm = OllamaLLM(model="deepseek-r1:14b")  # 使用新的 OllamaLLM 类
    tools = load_tools(["wikipedia", "llm-math"], llm=llm)
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # 捕获并处理异常
    try:
        response = agent.run(question)
        print("Answer:", response)
    except OutputParserException as e:
        print("解析 LLM 输出时失败!")
        print("LLM 原始输出：", e.llm_output)

    # run and get the response
    response = agent.run(question)    
    print(response)
    return response