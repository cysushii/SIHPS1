import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { RoleGuard } from './components/RoleGuard';
import { Login } from './pages/Login';
import { InstitutePortal } from './pages/institute/InstitutePortal';
import { AictePortal } from './pages/aicte/AictePortal';
import { StudentVerify } from './pages/public/StudentVerify';
import { DocumentVerifier } from './pages/public/DocumentVerify';

export default function App() {
  const { user } = useAuth();

  return (
    <Routes>
      {/* Root redirect based on role */}
      <Route
        path="/"
        element={
          user?.role === 'institute_admin' ? (
            <Navigate to="/institute/dashboard" replace />
          ) : user?.role === 'aicte_admin' ? (
            <Navigate to="/aicte/overview" replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      {/* Public Pages */}
      <Route path="/login" element={<Login />} />
      <Route path="/verify/:token" element={<StudentVerify />} />
      <Route path="/verify-document" element={<DocumentVerifier />} />

      {/* Institute Portal Routes */}
      <Route
        path="/institute/dashboard"
        element={
          <RoleGuard allowedRoles={['institute_admin']}>
            <InstitutePortal />
          </RoleGuard>
        }
      />

      {/* AICTE Portal Routes */}
      <Route
        path="/aicte/*"
        element={
          <RoleGuard allowedRoles={['aicte_admin']}>
            <AictePortal />
          </RoleGuard>
        }
      />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
