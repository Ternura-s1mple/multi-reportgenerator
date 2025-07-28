# backend/utils/ingest.py (与最终架构同步的完整版)

import os
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
import sys

# --- 配置 ---
# 1. 明确指向后端目录
BACKEND_DIR = Path(__file__).resolve().parent.parent

# 2. 指定您存放本地模型的路径
SENTENCE_MODEL_PATH = Path("/data2/models/bge-base-zh-v1.5")

# 3. 指定知识库目录
KNOWLEDGE_BASE_DIR = BACKEND_DIR / "knowledge_base"

# 4. 指定持久化数据库的路径和集合名称 (与 main.py 保持一致)
CHROMA_DB_PATH = str(BACKEND_DIR / ".chroma_db")
CHROMA_COLLECTION_NAME = "local_knowledge_base"

# 将项目根目录添加到Python的搜索路径中
sys.path.append(str(BACKEND_DIR.parent))

print("--- 开始注入本地知识库 ---")
print(f"知识库目录: {KNOWLEDGE_BASE_DIR}")
print(f"向量模型路径: {SENTENCE_MODEL_PATH}")
print(f"向量数据库路径: {CHROMA_DB_PATH}")

def main():
    print(f"正在从 '{KNOWLEDGE_BASE_DIR}' 目录加载文档...")
    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"错误：知识库目录 '{KNOWLEDGE_BASE_DIR}' 不存在。")
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
        print("错误：在知识库目录中没有找到任何文档。")
        return
    print(f"加载了 {len(documents)} 份文档。")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(documents)
    print(f"文档被分割为 {len(chunks)} 个小块。")

    # --- 核心修改：使用本地模型路径和持久化数据库 ---
    print("正在加载本地向量模型并创建向量...")
    try:
        # 1. 从本地路径加载模型
        model = SentenceTransformer(str(SENTENCE_MODEL_PATH), cache_folder=str(BACKEND_DIR / '.cache'))
        
        # 2. 手动将所有文本块编码为向量
        print("正在对所有文本块进行向量化...")
        embeddings = model.encode([chunk.page_content for chunk in chunks], show_progress_bar=True)
        print("向量化完成。")

        # 3. 连接到持久化的数据库
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        
        # 4. 获取或创建集合
        collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        
        # 5. 清空旧集合，确保数据最新
        if collection.count() > 0:
            print(f"正在清空旧的 '{CHROMA_COLLECTION_NAME}' 集合...")
            ids_to_delete = collection.get()['ids']
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)

        # 6. 将我们手动计算好的向量存入数据库
        collection.add(
            embeddings=embeddings.tolist(), # 传入计算好的向量
            documents=[chunk.page_content for chunk in chunks], # 同时存入原始文本
            metadatas=[chunk.metadata for chunk in chunks],
            ids=[f"chunk_{i}" for i in range(len(chunks))]
        )
        print("✅ 知识库注入成功！")
        print(f"集合 '{CHROMA_COLLECTION_NAME}' 中现在有 {collection.count()} 个向量。")

    except Exception as e:
        print(f"❌ 注入过程中发生错误: {e}")

if __name__ == "__main__":
    main()