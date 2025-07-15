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


    // 删除某个主题的处理函数
    const handleDeleteTheme = async (theme, e) => {
        e.stopPropagation(); // 阻止事件冒泡，防止触发 handleThemeClick
        if (window.confirm(`确定要删除主题 "${theme}" 及其下的所有报告吗？此操作不可逆！`)) {
            try {
                await axios.delete(`${API_URL}/api/theme/${theme}`);
                alert(`主题 "${theme}" 已被删除。`);
                // 从前端状态中移除该主题，实现界面即时更新
                setThemes(prevThemes => prevThemes.filter(t => t !== theme));
                if (selectedTheme === theme) {
                    setSelectedTheme(null);
                    setReports([]);
                }
            } catch (error) {
                console.error("删除主题时出错:", error);
                alert("删除主题失败！");
            }
        }
    };

    //：删除单个报告的处理函数
    const handleDeleteReport = async (reportId, e) => {
        e.stopPropagation();
        if (window.confirm(`确定要删除这份报告吗？`)) {
            try {
                await axios.delete(`${API_URL}/api/report/${reportId}`);
                alert(`报告已被删除。`);
                // 从前端状态中移除该报告
                setReports(prevReports => prevReports.filter(r => r.id !== reportId));
            } catch (error) {
                console.error("删除报告时出错:", error);
                alert("删除报告失败！");
            }
        }
    };

   
    return (
        <div style={{ display: 'flex', height: 'calc(100vh - 40px)', fontFamily: 'sans-serif' }}>
            {/* 左侧栏 */}
            <div style={{ width: '400px', borderRight: '1px solid #ccc', padding: '10px', overflowY: 'auto' }}>
                <h2>主题列表</h2>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    {themes.map(theme => (
                        <li key={theme} onClick={() => handleThemeClick(theme)} style={{ padding: '10px', cursor: 'pointer', background: selectedTheme === theme ? '#e0e0e0' : 'transparent', borderRadius: '4px' }}>
                             <span style={{ flexGrow: 1 }}>{theme}</span>
                              {/* 新增删除主题按钮 */}
                            <button onClick={(e) => handleDeleteTheme(theme, e)} style={{ background: 'red', color: 'white', border: 'none', cursor: 'pointer', padding: '2px 6px', borderRadius: '4px' }}>X</button>
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
                                    {/* 新增删除报告按钮 */}
                                    <button 
                                        onClick={(e) => handleDeleteReport(report.id, e)} 
                                        style={{ background: 'salmon', color: 'white', border: 'none', cursor: 'pointer', padding: '2px 8px', borderRadius: '4px', fontSize: '12px', marginLeft: '10px' }}
                                    >
                                     X
                                    </button>
                                    
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