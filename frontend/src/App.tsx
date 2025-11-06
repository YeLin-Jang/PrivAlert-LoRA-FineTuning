import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { UserAuthProvider } from './contexts/UserAuthContext';
import AdminRouteGuard from './components/common/AdminRouteGuard';
import HomePage from './components/pages/HomePage';
import MyPage from './components/pages/MyPage';
import UploadForm from './components/upload/UploadForm';
import AdminRoutes from './routes/AdminRoutes';
import AuthRoutes from './routes/AuthRoutes';
import './App.css';

function App() {
  return (
    <UserAuthProvider>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AdminRouteGuard>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/mypage" element={<MyPage />} />
            <Route path="/analyze" element={
              <div className="App">
                <UploadForm />
              </div>
            } />
            {/* 관리자 경로는 별도 인증 시스템 사용 - 일반 사용자 접근 차단 */}
            <Route path="/admin/*" element={<AdminRoutes />} />
            <Route path="/auth/*" element={<AuthRoutes />} />
          </Routes>
        </AdminRouteGuard>
      </BrowserRouter>
    </UserAuthProvider>
  );
}

export default App;
