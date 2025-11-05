/**
 * 메인페이지 컴포넌트
 * PrivAlert 팀의 컨셉에 맞는 깔끔한 디자인
 * 보안: 더미 사용자 데이터 사용 (인증 없음)
 */
import CommonHeader from './CommonHeader';
import './HomePage.css';

export default function HomePage() {
  return (
    <div className="homepage">
      {/* 공통 헤더 */}
      <CommonHeader />

      {/* 메인 콘텐츠 */}
      <main className="homepage-main">
        <div className="main-content">
          <h1 className="brand-name">PrivAlert</h1>
          <p className="service-description">
            개인정보를 안전하게 보호하는 프리미엄 서비스
          </p>
        </div>
      </main>
    </div>
  );
}

