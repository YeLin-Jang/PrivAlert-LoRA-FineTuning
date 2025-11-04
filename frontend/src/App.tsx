import { useState, useEffect } from 'react';
import UploadForm from './components/UploadForm';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import { logout, getCurrentUser, checkSession } from './api';
import type { User } from './types';
import './App.css';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 세션 확인
    checkSession().then((session) => {
      if (session.authenticated && session.user) {
        setUser(session.user);
      }
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });
  }, []);

  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    setShowRegister(false);
  };

  const handleRegisterSuccess = (registeredUser: User) => {
    setUser(registeredUser);
    setShowRegister(false);
  };

  const handleLogout = async () => {
    try {
      await logout();
      setUser(null);
    } catch (error) {
      console.error('로그아웃 실패:', error);
    }
  };

  if (loading) {
    return (
      <div className="App">
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <p>로딩 중...</p>
        </div>
      </div>
    );
  }

  // 로그인되지 않은 경우
  if (!user) {
    return (
      <div className="App">
        {showRegister ? (
          <RegisterForm
            onRegisterSuccess={handleRegisterSuccess}
            onSwitchToLogin={() => setShowRegister(false)}
          />
        ) : (
          <LoginForm
            onLoginSuccess={handleLoginSuccess}
            onSwitchToRegister={() => setShowRegister(true)}
          />
        )}
      </div>
    );
  }

  // 로그인된 경우
  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <h1>🔔 PrivAlert</h1>
          <div className="user-info">
            <span className="username">{user.username}</span>
            {user.roles.length > 0 && (
              <span className="roles">{user.roles.join(', ')}</span>
            )}
            <button onClick={handleLogout} className="logout-btn">
              로그아웃
            </button>
          </div>
        </div>
      </header>
      <main>
        <UploadForm />
      </main>
    </div>
  );
}

export default App;
