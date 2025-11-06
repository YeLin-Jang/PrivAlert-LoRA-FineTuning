import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { UserAuthProvider } from './contexts/UserAuthContext';
import HomePage from './components/pages/HomePage';
import MyPage from './components/pages/MyPage';
import UploadForm from './components/upload/UploadForm';
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
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/mypage" element={<MyPage />} />
          <Route path="/analyze" element={
            <div className="App">
              <UploadForm />
            </div>
          } />
          <Route path="/auth/*" element={<AuthRoutes />} />
        </Routes>
      </BrowserRouter>
    </UserAuthProvider>
  );
}

export default App;
