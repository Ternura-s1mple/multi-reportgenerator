import docx
from fastapi import UploadFile
import io

def parse_docx_template(file: UploadFile) -> str:
    """
    解析上传的Word(.docx)文件，提取其全部文本内容。
    """
    try:
        # UploadFile.file 是一个文件类对象，需要用 io.BytesIO 读取
        file_bytes = io.BytesIO(file.read())
        document = docx.Document(file_bytes)
        
        full_text = []
        for para in document.paragraphs:
            # 保留段落结构
            if para.text.strip(): # 忽略空段落
                full_text.append(para.text)
        
        print(f"成功解析Word模板，文件名: {file.filename}")
        # 用换行符连接所有段落，形成完整的模板内容
        return "\n".join(full_text)
    except Exception as e:
        print(f"❌ 解析Word文件时出错: {e}")
        return "" # 返回空字符串表示失败