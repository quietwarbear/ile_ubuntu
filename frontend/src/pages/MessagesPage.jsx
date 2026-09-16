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
        <h1 className="text-3xl font-light text-[rgb(var(--text-main))]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>
          Messages & Notifications
        </h1>
        <p className="text-sm text-[rgb(var(--text-muted))]">Stay connected with your learning community</p>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 p-1 bg-[rgb(var(--ink-card))] border border-[rgb(var(--ink-border))] rounded-md w-fit">
        {['notifications', 'messages'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-medium rounded transition-all ${
              activeTab === tab
                ? 'bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))]'
                : 'text-[rgb(var(--text-muted))] hover:text-[rgb(var(--text-main))]'
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
            <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
              <CardContent className="p-8 text-center">
                <Bell size={40} weight="duotone" className="text-[rgb(var(--gold))] mx-auto mb-3" />
                <p className="text-sm text-[rgb(var(--text-muted))]">No notifications yet</p>
              </CardContent>
            </Card>
          ) : (
            notifications.map(n => (
              <Card
                key={n.id}
                className={`bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))] cursor-pointer transition-all hover:border-[rgb(var(--gold)/0.2)] ${!n.read ? 'border-l-2 border-l-[rgb(var(--gold))]' : ''}`}
                onClick={() => !n.read && markRead(n.id)}
                data-testid={`notification-${n.id}`}
              >
                <CardContent className="p-4 flex items-center gap-3">
                  <Bell size={16} weight="duotone" className={n.read ? 'text-[rgb(var(--text-muted))]' : 'text-[rgb(var(--gold))]'} />
                  <div className="flex-1">
                    <p className="text-sm text-[rgb(var(--text-main))]">{n.title}</p>
                    <p className="text-xs text-[rgb(var(--text-muted))]">{n.message}</p>
                  </div>
                  <span className="text-[10px] text-[rgb(var(--text-muted))]">{new Date(n.created_at).toLocaleDateString()}</span>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'messages' && (
        <div className="space-y-2">
          {messages.length === 0 ? (
            <Card className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]">
              <CardContent className="p-8 text-center">
                <EnvelopeSimple size={40} weight="duotone" className="text-[rgb(var(--gold))] mx-auto mb-3" />
                <p className="text-sm text-[rgb(var(--text-muted))]">No messages yet</p>
              </CardContent>
            </Card>
          ) : (
            messages.map(msg => (
              <Card key={msg.id} className="bg-[rgb(var(--ink-card))] border-[rgb(var(--ink-border))]" data-testid={`message-${msg.id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-[rgb(var(--text-main))]">{msg.sender_name || 'Unknown'}</span>
                    <span className="text-[10px] text-[rgb(var(--text-muted))]">{new Date(msg.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-[rgb(var(--text-muted))]">{msg.message}</p>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
}
