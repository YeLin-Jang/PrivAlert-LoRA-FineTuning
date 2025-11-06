/**
 * 메인페이지 컴포넌트
 * PrivAlert 팀의 파란색 컨셉에 맞는 깔끔한 디자인
 */
import CommonHeader from '../common/CommonHeader';
import './HomePage.css';

export default function HomePage() {
  return (
    <div className="homepage">
      {/* 공통 헤더 */}
      <CommonHeader />

      {/* 메인 콘텐츠 */}
      <main className="homepage-main">
        <div className="main-content-card">
          <div className="brand-section">
            <div className="brand-icon">🔒</div>
            <h1 className="brand-name">PrivAlert</h1>
            <p className="concept-slogan">당신의 개인정보 보호 분석 시스템</p>
          </div>
          <p className="service-description">
            안전하고 신뢰할 수 있는 개인정보 보호 솔루션으로<br />
            당신의 소중한 데이터를 지켜드립니다
          </p>
        </div>
        <div className="background-decoration">
          <div className="decoration-box decoration-1"></div>
          <div className="decoration-box decoration-2"></div>
          <div className="decoration-box decoration-3"></div>
        </div>
      </main>
    </div>
  );
}

