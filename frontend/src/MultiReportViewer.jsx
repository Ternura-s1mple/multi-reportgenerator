// frontend/src/MultiReportViewer.jsx (功能完整版)

import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import { downloadMarkdownFile } from './utils/downloader'; // 导入下载工具

const API_URL = 'http://127.0.0.1:8000';

// 组件现在接收 reports 和 topic 两个 props
function MultiReportViewer({ reports, topic }) {
    const [activeTab, setActiveTab] = useState(0);

    if (!reports || reports.length === 0) {
        return <div>没有可展示的报告。</div>;
    }

    // --- 新增：保存报告的函数 ---
    const handleSave = async () => {
        const reportToSave = reports[activeTab];
        if (!reportToSave) return;
        try {
            await axios.post(`${API_URL}/api/save-report`, {
                topic: topic, // 使用从父组件传入的topic
                model_name: reportToSave.model_name,
                content: reportToSave.content,
            });
            alert(`方案 [${reportToSave.model_name}] 已成功保存！`);
        } catch (error) {
            console.error('保存报告时出错:', error);
            alert('保存失败！');
        }
    };

    // --- 新增：下载报告的函数 ---
    const handleDownload = () => {
        const reportToDownload = reports[activeTab];
        if (!reportToDownload) return;

        const safeTopic = topic.slice(0, 20).replace(/[/\\?%*:|"<>]/g, '_');
        const filename = `Report_${safeTopic}_${reportToDownload.model_name}.md`;

        downloadMarkdownFile(reportToDownload.content, filename);
    };

    return (
        <div className="multi-report-viewer">
            <div className="tabs" style={{ display: 'flex', borderBottom: '1px solid #ccc', marginBottom: '15px' }}>
                {reports.map((report, index) => (
                    <button
                        key={report.model_name}
                        onClick={() => setActiveTab(index)}
                        style={{
                            padding: '10px 15px', border: 'none', cursor: 'pointer', fontSize: '14px',
                            background: activeTab === index ? '#f0f0f0' : 'transparent',
                            borderBottom: activeTab === index ? '3px solid #007bff' : '3px solid transparent',
                        }}
                    >
                        {report.model_name}
                    </button>
                ))}
            </div>
            <div className="content">
                <ReactMarkdown>{reports[activeTab].content}</ReactMarkdown>
            </div>

            {/* --- 新增：操作按钮区域 --- */}
            <div style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '15px' }}>
                <button
                    onClick={handleSave}
                    style={{ padding: '8px 16px', background: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '14px' }}
                >
                    采用此方案并保存
                </button>
                <button
                    onClick={handleDownload}
                    style={{ marginLeft: '10px', padding: '8px 16px', background: '#007bff', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '14px' }}
                >
                    下载此版本
                </button>
            </div>
        </div>
    );
}

export default MultiReportViewer;