import sys
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

def load_pdf(file_path):
    if not os.path.exists(file_path):
        print("文件不存在")
        return None
    
    loader = PDFPlumberLoader(file_path)
    docs = loader.load()
    return docs

def vectorize_docs(docs):
    local_embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectorstore = Chroma.from_documents(documents=docs, embedding=local_embeddings)
    return vectorstore

def summarize_pdf(file_path):
    docs = load_pdf(file_path)
    if docs is None:
        print("文件不存在")
        return
    
    vectorstore = vectorize_docs(docs)

    # 打印向量存储中的所有文档
    all_docs = vectorstore.get()
    print(len(all_docs))
    print("docs print done")

    return

    # 创建一个提示模板
    prompt_template = """
    请总结以下文档的主要内容。请用中文回答，并包含以下方面：
    1. 文档的主要主题
    2. 关键要点
    3. 重要结论或建议
    
    文档内容：
    {text}
    """ 

    # 初始化 Ollama 模型
    model = ChatOllama(
        model="deepseek-r1:14b",
        temperature=0.7
    )
    # 创建一个提示模板
    prompt = ChatPromptTemplate.from_template(prompt_template)

    # 创建处理链
    chain = prompt | model | StrOutputParser()

    # 处理每个分块并生成总结
    summaries = []
    for split in all_splits:
        print("--------------------------------")
        print("split.page_content", split.page_content)
        summary = chain.invoke({"text": split.page_content})
        print("summary", summary)
        summaries.append(summary)    
    
    print("done")
    
    