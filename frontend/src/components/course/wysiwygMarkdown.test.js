import { mdToHtml, domToMd, normalizeColor } from './wysiwygMarkdown';

const fromHtml = (html) => {
  const el = document.createElement('div');
  el.innerHTML = html;
  return el;
};

describe('normalizeColor', () => {
  it('accepts six-digit hex', () => {
    expect(normalizeColor('#FF0000')).toBe('#ff0000');
  });

  it('expands three-digit hex', () => {
    expect(normalizeColor('#f00')).toBe('#ff0000');
  });

  it('converts the rgb() form browsers write for foreColor', () => {
    expect(normalizeColor('rgb(255, 0, 0)')).toBe('#ff0000');
    expect(normalizeColor('rgba(0, 128, 255, 0.5)')).toBe('#0080ff');
  });

  it.each([
    'red',                       // named colours are not round-trippable
    'url(evil.png)',
    'expression(alert(1))',
    '#12345',
    'rgb(300, 0, 0)',
    '',
    null,
  ])('rejects %p', (bad) => {
    expect(normalizeColor(bad)).toBeNull();
  });
});

describe('colour survives the editor round-trip', () => {
  it('renders a colour marker as a styled span', () => {
    expect(mdToHtml('{color:#ff0000}danger{/color}'))
      .toBe('<p><span style="color:#ff0000">danger</span></p>');
  });

  it('serialises a styled span back to the marker', () => {
    expect(domToMd(fromHtml('<p><span style="color: #ff0000">danger</span></p>')))
      .toBe('{color:#ff0000}danger{/color}');
  });

  it('serialises the <font> tag some browsers produce', () => {
    expect(domToMd(fromHtml('<p><font color="#00ff00">go</font></p>')))
      .toBe('{color:#00ff00}go{/color}');
  });

  it('survives a full md -> html -> md trip', () => {
    const md = 'plain {color:#3366cc}blue words{/color} plain';
    expect(domToMd(fromHtml(mdToHtml(md)))).toBe(md);
  });

  it('keeps bold inside a coloured run', () => {
    const md = '{color:#ff0000}very **bold** point{/color}';
    expect(domToMd(fromHtml(mdToHtml(md)))).toBe(md);
  });

  it('keeps colour inside a heading and a list item', () => {
    expect(domToMd(fromHtml(mdToHtml('## {color:#ff0000}Title{/color}'))))
      .toBe('## {color:#ff0000}Title{/color}');
    expect(domToMd(fromHtml(mdToHtml('- {color:#ff0000}one{/color}'))))
      .toBe('- {color:#ff0000}one{/color}');
  });

  it('drops an uncoloured span rather than inventing a marker', () => {
    expect(domToMd(fromHtml('<p><span>plain</span></p>'))).toBe('plain');
  });

  it('drops a span whose colour is not hex or rgb, keeping its text', () => {
    expect(domToMd(fromHtml('<p><span style="color: red">text</span></p>'))).toBe('text');
  });

  it('never lets an unsafe value reach a style attribute', () => {
    // A non-hex value simply fails to match, so the marker stays inert text.
    // What matters is that no style attribute is ever built from it.
    const html = mdToHtml('{color:url(javascript:alert(1))}x{/color}');
    expect(html).not.toContain('<span style');
    expect(html).not.toContain('style=');
    expect(html).toBe('<p>{color:url(javascript:alert(1))}x{/color}</p>');
  });
});

describe('existing behaviour is unchanged', () => {
  it.each([
    ['## Heading', '## Heading'],
    ['- one\n- two', '- one\n- two'],
    ['> quoted', '> quoted'],
    ['**bold** and *italic*', '**bold** and *italic*'],
    ['[text](https://example.test)', '[text](https://example.test)'],
  ])('round-trips %p', (md, expected) => {
    expect(domToMd(fromHtml(mdToHtml(md)))).toBe(expected);
  });
});
