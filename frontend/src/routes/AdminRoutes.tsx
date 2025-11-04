import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AdminAuthProvider } from '../contexts/AdminAuthContext';
import ProtectedRoute from '../components/admin/ProtectedRoute';
import AdminLogin from '../components/admin/AdminLogin';
import Dashboard from '../components/admin/Dashboard';
import UserManagement from '../components/admin/UserManagement';

const AdminRoutes: React.FC = () => {
  return (
    <AdminAuthProvider>
      <Routes>
        <Route path="/login" element={<AdminLogin />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/users"
          element={
            <ProtectedRoute>
              <UserManagement />
            </ProtectedRoute>
          }
        />
        <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      </Routes>
    </AdminAuthProvider>
  );
};

export default AdminRoutes;

