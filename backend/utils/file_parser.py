# backend/utils/file_parser.py (使用unstructured的全新版本)

from fastapi import UploadFile
from unstructured.partition.docx import partition_docx
import tempfile
import os
import asyncio

async def parse_docx_template(file: UploadFile) -> str:
    """
    使用 unstructured 库解析上传的Word(.docx)文件。
    这个版本能够智能地处理段落、标题、表格等多种元素。
    """
    try:
        # unstructured 处理文件路径比处理内存中的对象更稳定，
        # 所以我们先将上传的文件临时保存到磁盘上。
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            # 读取上传文件的内容并写入临时文件
            content_bytes = await file.read()
            tmp.write(content_bytes)
            tmp_path = tmp.name

        print(f"文件已临时保存至: {tmp_path}")
        print(f"开始使用 unstructured 解析文件: {file.filename}...")

        # 使用 unstructured 的 partition_docx 函数来解析文件
        elements = await asyncio.to_thread(partition_docx, filename=tmp_path)

        # 将解析出的所有元素拼接成一个字符串
        # 每个元素之间用两个换行符隔开，以保持基本的段落结构
        full_text = "\n\n".join([el.text for el in elements])

        print(f"✅ 使用 unstructured 解析成功！提取内容长度: {len(full_text)}")

    except Exception as e:
        print(f"❌ 使用 unstructured 解析时出错: {e}")
        full_text = ""
    finally:
        # 确保删除临时文件
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)
            print(f"已删除临时文件: {tmp_path}")

    return full_text