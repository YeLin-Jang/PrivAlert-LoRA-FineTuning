import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

console.log('[main.tsx] 앱 시작');

const rootElement = document.getElementById('root');

if (!rootElement) {
  console.error('[main.tsx] root 요소를 찾을 수 없습니다!');
  document.body.innerHTML = '<div style="padding: 2rem; text-align: center;"><h1>오류: root 요소를 찾을 수 없습니다</h1></div>';
} else {
  console.log('[main.tsx] root 요소 찾음, 렌더링 시작');
  try {
    const root = createRoot(rootElement);
    root.render(
      <StrictMode>
        <App />
      </StrictMode>
    );
    console.log('[main.tsx] 렌더링 완료');
  } catch (error) {
    console.error('[main.tsx] 렌더링 오류:', error);
    rootElement.innerHTML = `
      <div style="padding: 2rem; text-align: center;">
        <h1 style="color: #dc3545;">렌더링 오류</h1>
        <p>${error instanceof Error ? error.message : '알 수 없는 오류'}</p>
        <button onclick="window.location.reload()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #4a90e2; color: white; border: none; border-radius: 4px; cursor: pointer;">
          새로고침
        </button>
      </div>
    `;
  }
}
