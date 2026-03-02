'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Send, Menu, FileText, Book, Code, Plus, Trash2 } from 'lucide-react';
import Editor from '@monaco-editor/react';

// 类型定义
interface ToolCall {
  id: string;
  name: string;
  args: Record<string, any>;
}

interface ToolResult {
  tool_call_id: string;
  name: string;
  result: any;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'thought' | 'tool' | 'error';
  content: string;
  tool_calls?: ToolCall[];
  tool_result?: ToolResult;
}

interface Session {
  id: string;
  name: string;
}

interface Skill {
  name: string;
  description: string;
  location: string;
}

export default function Home() {
  // 状态管理
  const [activeTab, setActiveTab] = useState<'chat' | 'memory' | 'skills'>('memory');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSession, setActiveSession] = useState<string>('main_session');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false);
  const [showFileModal, setShowFileModal] = useState(false);
  const [currentFile, setCurrentFile] = useState<{ path: string; content: string }>({ path: '', content: '' });
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionName, setEditingSessionName] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 加载会话列表
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const response = await fetch('/api/sessions');
        if (response.ok) {
          const data = await response.json();
          const sessionList = data.sessions.map((session: { session_id: string; session_name: string }) => ({
            id: session.session_id,
            name: session.session_name
          }));
          setSessions(sessionList);
          if (sessionList.length > 0) {
            setActiveSession(sessionList[0].id);
          }
        }
      } catch (error) {
        console.error('加载会话失败:', error);
      }
    };
    loadSessions();
  }, []);

  // 加载历史消息
  useEffect(() => {
    if (!activeSession) return;
    const loadHistory = async () => {
      try {
        const response = await fetch(`/api/history/${activeSession}`);
        if (response.ok) {
          const data = await response.json();
          const formattedMessages: Message[] = [];

          for (let i = 0; i < data.messages.length; i++) {
            const msg = data.messages[i];
            // 确保 content 是字符串
            const contentStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);

            if (msg.role === 'user') {
              formattedMessages.push({
                id: `hist_${i}_user`,
                role: 'user',
                content: contentStr
              });
            } else if (msg.role === 'assistant') {
              formattedMessages.push({
                id: `hist_${i}_assistant`,
                role: 'assistant',
                content: contentStr,
                tool_calls: msg.tool_calls
              });
            } else if (msg.role === 'tool') {
              formattedMessages.push({
                id: `hist_${i}_tool`,
                role: 'tool',
                content: contentStr,
                tool_result: {
                  tool_call_id: msg.tool_call_id,
                  name: msg.name,
                  result: msg.content // 保留原始结果（可能用于后续）
                }
              });
            }
          }
          setMessages(formattedMessages);
        }
      } catch (error) {
        console.error('加载会话历史失败:', error);
      }
    };
    loadHistory();
  }, [activeSession]);

  // 加载技能列表
  useEffect(() => {
    const loadSkills = async () => {
      try {
        const response = await fetch('/api/skills/list');
        if (response.ok) {
          const data = await response.json();
          setSkills(data.skills);
        } else {
          setSkills([
            {
              name: 'get_weather',
              description: '获取指定城市的实时天气信息',
              location: 'skills/get_weather/SKILL.md'
            }
          ]);
        }
      } catch (error) {
        console.error('加载技能失败:', error);
        setSkills([
          {
            name: 'get_weather',
            description: '获取指定城市的实时天气信息',
            location: 'skills/get_weather/SKILL.md'
          }
        ]);
      }
    };
    loadSkills();
  }, []);

  // 滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [messages]);

  // 发送消息
  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage
    };
    setMessages(prev => [...prev, userMsg]);
    setInputMessage('');
    setIsStreaming(true);

    const thoughtMsg: Message = {
      id: Date.now().toString() + '_thought',
      role: 'thought',
      content: '正在分析用户请求...'
    };
    setMessages(prev => [...prev, thoughtMsg]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputMessage,
          session_id: activeSession,
          stream: true
        })
      });

      if (response.ok && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        let currentAssistantMsg: Message | null = null;
        const pendingToolCalls = new Map<string, ToolCall>();
        let thoughtRemoved = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6);
              if (data === '[DONE]') continue;

              try {
                const event = JSON.parse(data);

                if (!thoughtRemoved && event.type !== 'thought') {
                  setMessages(prev => prev.filter(m => m.id !== thoughtMsg.id));
                  thoughtRemoved = true;
                }

                switch (event.type) {
                  case 'message_chunk':
                    if (!currentAssistantMsg) {
                      currentAssistantMsg = {
                        id: `assistant_${Date.now()}`,
                        role: 'assistant',
                        content: '',
                        tool_calls: []
                      };
                      setMessages(prev => [...prev, currentAssistantMsg!]);
                    }
                    currentAssistantMsg.content += event.content;
                    setMessages(prev =>
                      prev.map(m => m.id === currentAssistantMsg!.id ? currentAssistantMsg! : m)
                    );
                    break;

                  case 'tool_call':
                    if (currentAssistantMsg) {
                      const toolCalls = event.content as ToolCall[];
                      currentAssistantMsg.tool_calls = [
                        ...(currentAssistantMsg.tool_calls || []),
                        ...toolCalls
                      ];
                      toolCalls.forEach(tc => pendingToolCalls.set(tc.id, tc));
                      setMessages(prev =>
                        prev.map(m => m.id === currentAssistantMsg!.id ? currentAssistantMsg! : m)
                      );
                    }
                    break;

                  case 'tool_result':
                    const result = event.content;
                    // 确保结果是字符串形式显示
                    const resultContent = typeof result.result === 'string'
                      ? result.result
                      : JSON.stringify(result.result, null, 2);
                    const toolMsg: Message = {
                      id: `tool_${Date.now()}_${result.tool_call_id}`,
                      role: 'tool',
                      content: resultContent,
                      tool_result: {
                        tool_call_id: result.tool_call_id,
                        name: result.name,
                        result: result.result
                      }
                    };
                    setMessages(prev => [...prev, toolMsg]);
                    pendingToolCalls.delete(result.tool_call_id);
                    break;

                  case 'error':
                    setMessages(prev => [...prev, {
                      id: `error_${Date.now()}`,
                      role: 'error',
                      content: event.content
                    }]);
                    break;
                }
              } catch (e) {
                console.error('解析事件失败:', e);
              }
            }
          }
        }

        // 流结束后重新加载历史，确保一致性
        const historyResponse = await fetch(`/api/history/${activeSession}`);
        if (historyResponse.ok) {
          const data = await historyResponse.json();
          const formattedMessages: Message[] = [];
          for (let i = 0; i < data.messages.length; i++) {
            const msg = data.messages[i];
            const contentStr = typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content);
            if (msg.role === 'user') {
              formattedMessages.push({
                id: `hist_${i}_user`,
                role: 'user',
                content: contentStr
              });
            } else if (msg.role === 'assistant') {
              formattedMessages.push({
                id: `hist_${i}_assistant`,
                role: 'assistant',
                content: contentStr,
                tool_calls: msg.tool_calls
              });
            } else if (msg.role === 'tool') {
              formattedMessages.push({
                id: `hist_${i}_tool`,
                role: 'tool',
                content: contentStr,
                tool_result: {
                  tool_call_id: msg.tool_call_id,
                  name: msg.name,
                  result: msg.content
                }
              });
            }
          }
          setMessages(formattedMessages);
        }
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'error',
        content: `发送消息失败: ${error}`
      }]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const loadFileToEditor = async (path: string) => {
    try {
      const response = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
      if (response.ok) {
        const data = await response.json();
        const processedContent = data.content.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n');
        setCurrentFile({ path, content: processedContent });
        setShowFileModal(true);
      }
    } catch (error) {
      console.error('加载文件失败:', error);
      setCurrentFile({
        path,
        content: `# ${path}\n\n这是 ${path} 的默认内容`
      });
      setShowFileModal(true);
    }
  };

  const saveEditorContent = async () => {
    if (!currentFile.path) return;
    try {
      const response = await fetch('/api/files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: currentFile.path,
          content: currentFile.content
        })
      });
      if (response.ok) alert('文件保存成功');
    } catch (error) {
      console.error('保存文件失败:', error);
      alert('保存文件失败');
    }
  };

  const createNewSession = async () => {
    const newSessionId = `session_${Date.now()}`;
    const newSessionName = newSessionId;
    
    try {
      // 向后端发送请求，创建会话并添加到映射
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: newSessionId,
          session_name: newSessionName
        })
      });
      
      if (response.ok) {
        // 更新会话列表
        setSessions(prev => [...prev, { id: newSessionId, name: newSessionName }]);
        setActiveSession(newSessionId);
        setMessages([]);
      } else {
        alert('创建会话失败');
      }
    } catch (error) {
      console.error('创建会话失败:', error);
      alert('创建会话时发生错误');
    }
  };

  const deleteSession = async (sessionId: string) => {
    if (window.confirm('确定要删除这个会话吗？此操作不可恢复！')) {
      try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
        });

        if (response.ok) {
          setSessions(prev => prev.filter(session => session.id !== sessionId));
          
          if (activeSession === sessionId) {
            const remainingSessions = sessions.filter(s => s.id !== sessionId);
            if (remainingSessions.length > 0) {
              setActiveSession(remainingSessions[0].id);
            } else {
              setActiveSession('');
              setMessages([]);
            }
          }
        } else if (response.status === 404) {
          alert('会话不存在');
        } else {
          alert('删除会话失败');
        }
      } catch (error) {
        console.error('删除会话失败:', error);
        alert('删除会话时发生错误');
      }
    }
  };

  const startEditSession = (sessionId: string, currentName: string) => {
    setEditingSessionId(sessionId);
    setEditingSessionName(currentName);
  };

  const saveSessionName = async () => {
    if (!editingSessionId || !editingSessionName.trim()) return;
    
    try {
      const response = await fetch(`/api/sessions/${editingSessionId}/rename`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editingSessionName.trim() })
      });
      
      if (response.ok) {
        // 更新会话列表
        setSessions(prev => prev.map(session => 
          session.id === editingSessionId 
            ? { ...session, name: editingSessionName.trim() } 
            : session
        ));
        
        setEditingSessionId(null);
        setEditingSessionName('');
      } else {
        alert('重命名会话失败');
      }
    } catch (error) {
      console.error('重命名会话失败:', error);
      alert('重命名会话时发生错误');
    }
  };

  const cancelEditSession = () => {
    setEditingSessionId(null);
    setEditingSessionName('');
  };

  // 点击外部区域退出编辑状态
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (editingSessionId) {
        const target = event.target as HTMLElement;
        // 检查点击的元素是否在编辑区域内
        const editingElement = document.querySelector(`[data-session-id="${editingSessionId}"]`);
        if (editingElement && !editingElement.contains(target)) {
          cancelEditSession();
        }
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  }, [editingSessionId]);

  return (
    <div className="app-shell flex h-screen overflow-hidden bg-gray-50">
      {/* 左侧会话侧边栏 */}
      {!sidebarCollapsed ? (
        <div className="sidebar flex flex-col w-80 bg-white border-r border-gray-200">
          <div className="sidebar-header p-5">
            <div className="flex items-center justify-between mb-6">
              <h1 className="text-xl font-bold text-blue-600 flex items-center">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-blue-400 flex items-center justify-center text-white mr-3">
                  <FileText className="w-5 h-5" />
                </div>
                Mini OpenClaw
              </h1>
              <button
                onClick={() => setSidebarCollapsed(true)}
                className="p-2 rounded-md hover:bg-gray-100 transition-colors"
              >
                <Menu className="w-5 h-5" />
              </button>
            </div>
            <button
              onClick={createNewSession}
              className="w-full flex items-center gap-3 p-2 rounded-md border border-gray-300 hover:bg-gray-100 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>

          <div className="flex-1 overflow-auto p-5">
            <h2 className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wider">Recent</h2>
            <div className="space-y-3">
              {sessions.map(session => (
                <div
                  key={session.id}
                  data-session-id={session.id}
                  className={`flex items-center justify-between p-2 rounded-md cursor-pointer ${
                    activeSession === session.id ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100'
                  }`}
                  onClick={() => setActiveSession(session.id)}
                >
                  {editingSessionId === session.id ? (
                    <div className="flex-1 flex items-center gap-2">
                      <input
                        type="text"
                        value={editingSessionName}
                        onChange={(e) => setEditingSessionName(e.target.value)}
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            e.stopPropagation();
                            saveSessionName();
                          }
                        }}
                        className="w-40 px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        autoFocus
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          saveSessionName();
                        }}
                        className="p-1 text-green-600 hover:bg-green-100 rounded-md"
                        title="保存"
                      >
                        ✓
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelEditSession();
                        }}
                        className="p-1 text-gray-600 hover:bg-gray-100 rounded-md"
                        title="取消"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <>
                      <span className="text-sm font-medium truncate">{session.name}</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startEditSession(session.id, session.name);
                          }}
                          className="p-1 rounded-md hover:bg-gray-200 transition-colors"
                          title="重命名"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                          }}
                          className="p-1 rounded-md hover:bg-gray-200 transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="sidebar-collapsed w-16 flex flex-col items-center py-6 bg-white border-r border-gray-200">
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="p-2 mb-6 rounded-md hover:bg-gray-100"
          >
            <Menu className="w-5 h-5" />
          </button>
          <button
            onClick={createNewSession}
            className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 transition-all mb-6"
            title="New Chat"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* 中间聊天区域 */}
      <div className="main-content flex flex-col flex-1 bg-gray-50">
        <div className="topbar sticky top-0 z-10 p-5 bg-white border-b border-gray-200">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-blue-400 flex items-center justify-center text-white">
                <FileText className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-medium">{activeSession}</h2>
            </div>
            <div className="flex items-center gap-6">
              <a
                href="https://chat.deepseek.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:underline font-medium"
              >
                jerry🐱来了
              </a>
              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                <div className="w-5 h-5 rounded-full bg-blue-600"></div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-8">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center mb-6">
                <FileText className="w-10 h-10 text-blue-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Welcome to Mini OpenClaw</h3>
              <p className="text-gray-500 mb-8 max-w-md">
                Start a new chat to interact with your AI assistant. You can ask questions, run code, and more.
              </p>
              <button
                onClick={createNewSession}
                className="flex items-center gap-3 px-6 py-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-all"
              >
                <Plus className="w-5 h-5" />
                New Chat
              </button>
            </div>
          ) : (
            <div className="space-y-8">
              {messages.map(message => (
                <div
                  key={message.id}
                  className={`p-4 rounded-lg ${message.role === 'user' ? 'bg-blue-600 text-white ml-auto max-w-3xl' :
                      message.role === 'assistant' ? 'bg-white border border-gray-200 max-w-3xl' :
                        message.role === 'thought' ? 'bg-purple-50 border border-purple-200 max-w-3xl' :
                          message.role === 'tool' ? 'bg-green-50 border border-green-200 max-w-3xl' :
                            message.role === 'error' ? 'bg-red-50 border border-red-200 text-red-600 max-w-3xl' :
                              'bg-gray-50 border border-gray-200 max-w-3xl'
                    }`}
                >
                  <div className="font-medium mb-2 text-sm">
                    {message.role === 'user' ? 'You' :
                      message.role === 'assistant' ? 'Assistant' :
                        message.role === 'thought' ? 'Thinking' :
                          message.role === 'tool' ? 'Tool' :
                            message.role === 'error' ? 'Error' : ''}
                  </div>

                  {message.role === 'assistant' && (
                    <>
                      <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                      {message.tool_calls && message.tool_calls.length > 0 && (
                        <div className="mt-3 space-y-2 border-t pt-2">
                          {message.tool_calls.map(tc => (
                            <div key={tc.id} className="bg-blue-100 p-2 rounded text-xs">
                              🔧 调用工具 <span className="font-mono">{tc.name}</span> 参数: {JSON.stringify(tc.args)}
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  {message.role === 'tool' && (
                    <div className="text-sm">
                      <div className="text-xs text-gray-500 mb-1">
                        工具: {message.tool_result?.name} (调用ID: {message.tool_result?.tool_call_id})
                      </div>
                      <pre className="whitespace-pre-wrap bg-green-100 p-2 rounded">
                        {message.content}
                      </pre>
                    </div>
                  )}

                  {!['assistant', 'tool'].includes(message.role) && (
                    <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                  )}
                </div>
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-area p-5 bg-white border-t border-gray-200">
          <div className="flex gap-3">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask Mini OpenClaw anything..."
              className="flex-1 p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              disabled={isStreaming}
            />
            <button
              onClick={handleSendMessage}
              className="self-end px-4 py-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isStreaming || !inputMessage.trim()}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <div className="mt-3 text-xs text-gray-500 flex justify-between items-center">
            <span>Powered by DeepSeek • mini OpenClaw v0.1</span>
            <span className="text-blue-600/70">AI Assistant</span>
          </div>
        </div>
      </div>

      {/* 右侧编辑器/检查器 */}
      {!inspectorCollapsed ? (
        <div className="inspector flex flex-col w-80 bg-white border-l border-gray-200">
          <div className="panel-header flex justify-between items-center p-5 border-b border-gray-200">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setActiveTab('memory')}
                className={`flex items-center gap-2 px-2 py-1 rounded-md ${activeTab === 'memory' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100'
                  }`}
              >
                <Book className="w-5 h-5" />
                Memory
              </button>
              <button
                onClick={() => setActiveTab('skills')}
                className={`flex items-center gap-2 px-2 py-1 rounded-md ${activeTab === 'skills' ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100'
                  }`}
              >
                <Code className="w-5 h-5" />
                Skills
              </button>
            </div>
            <button
              onClick={() => setInspectorCollapsed(true)}
              className="p-2 rounded-md hover:bg-gray-100"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>

          {activeTab === 'memory' && (
            <div className="p-5 flex-1 overflow-auto">
              <h3 className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wider">Workspace</h3>
              <div className="space-y-3">
                {[
                  { name: 'MEMORY.md', size: '72k' },
                  { name: 'SOUL.md', size: '3.1kb' },
                  { name: 'IDENTITY.md', size: '1.1kb' },
                  { name: 'USER.md', size: '860b' },
                  { name: 'AGENTS.md', size: '551b' },
                  { name: 'SKILLS_SNAPSHOT.md', size: '1.2kb' }
                ].map(file => (
                  <button
                    key={file.name}
                    onClick={() => loadFileToEditor(file.name)}
                    className="w-full text-left p-3 rounded-lg hover:bg-gray-100 flex justify-between items-center transition-all"
                  >
                    <span className="font-medium">{file.name}</span>
                    <span className="text-xs text-gray-400">{file.size}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'skills' && (
            <div className="p-5 flex-1 overflow-auto">
              <h3 className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wider">Skills</h3>
              <div className="space-y-3">
                {skills.map(skill => (
                  <button
                    key={skill.name}
                    onClick={() => loadFileToEditor(skill.location)}
                    className="w-full text-left p-3 rounded-lg hover:bg-gray-100 transition-all"
                  >
                    <div className="font-medium">{skill.name}</div>
                    <div className="text-sm text-gray-600 mt-1">{skill.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="inspector-collapsed w-16 flex flex-col items-center py-6 bg-white border-l border-gray-200">
          <button
            onClick={() => setInspectorCollapsed(false)}
            className="p-2 mb-6 rounded-md hover:bg-gray-100"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* 文件编辑模态框 */}
      {showFileModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-2xl w-[70vw] max-w-[70vw] h-[80vh] max-h-[80vh] flex flex-col">
            <div className="p-5 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-medium">{currentFile.path}</h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={saveEditorContent}
                  className="px-4 py-2 rounded-md border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => setShowFileModal(false)}
                  className="px-4 py-2 rounded-md border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-5">
              <Editor
                height="100%"
                defaultLanguage="markdown"
                value={currentFile.content}
                onChange={(value) => setCurrentFile({ ...currentFile, content: value || '' })}
                options={{
                  theme: 'vs-light',
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 14,
                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                  lineNumbers: 'on',
                  wordWrap: 'on',
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}