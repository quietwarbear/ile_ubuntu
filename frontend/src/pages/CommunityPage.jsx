import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Chats, Plus, Heart, ChatCircle } from '@phosphor-icons/react';
import { apiGet, apiPost, apiDelete } from '../lib/api';

export default function CommunityPage({ user }) {
  const [posts, setPosts] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ title: '', content: '', category: 'general' });
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyContent, setReplyContent] = useState('');
  const [expandedPost, setExpandedPost] = useState(null);

  useEffect(() => { loadPosts(); }, []);

  const loadPosts = async () => {
    try { setPosts(await apiGet('/api/community/posts')); } catch (e) { console.error(e); }
  };

  const handleCreate = async () => {
    try {
      await apiPost('/api/community/posts', form);
      setForm({ title: '', content: '', category: 'general' });
      setCreateOpen(false);
      loadPosts();
    } catch (e) { alert(e.message); }
  };

  const handleLike = async (postId) => {
    try { await apiPost(`/api/community/posts/${postId}/like`, {}); loadPosts(); }
    catch (e) { alert(e.message); }
  };

  const handleReply = async (postId) => {
    if (!replyContent.trim()) return;
    try {
      await apiPost(`/api/community/posts/${postId}/reply`, { content: replyContent });
      setReplyContent('');
      setReplyingTo(null);
      loadPosts();
    } catch (e) { alert(e.message); }
  };

  const handleDeletePost = async (postId) => {
    if (!window.confirm('Delete this post?')) return;
    try { await apiDelete(`/api/community/posts/${postId}`); loadPosts(); }
    catch (e) { alert(e.message); }
  };

  const categories = ['general', 'announcements', 'questions', 'resources', 'introductions'];

  return (
    <div className="space-y-6 animate-fade-in-up" data-testid="community-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-light text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>Community</h1>
          <p className="text-sm text-[#94A3B8]">Discussions, announcements, and shared knowledge</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="create-post-btn">
              <Plus size={16} weight="bold" className="mr-1.5" /> New Post
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#0F172A] border-[#1E293B]">
            <DialogHeader>
              <DialogTitle className="text-[#F8FAFC]" style={{ fontFamily: 'Cormorant Garamond, serif' }}>New Discussion</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <Input placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC]" data-testid="post-title-input" />
              <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} className="w-full p-2 rounded-md bg-[#050814] border border-[#1E293B] text-[#F8FAFC] text-sm" data-testid="post-category-select">
                {categories.map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
              </select>
              <Textarea placeholder="Share your thoughts..." value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] min-h-[120px]" data-testid="post-content-input" />
              <Button onClick={handleCreate} className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB]" data-testid="submit-post-btn">Post</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {posts.length === 0 ? (
        <Card className="bg-[#0F172A] border-[#1E293B]">
          <CardContent className="p-10 text-center">
            <Chats size={48} weight="duotone" className="text-emerald-400 mx-auto mb-4" />
            <h3 className="text-lg text-[#F8FAFC] mb-2" style={{ fontFamily: 'Cormorant Garamond, serif' }}>No discussions yet</h3>
            <p className="text-sm text-[#94A3B8]">Be the first to start a conversation.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {posts.map(post => (
            <Card key={post.id} className="bg-[#0F172A] border-[#1E293B] hover:border-[#D4AF37]/20 transition-all" data-testid={`post-card-${post.id}`}>
              <CardContent className="p-5">
                <div className="flex items-start gap-3">
                  <img src={post.author_picture || `https://ui-avatars.com/api/?name=${post.author_name}&background=0F172A&color=D4AF37`} alt="" className="w-8 h-8 rounded-full border border-[#1E293B]" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-[#F8FAFC]">{post.author_name}</span>
                      <span className="text-[10px] tracking-wider uppercase text-[#D4AF37]">{post.author_role}</span>
                      <span className="text-[10px] text-[#94A3B8]">{new Date(post.created_at).toLocaleDateString()}</span>
                    </div>
                    <h3 className="text-base text-[#F8FAFC] mb-1" style={{ fontFamily: 'Cormorant Garamond, serif' }}>{post.title}</h3>
                    <p className="text-sm text-[#94A3B8] leading-relaxed">{post.content}</p>

                    <div className="flex items-center gap-4 mt-3">
                      <button onClick={() => handleLike(post.id)} className={`flex items-center gap-1 text-xs transition-colors ${post.likes?.includes(user?.id) ? 'text-red-400' : 'text-[#94A3B8] hover:text-red-400'}`} data-testid={`like-post-${post.id}`}>
                        <Heart size={14} weight={post.likes?.includes(user?.id) ? 'fill' : 'regular'} /> {post.likes?.length || 0}
                      </button>
                      <button onClick={() => { setExpandedPost(expandedPost === post.id ? null : post.id); setReplyingTo(post.id); }} className="flex items-center gap-1 text-xs text-[#94A3B8] hover:text-[#D4AF37] transition-colors" data-testid={`reply-toggle-${post.id}`}>
                        <ChatCircle size={14} /> {post.replies?.length || 0}
                      </button>
                      {(post.author_id === user?.id || ['faculty', 'elder', 'admin'].includes(user?.role)) && (
                        <button onClick={() => handleDeletePost(post.id)} className="text-xs text-[#94A3B8] hover:text-red-400 ml-auto transition-colors" data-testid={`delete-post-${post.id}`}>Delete</button>
                      )}
                    </div>

                    {/* Replies */}
                    {expandedPost === post.id && (
                      <div className="mt-3 pt-3 border-t border-[#1E293B] space-y-2">
                        {post.replies?.map(reply => (
                          <div key={reply.id} className="flex items-start gap-2 p-2 bg-[#050814] rounded">
                            <img src={reply.author_picture || `https://ui-avatars.com/api/?name=${reply.author_name}&background=050814&color=D4AF37`} alt="" className="w-6 h-6 rounded-full" />
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-medium text-[#F8FAFC]">{reply.author_name}</span>
                                <span className="text-[9px] text-[#D4AF37]">{reply.author_role}</span>
                              </div>
                              <p className="text-xs text-[#94A3B8]">{reply.content}</p>
                            </div>
                          </div>
                        ))}
                        <div className="flex gap-2 mt-2">
                          <Input placeholder="Write a reply..." value={replyingTo === post.id ? replyContent : ''} onChange={e => { setReplyingTo(post.id); setReplyContent(e.target.value); }} className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs" data-testid={`reply-input-${post.id}`} />
                          <Button size="sm" onClick={() => handleReply(post.id)} className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs" data-testid={`submit-reply-${post.id}`}>Reply</Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
