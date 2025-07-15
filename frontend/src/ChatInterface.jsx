// frontend/src/ChatInterface.jsx (最终完整版)

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import MultiReportViewer from './MultiReportViewer';
import './ChatInterface.css';

const API_URL = 'http://127.0.0.1:8000';

// vvvv 从 props 中接收 messages 和 setMessages vvvv
function ChatInterface({ messages, setMessages }) {
    // --- 删除了这里的 useState for messages，状态已被提升到 App.jsx ---

    // 这些状态是本组件私有的，不需要提升，所以保留
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [selectedModel, setSelectedModel] = useState('gemini');
    const [similarReports, setSimilarReports] = useState([]);
    const [showSimilar, setShowSimilar] = useState(false);

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage = { role: 'user', content: input };
        const newMessages = [...messages, userMessage];
        const submittedInput = input;

        // --- 修改：现在使用从 props 传来的 setMessages ---
        setMessages(newMessages);
        setInput('');
        setIsLoading(true);

        try {
            const simResponse = await axios.post(`${API_URL}/api/find-similar`, { topic: submittedInput });
            if (simResponse.data && simResponse.data.length > 0) {
                setSimilarReports(simResponse.data);
                setShowSimilar(true);
                setIsLoading(false);
                return;
            }
        } catch (error) {
            console.error("检索相似报告时出错:", error);
        }

        if (selectedModel === 'mixed-mode') {
            try {
                const response = await axios.post(`${API_URL}/api/reports/generate-mixed`, {
                    topic: submittedInput,
                });
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: response.data.reports,
                    isMultiReport: true,
                    topic: submittedInput
                }]);
            } catch (error) {
                console.error('混合模式生成报告时出错:', error);
                setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，混合模式生成失败。' }]);
            } finally {
                setIsLoading(false);
            }
        } else {
            try {
                setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
                const response = await fetch(`${API_URL}/api/chat/completions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: newMessages, model: selectedModel }),
                });

                if (!response.body) return;
                const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    setMessages(prev => {
                        const lastMessage = prev[prev.length - 1];
                        const updatedLastMessage = { ...lastMessage, content: lastMessage.content + value };
                        return [...prev.slice(0, -1), updatedLastMessage];
                    });
                }
            } catch (error) {
                console.error('Error fetching stream:', error);
                setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，连接时出现问题。' }]);
            } finally {
                setIsLoading(false);
            }
        }
    };
    
    // 这个函数是当用户在“相似推荐”弹窗中点击“仍然生成”时调用的
    const proceedToGenerate = () => {
        setShowSimilar(false); // 先隐藏弹窗
        // 这里的逻辑和 handleSubmit 很像，但不包含 find-similar 的部分
        // 为了简化，我们暂时让用户点击“仍然生成”时，重新触发一次完整的 handleSubmit
        // 更好的做法是把生成逻辑抽成独立函数，这里为了快速修复先这样做
        handleSubmit({ preventDefault: () => {} }); // 传递一个假的 event 对象
    };

    return (
        <div className="chat-container">
            <div className="model-selector" style={{ padding: '10px', borderBottom: '1px solid #ccc', background: '#f9f9f9', textAlign: 'center' }}>
                <label htmlFor="model-select" style={{ marginRight: '10px', fontWeight: 'bold' }}>当前模式: </label>
                <select id="model-select" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} style={{ padding: '5px' }}>
                    <option value="gemini">Gemini (对话)</option>
                    <option value="deepseek">DeepSeek (对话)</option>
                    <option value="qwen">Qwen 2.5 (本地对话)</option>
                    <option value="mixed-mode">混合模式 (生成多份报告)</option>
                </select>
            </div>

            <div className="chat-messages">
                {messages.slice(1).map((msg, index) => (
                    <div key={index} className={`message ${msg.role}`}>
                        <div className="message-content">
                            {msg.isMultiReport ? (
                                <MultiReportViewer reports={msg.content} topic={msg.topic} />
                            ) : (
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* 当找到相似报告时，显示这个模块 */}
            {showSimilar && (
                <div style={{ border: '2px dashed #007bff', padding: '20px', margin: '10px', borderRadius: '8px', background: '#f8f9fa' }}>
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

            <form onSubmit={handleSubmit} className="chat-input-form">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={selectedModel === 'mixed-mode' ? "请输入您要生成报告的主题..." : "输入您的问题..."}
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading}>
                    {isLoading ? '生成中...' : '发送'}
                </button>
            </form>
        </div>
    );
}

export default ChatInterface;