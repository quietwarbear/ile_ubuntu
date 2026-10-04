import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { EnrolledStudents } from './EnrolledStudents';
import { apiDelete, apiPost } from '../../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../../lib/api', () => ({
  apiDelete: jest.fn(),
  apiPost: jest.fn(),
}));

describe('EnrolledStudents roster controls', () => {
  let container;
  let root;

  beforeEach(() => {
    apiDelete.mockReset().mockResolvedValue({ success: true });
    apiPost.mockReset().mockResolvedValue({ id: 'enrollment-2' });
    window.confirm = jest.fn(() => true);
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  test('keeps the add-student control visible for an empty course', async () => {
    const onChanged = jest.fn().mockResolvedValue();
    act(() => root.render(
      <EnrolledStudents courseId="course-1" enrollments={[]} onChanged={onChanged} />,
    ));

    const email = container.querySelector('input[type="email"]');
    act(() => {
      Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')
        .set.call(email, 'learner@example.com');
      email.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      container.querySelector('[data-testid="add-student-form"]')
        .dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });

    expect(apiPost).toHaveBeenCalledWith('/api/courses/course-1/enrollments', {
      email: 'learner@example.com',
    });
    expect(onChanged).toHaveBeenCalled();
  });

  test('removes the selected student after confirmation', async () => {
    const onChanged = jest.fn().mockResolvedValue();
    const enrollment = {
      id: 'enrollment-1', user_id: 'student-1', user_name: 'Iya Sobande',
      user_email: 'iya@example.com', enrolled_at: '2026-10-04T12:00:00Z', progress: 25,
    };
    act(() => root.render(
      <EnrolledStudents courseId="course-1" enrollments={[enrollment]} onChanged={onChanged} />,
    ));

    await act(async () => {
      container.querySelector('[data-testid="remove-student-student-1"]').click();
    });

    expect(window.confirm).toHaveBeenCalled();
    expect(apiDelete).toHaveBeenCalledWith('/api/courses/course-1/enrollments/student-1');
    expect(onChanged).toHaveBeenCalled();
  });
});
