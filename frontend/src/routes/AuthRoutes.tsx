import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { UserAuthProvider } from '../contexts/UserAuthContext';
import Signup from '../components/auth/Signup';
import EmailVerification from '../components/auth/EmailVerification';
import Login from '../components/auth/Login';

const AuthRoutes: React.FC = () => {
  return (
    <UserAuthProvider>
      <Routes>
        <Route path="signup" element={<Signup />} />
        <Route path="verify" element={<EmailVerification />} />
        <Route path="login" element={<Login />} />
        <Route path="" element={<Navigate to="login" replace />} />
      </Routes>
    </UserAuthProvider>
  );
};

export default AuthRoutes;
