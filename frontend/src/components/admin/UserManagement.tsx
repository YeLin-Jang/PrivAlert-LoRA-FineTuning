import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getUsers, updateUserStatus, updateUserRole, type User } from '../../services/adminApi';
import { useAdminAuth } from '../../contexts/AdminAuthContext';
import './UserManagement.css';

const UserManagement: React.FC = () => {
  const { isSuperAdmin } = useAdminAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [perPage] = useState(10);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    fetchUsers();
  }, [page, search, roleFilter, statusFilter]);

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await getUsers(
        page,
        perPage,
        search || undefined,
        roleFilter || undefined,
        statusFilter
      );
      setUsers(response.data);
      setTotal(response.pagination.total);
    } catch (err: any) {
      setError(err.message || '사용자 목록을 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusToggle = async (userId: number, currentStatus: boolean) => {
    try {
      await updateUserStatus(userId, !currentStatus);
      fetchUsers();
    } catch (err: any) {
      alert(err.message || '상태 변경에 실패했습니다');
    }
  };

  const handleRoleChange = async (userId: number, newRole: 'user' | 'admin' | 'super_admin') => {
    try {
      await updateUserRole(userId, newRole);
      fetchUsers();
    } catch (err: any) {
      alert(err.message || '역할 변경에 실패했습니다');
    }
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="user-management-container">
      <nav className="dashboard-nav">
        <Link to="/admin/dashboard" className="nav-link">대시보드</Link>
        <Link to="/admin/users" className="nav-link active">사용자 관리</Link>
      </nav>
      <div className="content-wrapper">
        <h2>사용자 관리</h2>

      <div className="filters">
        <input
          type="text"
          placeholder="사용자명 또는 이메일 검색..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="search-input"
        />
        <select
          value={roleFilter}
          onChange={(e) => {
            setRoleFilter(e.target.value);
            setPage(1);
          }}
          className="filter-select"
        >
          <option value="">모든 역할</option>
          <option value="user">사용자</option>
          <option value="admin">관리자</option>
          <option value="super_admin">슈퍼 관리자</option>
        </select>
        <select
          value={statusFilter === undefined ? '' : statusFilter.toString()}
          onChange={(e) => {
            const value = e.target.value;
            setStatusFilter(value === '' ? undefined : value === 'true');
            setPage(1);
          }}
          className="filter-select"
        >
          <option value="">모든 상태</option>
          <option value="true">활성</option>
          <option value="false">비활성</option>
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">로딩 중...</div>
      ) : users.length === 0 ? (
        <div className="empty-state">
          <p>등록된 사용자가 없습니다.</p>
          <p className="empty-state-hint">사용자가 회원가입하면 여기에 표시됩니다.</p>
        </div>
      ) : (
        <>
          <table className="users-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>사용자명</th>
                <th>이메일</th>
                <th>역할</th>
                <th>상태</th>
                <th>생성일</th>
                <th>마지막 로그인</th>
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.username}</td>
                  <td>{user.email || '-'}</td>
                  <td>
                    {isSuperAdmin ? (
                      <select
                        value={user.role}
                        onChange={(e) =>
                          handleRoleChange(user.id, e.target.value as 'user' | 'admin' | 'super_admin')
                        }
                        className="role-select"
                      >
                        <option value="user">사용자</option>
                        <option value="admin">관리자</option>
                        <option value="super_admin">슈퍼 관리자</option>
                      </select>
                    ) : (
                      user.role
                    )}
                  </td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? '활성' : '비활성'}
                    </span>
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString('ko-KR')}</td>
                  <td>
                    {user.last_login
                      ? new Date(user.last_login).toLocaleDateString('ko-KR')
                      : '-'}
                  </td>
                  <td>
                    <button
                      onClick={() => handleStatusToggle(user.id, user.is_active)}
                      className={`status-toggle ${user.is_active ? 'deactivate' : 'activate'}`}
                    >
                      {user.is_active ? '비활성화' : '활성화'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="page-button"
            >
              이전
            </button>
            <span className="page-info">
              페이지 {page} / {totalPages} (총 {total}개)
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="page-button"
            >
              다음
            </button>
          </div>
        </>
      )}
      </div>
    </div>
  );
};

export default UserManagement;

