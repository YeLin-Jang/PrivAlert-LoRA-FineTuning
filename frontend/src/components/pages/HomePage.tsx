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

      {/* 히어로 섹션 */}
      <section className="hero-section">
        <div className="main-content-card">
          <div className="brand-section">
            <div className="brand-icon-wrapper">
              <div className="brand-icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 1L3 5V11C3 16.55 6.84 21.74 12 23C17.16 21.74 21 16.55 21 11V5L12 1Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M12 11V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <circle cx="12" cy="8" r="1" fill="currentColor"/>
                </svg>
              </div>
            </div>
            <h1 className="brand-name">PrivAlert</h1>
            <p className="concept-slogan">Enterprise-Grade Privacy Protection Platform</p>
            <p className="concept-slogan-kr">엔터프라이즈급 개인정보 보호 분석 시스템</p>
          </div>
          <p className="service-description">
            AI 기반 최첨단 보안 기술로<br />
            민감 정보를 사전에 탐지하고 보호합니다
          </p>
        </div>
        <div className="background-decoration">
          <div className="decoration-box decoration-1"></div>
          <div className="decoration-box decoration-2"></div>
          <div className="decoration-box decoration-3"></div>
        </div>
      </section>

      {/* 기능 소개 섹션 */}
      <section className="features-section">
        <div className="features-container">
          <h2 className="section-title">PrivAlert의 핵심 기능</h2>
          
          {/* 기능 카드 그리드 */}
          <div className="features-grid">
            {/* 1. 텍스트+이미지+동영상에서 민감 정보 탐지 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M14 2V8H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M16 13H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M16 17H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M10 9H8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <h3 className="feature-title">다양한 형식 지원</h3>
              <p className="feature-description">
                텍스트, 이미지, 동영상에서 민감 정보를 자동으로 탐지합니다.
                모든 형식의 콘텐츠를 한 번에 분석하여 누락 없이 보호합니다.
              </p>
            </div>

            {/* 2. Claude 기반 수정 문장 제공 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <h3 className="feature-title">Claude AI 기반 수정 제안</h3>
              <p className="feature-description">
                최첨단 Claude AI가 민감 정보를 제거한 자연스러운 수정 문장을 제공합니다.
                문맥을 이해하여 의미를 손상시키지 않으면서 개인정보를 보호합니다.
              </p>
            </div>

            {/* 3. 사용자 안심 2단계 마스킹 처리 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M12 8V12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M12 16H12.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <h3 className="feature-title">2단계 마스킹 처리</h3>
              <p className="feature-description">
                이중 보안 마스킹으로 개인정보를 완벽하게 보호합니다.
                사용자 안심을 위한 추가 검증 단계를 거쳐 더욱 안전합니다.
              </p>
            </div>

            {/* 4. 필터링 기반 민감 정보 탐지 설정 가능 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1225 17.2863 20.22 17.5291C20.3175 17.7719 20.364 18.0322 20.357 18.294C20.3501 18.5558 20.2898 18.814 20.18 19.05C20.0702 19.286 19.913 19.4947 19.718 19.6626C19.523 19.8305 19.2941 19.9542 19.05 20.025H18.95C18.6814 20.0842 18.4048 20.0842 18.136 20.025C17.8672 19.9658 17.6128 19.8491 17.39 19.682L17.33 19.622C17.0962 19.3916 16.797 19.2369 16.4726 19.1781C16.1482 19.1193 15.8136 19.159 15.512 19.292H15.412C15.1104 19.159 14.7758 19.1193 14.4514 19.1781C14.127 19.2369 13.8278 19.3916 13.594 19.622L13.534 19.682C13.3112 19.8491 13.0568 19.9658 12.788 20.025C12.5192 20.0842 12.2426 20.0842 11.974 20.025H11.874C11.6299 19.9542 11.401 19.8305 11.206 19.6626C11.011 19.4947 10.8538 19.286 10.744 19.05C10.6342 18.814 10.5739 18.5558 10.567 18.294C10.5601 18.0322 10.6065 17.7719 10.704 17.5291C10.8015 17.2863 10.948 17.0657 11.134 16.88L11.194 16.82C11.4245 16.5843 11.5792 16.285 11.638 15.9606C11.6968 15.6362 11.6571 15.3016 11.524 15H11.424C11.2909 14.6984 11.2512 14.3638 11.31 14.0394C11.3688 13.715 11.5235 13.4157 11.754 13.18L11.814 13.12C12 12.9343 12.1465 12.7137 12.244 12.4709C12.3415 12.2281 12.388 11.9678 12.381 11.706C12.3741 11.4442 12.3138 11.186 12.204 10.95C12.0942 10.714 11.937 10.5053 11.742 10.3374C11.547 10.1695 11.3181 10.0458 11.074 9.975H10.974C10.7054 9.91581 10.4288 9.91581 10.16 9.975C9.89123 10.0342 9.63679 10.1509 9.414 10.318L9.354 10.378C9.12024 10.6084 8.82102 10.7631 8.49661 10.8219C8.1722 10.8807 7.83757 10.841 7.536 10.708H7.436C7.13443 10.841 6.79979 10.8807 6.47538 10.8219C6.15097 10.7631 5.85176 10.6084 5.618 10.378L5.558 10.318C5.33521 10.1509 5.08077 10.0342 4.812 9.975C4.54323 9.91581 4.26657 9.91581 3.998 9.975H3.898C3.65387 10.0458 3.42504 10.1695 3.23 10.3374C3.03496 10.5053 2.87779 10.714 2.768 10.95C2.65821 11.186 2.59789 11.4442 2.591 11.706C2.58411 11.9678 2.63059 12.2281 2.728 12.4709C2.82542 12.7137 2.97193 12.9343 3.158 13.12L3.218 13.18C3.44853 13.4157 3.60316 13.715 3.662 14.0394C3.72084 14.3638 3.68114 14.6984 3.548 15H3.448C3.31486 15.3016 3.27516 15.6362 3.334 15.9606C3.39284 16.285 3.54747 16.5843 3.778 16.82L3.838 16.88C4.02407 17.0657 4.17058 17.2863 4.268 17.5291C4.36541 17.7719 4.41189 18.0322 4.405 18.294C4.39811 18.5558 4.33779 18.814 4.228 19.05C4.11821 19.286 3.96104 19.4947 3.766 19.6626C3.57096 19.8305 3.34213 19.9542 3.098 20.025H3.002" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <h3 className="feature-title">맞춤형 필터링 설정</h3>
              <p className="feature-description">
                사용자가 직접 탐지할 민감 정보 유형을 선택할 수 있습니다.
                얼굴, 전화번호, 주민등록번호 등 다양한 옵션으로 맞춤 설정이 가능합니다.
              </p>
            </div>

            {/* 5. 공급망 보안, 제로트러스트 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M7 11V7C7 5.67392 7.52678 4.40215 8.46447 3.46447C9.40215 2.52678 10.6739 2 12 2C13.3261 2 14.5979 2.52678 15.5355 3.46447C16.4732 4.40215 17 5.67392 17 7V11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <h3 className="feature-title">제로트러스트 보안</h3>
              <p className="feature-description">
                공급망 보안을 강화한 제로트러스트 아키텍처로 구현되어 있습니다.
                모든 접근을 검증하고 신뢰하지 않는 것이 기본 원칙입니다.
              </p>
            </div>

            {/* 6. 보안 컴플라이언스 교육 */}
            <div className="feature-card">
              <div className="feature-icon-wrapper">
                <div className="feature-icon">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4 19.5C4 18.837 4.26339 18.2011 4.73223 17.7322C5.20107 17.2634 5.83696 17 6.5 17H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M6.5 2H20V22H6.5C5.83696 22 5.20107 21.7366 4.73223 21.2678C4.26339 20.7989 4 20.163 4 19.5V4.5C4 3.83696 4.26339 3.20107 4.73223 2.73223C5.20107 2.26339 5.83696 2 6.5 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M8 7H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M8 11H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
              <h3 className="feature-title">보안 교육 지원</h3>
              <p className="feature-description">
                보안 컴플라이언스 교육 자료를 제공하여 조직의 보안 인식을 높입니다.
                개인정보 보호 모범 사례를 학습하고 실천할 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 가치 제안 섹션 */}
      <section className="value-section">
        <div className="value-container">
          <div className="value-card main-value">
            <div className="value-icon-wrapper">
              <div className="value-icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M2 12H22" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M12 2C14.5013 4.73835 15.9228 8.29203 16 12C15.9228 15.708 14.5013 19.2616 12 22C9.49872 19.2616 8.07725 15.708 8 12C8.07725 8.29203 9.49872 4.73835 12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>
            <h2 className="value-title">보안의 민주화</h2>
            <p className="value-description">
              누구나 무료로 고성능 AI 보안 기술을 이용할 수 있습니다.
              기업만이 아닌 개인도 최첨단 보안 솔루션의 혜택을 누리세요.
            </p>
          </div>

          <div className="value-card highlight-value">
            <div className="value-icon-wrapper">
              <div className="value-icon">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
            </div>
            <h2 className="value-title">게시 전 점검 일상화</h2>
            <p className="value-description">
              SNS 유출 사고를 사전에 차단합니다.
              게시하기 전 반드시 점검하여 실수로 인한 개인정보 유출을 방지합니다.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

