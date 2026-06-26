// Pure markdown <-> DOM converters for WysiwygEditor. No React, no DOM-library
// dependency — domToMd walks a live DOM node at runtime, but every function
// here is plain and unit-testable in isolation. Markdown stays the stored
// format; the editor converts to HTML on load and back to markdown on edit.

export const EMBED_RE = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch|youtu\.be\/|vimeo\.com\/|docs\.google\.com\/(presentation|document)\/|drive\.google\.com\/file\/)|^https?:\/\/\S+\.pdf(\?\S*)?$/i;

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// inline markdown -> html (images, links, bold, italic)
function inlineMd(text) {
  let h = esc(text);
  h = h.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_m, alt, url) => `<img src="${url}" alt="${esc(alt)}">`);
  h = h.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, t, url) => `<a href="${url}">${t}</a>`);
  h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  return h;
}

export function mdToHtml(md) {
  const lines = (md || '').replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let listBuf = [];
  const flushList = () => {
    if (listBuf.length) { out.push('<ul>' + listBuf.map(li => `<li>${inlineMd(li)}</li>`).join('') + '</ul>'); listBuf = []; }
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^- +/.test(line)) { listBuf.push(line.replace(/^- +/, '')); continue; }
    flushList();
    if (!line.trim()) continue;
    if (EMBED_RE.test(line.trim())) {
      const u = line.trim();
      out.push(`<div class="wys-embed" data-embed-url="${esc(u)}" contenteditable="false">▶ ${esc(u)}</div>`);
    } else if (/^#{1,2}\s+/.test(line)) {
      out.push(`<h2>${inlineMd(line.replace(/^#{1,2}\s+/, ''))}</h2>`);
    } else if (/^#{3,}\s+/.test(line)) {
      out.push(`<h3>${inlineMd(line.replace(/^#{3,}\s+/, ''))}</h3>`);
    } else if (/^>\s+/.test(line)) {
      out.push(`<blockquote>${inlineMd(line.replace(/^>\s+/, ''))}</blockquote>`);
    } else {
      out.push(`<p>${inlineMd(line)}</p>`);
    }
  }
  flushList();
  return out.join('') || '<p><br></p>';
}

// live DOM node -> markdown
function inlineToMd(node) {
  let md = '';
  node.childNodes.forEach((n) => {
    if (n.nodeType === 3) { md += n.textContent; return; }
    const tag = n.tagName ? n.tagName.toLowerCase() : '';
    if (tag === 'br') md += '\n';
    else if (tag === 'strong' || tag === 'b') md += `**${inlineToMd(n)}**`;
    else if (tag === 'em' || tag === 'i') md += `*${inlineToMd(n)}*`;
    else if (tag === 'a') md += `[${inlineToMd(n)}](${n.getAttribute('href') || ''})`;
    else if (tag === 'img') md += `![${n.getAttribute('alt') || ''}](${n.getAttribute('src') || ''})`;
    else md += inlineToMd(n);
  });
  return md;
}

export function domToMd(root) {
  const blocks = [];
  root.childNodes.forEach((n) => {
    if (n.nodeType === 3) {
      const t = n.textContent.trim();
      if (t) blocks.push(t);
      return;
    }
    const tag = n.tagName ? n.tagName.toLowerCase() : '';
    if (n.classList && n.classList.contains('wys-embed')) {
      blocks.push(n.getAttribute('data-embed-url') || '');
    } else if (tag === 'h1' || tag === 'h2') {
      blocks.push('## ' + inlineToMd(n));
    } else if (tag === 'h3') {
      blocks.push('### ' + inlineToMd(n));
    } else if (tag === 'ul' || tag === 'ol') {
      const items = [];
      n.querySelectorAll(':scope > li').forEach(li => items.push('- ' + inlineToMd(li)));
      if (items.length) blocks.push(items.join('\n'));  // one block; items stay tight
    } else if (tag === 'blockquote') {
      blocks.push('> ' + inlineToMd(n));
    } else if (tag === 'img') {
      blocks.push(`![${n.getAttribute('alt') || ''}](${n.getAttribute('src') || ''})`);
    } else {
      const md = inlineToMd(n).trim();
      if (md) blocks.push(md);
    }
  });
  return blocks.join('\n\n').replace(/\n{3,}/g, '\n\n').trim();
}
