/**
 * 마이페이지 컴포넌트
 * 필터링 설정 및 수정 기록 표시
 * 보안: 더미 사용자 데이터 사용 (인증 없음)
 */
import { useState, useEffect } from 'react';
import { dummyUserApi, type FilteringSettings, type RevisionHistory, type DemoUser, type DetectionOptions } from '../services/dummyUserApi';
import CommonHeader from './CommonHeader';
import './MyPage.css';

export default function MyPage() {
  const [demoUser, setDemoUser] = useState<DemoUser | null>(null);
  const [filteringSettings, setFilteringSettings] = useState<FilteringSettings | null>(null);
  const [revisionHistory, setRevisionHistory] = useState<RevisionHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingSettings, setEditingSettings] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // 비밀번호 변경 관련 상태
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [currentPasswordVerified, setCurrentPasswordVerified] = useState(false);
  const [verifyingPassword, setVerifyingPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // 초기 로드
  useEffect(() => {
    loadData();
  }, [currentPage]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      // 더미 사용자 정보 조회
      const user = await dummyUserApi.getDemoUser();
      setDemoUser(user);

      // 필터링 설정 조회
      const settings = await dummyUserApi.getFilteringSettings();
      setFilteringSettings(settings);

      // 수정 기록 조회
      const historyData = await dummyUserApi.getRevisionHistory(currentPage, 20);
      setRevisionHistory(historyData.records);
      setTotalPages(historyData.pagination.pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : '데이터를 불러오는 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!filteringSettings) return;

    try {
      setSaving(true);
      setError(null);

      const updatedSettings = await dummyUserApi.updateFilteringSettings(
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

  const handleToggleOption = (option: keyof DetectionOptions) => {
    if (!filteringSettings || !editingSettings) return;

    // 보안: 허용된 옵션만 허용
    const allowedOptions = [
      'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
      'email', 'account', 'school', 'workplace', 'name', 'address',
      'driverLicense', 'postalCode'
    ];
    
    if (!allowedOptions.includes(option)) {
      setError('허용되지 않은 옵션입니다');
      return;
    }

    setFilteringSettings({
      ...filteringSettings,
      detection_options: {
        ...filteringSettings.detection_options,
        [option]: !filteringSettings.detection_options[option],
      },
    });
  };

  const handleCancelEdit = () => {
    // 설정을 다시 로드하여 변경사항 취소
    loadData();
    setEditingSettings(false);
  };

  const handleVerifyCurrentPassword = async () => {
    if (!currentPassword) {
      setPasswordError('기존 비밀번호를 입력해주세요');
      return;
    }

    try {
      setVerifyingPassword(true);
      setPasswordError(null);

      await dummyUserApi.verifyPassword(currentPassword);
      
      // 기존 비밀번호 확인 성공
      setCurrentPasswordVerified(true);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : '기존 비밀번호 확인 중 오류가 발생했습니다');
      setCurrentPasswordVerified(false);
    } finally {
      setVerifyingPassword(false);
    }
  };

  const handlePasswordChange = async () => {
    // 보안: 입력 검증
    if (!newPassword || !confirmPassword) {
      setPasswordError('새 비밀번호와 확인 비밀번호를 입력해주세요');
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError('새 비밀번호는 최소 8자 이상이어야 합니다');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('새 비밀번호와 확인 비밀번호가 일치하지 않습니다');
      return;
    }

    if (currentPassword === newPassword) {
      setPasswordError('새 비밀번호는 기존 비밀번호와 달라야 합니다');
      return;
    }

    // 보안: 비밀번호 복잡도 검증 (영문, 숫자, 특수문자 중 2가지 이상)
    const hasLetter = /[a-zA-Z]/.test(newPassword);
    const hasNumber = /[0-9]/.test(newPassword);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(newPassword);
    const complexityCount = [hasLetter, hasNumber, hasSpecial].filter(Boolean).length;
    
    if (complexityCount < 2) {
      setPasswordError('새 비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 포함해야 합니다');
      return;
    }

    try {
      setChangingPassword(true);
      setPasswordError(null);

      await dummyUserApi.changePassword(currentPassword, newPassword);
      
      // 성공 시 폼 초기화
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setCurrentPasswordVerified(false);
      setShowPasswordChange(false);
      setError('비밀번호가 성공적으로 변경되었습니다');
      
      // 3초 후 성공 메시지 제거
      setTimeout(() => setError(null), 3000);
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : '비밀번호 변경 중 오류가 발생했습니다');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleCancelPasswordChange = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setCurrentPasswordVerified(false);
    setPasswordError(null);
    setShowPasswordChange(false);
  };

  const handleResetPasswordVerification = () => {
    setCurrentPassword('');
    setCurrentPasswordVerified(false);
    setPasswordError(null);
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

      {/* 페이지 헤더 */}
      <header className="mypage-header">
        <div className="page-header-content">
          <h1 className="page-title">마이페이지</h1>
          {demoUser && (
            <span className="user-info-text">안녕하세요, {demoUser.username}님</span>
          )}
        </div>
      </header>

      <main className="mypage-main">
        {loading ? (
          <div className="loading">로딩 중...</div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : (
          <>
            {/* 비밀번호 변경 섹션 */}
            <section className="settings-section">
              <div className="section-header">
                <h2>비밀번호 변경</h2>
                {!showPasswordChange ? (
                  <button
                    className="edit-button"
                    onClick={() => setShowPasswordChange(true)}
                  >
                    변경
                  </button>
                ) : (
                  <div className="edit-actions">
                    <button
                      className="save-button"
                      onClick={handlePasswordChange}
                      disabled={changingPassword}
                    >
                      {changingPassword ? '변경 중...' : '저장'}
                    </button>
                    <button
                      className="cancel-button"
                      onClick={handleCancelPasswordChange}
                      disabled={changingPassword}
                    >
                      취소
                    </button>
                  </div>
                )}
              </div>

              {showPasswordChange && (
                <div className="password-change-form">
                  {passwordError && (
                    <div className="password-error">{passwordError}</div>
                  )}
                  
                  {/* 1단계: 기존 비밀번호 확인 */}
                  {!currentPasswordVerified && (
                    <div className="password-verify-step">
                      <div className="form-group">
                        <label htmlFor="current-password">기존 비밀번호</label>
                        <div className="password-input-group">
                          <input
                            id="current-password"
                            type="password"
                            value={currentPassword}
                            onChange={(e) => setCurrentPassword(e.target.value)}
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') {
                                handleVerifyCurrentPassword();
                              }
                            }}
                            placeholder="기존 비밀번호를 입력하세요"
                            disabled={verifyingPassword}
                            className="password-input"
                          />
                          <button
                            type="button"
                            className="verify-button"
                            onClick={handleVerifyCurrentPassword}
                            disabled={verifyingPassword || !currentPassword}
                          >
                            {verifyingPassword ? '확인 중...' : '확인'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 2단계: 새 비밀번호 입력 (기존 비밀번호 확인 후 표시) */}
                  {currentPasswordVerified && (
                    <div className="password-change-step">
                      <div className="step-indicator">
                        <span className="step-success">✓ 기존 비밀번호 확인 완료</span>
                        <button
                          type="button"
                          className="reset-verification-button"
                          onClick={handleResetPasswordVerification}
                        >
                          다시 입력
                        </button>
                      </div>

                      <div className="form-group">
                        <label htmlFor="new-password">새 비밀번호</label>
                        <input
                          id="new-password"
                          type="password"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder="새 비밀번호를 입력하세요 (최소 8자)"
                          disabled={changingPassword}
                          className="password-input"
                        />
                        <small className="password-hint">
                          영문, 숫자, 특수문자 중 2가지 이상 포함
                        </small>
                      </div>

                      <div className="form-group">
                        <label htmlFor="confirm-password">새 비밀번호 확인</label>
                        <input
                          id="confirm-password"
                          type="password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="새 비밀번호를 다시 입력하세요"
                          disabled={changingPassword}
                          className="password-input"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* 필터링 설정 섹션 */}
            <section className="settings-section">
              <div className="section-header">
                <h2>필터링 설정</h2>
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
                {filteringSettings && (
                  <div className="detection-options">
                    <h3>탐지 옵션</h3>
                    <div className="options-grid">
                      {(Object.keys(filteringSettings.detection_options) as Array<keyof DetectionOptions>).map((key) => (
                        <label key={key} className="option-item">
                          <input
                            type="checkbox"
                            checked={filteringSettings.detection_options[key] || false}
                            onChange={() => handleToggleOption(key)}
                            disabled={!editingSettings}
                          />
                          <span>{getOptionLabel(key)}</span>
                        </label>
                      ))}
                    </div>
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
                                  <span key={idx} className="category-badge">
                                    {cat}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="history-sentence">
                            {/* 보안: XSS 방지 - React가 자동으로 이스케이프 처리 */}
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

