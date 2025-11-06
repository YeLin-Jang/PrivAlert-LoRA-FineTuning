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
  const { isAuthenticated, user, logout } = useUserAuth();

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
      console.error('로그아웃 오류:', error);
    }
  };

  return (
    <header className="common-header">
      <div className="header-logo">
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
        {isAuthenticated ? (
          <>
            <span className="user-greeting">안녕하세요, {user?.nickname || user?.email || '사용자'}님</span>
            <button className="logout-button" onClick={handleLogout}>
              로그아웃
            </button>
          </>
        ) : (
          <>
            <button className="login-button" onClick={handleLogin}>
              로그인
            </button>
            <button className="signup-button" onClick={handleSignup}>
              회원가입
            </button>
          </>
        )}
      </div>
    </header>
  );
}

