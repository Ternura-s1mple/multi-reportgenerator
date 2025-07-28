# debug_chroma.py

import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
import sys

# 添加后端目录到搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

print("--- ChromaDB 数据库状态深度检查脚本 ---")

# --- 配置 ---
DB_PATH = str(BACKEND_DIR / ".chroma_db")
COLLECTION_NAME = "reports_collection" # 我们要检查的是这个集合
MODEL_NAME = 'all-MiniLM-L6-v2'

try:
    # 1. 连接到持久化的数据库
    print(f"正在连接到数据库: {DB_PATH}")
    client = chromadb.PersistentClient(path=DB_PATH)

    # 2. 获取集合
    print(f"正在获取集合: '{COLLECTION_NAME}'")
    collection = client.get_collection(name=COLLECTION_NAME)

    # 3. 查看集合中的条目总数
    count = collection.count()
    print(f"\n[检查点 1] 集合 '{COLLECTION_NAME}' 中的条目总数: {count}")

    if count > 0:
        # 4. “窥视”集合中的所有数据
        print("\n[检查点 2] 集合中的所有数据 (get):")
        get_result = collection.get() # get()会返回所有数据

        for i in range(len(get_result['ids'])):
            print(f"  - ID: {get_result['ids'][i]}")
            print(f"    Metadata: {get_result['metadatas'][i]}")
            # 我们也看看向量本身的前几个维度
            embedding_preview = str(get_result['embeddings'][i][:5]) if get_result['embeddings'] else "N/A"
            print(f"    Embedding (前5维): {embedding_preview}...")
    else:
        print("\n数据库为空，无法进行测试。")
        print("--- 检查结束 ---")
        exit()

    # 5. 执行一次手动查询测试
    print("\n[检查点 3] 执行手动相似度搜索测试...")
    test_topic = "中国民族历史偏见"
    print(f"    测试主题: '{test_topic}'")

    print("    正在加载向量模型...")
    sentence_model = SentenceTransformer(MODEL_NAME, cache_folder=str(BACKEND_DIR / '.cache'))

    print("    正在生成查询向量...")
    embedding = sentence_model.encode(test_topic).tolist()

    print("    正在执行 collection.query()...")
    query_results = collection.query(
        query_embeddings=[embedding],
        n_results=3
    )

    print("\n--- ✅ 查询完成！---")
    print("查询结果如下:")
    print(query_results)

except Exception as e:
    print(f"\n❌ 检查过程中发生错误: {e}")

print("\n--- 检查结束 ---")