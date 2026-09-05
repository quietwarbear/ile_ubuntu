import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { apiGet, apiPost, apiDelete } from '../../lib/api';

const when = (value) => {
  if (!value) return '';
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? ''
    : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

function Byline({ post }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-medium text-[#F8FAFC]">{post.author_name || 'Someone'}</span>
      {post.is_instructor && (
        <span className="rounded-full bg-[#D4AF37]/15 px-2 py-0.5 text-[10px] font-medium text-[#D4AF37]">
          Teacher
        </span>
      )}
      <span className="text-[10px] text-[#94A3B8]">{when(post.created_at)}</span>
      {post.edited && <span className="text-[10px] text-[#64748B]">edited</span>}
    </div>
  );
}

/**
 * The class discussion room. Anyone in the course opens a topic and anyone
 * replies, teachers included. Teachers additionally pin, lock and remove.
 */
export function CourseDiscussion({ courseId, user, isStaff }) {
  const [topics, setTopics] = useState([]);
  const [openTopic, setOpenTopic] = useState(null);   // { topic, posts }
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ title: '', content: '' });
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const base = `/api/courses/${courseId}/discussion`;

  const loadTopics = useCallback(async () => {
    try {
      const res = await apiGet(`${base}/topics`);
      setTopics(res.topics || []);
    } catch (e) { setError(e.message); }
  }, [base]);

  useEffect(() => { loadTopics(); }, [loadTopics]);

  const openThread = async (topicId) => {
    setError('');
    try {
      setOpenTopic(await apiGet(`${base}/topics/${topicId}`));
      setReply('');
    } catch (e) { setError(e.message); }
  };

  const startTopic = async () => {
    if (!form.title.trim() || !form.content.trim()) return;
    setBusy(true); setError('');
    try {
      const res = await apiPost(`${base}/topics`, form);
      setForm({ title: '', content: '' });
      setShowNew(false);
      await loadTopics();
      await openThread(res.topic.id);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const postReply = async () => {
    if (!reply.trim()) return;
    setBusy(true); setError('');
    try {
      await apiPost(`${base}/topics/${openTopic.topic.id}/posts`, { content: reply });
      setReply('');
      await openThread(openTopic.topic.id);
      await loadTopics();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const toggle = async (what, value) => {
    setBusy(true); setError('');
    try {
      await apiPost(`${base}/topics/${openTopic.topic.id}/${what}`, { [what === 'pin' ? 'pinned' : 'locked']: value });
      await openThread(openTopic.topic.id);
      await loadTopics();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const removeTopic = async () => {
    if (!window.confirm(`Delete "${openTopic.topic.title}" and every message in it? This can't be undone.`)) return;
    setBusy(true); setError('');
    try {
      await apiDelete(`${base}/topics/${openTopic.topic.id}`);
      setOpenTopic(null);
      await loadTopics();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const removePost = async (post) => {
    if (!window.confirm('Delete this message?')) return;
    setBusy(true); setError('');
    try {
      await apiDelete(`${base}/posts/${post.id}`);
      await openThread(openTopic.topic.id);
      await loadTopics();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  // --- one thread ---
  if (openTopic) {
    const { topic, posts } = openTopic;
    const canReply = !topic.locked || isStaff;
    return (
      <div data-testid="discussion-thread">
        <button onClick={() => { setOpenTopic(null); setError(''); }}
          className="mb-4 text-xs text-[#94A3B8] hover:text-[#D4AF37]" data-testid="back-to-topics">
          ← All topics
        </button>
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-4 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="text-sm font-medium text-[#F8FAFC]">{topic.title}</h3>
              {isStaff && (
                <div className="flex gap-1">
                  <Button onClick={() => toggle('pin', !topic.pinned)} disabled={busy} size="sm" variant="ghost"
                    className="text-[#94A3B8] hover:text-[#D4AF37] text-[11px]" data-testid="toggle-pin">
                    {topic.pinned ? 'Unpin' : 'Pin'}
                  </Button>
                  <Button onClick={() => toggle('lock', !topic.locked)} disabled={busy} size="sm" variant="ghost"
                    className="text-[#94A3B8] hover:text-[#D4AF37] text-[11px]" data-testid="toggle-lock">
                    {topic.locked ? 'Reopen' : 'Close'}
                  </Button>
                </div>
              )}
            </div>

            {posts.map(post => (
              <div key={post.id} className="rounded border border-[#1E293B] bg-[#050814] p-3"
                data-testid={`post-${post.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <Byline post={post} />
                  {(post.author_id === user?.id || isStaff) && !post.is_opening_post && (
                    <button onClick={() => removePost(post)} disabled={busy}
                      className="text-[10px] text-[#64748B] hover:text-red-400" data-testid={`delete-post-${post.id}`}>
                      Delete
                    </button>
                  )}
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm text-[#CBD5E1]">{post.content}</p>
              </div>
            ))}

            {canReply ? (
              <div className="space-y-2">
                <textarea value={reply} onChange={e => setReply(e.target.value)} rows={3}
                  placeholder={topic.locked ? 'This topic is closed — your reply posts as a teacher.' : 'Add to the conversation…'}
                  className="w-full rounded-md border border-[#1E293B] bg-[#050814] p-3 text-sm text-[#F8FAFC] focus:border-[#D4AF37]/50 focus:outline-none"
                  data-testid="reply-box" />
                <div className="flex gap-2">
                  <Button onClick={postReply} disabled={busy || !reply.trim()} size="sm"
                    className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="submit-reply">
                    {busy ? 'Posting…' : 'Reply'}
                  </Button>
                  {(topic.author_id === user?.id || isStaff) && (
                    <Button onClick={removeTopic} disabled={busy} size="sm" variant="ghost"
                      className="text-[#94A3B8] hover:text-red-400 text-xs" data-testid="delete-topic">
                      Delete topic
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-[#64748B]">This topic is closed to new replies.</p>
            )}

            {error && <p className="text-[11px] text-red-400" data-testid="discussion-error">{error}</p>}
          </CardContent>
        </Card>
      </div>
    );
  }

  // --- topic list ---
  return (
    <div data-testid="discussion-room">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xs tracking-[0.15em] uppercase text-[#D4AF37]">
          Class Discussion
        </h2>
        <Button onClick={() => setShowNew(v => !v)} size="sm"
          className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="new-topic-btn">
          {showNew ? 'Cancel' : 'Start a Topic'}
        </Button>
      </div>

      {showNew && (
        <Card className="bg-[#0F172A] border-[#D4AF37]/30 mb-4">
          <CardContent className="p-4 space-y-3">
            <Input placeholder="What is this topic about?" value={form.title} maxLength={140}
              onChange={e => setForm({ ...form, title: e.target.value })}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="new-topic-title" />
            <textarea value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} rows={4}
              placeholder="Say what you're thinking, and what you'd like people to respond to…"
              className="w-full rounded-md border border-[#1E293B] bg-[#050814] p-3 text-sm text-[#F8FAFC] focus:border-[#D4AF37]/50 focus:outline-none"
              data-testid="new-topic-content" />
            <Button onClick={startTopic} disabled={busy || !form.title.trim() || !form.content.trim()} size="sm"
              className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid="submit-topic">
              {busy ? 'Posting…' : 'Post Topic'}
            </Button>
          </CardContent>
        </Card>
      )}

      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardContent className="p-4 space-y-2">
          {topics.length === 0 ? (
            <p className="py-4 text-center text-sm text-[#94A3B8]">
              No topics yet — start the first one.
            </p>
          ) : topics.map(topic => (
            <button key={topic.id} onClick={() => openThread(topic.id)}
              className="flex w-full items-center justify-between rounded border border-[#1E293B] bg-[#050814] p-3 text-left hover:border-[#D4AF37]/40"
              data-testid={`topic-${topic.id}`}>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  {topic.pinned && (
                    <span className="rounded-full bg-[#D4AF37]/15 px-2 py-0.5 text-[10px] text-[#D4AF37]">Pinned</span>
                  )}
                  {topic.locked && (
                    <span className="rounded-full bg-[#334155] px-2 py-0.5 text-[10px] text-[#CBD5E1]">Closed</span>
                  )}
                  <span className="truncate text-sm text-[#F8FAFC]">{topic.title}</span>
                </div>
                <p className="mt-1 text-[10px] text-[#94A3B8]">
                  {topic.author_name} · {when(topic.last_activity_at)}
                </p>
              </div>
              <span className="ml-3 shrink-0 text-[10px] text-[#94A3B8]">
                {topic.reply_count || 0} {topic.reply_count === 1 ? 'reply' : 'replies'}
              </span>
            </button>
          ))}
          {error && <p className="text-[11px] text-red-400" data-testid="discussion-error">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
