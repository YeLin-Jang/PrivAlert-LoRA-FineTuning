import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { cleanCurrentUrl } from './utils/urlSecurity'

// 보안: 앱 시작 시 URL에서 민감 정보 제거
cleanCurrentUrl();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
