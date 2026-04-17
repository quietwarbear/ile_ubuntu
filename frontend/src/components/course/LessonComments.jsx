import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import {
  ChatCircle, PaperPlaneTilt, ArrowBendUpLeft, Trash, PencilSimple, X, Check,
  ChalkboardTeacher,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete } from '../../lib/api';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function CommentItem({ comment, courseId, lessonId, user, isInstructor, onRefresh, depth = 0 }) {
  const [showReply, setShowReply] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(comment.content);
  const [submitting, setSubmitting] = useState(false);

  const isAuthor = user?.id === comment.author_id;
  const canDelete = isAuthor || isInstructor;

  const handleReply = async () => {
    if (!replyText.trim()) return;
    setSubmitting(true);
    try {
      await apiPost(`/api/courses/${courseId}/lessons/${lessonId}/comments`, {
        content: replyText.trim(),
        parent_id: comment.id,
      });
      setReplyText('');
      setShowReply(false);
      onRefresh();
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  const handleEdit = async () => {
    if (!editText.trim()) return;
    setSubmitting(true);
    try {
      await apiPut(`/api/courses/${courseId}/lessons/${lessonId}/comments/${comment.id}`, {
        content: editText.trim(),
      });
      setEditing(false);
      onRefresh();
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this comment?')) return;
    try {
      await apiDelete(`/api/courses/${courseId}/lessons/${lessonId}/comments/${comment.id}`);
      onRefresh();
    } catch (e) { alert(e.message); }
  };

  return (
    <div className={`${depth > 0 ? 'ml-6 pl-3 border-l border-[#1E293B]' : ''}`}
      data-testid={`comment-${comment.id}`}>
      <div className="py-2.5">
        {/* Author line */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-[#F8FAFC]">{comment.author_name}</span>
          {comment.is_instructor && (
            <span className="flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/20">
              <ChalkboardTeacher size={10} /> Instructor
            </span>
          )}
          <span className="text-[10px] text-[#64748B]">{timeAgo(comment.created_at)}</span>
          {comment.edited && <span className="text-[10px] text-[#64748B] italic">(edited)</span>}
        </div>

        {/* Content */}
        {editing ? (
          <div className="space-y-2">
            <Textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs min-h-[60px]"
            />
            <div className="flex gap-1">
              <Button size="sm" onClick={handleEdit} disabled={submitting}
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px] h-6">
                <Check size={12} className="mr-1" /> Save
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setEditing(false); setEditText(comment.content); }}
                className="text-[#94A3B8] text-[10px] h-6">
                <X size={12} />
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-xs text-[#94A3B8] leading-relaxed whitespace-pre-wrap">{comment.content}</p>
        )}

        {/* Actions */}
        {!editing && (
          <div className="flex items-center gap-2 mt-1.5">
            {depth === 0 && (
              <button onClick={() => setShowReply(!showReply)}
                className="flex items-center gap-1 text-[10px] text-[#64748B] hover:text-[#D4AF37] transition-colors">
                <ArrowBendUpLeft size={12} /> Reply
              </button>
            )}
            {isAuthor && (
              <button onClick={() => setEditing(true)}
                className="flex items-center gap-1 text-[10px] text-[#64748B] hover:text-[#D4AF37] transition-colors">
                <PencilSimple size={12} /> Edit
              </button>
            )}
            {canDelete && (
              <button onClick={handleDelete}
                className="flex items-center gap-1 text-[10px] text-[#64748B] hover:text-red-400 transition-colors">
                <Trash size={12} /> Delete
              </button>
            )}
          </div>
        )}

        {/* Reply form */}
        {showReply && (
          <div className="mt-2 ml-2 space-y-2">
            <Textarea
              placeholder="Write a reply..."
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs min-h-[50px]"
            />
            <div className="flex gap-1">
              <Button size="sm" onClick={handleReply} disabled={submitting || !replyText.trim()}
                className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px] h-6">
                <PaperPlaneTilt size={12} className="mr-1" /> Reply
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowReply(false); setReplyText(''); }}
                className="text-[#94A3B8] text-[10px] h-6">Cancel</Button>
            </div>
          </div>
        )}
      </div>

      {/* Replies */}
      {comment.replies?.map(reply => (
        <CommentItem
          key={reply.id}
          comment={reply}
          courseId={courseId}
          lessonId={lessonId}
          user={user}
          isInstructor={isInstructor}
          onRefresh={onRefresh}
          depth={depth + 1}
        />
      ))}
    </div>
  );
}

export function LessonComments({ courseId, lessonId, user, isInstructor }) {
  const [comments, setComments] = useState([]);
  const [total, setTotal] = useState(0);
  const [newComment, setNewComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadComments = async () => {
    try {
      const data = await apiGet(`/api/courses/${courseId}/lessons/${lessonId}/comments`);
      setComments(data.comments || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error('Failed to load comments:', e);
    } finally { setLoading(false); }
  };

  useEffect(() => { loadComments(); }, [courseId, lessonId]);

  const handleSubmit = async () => {
    if (!newComment.trim()) return;
    setSubmitting(true);
    try {
      await apiPost(`/api/courses/${courseId}/lessons/${lessonId}/comments`, {
        content: newComment.trim(),
      });
      setNewComment('');
      loadComments();
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="space-y-3" data-testid="lesson-comments">
      <div className="flex items-center justify-between">
        <span className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-1">
          <ChatCircle size={12} weight="duotone" /> Discussion ({total})
        </span>
      </div>

      {/* New comment form */}
      <div className="space-y-2">
        <Textarea
          placeholder="Join the discussion..."
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs min-h-[60px] placeholder:text-[#64748B]"
        />
        <div className="flex justify-end">
          <Button size="sm" onClick={handleSubmit}
            disabled={submitting || !newComment.trim()}
            className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-[10px]">
            <PaperPlaneTilt size={12} className="mr-1" />
            {submitting ? 'Posting...' : 'Post Comment'}
          </Button>
        </div>
      </div>

      {/* Comments list */}
      {loading ? (
        <div className="flex justify-center py-4">
          <div className="w-5 h-5 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : comments.length === 0 ? (
        <p className="text-xs text-[#64748B] text-center py-4">No comments yet. Be the first to start the discussion.</p>
      ) : (
        <div className="divide-y divide-[#1E293B]">
          {comments.map(comment => (
            <CommentItem
              key={comment.id}
              comment={comment}
              courseId={courseId}
              lessonId={lessonId}
              user={user}
              isInstructor={isInstructor}
              onRefresh={loadComments}
            />
          ))}
        </div>
      )}
    </div>
  );
}
