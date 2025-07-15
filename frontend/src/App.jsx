// frontend/src/App.jsx (状态提升后的版本)

import React, { useState } from 'react'; // <--- 导入 useState
import { Routes, Route, Link } from 'react-router-dom';
import HistoryPage from './HistoryPage';
import ChatInterface from './ChatInterface';

function App() {
  // vvvv 将状态从 ChatInterface 提升到这里 vvvv
  const [messages, setMessages] = useState([
    { role: 'system', content: '你是一位资深的行业分析师。' },
    { role: 'assistant', content: '您好！请选择一个模型，然后提出您想分析的主题。' }
  ]);
  // ^^^^                                  ^^^^

  return (
    <div>
      <nav style={{ background: '#333', padding: '10px', display: 'flex', gap: '20px' }}>
        <Link to="/" style={{ color: 'white', textDecoration: 'none' }}>对话</Link>
        <Link to="/history" style={{ color: 'white', textDecoration: 'none' }}>历史记录</Link>
      </nav>
      <main>
        <Routes>
          {/* vvvv 将状态和更新函数作为 props 传递下去 vvvv */}
          <Route 
            path="/" 
            element={<ChatInterface messages={messages} setMessages={setMessages} />} 
          />
          {/* ^^^^                                       ^^^^ */}
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;