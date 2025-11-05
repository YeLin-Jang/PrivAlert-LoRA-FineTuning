import { BrowserRouter, Routes, Route } from 'react-router-dom';
import UploadForm from './components/UploadForm';
import AdminRoutes from './routes/AdminRoutes';
import AuthRoutes from './routes/AuthRoutes';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={
          <div className="App">
            <UploadForm />
          </div>
        } />
        <Route path="/admin/*" element={<AdminRoutes />} />
        <Route path="/auth/*" element={<AuthRoutes />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
