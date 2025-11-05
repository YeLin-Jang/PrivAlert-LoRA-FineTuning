/**
 * 공통 헤더 컴포넌트
 * 모든 페이지에서 사용되는 통일된 헤더
 */
import { useNavigate, useLocation } from 'react-router-dom';
import './CommonHeader.css';

export default function CommonHeader() {
  const navigate = useNavigate();
  const location = useLocation();

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
    // 로그인 페이지로 이동 (추후 구현)
    console.log('로그인 클릭');
  };

  const handleSignup = () => {
    // 회원가입 페이지로 이동 (추후 구현)
    console.log('회원가입 클릭');
  };

  return (
    <header className="common-header">
      <div className="header-left">
        <div className="logo" onClick={handleHome} style={{ cursor: 'pointer' }}>
          <span className="logo-icon">🔔</span>
          <span className="logo-text">PrivAlert</span>
        </div>
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
        <button className="login-button" onClick={handleLogin}>
          로그인
        </button>
        <button className="signup-button" onClick={handleSignup}>
          회원가입
        </button>
      </div>
    </header>
  );
}

