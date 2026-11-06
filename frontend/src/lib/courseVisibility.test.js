import {
  VISIBILITY_OPTIONS, certificatesEnabled, currentVisibility, visibilityExplanation, visibilityOptionsFor,
} from './courseVisibility';

describe('course visibility choices', () => {
  test('private is offered, with a plain one-line explanation', () => {
    const priv = VISIBILITY_OPTIONS.find(o => o.value === 'private');
    expect(priv.label).toBe('Private');
    expect(visibilityExplanation('private')).toMatch(/only people you enroll/i);
  });

  test('every option has an explanation', () => {
    VISIBILITY_OPTIONS.forEach(o => expect(visibilityExplanation(o.value)).not.toBe(''));
  });

  test('village only is offered just to village courses', () => {
    expect(visibilityOptionsFor({}).map(o => o.value)).toEqual(['listed', 'unlisted', 'private']);
    expect(visibilityOptionsFor({ village_id: 'v1' }).map(o => o.value)).toContain('village');
  });

  test('courses from before visibility existed count as listed', () => {
    expect(currentVisibility({})).toBe('listed');
    expect(currentVisibility({ visibility: 'private' })).toBe('private');
  });

  test('certificates are on unless explicitly switched off', () => {
    expect(certificatesEnabled({})).toBe(true);
    expect(certificatesEnabled({ certificates_enabled: true })).toBe(true);
    expect(certificatesEnabled({ certificates_enabled: false })).toBe(false);
  });
});
