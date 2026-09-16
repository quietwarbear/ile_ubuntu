import React, { useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  VideoCamera, Play, Link as LinkIcon, Upload, Trash, X,
} from '@phosphor-icons/react';
import { BACKEND_URL, apiUpload, apiPut } from '../../lib/api';

/**
 * LessonVideoPlayer — shows video from a URL (YouTube/Vimeo) or direct upload.
 * Instructors can set the video; students just watch.
 */
export function LessonVideoPlayer({
  lesson, courseId, isInstructor, onUpdate,
}) {
  const [mode, setMode] = useState(null); // 'url' | 'upload'
  const [videoUrl, setVideoUrl] = useState('');
  const [uploading, setUploading] = useState(false);

  const hasVideo = lesson.video_url || lesson.video_file_id;

  // Parse embed URL
  function getEmbedSrc() {
    const url = lesson.video_url || '';
    // YouTube
    const ytMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
    if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}`;
    // Vimeo
    const vimeoMatch = url.match(/vimeo\.com\/(\d+)/);
    if (vimeoMatch) return `https://player.vimeo.com/video/${vimeoMatch[1]}`;
    // Direct URL (mp4 etc)
    if (url.match(/\.(mp4|webm|mov)(\?|$)/i)) return null; // use <video> tag
    return null;
  }

  const embedSrc = lesson.video_url ? getEmbedSrc() : null;
  const isDirectUrl = lesson.video_url && !embedSrc;

  const handleSaveUrl = async () => {
    if (!videoUrl.trim()) return;
    try {
      await apiPut(`/api/courses/${courseId}/lessons/${lesson.id}`, { video_url: videoUrl.trim() });
      setVideoUrl('');
      setMode(null);
      onUpdate?.();
    } catch (e) { alert(e.message); }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lesson_id', lesson.id);
      formData.append('course_id', courseId);
      const result = await apiUpload('/api/files/upload', formData);
      // Set the video_file_id on the lesson
      await apiPut(`/api/courses/${courseId}/lessons/${lesson.id}`, {
        video_file_id: result.file.id,
      });
      setMode(null);
      onUpdate?.();
    } catch (err) { alert(err.message); }
    finally { setUploading(false); }
  };

  const handleRemoveVideo = async () => {
    try {
      await apiPut(`/api/courses/${courseId}/lessons/${lesson.id}`, {
        video_url: '', video_file_id: '',
      });
      onUpdate?.();
    } catch (e) { alert(e.message); }
  };

  // No video and not instructor — nothing to show
  if (!hasVideo && !isInstructor) return null;

  return (
    <div className="space-y-2" data-testid="lesson-video-player">
      <span className="text-[10px] tracking-[0.15em] uppercase text-[rgb(var(--gold))] flex items-center gap-1">
        <VideoCamera size={12} weight="duotone" /> Lesson Video
      </span>

      {/* Video display */}
      {embedSrc && (
        <div className="rounded-md overflow-hidden border border-[rgb(var(--ink-border))]">
          <iframe
            src={embedSrc}
            className="w-full aspect-video"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            title="Lesson video"
          />
        </div>
      )}

      {isDirectUrl && (
        <div className="rounded-md overflow-hidden border border-[rgb(var(--ink-border))]">
          <video controls className="w-full" src={lesson.video_url}>
            Your browser does not support the video tag.
          </video>
        </div>
      )}

      {lesson.video_file_id && !lesson.video_url && (
        <div className="rounded-md overflow-hidden border border-[rgb(var(--ink-border))]">
          <video controls className="w-full"
            src={`${BACKEND_URL}/api/files/${lesson.video_file_id}/stream`}>
            Your browser does not support the video tag.
          </video>
        </div>
      )}

      {/* Instructor controls */}
      {isInstructor && (
        <div className="space-y-2">
          {hasVideo && (
            <Button size="sm" variant="ghost"
              onClick={handleRemoveVideo}
              className="text-red-400 hover:text-red-300 text-[10px] h-7">
              <Trash size={12} className="mr-1" /> Remove Video
            </Button>
          )}

          {!hasVideo && !mode && (
            <div className="flex gap-2">
              <Button size="sm" variant="ghost"
                onClick={() => setMode('url')}
                className="text-[rgb(var(--gold))] hover:text-[rgb(var(--gold-soft))] text-[10px] h-7">
                <LinkIcon size={12} className="mr-1" /> Add Video URL
              </Button>
              <Button size="sm" variant="ghost"
                onClick={() => setMode('upload')}
                className="text-[rgb(var(--gold))] hover:text-[rgb(var(--gold-soft))] text-[10px] h-7">
                <Upload size={12} className="mr-1" /> Upload Video
              </Button>
            </div>
          )}

          {mode === 'url' && (
            <div className="flex gap-2">
              <Input
                placeholder="YouTube, Vimeo, or direct video URL..."
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                className="bg-[rgb(var(--ink-deep))] border-[rgb(var(--ink-border))] text-[rgb(var(--text-main))] text-xs flex-1"
              />
              <Button size="sm" onClick={handleSaveUrl}
                className="bg-[rgb(var(--gold))] text-[rgb(var(--ink-deep))] hover:bg-[rgb(var(--gold-soft))] text-xs">
                Save
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setMode(null); setVideoUrl(''); }}
                className="text-[rgb(var(--text-muted))] text-xs">
                <X size={14} />
              </Button>
            </div>
          )}

          {mode === 'upload' && (
            <div className="flex items-center gap-2">
              <label className="cursor-pointer flex items-center gap-2 px-3 py-1.5 rounded bg-[rgb(var(--ink-deep))] border border-[rgb(var(--ink-border))] text-xs text-[rgb(var(--gold))] hover:border-[rgb(var(--gold)/0.4)] transition-colors">
                <Play size={14} />
                {uploading ? 'Uploading...' : 'Choose Video File'}
                <input type="file" className="hidden" accept="video/*" onChange={handleUpload} disabled={uploading} />
              </label>
              <Button size="sm" variant="ghost" onClick={() => setMode(null)}
                className="text-[rgb(var(--text-muted))] text-xs">
                <X size={14} />
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
