/**
 * 관리자 페이지 접근 차단 컴포넌트
 * 보안: 일반 사용자가 관리자 경로에 접근하지 못하도록 완전히 차단
 */
import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUserAuth } from '../../contexts/UserAuthContext';

/**
 * 관리자 경로 접근 시 일반 사용자를 홈으로 리다이렉트
 * 관리자 페이지는 완전히 별도 인증 시스템을 사용하므로
 * 일반 사용자 인증 상태와 무관하게 항상 차단
 */
export default function AdminRouteGuard({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useUserAuth();

  useEffect(() => {
    // 관리자 경로 접근 시도 감지 (로그인 페이지 제외)
    if (location.pathname.startsWith('/admin') && !location.pathname.startsWith('/admin/login')) {
      // 일반 사용자는 관리자 페이지 접근 불가 (로그인 페이지는 허용)
      // 관리자 인증은 별도 시스템(/admin/login)을 사용
      navigate('/', { replace: true });
    }
  }, [location.pathname, navigate, isAuthenticated]);

  // 관리자 경로에서는 로그인 페이지를 제외하고 null 반환 (렌더링 방지)
  if (location.pathname.startsWith('/admin') && !location.pathname.startsWith('/admin/login')) {
    return null;
  }

  return <>{children}</>;
}

