import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { cleanCurrentUrl } from './utils/urlSecurity'

// 보안: 앱 시작 시 URL에서 민감 정보 제거
try {
  cleanCurrentUrl();
} catch (error) {
  // URL 정리 실패해도 앱은 계속 실행
  console.warn('URL 정리 실패:', error);
}

// root 요소 확인
const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
