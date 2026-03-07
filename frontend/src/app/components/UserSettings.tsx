'use client';

import React, { useState } from 'react';
import { User, Lock, Edit, Check, X, Settings, Eye, EyeOff } from 'lucide-react';

interface UserSettingsProps {
  user_id: string;
  onClose: () => void;
}

export default function UserSettings({ user_id, onClose }: UserSettingsProps) {
  // 状态管理
  const [activeTab, setActiveTab] = useState<'profile' | 'password'>('profile');
  const [username, setUsername] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // 获取用户信息
  React.useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setError('请先登录');
          return;
        }
        
        const response = await fetch(`/api/user/info?user_id=${user_id}`, {
          headers: {
            'X-Token': token,
            'X-User-Id': user_id
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setUsername(data.user_info.username);
          setNewUsername(data.user_info.username);
        } else {
          const errorData = await response.json();
          setError(errorData.detail || '获取用户信息失败');
        }
      } catch (error) {
        console.error('获取用户信息失败:', error);
        setError('获取用户信息失败，请稍后重试');
      }
    };
    
    fetchUserInfo();
  }, [user_id]);

  // 获取认证头
  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    const user_id = localStorage.getItem('user_id');
    const headers: Record<string, string> = {};
    if (token) {
      headers['X-Token'] = token;
    }
    if (user_id) {
      headers['X-User-Id'] = user_id;
    }
    return headers;
  };

  // 处理修改用户名
  const handleUpdateUsername = async () => {
    if (!newUsername.trim()) {
      setError('用户名不能为空');
      return;
    }
    
    if (newUsername === username) {
      setError('新用户名与当前用户名相同');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await fetch('/api/user/update-username', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          user_id: parseInt(user_id),
          new_username: newUsername
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setUsername(newUsername);
        setSuccess('修改用户名成功');
        // 更新localStorage中的用户名
        localStorage.setItem('username', newUsername);
        // 通知父组件更新用户名
        window.dispatchEvent(new CustomEvent('usernameUpdated', { detail: { username: newUsername } }));
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '修改用户名失败');
      }
    } catch (error) {
      console.error('修改用户名失败:', error);
      setError('修改用户名失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // 处理修改密码
  const handleUpdatePassword = async () => {
    if (!oldPassword || !newPassword || !confirmPassword) {
      setError('请填写所有密码字段');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      setError('两次输入的新密码不一致');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await fetch('/api/user/update-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          user_id: parseInt(user_id),
          old_password: oldPassword,
          new_password: newPassword
        })
      });
      
      if (response.ok) {
        setOldPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setSuccess('修改密码成功');
      } else {
        const errorData = await response.json();
        setError(errorData.detail || '修改密码失败');
      }
    } catch (error) {
      console.error('修改密码失败:', error);
      setError('修改密码失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-md p-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <Settings className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-bold">用户设置</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 错误和成功消息 */}
        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded-md mb-4">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-100 text-green-700 p-3 rounded-md mb-4">
            {success}
          </div>
        )}

        {/* 标签页 */}
        <div className="border-b border-gray-200 mb-4">
          <div className="flex">
            <button
              onClick={() => setActiveTab('profile')}
              className={`px-4 py-2 font-medium ${activeTab === 'profile' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              个人资料
            </button>
            <button
              onClick={() => setActiveTab('password')}
              className={`px-4 py-2 font-medium ${activeTab === 'password' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              修改密码
            </button>
          </div>
        </div>

        {/* 个人资料标签页 */}
        {activeTab === 'profile' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                用户名
              </label>
              <div>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <button
              onClick={handleUpdateUsername}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? (
                <span>修改中...</span>
              ) : (
                <>
                  <Check className="w-5 h-5" />
                  <span>保存修改</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* 修改密码标签页 */}
        {activeTab === 'password' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                旧密码
              </label>
              <div>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                新密码
              </label>
              <div>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                确认新密码
              </label>
              <div>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <button
              onClick={handleUpdatePassword}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? (
                <span>修改中...</span>
              ) : (
                <>
                  <Check className="w-5 h-5" />
                  <span>修改密码</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
