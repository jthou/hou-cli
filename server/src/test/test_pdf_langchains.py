import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from pdf_langchains import *

def test_summarize_pdf():
    file_path = "/Users/jintinghou/Downloads/侯金亭的个人简历.pdf"
    summarize_pdf(file_path)

if __name__ == "__main__":
    pytest.main()

