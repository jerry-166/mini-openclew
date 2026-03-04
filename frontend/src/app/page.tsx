'use client';

import React, { useState, useEffect } from 'react';
import LoginForm from './components/LoginForm';
import AppContent from './components/AppContent';

export default function Home() {
  // 登录状态
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<{ id: string } | null>(null);

  // 检查登录状态
  useEffect(() => {
    const checkLoginStatus = () => {
      const user = localStorage.getItem('user');
      const token = localStorage.getItem('token');
      console.log('Check login status - User:', user, 'Token:', token);
      if (user && token) {
        setCurrentUser(JSON.parse(user));
        setIsLoggedIn(true);
      }
    };
    checkLoginStatus();
  }, []);

  // 登录处理
  const handleLogin = (user: { id: string }) => {
    setCurrentUser(user);
    setIsLoggedIn(true);
    localStorage.setItem('user', JSON.stringify(user));
    console.log('Login handled - User:', user, 'Token:', localStorage.getItem('token'));
  };

  // 登出处理
  const handleLogout = async () => {
    try {
      // 调用后端logout接口
      const token = localStorage.getItem('token');
      const user = localStorage.getItem('user');
      const user_id = user ? JSON.parse(user).id : null;
      
      if (token && user_id) {
        const response = await fetch('/api/logout', {
          method: 'DELETE',
          headers: {
            'X-Token': token,
            'X-User-Id': user_id
          }
        });
        
        if (response.ok) {
          console.log('Logout successful');
        }
      }
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      // 无论后端是否成功，都清除本地存储
      setIsLoggedIn(false);
      setCurrentUser(null);
      localStorage.removeItem('user');
      localStorage.removeItem('token');
    }
  };

  return isLoggedIn && currentUser ? (
    <AppContent currentUser={currentUser} onLogout={handleLogout} />
  ) : (
    <LoginForm onLogin={handleLogin} />
  );
}