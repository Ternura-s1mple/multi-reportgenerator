// frontend/src/ReportGenerator.jsx (最终完整版)

import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_URL = 'http://127.0.0.1:8000'; // 后端地址

function ReportGenerator() {
    const [topic, setTopic] = useState('分析2025年新能源汽车市场的机遇与挑战');
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState(0);

    // --- 新增 state: 用于存储和显示相似报告 ---
    const [similarReports, setSimilarReports] = useState([]);
    const [showSimilar, setShowSimilar] = useState(false);

    // --- 修改: 将核心生成逻辑拆分为一个独立函数 ---
    const proceedToGenerate = async () => {
        setShowSimilar(false); // 如果相似报告提示框是打开的，先关掉
        setLoading(true);
        setReports([]);
        try {
            const response = await axios.post(`${API_URL}/api/generate-reports`, { topic });
            setReports(response.data.reports);
            setActiveTab(0);
        } catch (error) {
            console.error('生成报告时出错:', error);
            alert('生成报告失败，请检查后端服务是否开启。');
        }
        setLoading(false);
    };

    // --- 修改: 这是"生成/检索"按钮现在调用的主函数 ---
    const handleGenerateClick = async () => {
        if (!topic) {
            alert('请输入一个主题！');
            return;
        }
        // 第一步：先查找相似项
        setLoading(true);
        setReports([]); // 清空旧的生成结果
        try {
            const simResponse = await axios.post(`${API_URL}/api/find-similar`, { topic });
            setLoading(false);

            if (simResponse.data && simResponse.data.length > 0) {
                // 如果找到了相似项，就显示提示框
                setSimilarReports(simResponse.data);
                setShowSimilar(true);
            } else {
                // 如果没有相似项，直接进入生成流程
                proceedToGenerate();
            }
        } catch (error) {
            setLoading(false);
            console.error('检索相似报告时出错:', error);
            // 即使检索失败，也应该继续生成
            proceedToGenerate();
        }
    };

    // 保存函数保持不变
    const handleSave = async () => {
        const reportToSave = reports[activeTab];
        if (!reportToSave) return;
        try {
            const response = await axios.post(`${API_URL}/api/save-report`, {
                topic: topic,
                model_name: reportToSave.model_name,
                content: reportToSave.content,
            });
            alert(`保存成功！文件路径: ${response.data.path}`);
        } catch (error) {
            console.error('保存报告时出错:', error);
            alert('保存失败！');
        }
    };

    return (
        <div style={{ fontFamily: 'sans-serif', padding: '20px', maxWidth: '1000px', margin: 'auto' }}>
            <h1>多模型报告生成器</h1>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="输入你的报告主题..."
                    style={{ flexGrow: 1, padding: '10px', fontSize: '16px' }}
                    disabled={loading}
                />
                {/* --- 修改: 调用新的 handleGenerateClick 函数 --- */}
                <button onClick={handleGenerateClick} disabled={loading} style={{ padding: '10px 20px', fontSize: '16px' }}>
                    {loading ? '处理中...' : '生成/检索报告'}
                </button>
            </div>
            
            {/* --- 新增：相似报告推荐模块 --- */}
            {showSimilar && (
                <div style={{ border: '2px dashed #007bff', padding: '20px', marginBottom: '20px', borderRadius: '8px', background: '#f8f9fa' }}>
                    <h3>发现相似的历史报告！</h3>
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {similarReports.map(report => (
                            <li key={report.id} style={{ marginBottom: '10px', background: 'white', padding: '10px', borderRadius: '4px' }}>
                                <strong>主题:</strong> {report.original_topic} <br />
                                <small><strong>模型:</strong> {report.model_name} | <strong>保存于:</strong> {new Date(report.saved_at).toLocaleString()}</small>
                            </li>
                        ))}
                    </ul>
                    <p>您可以前往“历史记录”页面查看详情，或选择重新生成。</p>
                    <button onClick={proceedToGenerate} style={{ padding: '10px', background: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                        仍然重新生成
                    </button>
                    <button onClick={() => setShowSimilar(false)} style={{ padding: '10px', marginLeft: '10px', cursor: 'pointer' }}>
                        关闭
                    </button>
                </div>
            )}


            {/* 当有新生成的报告时，显示结果区域 (这部分保持不变) */}
            {reports.length > 0 && (
                <div className="results-container">
                    <div className="tabs" style={{ display: 'flex', borderBottom: '1px solid #ccc' }}>
                        {reports.map((report, index) => (
                            <button
                                key={report.model_name}
                                onClick={() => setActiveTab(index)}
                                style={{
                                    padding: '10px 15px',
                                    border: 'none',
                                    background: activeTab === index ? '#f0f0f0' : 'transparent',
                                    cursor: 'pointer',
                                    borderBottom: activeTab === index ? '3px solid #007bff' : '3px solid transparent',
                                    fontSize: '16px'
                                }}
                            >
                                {report.model_name}
                            </button>
                        ))}
                    </div>

                    <div className="content" style={{ marginTop: '20px', border: '1px solid #eee', padding: '0 20px', borderRadius: '5px', background: '#fafafa' }}>
                       <ReactMarkdown>{reports[activeTab].content}</ReactMarkdown>
                    </div>
                    
                    <button
                        onClick={handleSave}
                        style={{ marginTop: '20px', padding: '10px 20px', background: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontSize: '16px' }}
                    >
                        采用此方案并保存
                    </button>
                </div>
            )}
        </div>
    );
}

export default ReportGenerator;