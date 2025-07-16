// frontend/src/ChatInterface.jsx (最终完整、功能齐全的版本)

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';
import MultiReportViewer from './MultiReportViewer';
import './ChatInterface.css';

const API_URL = 'http://127.0.0.1:8000';

// 从父组件 App.jsx 接收 messages 和 setMessages，以实现状态保持
function ChatInterface({ messages, setMessages }) {
    // 本组件私有的状态
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [selectedModel, setSelectedModel] = useState('mixed-mode');
    const [templateFile, setTemplateFile] = useState(null);
    const [similarReports, setSimilarReports] = useState([]);
    const [showSimilar, setShowSimilar] = useState(false);

    // ref 用于文件输入框的重置和聊天记录的自动滚动
    const fileInputRef = useRef(null);
    const messagesEndRef = useRef(null);

    // 自动滚动到聊天底部的效果
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    useEffect(scrollToBottom, [messages]);

    // 核心的生成逻辑，被 handleSubmit 和 proceedToGenerate 调用
    const generateResponse = async (messagesForApi, topicForApi) => {
        setIsLoading(true);
        setShowSimilar(false); 

        if (selectedModel === 'mixed-mode') {
            try {
                let response;
                // 根据有无模板文件，决定调用哪个API
                if (templateFile) {
                    console.log("执行带模板的混合模式生成...");
                    const formData = new FormData();
                    formData.append('topic', topicForApi);
                    formData.append('template_file', templateFile);
                    response = await axios.post(`${API_URL}/api/reports/generate-from-template`, formData, {
                        headers: { 'Content-Type': 'multipart/form-data' }
                    });
                } else {
                    console.log("执行无模板的混合模式生成...");
                    response = await axios.post(`${API_URL}/api/reports/generate-mixed`, {
                        topic: topicForApi,
                    });
                }
                
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: response.data.reports,
                    isMultiReport: true,
                    topic: topicForApi
                }]);
                
            } catch (error) {
                console.error('混合模式生成报告时出错:', error);
                const errorMsg = error.response?.data?.detail || '抱歉，混合模式生成失败。';
                setMessages(prev => [...prev, { role: 'assistant', content: errorMsg }]);
            } finally {
                setIsLoading(false);
                setTemplateFile(null); // 清空已上传的文件
                if(fileInputRef.current) fileInputRef.current.value = "";
            }
        } else {
            // 单模型对话逻辑 (流式)
            try {
                // 在发送API请求前，净化消息历史
                const apiMessages = messagesForApi.map(msg => {
                    if (msg.isMultiReport) {
                        return { 
                            role: 'assistant', 
                            content: `(系统提示：用户已针对主题“${msg.topic}”生成并查看了一份多模型报告)` 
                        };
                    }
                    return { role: msg.role, content: msg.content };
                });

                setMessages(prev => [...prev, { role: 'assistant', content: '' }]);
                const response = await fetch(`${API_URL}/api/chat/completions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: apiMessages, model: selectedModel }),
                });

                if (!response.body) throw new Error("Response body is empty.");
                
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

    // 表单提交时的主处理函数
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessageContent = `主题: ${input}${templateFile ? `\n模板: ${templateFile.name}` : ''}`;
        const userMessage = { role: 'user', content: userMessageContent };
        const newMessages = [...messages, userMessage];
        const submittedInput = input;

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

        await generateResponse(newMessages, submittedInput);
    };

    // 当用户在“相似推荐”弹窗中点击“仍然生成”时调用
    const proceedToGenerate = async () => {
        const lastUserMessage = messages.slice().reverse().find(m => m.role === 'user');
        if (!lastUserMessage) return;
        
        await generateResponse(messages, lastUserMessage.content.split('\n')[0].replace('主题: ', ''));
    };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file && file.name.endsWith('.docx')) {
            setTemplateFile(file);
        } else if (file) {
            alert("请选择 .docx 格式的Word文件。");
            setTemplateFile(null);
            if(fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    return (
        <div className="chat-container">
            <div className="model-selector" style={{ padding: '10px', borderBottom: '1px solid #ccc', background: '#f9f9f9', textAlign: 'center' }}>
                <label htmlFor="model-select" style={{ marginRight: '10px', fontWeight: 'bold' }}>当前模式: </label>
                <select id="model-select" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} style={{ padding: '5px' }}>
                    <option value="mixed-mode">混合模式 (生成多份报告)</option>
                    <option value="gemini">Gemini (对话)</option>
                    <option value="deepseek">DeepSeek (对话)</option>
                    <option value="qwen">Qwen 2.5 (本地对话)</option>
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
            
            <div className="input-area-container" style={{ padding: '10px', borderTop: '1px solid #ccc' }}>
                {selectedModel === 'mixed-mode' && (
                    <div className="file-upload-section" style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <label htmlFor="template-upload" className="file-upload-label" style={{ background: '#6c757d', color: 'white', padding: '8px 12px', borderRadius: '5px', cursor: 'pointer' }}>
                            上传Word模板(可选)
                        </label>
                        <input id="template-upload" type="file" accept=".docx" onChange={handleFileChange} ref={fileInputRef} style={{ display: 'none' }} />
                        {templateFile && <span>{templateFile.name}</span>}
                        {templateFile && <button onClick={() => { setTemplateFile(null); if(fileInputRef.current) fileInputRef.current.value = ""; }} style={{background: 'none', border: 'none', color: 'red', cursor: 'pointer', fontSize: '16px'}}>X</button>}
                    </div>
                )}
                
                <form onSubmit={handleSubmit} className="chat-input-form">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={selectedModel === 'mixed-mode' ? "输入主题要求（可配合模板使用）..." : "输入您的问题..."}
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={isLoading}>
                        {isLoading ? '生成中...' : '发送'}
                    </button>
                </form>
            </div>
        </div>
    );
}

export default ChatInterface;