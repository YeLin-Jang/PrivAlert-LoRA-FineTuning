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
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [editingSettings, setEditingSettings] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // 로그인 체크
  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (!isAuthenticated) {
      navigate('/auth/login', {
        replace: true,
        state: {
          redirectTo: '/mypage',
          message: '마이페이지는 로그인이 필요합니다.',
        },
      });
    }
  }, [isAuthenticated, authLoading, navigate]);

  // 초기 로드 (로그인 상태일 때만)
  useEffect(() => {
    if (authLoading) {
      return;
    }
    if (isAuthenticated) {
      loadData();
    } else {
      setLoading(false);
    }
  }, [currentPage, isAuthenticated, authLoading]);

  const loadData = async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
  
    try {
      setLoading(true);
      setError(null);

      // CSRF 토큰 확인 및 갱신 (보안: 403 에러 방지)
      // 사용자 정보 조회 시 CSRF 토큰도 함께 갱신될 수 있음
      try {
        await userApi.getCurrentUser();
        // 사용자 정보가 있으면 인증 상태 유지
      } catch (userErr) {
        // 사용자 정보 조회 실패 시에도 계속 진행 (필터링 설정은 별도로 조회)
        // 보안: 콘솔 로그 제거
      }

      // 실제 사용자 필터링 설정 조회
      // 보안: 민감 정보(user_id, id 등)가 포함된 로그는 제거
      const settings = await userApi.getFilteringSettings();
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
    if (!isAuthenticated || !filteringSettings) {
      setError('로그인이 필요하거나 필터링 설정을 불러올 수 없습니다');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);

      // CSRF 토큰 항상 갱신 (세션 ID 기반 토큰으로 업데이트)
      try {
        await userApi.getCurrentUser();
      } catch (tokenErr) {
        setError('인증 토큰이 만료되었습니다. 페이지를 새로고침하거나 다시 로그인해주세요.');
        setSaving(false);
        return;
      }

      // detection_options 추출
      const detectionOptions = filteringSettings.detection_options || {};
      
      const updatedSettings = await userApi.updateFilteringSettings(detectionOptions);
      setFilteringSettings(updatedSettings);
      setEditingSettings(false);
      setSuccessMessage('필터링 설정이 성공적으로 저장되었습니다');
      
      // 3초 후 성공 메시지 제거
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      // 403 에러인 경우 CSRF 토큰 갱신 후 재시도
      if (err?.response?.status === 403) {
        try {
          // CSRF 토큰 갱신 시도
          await userApi.getCurrentUser();
          // 재시도
          const detectionOptions = filteringSettings.detection_options || {};
          const updatedSettings = await userApi.updateFilteringSettings(detectionOptions);
          setFilteringSettings(updatedSettings);
          setEditingSettings(false);
          setSuccessMessage('필터링 설정이 성공적으로 저장되었습니다');
          setTimeout(() => setSuccessMessage(null), 3000);
        } catch (retryErr) {
          setError('인증 토큰이 만료되었거나 유효하지 않습니다. 페이지를 새로고침하거나 다시 로그인해주세요.');
        }
      } else {
        setError(err instanceof Error ? err.message : '설정 저장 중 오류가 발생했습니다');
      }
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

    const currentOptions = currentSettings.detection_options || {} as Record<string, boolean>;
    setFilteringSettings({
      ...currentSettings,
      detection_options: {
        ...currentOptions,
        [option]: !(currentOptions[option] || false),
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

              {error && (
                <div className="error-message" style={{ marginTop: '15px', marginBottom: '15px' }}>
                  {error}
                </div>
              )}
              {successMessage && (
                <div className="success-message" style={{ marginTop: '15px', marginBottom: '15px', color: '#22c55e', backgroundColor: '#d1fae5', padding: '12px 16px', borderRadius: '6px', border: '1px solid #86efac' }}>
                  {successMessage}
                </div>
              )}

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
                                    {getCategoryLabel(cat)}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="history-sentence">
                            {record.revised_sentence}
                          </div>
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

// 카테고리 라벨 매핑 (옵션 라벨과 동일)
function getCategoryLabel(key: string): string {
  return getOptionLabel(key);
}
