import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import { getDashboardOverview } from '../../services/adminApi';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const { user, logout } = useAdminAuth();
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const data = await getDashboardOverview();
        setOverview(data);
      } catch (err: any) {
        setError(err.message || '데이터를 불러오는데 실패했습니다');
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = '/admin/login';
    } catch (err) {
      console.error('로그아웃 오류:', err);
    }
  };

  if (loading) {
    return <div className="dashboard-loading">로딩 중...</div>;
  }

  if (error) {
    return <div className="dashboard-error">오류: {error}</div>;
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>관리자 대시보드</h1>
        <div className="header-right">
          <span className="user-info">안녕하세요, {user?.username}님 ({user?.role})</span>
          <button onClick={handleLogout} className="logout-button">로그아웃</button>
        </div>
      </header>

      <nav className="dashboard-nav">
        <Link to="/admin/dashboard" className="nav-link">대시보드</Link>
        <Link to="/admin/users" className="nav-link">사용자 관리</Link>
      </nav>

      <div className="dashboard-content">
        {overview && (
          <>
            <div className="stats-grid">
              <div className="stat-card">
                <h3>사용자</h3>
                <div className="stat-value">{overview.users?.total || 0}</div>
                <div className="stat-label">전체: {overview.users?.total || 0} | 활성: {overview.users?.active || 0}</div>
              </div>
              <div className="stat-card">
                <h3>탐지</h3>
                <div className="stat-value">{overview.detections?.total || 0}</div>
                <div className="stat-label">오늘: {overview.detections?.today || 0}</div>
              </div>
              <div className="stat-card">
                <h3>평균 위험도</h3>
                <div className="stat-value">{overview.detections?.avg_risk_score || 0}</div>
                <div className="stat-label">점수</div>
              </div>
              <div className="stat-card">
                <h3>시스템 가동률</h3>
                <div className="stat-value">{overview.system?.uptime || 'N/A'}</div>
                <div className="stat-label">응답 시간: {overview.system?.response_time || 'N/A'}</div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;

