'use client';

import React, { useState, useEffect } from 'react';
import LoginForm from './components/LoginForm';
import AppContent from './components/AppContent';

export default function Home() {
  // 登录状态 - 初始设为true，避免刷新时闪过登录页面
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(true);
  const [currentUser, setCurrentUser] = useState<{ id: string; username?: string } | null>(null);

  // 检查登录状态
  useEffect(() => {
    const checkLoginStatus = () => {
      const user_id = localStorage.getItem('user_id');
      const token = localStorage.getItem('token');
      const username = localStorage.getItem('username');
      console.log('Check login status - User ID:', user_id, 'Username:', username, 'Token:', token);
      if (user_id && token) {
        const user = { id: user_id };
        if (username) {
          user.username = username;
        }
        setCurrentUser(user);
        setIsLoggedIn(true);
      } else {
        // 只有在没有登录信息时才设置为false
        setIsLoggedIn(false);
        setCurrentUser(null);
      }
    };
    checkLoginStatus();
  }, []);

  // 登录处理
  const handleLogin = (user: { id: string; username?: string }) => {
    setCurrentUser(user);
    setIsLoggedIn(true);
    console.log('Login handled - User:', user, 'Token:', localStorage.getItem('token'));
  };

  // 登出处理
  const handleLogout = async () => {
    try {
      // 调用后端logout接口
      const token = localStorage.getItem('token');
      const user_id = localStorage.getItem('user_id');
      
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
      localStorage.removeItem('user_id');
      localStorage.removeItem('token');
      localStorage.removeItem('username');
    }
  };

  // 初始加载时，isLoggedIn为true但currentUser可能为null，需要等待检查登录状态完成
  if (isLoggedIn && currentUser) {
    return <AppContent currentUser={currentUser} onLogout={handleLogout} />;
  } else if (!isLoggedIn) {
    return <LoginForm onLogin={handleLogin} />;
  }
  // 加载中状态，返回null或加载指示器
  return null;
}