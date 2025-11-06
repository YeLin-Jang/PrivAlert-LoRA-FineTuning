/**
 * 마이페이지 컴포넌트
 * 필터링 설정 및 수정 기록 표시
 * 로그인 없이도 접근 가능 (데이터는 로그인 상태에서만 표시)
 */
import { useState, useEffect } from 'react';
import { useUserAuth } from '../../contexts/UserAuthContext';
import { userApi, type FilteringSettings, type RevisionHistory } from '../../services/userApi';
import CommonHeader from '../common/CommonHeader';
import './MyPage.css';

export default function MyPage() {
  const { isAuthenticated, loading: authLoading } = useUserAuth();
  const [filteringSettings, setFilteringSettings] = useState<FilteringSettings | null>(null);
  const [revisionHistory, setRevisionHistory] = useState<RevisionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingSettings, setEditingSettings] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // 초기 로드 (로그인 상태일 때만)
  useEffect(() => {
    // 인증 확인이 완료된 후에만 데이터 로드
    if (authLoading) {
      return;
    }
    
    if (isAuthenticated) {
      loadData();
    } else {
      // 로그인 안된 상태에서는 데이터 없이 페이지 표시
      setLoading(false);
    }
  }, [currentPage, isAuthenticated, authLoading]);

  // 모든 탐지 옵션 목록 (순서대로)
  const allDetectionOptions = [
    'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
    'email', 'account', 'school', 'workplace', 'name', 'address',
    'driverLicense', 'postalCode'
  ];

  const loadData = async () => {
    if (!isAuthenticated) return;
    
    try {
      setLoading(true);
      setError(null);

      // 실제 사용자 필터링 설정 조회
      const settings = await userApi.getFilteringSettings();
      
      // 모든 옵션이 포함되도록 보장 (없는 옵션은 false)
      const normalizedOptions: Record<string, boolean> = {};
      allDetectionOptions.forEach(key => {
        normalizedOptions[key] = settings.detection_options[key] || false;
      });
      
      setFilteringSettings({
        ...settings,
        detection_options: normalizedOptions
      });

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
    if (!filteringSettings || !isAuthenticated) return;

    try {
      setSaving(true);
      setError(null);

      const updatedSettings = await userApi.updateFilteringSettings(
        filteringSettings.detection_options
      );
      setFilteringSettings(updatedSettings);
      setEditingSettings(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : '설정 저장 중 오류가 발생했습니다');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleOption = (option: string) => {
    if (!filteringSettings || !editingSettings) return;

    // 보안: 허용된 옵션만 허용
    if (!allDetectionOptions.includes(option)) {
      setError('허용되지 않은 옵션입니다');
      return;
    }

    // 현재 값이 true면 false로, false면 true로 토글
    const currentValue = filteringSettings.detection_options[option] === true;
    
    setFilteringSettings({
      ...filteringSettings,
      detection_options: {
        ...filteringSettings.detection_options,
        [option]: !currentValue,
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
        {loading && isAuthenticated ? (
          <div className="loading">로딩 중...</div>
        ) : error && isAuthenticated ? (
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
                {isAuthenticated && !editingSettings ? (
                  <button
                    className="edit-button"
                    onClick={() => setEditingSettings(true)}
                  >
                    수정
                  </button>
                ) : isAuthenticated && editingSettings ? (
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
                ) : null}
              </div>

              <div className="settings-content">
                {!isAuthenticated ? (
                  <div className="empty-state">
                    <p>로그인하면 필터링 설정을 관리할 수 있습니다.</p>
                  </div>
                ) : filteringSettings ? (
                  <div className="detection-options">
                    <div className="options-grid">
                      {allDetectionOptions.map((key) => (
                        <label key={key} className="option-item">
                          <input
                            type="checkbox"
                            checked={filteringSettings.detection_options[key] === true}
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
                    <p>필터링 설정을 불러오는 중...</p>
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
                {!isAuthenticated ? (
                  <div className="empty-state">
                    <p>로그인하면 수정 기록을 확인할 수 있습니다.</p>
                  </div>
                ) : revisionHistory.length === 0 ? (
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
                                  <span key={idx} className="category-badge">
                                    {cat}
                                  </span>
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
    driverLicense: '운전면허번호',
    postalCode: '우편번호',
  };
  return labels[key] || key;
}
