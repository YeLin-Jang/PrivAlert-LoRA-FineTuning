/**
 * 공통 헤더 컴포넌트
 * 모든 페이지에서 사용되는 통일된 헤더
 */
import { useNavigate, useLocation } from 'react-router-dom';
import { useUserAuth } from '../../contexts/UserAuthContext';
import './CommonHeader.css';

export default function CommonHeader() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, logout, loading } = useUserAuth();

  const handleHome = () => {
    navigate('/');
  };

  const handleAnalyze = () => {
    navigate('/analyze');
  };

  const handleMyPage = () => {
    navigate('/mypage');
  };

  const handleLogin = () => {
    navigate('/auth/login');
  };

  const handleSignup = () => {
    navigate('/auth/signup');
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      // 보안: 콘솔 로그 제거
    }
  };

  return (
    <header className="common-header">
      <div className="header-logo" onClick={handleHome}>
        <img src="/Privalert.png" alt="PrivAlert" className="logo-image" />
        <span className="logo-text">PrivAlert</span>
      </div>
      <nav className="header-nav">
        <button 
          className={`nav-link primary ${location.pathname === '/' ? 'active' : ''}`}
          onClick={handleHome}
        >
          홈
        </button>
        <button 
          className={`nav-link primary ${location.pathname === '/analyze' ? 'active' : ''}`}
          onClick={handleAnalyze}
        >
          분석하기
        </button>
        <button 
          className={`nav-link primary ${location.pathname === '/mypage' ? 'active' : ''}`}
          onClick={handleMyPage}
        >
          마이페이지
        </button>
      </nav>

      <div className="header-right">
        {loading ? (
          <div className="auth-loading">
            <div className="loading-spinner"></div>
            <span className="loading-text">로딩 중...</span>
          </div>
        ) : isAuthenticated ? (
          <>
            <span className="user-greeting">안녕하세요, {user?.nickname || user?.email || '사용자'}님</span>
            <span className="logout-link" onClick={handleLogout}>
              로그아웃
            </span>
          </>
        ) : (
          <>
            <span className="login-link" onClick={handleLogin}>
              로그인
            </span>
            <span className="signup-link" onClick={handleSignup}>
              회원가입
            </span>
          </>
        )}
      </div>
    </header>
  );
}

