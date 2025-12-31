from langchain_community.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def summarize_pdf(pdf_path):
    # 加载 PDF 文件
    loader = PDFPlumberLoader(pdf_path)
    docs = loader.load()
    
    # 分割文档
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    splits = text_splitter.split_documents(docs)
    
    # 初始化 Ollama 模型
    model = ChatOllama(
        model="deepseek-r1:14b",
        temperature=0.7
    )
    
    # 创建总结提示模板
    prompt = ChatPromptTemplate.from_template("""
    请总结以下文档的主要内容。请用中文回答，并包含以下方面：
    1. 文档的主要主题
    2. 关键要点
    3. 重要结论或建议
    
    文档内容：
    {text}
    """)
    
    # 创建处理链
    chain = prompt | model | StrOutputParser()
    
    # 处理每个分块并生成总结
    summaries = []
    for split in splits:
        summary = chain.invoke({"text": split.page_content})
        summaries.append(summary)
    
    # 合并所有总结
    final_prompt = ChatPromptTemplate.from_template("""
    请将以下多个总结合并成一个连贯的总结。请用中文回答，并保持逻辑性和完整性：
    
    {summaries}
    """)
    
    final_chain = final_prompt | model | StrOutputParser()
    final_summary = final_chain.invoke({"summaries": "\n\n".join(summaries)})
    
    return final_summary

if __name__ == "__main__":
    # 使用示例
    pdf_path = "/Users/jintinghou/Downloads/华晓军_简历_简式_中文.pdf"  # 替换为你的 PDF 文件路径
    summary = summarize_pdf(pdf_path)
    print("\n=== PDF 总结 ===")
    print(summary) 