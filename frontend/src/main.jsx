// frontend/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { BrowserRouter } from 'react-router-dom'; // 导入

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* 用 BrowserRouter 包裹 App */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)