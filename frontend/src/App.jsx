// frontend/src/App.jsx
import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import ReportGenerator from './ReportGenerator';
import HistoryPage from './HistoryPage';

function App() {
  return (
    <div>
      <nav style={{ background: '#333', padding: '10px' }}>
        <Link to="/" style={{ color: 'white', marginRight: '20px', textDecoration: 'none' }}>报告生成器</Link>
        <Link to="/history" style={{ color: 'white', textDecoration: 'none' }}>历史记录</Link>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<ReportGenerator />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;