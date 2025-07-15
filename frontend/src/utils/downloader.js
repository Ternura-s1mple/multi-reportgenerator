// frontend/src/utils.js

/**
 * 触发浏览器下载文本内容为文件。
 * @param {string} content - 要下载的文件内容。
 * @param {string} filename - 下载时建议的文件名。
 */
export function downloadMarkdownFile(content, filename) {
  // 1. 创建一个 Blob 对象，这是文件内容的二进制表示
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });

  // 2. 创建一个指向该 Blob 的临时 URL
  const url = URL.createObjectURL(blob);

  // 3. 创建一个隐藏的 <a> 标签
  const link = document.createElement('a');
  link.href = url;
  link.download = filename; // 设置下载的文件名
  link.style.display = 'none'; // 确保它在页面上不可见

  // 4. 将 <a> 标签添加到页面，模拟点击，然后移除
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // 5. 释放创建的临时 URL，以节省内存
  URL.revokeObjectURL(url);
}