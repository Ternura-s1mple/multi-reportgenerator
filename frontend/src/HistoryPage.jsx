// frontend/src/HistoryPage.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_URL = 'http://127.0.0.1:8000';

function HistoryPage() {
    const [themes, setThemes] = useState([]);
    const [selectedTheme, setSelectedTheme] = useState(null);
    const [reports, setReports] = useState([]);
    const [selectedReportContent, setSelectedReportContent] = useState('');

    useEffect(() => {
        // 组件加载时获取所有主题
        axios.get(`${API_URL}/api/themes`).then(response => {
            setThemes(response.data);
        });
    }, []);

    const handleThemeClick = (theme) => {
        setSelectedTheme(theme);
        setSelectedReportContent(''); // 清空旧内容
        axios.get(`${API_URL}/api/reports/${theme}`).then(response => {
            setReports(response.data);
        });
    };

    const handleReportClick = (reportId) => {
        axios.get(`${API_URL}/api/report-content/${reportId}`).then(response => {
            setSelectedReportContent(response.data.content);
        });
    };

    return (
        <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
            {/* 左侧栏：主题和报告列表 */}
            <div style={{ width: '400px', borderRight: '1px solid #ccc', padding: '10px', overflowY: 'auto' }}>
                <h2>主题列表</h2>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    {themes.map(theme => (
                        <li key={theme} onClick={() => handleThemeClick(theme)} style={{ padding: '10px', cursor: 'pointer', background: selectedTheme === theme ? '#e0e0e0' : 'transparent' }}>
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
                                <li key={report.id} onClick={() => handleReportClick(report.id)} style={{ padding: '10px', border: '1px solid #eee', marginBottom: '5px', cursor: 'pointer' }}>
                                    <div><strong>模型:</strong> {report.model_name}</div>
                                    <div><strong>时间:</strong> {new Date(report.saved_at).toLocaleString()}</div>
                                </li>
                            ))}
                        </ul>
                    </>
                )}
            </div>
            {/* 右侧栏：报告内容 */}
            <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
                {selectedReportContent ? (
                    <ReactMarkdown>{selectedReportContent}</ReactMarkdown>
                ) : (
                    <div style={{ color: '#888', textAlign: 'center', marginTop: '50px' }}>请从左侧选择一个主题和报告来查看内容</div>
                )}
            </div>
        </div>
    );
}

export default HistoryPage;