import React, { useRef, useEffect, useCallback, useState } from 'react';
import {
  TextHOne, TextB, TextItalic, ListBullets, Quotes, LinkSimple,
  Image as ImageIcon, VideoCamera, FilePdf, Palette,
} from '@phosphor-icons/react';
import { mdToHtml, domToMd } from './wysiwygMarkdown';
import { apiUpload, BACKEND_URL } from '../../lib/api';

// Zero-dependency WYSIWYG. Markdown stays the stored format: we convert
// markdown → HTML when loading the editor (mdToHtml), and serialize the live
// DOM back to markdown on every edit (domToMd, in wysiwygMarkdown.js).
// Headings, bold/italic, lists, quotes, links and images render live;
// video/PDF/Slides URLs show as labelled embed blocks (the lesson viewer turns
// them into real players on save). No rich-text engine, no new packages.

// A short, readable set on the dark editor surface. Anything else goes through
// the native picker beside them.
const TEXT_COLORS = [
  { hex: '#D4AF37', name: 'Gold' },
  { hex: '#EF4444', name: 'Red' },
  { hex: '#F59E0B', name: 'Amber' },
  { hex: '#10B981', name: 'Green' },
  { hex: '#3B82F6', name: 'Blue' },
  { hex: '#A78BFA', name: 'Purple' },
  { hex: '#F8FAFC', name: 'White' },
];

export default function WysiwygEditor({ value, onChange, placeholder, minHeight = 200, testId }) {
  const ref = useRef(null);
  const lastEmitted = useRef(null);
  const pdfInputRef = useRef(null);
  const savedRange = useRef(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [showColors, setShowColors] = useState(false);

  // Initialise / re-initialise only when the incoming value isn't what we last
  // emitted (e.g. switching lessons) — never on our own keystrokes (caret jump).
  useEffect(() => {
    if (!ref.current) return;
    if (value !== lastEmitted.current) {
      ref.current.innerHTML = mdToHtml(value || '');
      lastEmitted.current = value || '';
    }
  }, [value]);

  const emit = useCallback(() => {
    if (!ref.current) return;
    const md = domToMd(ref.current);
    lastEmitted.current = md;
    onChange(md);
  }, [onChange]);

  const cmd = (command, arg) => {
    ref.current?.focus();
    document.execCommand(command, false, arg);
    emit();
  };

  // Opening a colour picker blurs the editor and can collapse the selection,
  // so the range is remembered on mousedown and put back before the command
  // runs. Without this the colour lands on nothing.
  const rememberSelection = () => {
    const sel = window.getSelection();
    if (sel && sel.rangeCount && ref.current?.contains(sel.anchorNode)) {
      savedRange.current = sel.getRangeAt(0).cloneRange();
    }
  };

  const restoreSelection = () => {
    const range = savedRange.current;
    if (!range || !ref.current) return;
    ref.current.focus();
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  };

  const applyColor = (hex) => {
    restoreSelection();
    // styleWithCSS asks the browser for <span style="color:…"> rather than the
    // legacy <font> tag. domToMd handles both, since browsers still disagree.
    document.execCommand('styleWithCSS', false, true);
    document.execCommand('foreColor', false, hex);
    emit();
    setShowColors(false);
  };

  const clearColor = () => {
    const root = ref.current;
    if (!root) return;
    restoreSelection();
    const sel = window.getSelection();
    const range = sel && sel.rangeCount ? sel.getRangeAt(0) : null;
    const coloured = Array.from(root.querySelectorAll('span[style*="color"], font[color]'));

    let targets = coloured;
    if (range && range.collapsed) {
      // Caret sitting inside a coloured run: clear just that run, rather than
      // every colour in the lesson.
      const start = range.startContainer;
      const el = start.nodeType === 3 ? start.parentNode : start;
      const owner = el && el.closest ? el.closest('span[style*="color"], font[color]') : null;
      targets = owner && root.contains(owner) ? [owner] : [];
    } else if (range) {
      targets = coloured.filter((n) => range.intersectsNode(n));
    }

    targets.forEach((n) => {
      const parent = n.parentNode;
      while (n.firstChild) parent.insertBefore(n.firstChild, n);
      parent.removeChild(n);
    });
    emit();
    setShowColors(false);
  };

  const insertHtml = (html) => {
    ref.current?.focus();
    document.execCommand('insertHTML', false, html);
    emit();
  };

  const insertUrl = (kind) => {
    const url = window.prompt(
      kind === 'image' ? 'Image URL:' :
      kind === 'video' ? 'Video URL (YouTube or Vimeo):' :
      kind === 'pdf' ? 'PDF URL (must end in .pdf):' : 'Link URL:');
    if (!url) return;
    const u = url.trim().replace(/"/g, '%22');
    if (kind === 'image') insertHtml(`<img src="${u}" alt="">`);
    else if (kind === 'link') cmd('createLink', u);
    else insertHtml(`<div class="wys-embed" data-embed-url="${u}" contenteditable="false">▶ ${u}</div><p><br></p>`);
  };

  // Upload a PDF from the user's device and embed it (the reported gap: the PDF button
  // used to only accept a URL). Uses the existing /api/files/upload endpoint. The lesson
  // viewer detects a PDF embed by a URL ending in ".pdf", and the file endpoint serves at
  // /download, so we append the original filename as a query param to satisfy that match
  // without any backend change. The download route is public, so the iframe loads fine.
  // Appends at the end of the content (selection is lost during the async upload).
  const handlePdfSelected = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    setUploadingPdf(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await apiUpload('/api/files/upload', fd);
      const dl = res?.download_url || (res?.file?.id ? `/api/files/${res.file.id}/download` : '');
      if (!dl) throw new Error('Upload failed');
      let name = res?.file?.original_filename || file.name || 'document.pdf';
      if (!/\.pdf$/i.test(name)) name += '.pdf';
      const safeName = name.replace(/[<>"]/g, '');
      const url = `${BACKEND_URL}${dl}?file=${encodeURIComponent(name)}`.replace(/"/g, '%22');
      if (ref.current) {
        ref.current.insertAdjacentHTML(
          'beforeend',
          `<div class="wys-embed" data-embed-url="${url}" contenteditable="false">📄 ${safeName}</div><p><br></p>`,
        );
        emit();
      }
    } catch (err) {
      window.alert(err?.message || 'Could not upload PDF.');
    } finally {
      setUploadingPdf(false);
    }
  };

  const Btn = ({ icon: Icon, label, onClick }) => (
    <button type="button" onMouseDown={(e) => { e.preventDefault(); onClick(); }} title={label}
      className="p-1.5 rounded text-[#94A3B8] hover:text-[#D4AF37] hover:bg-[#0F172A] transition-colors">
      <Icon size={15} weight="bold" />
    </button>
  );

  return (
    <div className="rounded-md border border-[#1E293B] bg-[#050814] overflow-hidden" data-testid={testId}>
      <div className="flex items-center gap-0.5 px-1.5 py-1 border-b border-[#1E293B] flex-wrap">
        <Btn icon={TextHOne} label="Heading" onClick={() => cmd('formatBlock', 'h2')} />
        <Btn icon={TextB} label="Bold" onClick={() => cmd('bold')} />
        <Btn icon={TextItalic} label="Italic" onClick={() => cmd('italic')} />
        <Btn icon={ListBullets} label="Bullet list" onClick={() => cmd('insertUnorderedList')} />
        <Btn icon={Quotes} label="Quote" onClick={() => cmd('formatBlock', 'blockquote')} />
        <span className="w-px h-4 bg-[#1E293B] mx-1" />
        <Btn icon={LinkSimple} label="Link" onClick={() => insertUrl('link')} />
        <Btn icon={ImageIcon} label="Image" onClick={() => insertUrl('image')} />
        <Btn icon={VideoCamera} label="Video (YouTube/Vimeo)" onClick={() => insertUrl('video')} />
        <Btn icon={FilePdf} label={uploadingPdf ? 'Uploading PDF…' : 'Upload PDF from your device'}
          onClick={() => !uploadingPdf && pdfInputRef.current?.click()} />
        <span className="w-px h-4 bg-[#1E293B] mx-1" />
        <div className="relative">
          <button type="button" title="Text colour"
            onMouseDown={(e) => { e.preventDefault(); rememberSelection(); setShowColors((v) => !v); }}
            className="p-1.5 rounded text-[#94A3B8] hover:text-[#D4AF37] hover:bg-[#0F172A] transition-colors"
            data-testid={testId ? `${testId}-color` : undefined}>
            <Palette size={15} weight="bold" />
          </button>
          {showColors && (
            <div className="absolute left-0 top-full z-20 mt-1 flex items-center gap-1 rounded-md border border-[#1E293B] bg-[#0F172A] p-2 shadow-lg">
              {TEXT_COLORS.map(({ hex, name }) => (
                <button key={hex} type="button" title={name}
                  onMouseDown={(e) => { e.preventDefault(); applyColor(hex); }}
                  className="h-5 w-5 rounded-full border border-[#334155]"
                  style={{ backgroundColor: hex }}
                  data-testid={`color-${hex.replace('#', '')}`} />
              ))}
              <label title="Any colour"
                className="flex h-5 w-5 cursor-pointer items-center justify-center rounded-full border border-dashed border-[#475569] text-[9px] text-[#94A3B8]">
                +
                <input type="color" className="sr-only"
                  onMouseDown={rememberSelection}
                  onChange={(e) => applyColor(e.target.value)} />
              </label>
              <button type="button" title="Remove colour"
                onMouseDown={(e) => { e.preventDefault(); clearColor(); }}
                className="ml-1 text-[10px] text-[#94A3B8] hover:text-[#D4AF37]"
                data-testid="color-clear">
                Clear
              </button>
            </div>
          )}
        </div>
        <span className="ml-auto text-[9px] text-[#475569] pr-1.5 hidden sm:block">
          {uploadingPdf ? 'Uploading PDF…' : 'Live preview · saved as markdown'}
        </span>
      </div>
      <input ref={pdfInputRef} type="file" accept="application/pdf,.pdf" className="hidden"
        onChange={handlePdfSelected} data-testid={testId ? `${testId}-pdf-upload` : undefined} />
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onInput={emit}
        data-placeholder={placeholder}
        style={{ minHeight }}
        className="wys-editor prose prose-invert prose-sm max-w-none px-3 py-2 text-[#F8FAFC] focus:outline-none
          prose-headings:text-[#F8FAFC] prose-h2:text-lg prose-h3:text-base
          prose-p:text-[#F8FAFC] prose-strong:text-[#F8FAFC] prose-em:text-[#D4AF37]
          prose-a:text-[#D4AF37] prose-li:text-[#F8FAFC]
          prose-blockquote:border-l-[#D4AF37] prose-blockquote:text-[#94A3B8]
          prose-img:rounded-md prose-img:border prose-img:border-[#1E293B] prose-img:max-h-72"
        data-testid={testId ? `${testId}-editable` : undefined}
      />
      <style>{`
        .wys-editor:empty:before { content: attr(data-placeholder); color: #475569; }
        .wys-embed { margin: 8px 0; padding: 8px 10px; border-radius: 6px; background:#0F172A;
          border:1px solid #1E293B; color:#D4AF37; font-size:12px; word-break:break-all; }
      `}</style>
    </div>
  );
}
