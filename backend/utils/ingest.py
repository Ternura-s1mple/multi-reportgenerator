# backend/utils/ingest.py (更新后的版本)

import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
import sys

# --- 配置 ---
# 使用 pathlib 和 __file__ 来健壮地定位路径
# Path(__file__) -> 当前文件(.../backend/utils/ingest.py)的路径
# .parent -> .../backend/utils/
# .parent.parent -> .../backend/ (这是我们需要的后端根目录)
BACKEND_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BACKEND_DIR / "knowledge_base"
CHROMA_COLLECTION_NAME = "local_knowledge_base"
SENTENCE_MODEL = 'all-MiniLM-L6-v2'

# 将项目根目录添加到Python的搜索路径中，以解决潜在的导入问题
sys.path.append(str(BACKEND_DIR.parent))

print("--- 开始注入本地知识库 ---")
print(f"知识库目录: {KNOWLEDGE_BASE_DIR}")

def main():
    # 1. 加载所有文档
    print(f"正在从 '{KNOWLEDGE_BASE_DIR}' 目录加载文档...")
    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"错误：知识库目录 '{KNOWLEDGE_BASE_DIR}' 不存在。请先创建并添加文件。")
        return
        
    loader = DirectoryLoader(
        str(KNOWLEDGE_BASE_DIR),
        glob="**/*.*",
        loader_map={".pdf": PyPDFLoader},
        show_progress=True,
        use_multithreading=True
    )
    documents = loader.load()
    if not documents:
        print("错误：在知识库目录中没有找到任何文档。请先添加文件。")
        return
    print(f"加载了 {len(documents)} 份文档。")

    # 2. 分割文档为小块 (Chunks)
    print("正在将文档分割成小块...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"文档被分割为 {len(chunks)} 个小块。")

    # 3. 创建向量并存入 ChromaDB
    print("正在加载向量模型并创建向量...")
    try:
        model = SentenceTransformer(SENTENCE_MODEL, cache_folder=str(BACKEND_DIR / '.cache'))
        chroma_client = chromadb.Client()
        
        collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        
        collection.add(
            documents=[chunk.page_content for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
            ids=[f"chunk_{i}" for i in range(len(chunks))]
        )
        print("✅ 知识库注入成功！")
        print(f"集合 '{CHROMA_COLLECTION_NAME}' 中现在有 {collection.count()} 个向量。")

    except Exception as e:
        print(f"❌ 注入过程中发生错误: {e}")

if __name__ == "__main__":
    main()