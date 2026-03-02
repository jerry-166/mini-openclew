from langchain_community.tools import ShellTool, ReadFileTool, RequestsGetTool
from langchain_community.utilities import RequestsWrapper
from langchain_experimental.tools import PythonREPLTool
from bs4 import BeautifulSoup
import html2text
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.retrievers import BaseRetriever
from typing import List, Dict, Any


class EnhancedRequestsGetTool(RequestsGetTool):
    """增强的网络信息获取工具，返回清洗后的Markdown内容"""

    def __init__(self, **kwargs):
        # 初始化RequestsWrapper（不传递allow_dangerous_requests参数）
        # 从kwargs中分离出allow_dangerous_requests参数
        allow_dangerous = kwargs.pop('allow_dangerous_requests', False)
        requests_wrapper = RequestsWrapper()
        super().__init__(requests_wrapper=requests_wrapper, allow_dangerous_requests=allow_dangerous)

    def _run(self, url: str) -> str:
        # 调用父类方法获取原始HTML
        html_content = super()._run(url)

        # 使用BeautifulSoup清洗HTML
        soup = BeautifulSoup(html_content, 'html.parser')  # features: html.parser, lxml, html5lib

        # 移除脚本和样式(去掉<script></script>和style)
        for script in soup(['script', 'style']):
            script.decompose()  # 移除当前节点

        # 转换为Markdown
        converter = html2text.HTML2Text()
        converter.ignore_links = False
        markdown_content = converter.handle(str(soup))

        return markdown_content


class RAGRetrievalTool:
    """RAG检索工具，支持混合检索"""

    def __init__(self, knowledge_dir: str = "knowledge", storage_dir: str = "storage"):
        self.knowledge_dir = knowledge_dir
        self.storage_dir = storage_dir
        self.index = None
        self._initialize_index()

    def _initialize_index(self):
        """初始化索引"""
        # 确保目录存在
        os.makedirs(self.knowledge_dir, exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)

        # 加载文档
        try:
            documents = SimpleDirectoryReader(self.knowledge_dir).load_data()
            if documents:
                self.index = VectorStoreIndex.from_documents(documents)
                # 持久化索引
                self.index.storage_context.persist(persist_dir=self.storage_dir)
        except Exception as e:
            print(f"初始化索引失败: {e}")

    def run(self, query: str) -> str:
        """执行检索"""
        if not self.index:
            return "索引尚未初始化，请先添加文档到knowledge目录"

        # 执行检索
        query_engine = self.index.as_query_engine()
        response = query_engine.query(query)

        return str(response)


def get_core_tools(root_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) -> List[Any]:
    """获取核心工具列表"""
    tools = []

    # 1. 命令行操作工具
    shell_tool = ShellTool(root_dir=root_dir)
    shell_tool.name = "terminal"
    tools.append(shell_tool)

    # 2. Python代码解释器
    python_repl_tool = PythonREPLTool()
    python_repl_tool.name = "python_repl"
    tools.append(python_repl_tool)

    # 3. Fetch网络信息获取
    fetch_tool = EnhancedRequestsGetTool(allow_dangerous_requests=True)
    fetch_tool.name = "fetch_url"
    tools.append(fetch_tool)

    # 4. 文件读取工具
    read_file_tool = ReadFileTool(root_dir=root_dir)
    read_file_tool.name = "read_file"
    tools.append(read_file_tool)

    # 5. RAG检索工具
    rag_tool = RAGRetrievalTool()
    # 包装为LangChain工具格式
    from langchain_core.tools import Tool
    rag_langchain_tool = Tool(
        name="search_knowledge_base",
        func=rag_tool.run,
        description="用于检索知识库中的信息，输入查询语句"
    )
    tools.append(rag_langchain_tool)

    return tools
