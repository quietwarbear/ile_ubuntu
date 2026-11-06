import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CourseNotice } from './CourseNotice';
import { apiGet, apiPut } from '../../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../lib/api', () => ({ apiGet: jest.fn(), apiPut: jest.fn() }));
jest.mock('../LessonContentViewer', () => ({ content }) => <div data-testid="viewer">{content}</div>);
jest.mock('./WysiwygEditor', () => ({ value, onChange, testId }) => (
  <textarea data-testid={testId} value={value} onChange={e => onChange(e.target.value)} />
));

const flush = () => act(() => new Promise(r => setTimeout(r, 0)));
let container; let root;
beforeEach(() => {
  apiGet.mockReset(); apiPut.mockReset();
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
const $ = id => container.querySelector(`[data-testid="${id}"]`);

test('enrolled students see the notice, without an edit control', async () => {
  apiGet.mockResolvedValue({ body: 'Please do not share recordings.' });
  act(() => root.render(<CourseNotice courseId="c1" canRead canEdit={false} />));
  await flush();
  expect(apiGet).toHaveBeenCalledWith('/api/courses/c1/notice');
  expect($('viewer').textContent).toBe('Please do not share recordings.');
  expect($('course-notice-edit')).toBeNull();
});

test('people outside the course do not even ask for it', async () => {
  act(() => root.render(<CourseNotice courseId="c1" canRead={false} canEdit={false} />));
  await flush();
  expect(apiGet).not.toHaveBeenCalled();
  expect(container.innerHTML).toBe('');
});

test('no notice: students see nothing, staff get an add button', async () => {
  apiGet.mockRejectedValue(new Error('No notice'));
  act(() => root.render(<CourseNotice courseId="c1" canRead canEdit={false} />));
  await flush();
  expect(container.innerHTML).toBe('');
  act(() => root.render(<CourseNotice courseId="c1" canRead canEdit />));
  await flush();
  expect($('course-notice-add')).not.toBeNull();
});

test('staff write and save a notice', async () => {
  apiGet.mockRejectedValue(new Error('No notice'));
  apiPut.mockResolvedValue({ body: 'Credits: our hosts.' });
  act(() => root.render(<CourseNotice courseId="c1" canRead canEdit />));
  await flush();
  await act(async () => { $('course-notice-add').click(); });
  const input = $('course-notice-input');
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set.call(input, 'Credits: our hosts.');
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await act(async () => { $('course-notice-save').click(); });
  await flush();
  expect(apiPut).toHaveBeenCalledWith('/api/courses/c1/notice', { body: 'Credits: our hosts.' });
  expect($('viewer').textContent).toBe('Credits: our hosts.');
});
