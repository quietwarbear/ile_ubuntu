import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function extractEmbeds(content) {
  if (!content) return { text: content, embeds: [] };

  const embeds = [];
  const youtubeRegex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)(?:\S*)?/g;
  const vimeoRegex = /(?:https?:\/\/)?(?:www\.)?vimeo\.com\/(\d+)/g;
  const imageRegex = /!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g;
  const slidesRegex = /(?:https?:\/\/)?docs\.google\.com\/presentation\/d\/([\w-]+)(?:\/[^\s)]*)?/g;
  const docsRegex = /(?:https?:\/\/)?docs\.google\.com\/document\/d\/([\w-]+)(?:\/[^\s)]*)?/g;

  let text = content;

  // Extract YouTube
  let match;
  while ((match = youtubeRegex.exec(content)) !== null) {
    embeds.push({ type: 'youtube', id: match[1], raw: match[0] });
  }
  // Extract Vimeo
  while ((match = vimeoRegex.exec(content)) !== null) {
    embeds.push({ type: 'vimeo', id: match[1], raw: match[0] });
  }
  // Extract Google Slides
  while ((match = slidesRegex.exec(content)) !== null) {
    embeds.push({ type: 'google_slides', id: match[1], raw: match[0] });
  }
  // Extract Google Docs
  while ((match = docsRegex.exec(content)) !== null) {
    embeds.push({ type: 'google_docs', id: match[1], raw: match[0] });
  }

  return { text, embeds };
}

export default function LessonContentViewer({ content }) {
  if (!content) return null;

  const { text, embeds } = extractEmbeds(content);

  return (
    <div className="lesson-content-viewer" data-testid="lesson-content-viewer">
      {/* Markdown Content */}
      <div className="prose prose-invert prose-sm max-w-none
        prose-headings:text-[#F8FAFC] prose-headings:font-light
        prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
        prose-p:text-[#94A3B8] prose-p:leading-relaxed prose-p:text-sm
        prose-strong:text-[#F8FAFC]
        prose-em:text-[#D4AF37]
        prose-a:text-[#D4AF37] prose-a:no-underline hover:prose-a:underline
        prose-code:text-[#D4AF37] prose-code:bg-[#050814] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:border prose-code:border-[#1E293B]
        prose-pre:bg-[#050814] prose-pre:border prose-pre:border-[#1E293B] prose-pre:rounded-md
        prose-blockquote:border-l-[#D4AF37] prose-blockquote:text-[#94A3B8] prose-blockquote:bg-[#050814]/50 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:rounded-r
        prose-ul:text-[#94A3B8] prose-ol:text-[#94A3B8]
        prose-li:text-sm prose-li:marker:text-[#D4AF37]
        prose-hr:border-[#1E293B]
        prose-img:rounded-md prose-img:border prose-img:border-[#1E293B]
        prose-table:border-collapse
        prose-th:bg-[#050814] prose-th:text-[#D4AF37] prose-th:text-xs prose-th:px-3 prose-th:py-2 prose-th:border prose-th:border-[#1E293B]
        prose-td:text-[#94A3B8] prose-td:text-xs prose-td:px-3 prose-td:py-2 prose-td:border prose-td:border-[#1E293B]
      ">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div>

      {/* Embedded Media */}
      {embeds.length > 0 && (
        <div className="mt-4 space-y-3">
          {embeds.map((embed, idx) => (
            <div key={idx} className="rounded-md overflow-hidden border border-[#1E293B]" data-testid={`embed-${embed.type}-${idx}`}>
              {embed.type === 'youtube' && (
                <iframe
                  src={`https://www.youtube.com/embed/${embed.id}`}
                  className="w-full aspect-video"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  title={`YouTube video ${embed.id}`}
                />
              )}
              {embed.type === 'vimeo' && (
                <iframe
                  src={`https://player.vimeo.com/video/${embed.id}`}
                  className="w-full aspect-video"
                  allow="autoplay; fullscreen; picture-in-picture"
                  allowFullScreen
                  title={`Vimeo video ${embed.id}`}
                />
              )}
              {embed.type === 'google_slides' && (
                <iframe
                  src={`https://docs.google.com/presentation/d/${embed.id}/embed?start=false&loop=false&delayms=3000`}
                  className="w-full aspect-video"
                  allowFullScreen
                  title="Google Slides"
                />
              )}
              {embed.type === 'google_docs' && (
                <iframe
                  src={`https://docs.google.com/document/d/${embed.id}/preview`}
                  className="w-full h-[500px]"
                  title="Google Doc"
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
