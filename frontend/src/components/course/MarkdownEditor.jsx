import React, { useRef } from 'react';
import {
  TextB, TextHOne, ListBullets, Quotes, LinkSimple, Image as ImageIcon,
  VideoCamera, FilePdf,
} from '@phosphor-icons/react';

// A plain textarea with an insert toolbar. The lesson viewer already
// auto-embeds raw YouTube/Vimeo/Slides/Docs/Drive/PDF URLs and markdown
// images, so the toolbar mostly drops the right scaffolding at the cursor —
// no rich-text engine, no new dependency, just markdown the viewer understands.
export default function MarkdownEditor({ value, onChange, placeholder, minHeight = 160, testId }) {
  const ref = useRef(null);

  // Replace the current selection with `text`; optionally re-select an inner
  // span (selStart/selEnd offsets within `text`) so typing replaces a placeholder.
  const apply = (text, selStart, selEnd) => {
    const el = ref.current;
    const start = el ? el.selectionStart : (value || '').length;
    const end = el ? el.selectionEnd : (value || '').length;
    const before = (value || '').slice(0, start);
    const after = (value || '').slice(end);
    const next = before + text + after;
    onChange(next);
    // Restore focus + caret after React re-renders.
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      const s = before.length + (selStart ?? text.length);
      const e = before.length + (selEnd ?? text.length);
      el.setSelectionRange(s, e);
    });
  };

  // Wrap the selection (or a placeholder) with prefix/suffix.
  const wrap = (prefix, suffix, placeholderText) => {
    const el = ref.current;
    const start = el ? el.selectionStart : 0;
    const end = el ? el.selectionEnd : 0;
    const sel = (value || '').slice(start, end) || placeholderText;
    apply(prefix + sel + suffix, prefix.length, prefix.length + sel.length);
  };

  // Prefix the current line (for headings, lists, quotes).
  const linePrefix = (prefix) => {
    const el = ref.current;
    const start = el ? el.selectionStart : 0;
    const v = value || '';
    const lineStart = v.lastIndexOf('\n', start - 1) + 1;
    const next = v.slice(0, lineStart) + prefix + v.slice(lineStart);
    onChange(next);
    requestAnimationFrame(() => {
      if (!el) return;
      el.focus();
      el.setSelectionRange(start + prefix.length, start + prefix.length);
    });
  };

  const insertUrl = (kind) => {
    const url = window.prompt(
      kind === 'image' ? 'Image URL:' :
      kind === 'video' ? 'Video URL (YouTube or Vimeo):' :
      kind === 'pdf' ? 'PDF URL (must end in .pdf):' : 'Link URL:'
    );
    if (!url) return;
    const u = url.trim();
    if (kind === 'image') apply(`\n![](${u})\n`);
    else if (kind === 'video') apply(`\n\n${u}\n\n`);   // raw URL auto-embeds
    else if (kind === 'pdf') apply(`\n\n${u}\n\n`);     // raw .pdf auto-embeds
    else { // link
      const el = ref.current;
      const sel = el ? (value || '').slice(el.selectionStart, el.selectionEnd) : '';
      const label = sel || 'link text';
      apply(`[${label}](${u})`, 1, 1 + label.length);
    }
  };

  const Btn = ({ icon: Icon, label, onClick }) => (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className="p-1.5 rounded text-[#94A3B8] hover:text-[#D4AF37] hover:bg-[#0F172A] transition-colors"
    >
      <Icon size={15} weight="bold" />
    </button>
  );

  return (
    <div className="rounded-md border border-[#1E293B] bg-[#050814] overflow-hidden" data-testid={testId}>
      <div className="flex items-center gap-0.5 px-1.5 py-1 border-b border-[#1E293B] flex-wrap">
        <Btn icon={TextHOne} label="Heading" onClick={() => linePrefix('## ')} />
        <Btn icon={TextB} label="Bold" onClick={() => wrap('**', '**', 'bold text')} />
        <Btn icon={ListBullets} label="Bullet list" onClick={() => linePrefix('- ')} />
        <Btn icon={Quotes} label="Quote / callout" onClick={() => linePrefix('> ')} />
        <span className="w-px h-4 bg-[#1E293B] mx-1" />
        <Btn icon={LinkSimple} label="Link" onClick={() => insertUrl('link')} />
        <Btn icon={ImageIcon} label="Image" onClick={() => insertUrl('image')} />
        <Btn icon={VideoCamera} label="Video (YouTube/Vimeo)" onClick={() => insertUrl('video')} />
        <Btn icon={FilePdf} label="PDF" onClick={() => insertUrl('pdf')} />
        <span className="ml-auto text-[9px] text-[#475569] pr-1.5 hidden sm:block">Pasted links embed automatically</span>
      </div>
      <textarea
        ref={ref}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{ minHeight }}
        className="w-full bg-transparent text-[#F8FAFC] text-sm placeholder-[#475569] px-3 py-2 focus:outline-none resize-y"
        data-testid={testId ? `${testId}-textarea` : undefined}
      />
    </div>
  );
}
