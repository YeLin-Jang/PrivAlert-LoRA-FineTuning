/**
 * 마이페이지 컴포넌트
 * 필터링 설정 및 수정 기록 표시
 * 보안: 로그인 필수
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUserAuth } from '../../contexts/UserAuthContext';
import { userApi, type FilteringSettings, type RevisionHistory } from '../../services/userApi';
import CommonHeader from '../common/CommonHeader';
import './MyPage.css';

// 보안: 허용된 옵션만 허용
const ALLOWED_OPTIONS: string[] = [
  'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
  'email', 'account', 'school', 'workplace', 'name', 'address'
];

export default function MyPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useUserAuth();
  const [filteringSettings, setFilteringSettings] = useState<FilteringSettings | null>(null);
  const [revisionHistory, setRevisionHistory] = useState<RevisionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingSettings, setEditingSettings] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // 로그인 체크
  useEffect(() => {
    // 인증 확인이 완료된 후에만 체크
    if (authLoading) {
      return; // 로딩 중이면 대기
    }
    
    // localStorage에 user_email이 있으면 로그인 상태로 간주 (세션 쿠키 확인 중일 수 있음)
    const storedEmail = localStorage.getItem('user_email');
    const isLoggedIn = isAuthenticated || !!storedEmail;
    
    if (!isLoggedIn) {
      // 로그인 안된 상태면 로그인 페이지로 리다이렉트
      navigate('/auth/login', { 
        replace: true,
        state: { 
          redirectTo: '/mypage',
          message: '마이페이지는 로그인이 필요합니다.'
        } 
      });
    }
  }, [isAuthenticated, authLoading, navigate]);

  // 초기 로드 (로그인 상태일 때만)
  useEffect(() => {
    // localStorage에 user_email이 있으면 로그인 상태로 간주
    const storedEmail = localStorage.getItem('user_email');
    const isLoggedIn = isAuthenticated || !!storedEmail;
    
    if (isLoggedIn) {
      loadData();
    } else {
      setLoading(false);
    }
  }, [currentPage, isAuthenticated]);

  const loadData = async () => {
    // localStorage에 user_email이 있으면 로그인 상태로 간주
    const storedEmail = localStorage.getItem('user_email');
    const isLoggedIn = isAuthenticated || !!storedEmail;
    if (!isLoggedIn) return;
    
    try {
      setLoading(true);
      setError(null);

      // 실제 사용자 필터링 설정 조회
      const settings = await userApi.getFilteringSettings();
      console.log('필터링 설정 로드:', settings);
      setFilteringSettings(settings);

      // 수정 기록 조회
      const historyData = await userApi.getRevisionHistory(currentPage, 20);
      setRevisionHistory(historyData.records || []);
      setTotalPages(historyData.pagination?.pages || 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!isAuthenticated) return;

    try {
      setSaving(true);
      setError(null);

      // filteringSettings가 없으면 빈 객체로 초기화
      const detectionOptions = filteringSettings?.detection_options || {};
      
      const updatedSettings = await userApi.updateFilteringSettings(detectionOptions);
      setFilteringSettings(updatedSettings);
      setEditingSettings(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '설정 저장 중 오류가 발생했습니다');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleOption = (option: string) => {
    if (!editingSettings) return;
    
    if (!ALLOWED_OPTIONS.includes(option)) {
      setError('허용되지 않은 옵션입니다');
      return;
    }

    // filteringSettings가 없으면 초기화
    const currentSettings: FilteringSettings = filteringSettings || {
      id: 0,
      user_id: 0,
      detection_options: {} as Record<string, boolean>,
      created_at: undefined,
      updated_at: undefined,
    };

    setFilteringSettings({
      ...currentSettings,
      detection_options: {
        ...(currentSettings.detection_options || {}),
        [option]: !((currentSettings.detection_options?.[option] as boolean) || false),
      },
    });
  };

  const handleCancelEdit = () => {
    // 설정을 다시 로드하여 변경사항 취소
    loadData();
    setEditingSettings(false);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="mypage">
      {/* 공통 헤더 */}
      <CommonHeader />

      {/* 페이지 헤더 - 이미지 참조 디자인 */}
      <header className="mypage-header">
        <div className="page-header-content">
          <div className="header-left">
            <button className="back-button" onClick={() => navigate('/')}>
              ←
            </button>
            <span className="nav-breadcrumb">홈</span>
            <span className="nav-separator">/</span>
            <span className="nav-breadcrumb active">마이페이지</span>
          </div>
        </div>
      </header>

      <main className="mypage-main">
        {loading ? (
          <div className="loading">로딩 중...</div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : (
          <>
            {/* 필터링 설정 섹션 */}
            <section className="settings-section">
              <div className="section-header">
                <div className="section-title-group">
                  <h2>필터링 설정</h2>
                  <h3 className="section-subtitle">탐지 옵션</h3>
                </div>
                {!editingSettings ? (
                  <button
                    className="edit-button"
                    onClick={() => setEditingSettings(true)}
                  >
                    수정
                  </button>
                ) : (
                  <div className="edit-actions">
                    <button
                      className="save-button"
                      onClick={handleSaveSettings}
                      disabled={saving}
                    >
                      {saving ? '저장 중...' : '저장'}
                    </button>
                    <button
                      className="cancel-button"
                      onClick={handleCancelEdit}
                      disabled={saving}
                    >
                      취소
                    </button>
                  </div>
                )}
              </div>

              <div className="settings-content">
                {ALLOWED_OPTIONS && ALLOWED_OPTIONS.length > 0 ? (
                  <div className="detection-options">
                    <div className="options-grid">
                      {ALLOWED_OPTIONS.map((key) => (
                        <label key={key} className="option-item">
                          <input
                            type="checkbox"
                            checked={filteringSettings?.detection_options?.[key] || false}
                            onChange={() => handleToggleOption(key)}
                            disabled={!editingSettings}
                          />
                          <span>{getOptionLabel(key)}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    <p>탐지 옵션을 불러올 수 없습니다.</p>
                  </div>
                )}
              </div>
            </section>

            {/* 수정 기록 섹션 */}
            <section className="history-section">
              <div className="section-header">
                <h2>수정 기록</h2>
              </div>

              <div className="history-content">
                {revisionHistory.length === 0 ? (
                  <div className="empty-state">
                    <p>아직 수정 기록이 없습니다.</p>
                    <p className="empty-hint">분석 결과에서 LLM이 생성한 수정 문장이 여기에 저장됩니다.</p>
                  </div>
                ) : (
                  <>
                    <div className="history-list">
                      {revisionHistory.map((record) => (
                        <div key={record.id} className="history-item">
                          <div className="history-header">
                            <span className="history-date">
                              {formatDate(record.created_at)}
                            </span>
                            {record.categories && record.categories.length > 0 && (
                              <div className="history-categories">
                                {record.categories.map((cat, idx) => (
                                  <button key={idx} className="category-badge">
                                    {cat}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="history-sentence">
                            {record.revised_sentence}
                          </div>
                          <input
                            type="text"
                            className="history-text-input"
                            placeholder="수정된 텍스트를 확인하세요"
                            readOnly
                          />
                        </div>
                      ))}
                    </div>

                    {/* 페이지네이션 */}
                    {totalPages > 1 && (
                      <div className="pagination">
                        <button
                          className="page-button"
                          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                          disabled={currentPage === 1}
                        >
                          이전
                        </button>
                        <span className="page-info">
                          {currentPage} / {totalPages}
                        </span>
                        <button
                          className="page-button"
                          onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                          disabled={currentPage === totalPages}
                        >
                          다음
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

// 옵션 라벨 매핑
function getOptionLabel(key: string): string {
  const labels: Record<string, string> = {
    face: '얼굴',
    fingerprint: '손가락',
    phone: '전화번호',
    rrn: '주민등록번호',
    passport: '여권번호',
    ip_address: 'IP주소',
    email: '이메일',
    account: '계좌번호',
    school: '학교명',
    workplace: '직장명',
    name: '이름',
    address: '주소',
  };
  return labels[key] || key;
}
