import React, { useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import {
  CheckCircle, Circle, Paperclip, CaretDown, CaretUp,
  DownloadSimple, Trash, Plus, GoogleLogo, Presentation, Article, ArrowSquareOut,
  File as FileIcon, FilePdf, FileDoc, FileXls, FilePpt, FileImage, Eye, X,
} from '@phosphor-icons/react';
import { BACKEND_URL } from '../../lib/api';
import LessonContentViewer from '../LessonContentViewer';
import { LessonVideoPlayer } from './LessonVideoPlayer';
import { LessonQuiz } from './LessonQuiz';
import { LessonComments } from './LessonComments';

const FILE_ICONS = {
  'application/pdf': FilePdf,
  'application/msword': FileDoc,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileDoc,
  'application/vnd.ms-powerpoint': FilePpt,
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': FilePpt,
  'application/vnd.ms-excel': FileXls,
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': FileXls,
  'image/jpeg': FileImage,
  'image/png': FileImage,
  'image/gif': FileImage,
};

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

export function LessonCard({
  lesson, idx, isEnrolled, isLessonCompleted, isExpanded, isInstructor,
  lessonFiles, googleConnected, uploading, uploadingFor,
  onToggleExpand, onComplete, onUploadClick, onDeleteFile, onOpenImport,
  courseId, user, onReloadCourse,
}) {
  const [viewingPdf, setViewingPdf] = useState(null);

  return (
    <Card
      className={`bg-[#0F172A] border-[#1E293B] transition-all ${
        isLessonCompleted ? 'border-l-2 border-l-emerald-500' : ''
      }`}
      data-testid={`lesson-card-${lesson.id}`}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-4">
          <div className="flex-shrink-0">
            {isEnrolled ? (
              isLessonCompleted ? (
                <CheckCircle size={24} weight="fill" className="text-emerald-400" />
              ) : (
                <button
                  onClick={() => onComplete(lesson.id)}
                  className="text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                  data-testid={`complete-lesson-${lesson.id}`}
                  title="Mark as complete"
                >
                  <Circle size={24} weight="regular" />
                </button>
              )
            ) : (
              <div className="w-6 h-6 rounded-full bg-[#050814] border border-[#1E293B] flex items-center justify-center">
                <span className="text-[10px] text-[#94A3B8]">{idx + 1}</span>
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onToggleExpand(lesson.id)}>
            <div className="flex items-center gap-2">
              <h3 className={`text-sm font-medium ${isLessonCompleted ? 'text-emerald-400' : 'text-[#F8FAFC]'}`}>
                {lesson.title}
              </h3>
              {lessonFiles.length > 0 && (
                <span className="flex items-center gap-0.5 text-[10px] text-[#94A3B8]">
                  <Paperclip size={10} /> {lessonFiles.length}
                </span>
              )}
            </div>
            {lesson.description && (
              <p className="text-xs text-[#94A3B8] mt-0.5 truncate">{lesson.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            {isLessonCompleted && (
              <Badge className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20">Done</Badge>
            )}
            <button
              onClick={() => onToggleExpand(lesson.id)}
              className="text-[#94A3B8] hover:text-[#F8FAFC] p-1"
              data-testid={`expand-lesson-${lesson.id}`}
            >
              {isExpanded ? <CaretUp size={16} /> : <CaretDown size={16} />}
            </button>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-[#1E293B] space-y-4">
            {lesson.content && (
              <div className="p-3 bg-[#050814] rounded-md border border-[#1E293B]">
                <LessonContentViewer content={lesson.content} />
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-1">
                  <Paperclip size={12} /> Materials ({lessonFiles.length})
                </span>
                {isInstructor && (
                  <div className="flex gap-1">
                    <Button
                      size="sm" variant="ghost"
                      onClick={() => onUploadClick(lesson.id)}
                      className="text-[#D4AF37] hover:text-[#F3E5AB] text-[10px] h-7"
                      disabled={uploading}
                      data-testid={`upload-file-${lesson.id}`}
                    >
                      {uploading && uploadingFor === lesson.id ? (
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 border border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
                          Uploading...
                        </span>
                      ) : (
                        <><Plus size={12} className="mr-1" /> Attach File</>
                      )}
                    </Button>
                    {googleConnected && (
                      <Button
                        size="sm" variant="ghost"
                        onClick={() => onOpenImport(lesson.id)}
                        className="text-[#94A3B8] hover:text-[#F3E5AB] text-[10px] h-7"
                        data-testid={`import-google-${lesson.id}`}
                      >
                        <GoogleLogo size={12} className="mr-1" /> Import
                      </Button>
                    )}
                  </div>
                )}
              </div>

              {lessonFiles.length > 0 ? (
                <div className="space-y-1.5">
                  {lessonFiles.map(file => {
                    const Icon = FILE_ICONS[file.mime_type] || FileIcon;
                    const isPdf = file.mime_type === 'application/pdf';
                    const isPdfOpen = viewingPdf === file.id;
                    return (
                      <div key={file.id} data-testid={`file-${file.id}`}>
                        <div
                          className="flex items-center gap-3 p-2.5 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors group"
                        >
                          <Icon size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-[#F8FAFC] truncate">{file.original_filename}</p>
                            <p className="text-[10px] text-[#94A3B8]">{formatFileSize(file.file_size)}</p>
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            {isPdf && (
                              <button
                                onClick={() => setViewingPdf(isPdfOpen ? null : file.id)}
                                className={`p-1 transition-colors ${isPdfOpen ? 'text-[#D4AF37]' : 'text-[#94A3B8] hover:text-[#D4AF37]'}`}
                                title={isPdfOpen ? 'Close PDF' : 'View PDF'}
                              >
                                {isPdfOpen ? <X size={14} /> : <Eye size={14} />}
                              </button>
                            )}
                            <a
                              href={`${BACKEND_URL}/api/files/${file.id}/download`}
                              target="_blank" rel="noopener noreferrer"
                              className="p-1 text-[#94A3B8] hover:text-[#D4AF37] transition-colors"
                              title="Download"
                              data-testid={`download-file-${file.id}`}
                              onClick={e => e.stopPropagation()}
                            >
                              <DownloadSimple size={14} />
                            </a>
                            {isInstructor && (
                              <button
                                onClick={() => onDeleteFile(file.id)}
                                className="p-1 text-[#94A3B8] hover:text-red-400 transition-colors"
                                title="Delete"
                                data-testid={`delete-file-${file.id}`}
                              >
                                <Trash size={14} />
                              </button>
                            )}
                          </div>
                        </div>
                        {isPdf && isPdfOpen && (
                          <div className="mt-1 rounded-md overflow-hidden border border-[#1E293B]">
                            <iframe
                              src={`${BACKEND_URL}/api/files/${file.id}/download`}
                              className="w-full h-[600px] bg-white"
                              title={file.original_filename}
                            />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-[10px] text-[#94A3B8]">
                  {isInstructor ? 'No files attached. Click "Attach File" to add materials.' : 'No materials attached to this lesson.'}
                </p>
              )}
            </div>

            {lesson.google_resources?.length > 0 && (
              <div>
                <span className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-1 mb-2">
                  <GoogleLogo size={12} /> Imported from Google
                </span>
                <div className="space-y-1.5">
                  {lesson.google_resources.map((res) => (
                    <a
                      key={res.google_id || res.view_url}
                      href={res.view_url || res.embed_url}
                      target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-3 p-2.5 bg-[#050814] border border-[#1E293B] rounded-md hover:border-[#D4AF37]/20 transition-colors group"
                      data-testid={`google-resource-${res.google_id}`}
                    >
                      {res.type === 'google_slide' ? (
                        <Presentation size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                      ) : (
                        <Article size={18} weight="duotone" className="text-[#D4AF37] flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-[#F8FAFC] truncate">{res.title}</p>
                        <p className="text-[10px] text-[#94A3B8]">
                          {res.type === 'google_slide' ? `${res.slide_count} slides` : 'Google Doc'}
                        </p>
                      </div>
                      <ArrowSquareOut size={14} className="text-[#94A3B8] opacity-0 group-hover:opacity-100 transition-opacity" />
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Video Player */}
            {(lesson.video_url || lesson.video_file_id || isInstructor) && (
              <LessonVideoPlayer
                lesson={lesson}
                courseId={courseId}
                isInstructor={isInstructor}
                onUpdate={onReloadCourse}
              />
            )}

            {/* Quiz */}
            {(isEnrolled || isInstructor) && (
              <LessonQuiz
                courseId={courseId}
                lessonId={lesson.id}
                user={user}
                isInstructor={isInstructor}
              />
            )}

            {/* Discussion / Comments */}
            {(isEnrolled || isInstructor) && (
              <LessonComments
                courseId={courseId}
                lessonId={lesson.id}
                user={user}
                isInstructor={isInstructor}
              />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
