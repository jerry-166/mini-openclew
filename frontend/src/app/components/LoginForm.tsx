'use client';

import React, { useState } from 'react';
import { LogIn, UserPlus, FileText } from 'lucide-react';

interface LoginFormProps {
  onLogin: (user: { id: string }) => void;
}

export default function LoginForm({ onLogin }: LoginFormProps) {
  const [userName, setUserName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRegister, setIsRegister] = useState<boolean>(false);

  const handleLogin = async () => {
    setError('');
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
        
        // 获取用户信息
        const userInfoResponse = await fetch(`/api/user/info?user_id=${data.user_id}`, {
          headers: {
            'X-Token': data.token,
            'X-User-Id': data.user_id
          }
        });
        
        let user = { id: data.user_id };
        if (userInfoResponse.ok) {
          const userInfoData = await userInfoResponse.json();
          user = {
            id: data.user_id,
            username: userInfoData.user_info.username
          };
          localStorage.setItem('username', userInfoData.user_info.username);
        }
        
        // 存储token到localStorage
        localStorage.setItem('token', data.token);
        localStorage.setItem('user_id', data.user_id);
        console.log('Token stored:', data.token);
        onLogin(user);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '登录失败');
      }
    } catch (error) {
      console.error('登录失败:', error);
      setError('登录时发生错误');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async () => {
    setError('');
    setIsLoading(true);
    try {
      console.log('开始注册，用户名:', userName, '密码:', password);
      const response = await fetch('/api/user/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: userName, password })
      });
      
      console.log('注册响应状态:', response.status, '响应头:', response.headers);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Register response:', data);
        
        // 获取用户信息
        const userInfoResponse = await fetch(`/api/user/info?user_id=${data.user_id}`, {
          headers: {
            'X-Token': data.token,
            'X-User-Id': data.user_id
          }
        });
        
        let user = { id: data.user_id };
        if (userInfoResponse.ok) {
          const userInfoData = await userInfoResponse.json();
          user = {
            id: data.user_id,
            username: userInfoData.user_info.username
          };
          localStorage.setItem('username', userInfoData.user_info.username);
        }
        
        // 存储token到localStorage
        localStorage.setItem('token', data.token);
        localStorage.setItem('user_id', data.user_id);
        console.log('Token stored:', data.token, 'User ID stored:', data.user_id);
        console.log('调用onLogin函数，用户信息:', user);
        onLogin(user);
      } else {
        console.log('注册失败，状态码:', response.status);
        try {
          const errorData = await response.json();
          console.log('错误信息:', errorData);
          setError(errorData.detail || '注册失败');
        } catch (e) {
          console.error('解析错误信息失败:', e);
          setError('注册失败，请稍后重试');
        }
      }
    } catch (error) {
      console.error('注册失败:', error);
      setError('注册时发生错误');
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
          <p className="text-gray-600 mt-2">{isRegister ? '请注册以使用系统' : '请登录以使用系统'}</p>
        </div>
        
        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded-md mb-4">
            {error}
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
            onClick={isRegister ? handleRegister : handleLogin}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading || !userName || !password}
          >
            {isRegister ? <UserPlus className="w-5 h-5" /> : <LogIn className="w-5 h-5" />}
            {isLoading ? (isRegister ? '注册中...' : '登录中...') : (isRegister ? '注册' : '登录')}
          </button>
        </div>
        
        <div className="mt-4 text-center">
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            disabled={isLoading}
          >
            {isRegister ? '已有账号？立即登录' : '没有账号？立即注册'}
          </button>
        </div>
        
        {!isRegister && (
          <div className="mt-6 text-center text-sm text-gray-500">
            <p>默认账号: admin</p>
            <p>默认密码: 1234</p>
          </div>
        )}
      </div>
    </div>
  );
}