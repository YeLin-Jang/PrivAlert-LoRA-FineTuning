import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import UploadForm from './components/UploadForm';
import LoginForm from './components/LoginForm';
import SignupForm from './components/SignupForm';
import './App.css';

function AppContent() {
  console.log('[AppContent] 함수 시작');
  let authContextData;
  try {
    authContextData = useAuth();
    console.log('[AppContent] useAuth 성공:', authContextData);
  } catch (error: any) {
    console.error('[AppContent] useAuth 실패:', error);
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <h2>인증 컨텍스트 오류</h2>
        <p>{error?.message || '알 수 없는 오류'}</p>
      </div>
    );
  }
  
  const { isAuthenticated, user, loading, logout } = authContextData;
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login');

  console.log('[AppContent] 렌더링:', { loading, isAuthenticated, user: user?.email });

  // 인증되어 있으면 메인 화면 표시
  if (isAuthenticated) {
    console.log('[AppContent] 메인 화면 표시 (인증됨)');
    return (
      <div className="App">
        <header className="app-header">
          <div className="header-content">
            <h1>PrivAlert</h1>
            <div className="user-info">
              <span>{user?.email}</span>
              {user?.is_admin && <span className="admin-badge">관리자</span>}
              <button onClick={logout} className="logout-btn">
                로그아웃
              </button>
            </div>
          </div>
        </header>
        <UploadForm />
      </div>
    );
  }

  // 인증되지 않았으면 로그인/회원가입 화면 표시 (로딩 중이어도 먼저 표시)
  console.log('[AppContent] 로그인 화면 표시');
  return (
    <div className="App">
      <div className="auth-container">
        <div className="auth-header">
          <h1>PrivAlert</h1>
          <p>개인정보 탐지 및 분석 서비스</p>
        </div>
        
        {authMode === 'login' ? (
          <LoginForm
            onSwitchToSignup={() => setAuthMode('signup')}
          />
        ) : (
          <SignupForm
            onSwitchToLogin={() => setAuthMode('login')}
          />
        )}
      </div>
    </div>
  );
}

function App() {
  console.log('[App] 렌더링 시작');
  
  try {
    return (
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    );
  } catch (error: any) {
    console.error('[App] 렌더링 오류:', error);
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <h2 style={{ color: '#dc3545' }}>앱 초기화 오류</h2>
          <p style={{ color: '#666', marginTop: '1rem' }}>{error?.message || '알 수 없는 오류'}</p>
          <button 
            onClick={() => window.location.reload()} 
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', backgroundColor: '#4a90e2', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            새로고침
          </button>
        </div>
      </div>
    );
  }
}

export default App;
