// frontend/src/HistoryPage.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

// --- 新增：导入下载工具函数 ---
import { downloadMarkdownFile } from './utils/downloader';

const API_URL = 'http://127.0.0.1:8000';

function HistoryPage() {
    const [themes, setThemes] = useState([]);
    const [selectedTheme, setSelectedTheme] = useState(null);
    const [reports, setReports] = useState([]);
    const [selectedReportContent, setSelectedReportContent] = useState('');

     // --- 新增 state: 用于保存当前查看报告的元数据 ---
    const [selectedReportMeta, setSelectedReportMeta] = useState(null);

    useEffect(() => {
        // 组件加载时获取所有主题
        axios.get(`${API_URL}/api/themes`).then(response => {
            setThemes(response.data);
        });
    }, []);

    const handleThemeClick = (theme) => {
        setSelectedTheme(theme);
        setSelectedReportContent(''); // 清空旧内容
        setSelectedReportMeta(null); // 清空元数据
        axios.get(`${API_URL}/api/reports/${theme}`).then(response => {
            setReports(response.data);
        });
    };

 const handleReportClick = (report) => { 
    setSelectedReportMeta(report); 
    axios.get(`${API_URL}/api/report-content/${report.id}`).then(response => {
        setSelectedReportContent(response.data.content);
    });
};

    // --- 新增：处理下载历史文件的函数 ---
    const handleDownloadHistory = () => {
        if (!selectedReportMeta || !selectedReportContent) {
            alert("没有可下载的内容！");
            return;
        }
        const filename = `History_${selectedReportMeta.theme}_${selectedReportMeta.model_name}_${new Date(selectedReportMeta.saved_at).toISOString()}.md`;
        downloadMarkdownFile(selectedReportContent, filename);
    };

   
    return (
        <div style={{ display: 'flex', height: 'calc(100vh - 40px)', fontFamily: 'sans-serif' }}>
            {/* 左侧栏 */}
            <div style={{ width: '400px', borderRight: '1px solid #ccc', padding: '10px', overflowY: 'auto' }}>
                <h2>主题列表</h2>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    {themes.map(theme => (
                        <li key={theme} onClick={() => handleThemeClick(theme)} style={{ padding: '10px', cursor: 'pointer', background: selectedTheme === theme ? '#e0e0e0' : 'transparent', borderRadius: '4px' }}>
                            {theme}
                        </li>
                    ))}
                </ul>
                {selectedTheme && (
                    <>
                        <hr />
                        <h3>{selectedTheme} 下的报告</h3>
                        <ul style={{ listStyle: 'none', padding: 0 }}>
                            {reports.map(report => (
                                // --- 修改：传入整个 report 对象 ---
                                <li key={report.id} onClick={() => handleReportClick(report)} style={{ padding: '10px', border: '1px solid #eee', marginBottom: '5px', cursor: 'pointer', borderRadius: '4px' }}>
                                    <div><strong>模型:</strong> {report.model_name}</div>
                                    <div><strong>时间:</strong> {new Date(report.saved_at).toLocaleString()}</div>
                                </li>
                            ))}
                        </ul>
                    </>
                )}
            </div>
            {/* 右侧栏 */}
            <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
                {/* --- 修改：当有内容时，显示下载按钮 --- */}
                {selectedReportContent ? (
                    <>
                        <button onClick={handleDownloadHistory} style={{ float: 'right', padding: '8px 16px', background: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                            下载这个版本
                        </button>
                        <ReactMarkdown>{selectedReportContent}</ReactMarkdown>
                    </>
                ) : (
                    <div style={{ color: '#888', textAlign: 'center', marginTop: '50px' }}>请从左侧选择一个主题和报告来查看内容</div>
                )}
            </div>
        </div>
    );
}

export default HistoryPage;