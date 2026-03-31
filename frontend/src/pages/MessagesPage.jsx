import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Bell, Chat, EnvelopeSimple } from '@phosphor-icons/react';
import { apiGet, apiPut } from '../lib/api';

export default function MessagesPage({ user }) {
  const [notifications, setNotifications] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeTab, setActiveTab] = useState('notifications');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [notifs, msgs] = await Promise.all([
        apiGet('/api/notifications'),
        apiGet('/api/messages'),
      ]);
      setNotifications(notifs);
      setMessages(msgs);
    } catch (e) { console.error(e); }
  };

  const markRead = async (id) => {
    try {
      await apiPut(`/api/notifications/${id}/read`, {});
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (e) { console.error(e); }
  };

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="messages-page">
      <div>
        <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Messages & Notifications
        </h1>
        <p className="text-sm text-[#94A3B8]">Stay connected with your learning community</p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 p-1 bg-[#0F172A] border border-[#1E293B] rounded-md w-fit">
        {['notifications', 'messages'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium rounded transition-all ${
              activeTab === tab
                ? 'bg-[#D4AF37] text-[#050814]'
                : 'text-[#94A3B8] hover:text-[#F8FAFC]'
            }`}
            data-testid={`tab-${tab}`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'notifications' && (
        <div className="space-y-2">
          {notifications.length === 0 ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-8 text-center">
                <Bell size={40} weight="duotone" className="text-[#D4AF37] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">No notifications yet</p>
              </CardContent>
            </Card>
          ) : (
            notifications.map(n => (
              <Card
                key={n.id}
                className={`bg-[#0F172A] border-[#1E293B] cursor-pointer transition-all hover:border-[#D4AF37]/20 ${!n.read ? 'border-l-2 border-l-[#D4AF37]' : ''}`}
                onClick={() => !n.read && markRead(n.id)}
                data-testid={`notification-${n.id}`}
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <Bell size={16} weight="duotone" className={n.read ? 'text-[#94A3B8]' : 'text-[#D4AF37]'} />
                  <div className="flex-1">
                    <p className="text-sm text-[#F8FAFC]">{n.title}</p>
                    <p className="text-xs text-[#94A3B8]">{n.message}</p>
                  </div>
                  <span className="text-[10px] text-[#94A3B8]">{new Date(n.created_at).toLocaleDateString()}</span>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'messages' && (
        <div className="space-y-2">
          {messages.length === 0 ? (
            <Card className="bg-[#0F172A] border-[#1E293B]">
              <CardContent className="p-8 text-center">
                <EnvelopeSimple size={40} weight="duotone" className="text-[#D4AF37] mx-auto mb-3" />
                <p className="text-sm text-[#94A3B8]">No messages yet</p>
              </CardContent>
            </Card>
          ) : (
            messages.map(msg => (
              <Card key={msg.id} className="bg-[#0F172A] border-[#1E293B]" data-testid={`message-${msg.id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-[#F8FAFC]">{msg.sender_name || 'Unknown'}</span>
                    <span className="text-[10px] text-[#94A3B8]">{new Date(msg.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-[#94A3B8]">{msg.message}</p>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}
