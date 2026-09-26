import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { LessonCard } from './LessonCard';
import { apiPut } from '../../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../../lib/api', () => ({
  BACKEND_URL: '',
  apiPut: jest.fn(),
  apiDelete: jest.fn(),
}));
jest.mock('./WysiwygEditor', () => function MockEditor({ value, onChange, testId }) {
  return <textarea value={value} onChange={e => onChange(e.target.value)} data-testid={testId} />;
});
jest.mock('../LessonContentViewer', () => () => null);
jest.mock('./LessonVideoPlayer', () => ({ LessonVideoPlayer: () => null }));
jest.mock('./LessonQuiz', () => ({ LessonQuiz: () => null }));
jest.mock('./LessonSubmissions', () => ({ LessonSubmissions: () => null }));
jest.mock('./LessonComments', () => ({ LessonComments: () => null }));

describe('LessonCard section editing', () => {
  let container;
  let root;
  const lesson = {
    id: 'lesson-1',
    title: 'All Meeting Info',
    description: 'Info needed for all meetings',
    content: '',
    module_id: null,
    hidden: false,
  };
  const modules = [
    { id: 'protocol-id', title: 'Protocol' },
    { id: 'wisdom-id', title: 'Wisdom Circle' },
  ];

  beforeEach(() => {
    apiPut.mockReset();
    apiPut.mockResolvedValue({});
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  test('lets an instructor assign an existing lesson to a section', async () => {
    const onReloadCourse = jest.fn();
    act(() => {
      root.render(
        <LessonCard
          lesson={lesson}
          idx={0}
          isEnrolled={false}
          isLessonCompleted={false}
          isExpanded
          isInstructor
          lessonFiles={[]}
          googleConnected={false}
          uploading={false}
          uploadingFor={null}
          onToggleExpand={() => {}}
          onComplete={() => {}}
          onUploadClick={() => {}}
          onDeleteFile={() => {}}
          onOpenImport={() => {}}
          courseId="course-1"
          user={{ id: 'teacher-1' }}
          onReloadCourse={onReloadCourse}
          modules={modules}
        />,
      );
    });

    act(() => container.querySelector('[data-testid="edit-lesson-lesson-1"]').click());
    const select = container.querySelector('[data-testid="edit-lesson-module-lesson-1"]');
    expect([...select.options].map(option => option.text)).toEqual([
      'No section', 'Protocol', 'Wisdom Circle',
    ]);

    act(() => {
      select.value = 'protocol-id';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await act(async () => {
      container.querySelector('[data-testid="save-lesson-lesson-1"]').click();
    });

    expect(apiPut).toHaveBeenCalledWith('/api/courses/course-1/lessons/lesson-1', expect.objectContaining({
      module_id: 'protocol-id',
    }));
    expect(onReloadCourse).toHaveBeenCalled();
  });
});
