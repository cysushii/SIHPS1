import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function RoleGuard({ children, allowedRoles }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // If institute admin tries to hit aicte routes or vice-versa, redirect cleanly
    if (user.role === 'institute_admin') {
      return <Navigate to="/institute/dashboard" replace />;
    } else if (user.role === 'aicte_admin') {
      return <Navigate to="/aicte/overview" replace />;
    }
    return <Navigate to="/login" replace />;
  }

  return children;
}

