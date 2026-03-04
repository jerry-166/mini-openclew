'use client';

import React, { useState } from 'react';
import { LogIn, FileText } from 'lucide-react';

interface LoginFormProps {
  onLogin: (user: { id: string }) => void;
}

export default function LoginForm({ onLogin }: LoginFormProps) {
  const [userName, setUserName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [loginError, setLoginError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleLogin = async () => {
    setLoginError('');
    setIsLoading(true);
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName, password })
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Login response:', data);
        const user = { id: data.user_id };
        // 存储token到localStorage
        localStorage.setItem('token', data.token);
        console.log('Token stored:', data.token);
        onLogin(user);
      } else {
        const errorData = await response.json();
        setLoginError(errorData.detail || '登录失败');
      }
    } catch (error) {
      console.error('登录失败:', error);
      setLoginError('登录时发生错误');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-600 to-blue-400 flex items-center justify-center text-white mx-auto mb-4">
            <FileText className="w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800">Mini OpenClaw</h1>
          <p className="text-gray-600 mt-2">请登录以使用系统</p>
        </div>
        
        {loginError && (
          <div className="bg-red-100 text-red-700 p-3 rounded-md mb-4">
            {loginError}
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              用户名
            </label>
            <input
              type="text"
              id="username"
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入用户名"
              disabled={isLoading}
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              密码
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入密码"
              disabled={isLoading}
            />
          </div>
          <button
            onClick={handleLogin}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading || !userName || !password}
          >
            <LogIn className="w-5 h-5" />
            {isLoading ? '登录中...' : '登录'}
          </button>
        </div>
        
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>默认账号: admin</p>
          <p>默认密码: 1234</p>
        </div>
      </div>
    </div>
  );
}