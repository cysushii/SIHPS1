import React, { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentUser, authApi } from '../api/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getCurrentUser());
  const [loading, setLoading] = useState(false);

  const login = async (username, role, instituteId = null) => {
    setLoading(true);
    try {
      await authApi.login(username, role, instituteId);
      const currentUser = getCurrentUser();
      setUser(currentUser);
      return currentUser;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

