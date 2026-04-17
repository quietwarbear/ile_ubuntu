import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import {
  Exam, Plus, Trash, Check, X, ArrowRight, Trophy, Warning, Eye,
  PencilSimple, ListChecks, TextT, ArrowsLeftRight, CheckCircle, XCircle,
} from '@phosphor-icons/react';
import { apiGet, apiPost, apiPut, apiDelete } from '../../lib/api';

const QUESTION_TYPES = [
  { value: 'multiple_choice', label: 'Multiple Choice', icon: ListChecks },
  { value: 'true_false', label: 'True / False', icon: CheckCircle },
  { value: 'short_answer', label: 'Short Answer', icon: TextT },
  { value: 'matching', label: 'Matching', icon: ArrowsLeftRight },
];

// ───────────────────────── Quiz Builder (Instructor) ─────────────────────────

function QuestionEditor({ question, index, onChange, onRemove }) {
  const q = question;

  const update = (field, val) => onChange({ ...q, [field]: val });

  const handleOptionChange = (i, val) => {
    const opts = [...(q.options || [])];
    opts[i] = val;
    update('options', opts);
  };

  const addOption = () => update('options', [...(q.options || []), '']);
  const removeOption = (i) => {
    const opts = (q.options || []).filter((_, idx) => idx !== i);
    update('options', opts);
  };

  // Matching pairs
  const handlePairChange = (i, side, val) => {
    const pairs = [...(q.matching_pairs || [])];
    pairs[i] = { ...pairs[i], [side]: val };
    update('matching_pairs', pairs);
    // Also update correct_answer map
    const ca = {};
    pairs.forEach(p => { if (p.left && p.right) ca[p.left] = p.right; });
    update('correct_answer', ca);
  };
  const addPair = () => update('matching_pairs', [...(q.matching_pairs || []), { left: '', right: '' }]);
  const removePair = (i) => {
    const pairs = (q.matching_pairs || []).filter((_, idx) => idx !== i);
    update('matching_pairs', pairs);
    const ca = {};
    pairs.forEach(p => { if (p.left && p.right) ca[p.left] = p.right; });
    update('correct_answer', ca);
  };

  return (
    <Card className="bg-[#050814] border-[#1E293B]">
      <CardContent className="p-3 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-[#D4AF37] font-medium">Question {index + 1}</span>
          <div className="flex items-center gap-2">
            <Input
              type="number" min={1} max={100}
              value={q.points || 1}
              onChange={(e) => update('points', parseInt(e.target.value) || 1)}
              className="w-16 bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-[10px] h-6"
              title="Points"
            />
            <span className="text-[10px] text-[#64748B]">pts</span>
            <button onClick={onRemove} className="text-[#64748B] hover:text-red-400 transition-colors">
              <Trash size={14} />
            </button>
          </div>
        </div>

        {/* Type selector */}
        <div className="flex gap-1 flex-wrap">
          {QUESTION_TYPES.map(t => (
            <button key={t.value}
              onClick={() => update('type', t.value)}
              className={`flex items-center gap-1 px-2 py-1 rounded text-[10px] transition-colors ${
                q.type === t.value
                  ? 'bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/30'
                  : 'bg-[#0F172A] text-[#64748B] border border-[#1E293B] hover:text-[#94A3B8]'
              }`}>
              <t.icon size={12} /> {t.label}
            </button>
          ))}
        </div>

        {/* Question text */}
        <Textarea
          placeholder="Enter your question..."
          value={q.text || ''}
          onChange={(e) => update('text', e.target.value)}
          className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-xs min-h-[50px]"
        />

        {/* Type-specific fields */}
        {q.type === 'multiple_choice' && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-[#64748B]">Options (click to set correct answer):</span>
            {(q.options || ['', '', '', '']).map((opt, i) => (
              <div key={i} className="flex items-center gap-2">
                <button
                  onClick={() => update('correct_answer', opt)}
                  className={`w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center border transition-colors ${
                    q.correct_answer === opt && opt
                      ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                      : 'border-[#1E293B] text-[#64748B] hover:border-[#D4AF37]'
                  }`}
                  title="Set as correct answer"
                >
                  {q.correct_answer === opt && opt && <Check size={10} />}
                </button>
                <Input
                  placeholder={`Option ${String.fromCharCode(65 + i)}`}
                  value={opt}
                  onChange={(e) => handleOptionChange(i, e.target.value)}
                  className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-xs flex-1"
                />
                {(q.options || []).length > 2 && (
                  <button onClick={() => removeOption(i)} className="text-[#64748B] hover:text-red-400">
                    <X size={12} />
                  </button>
                )}
              </div>
            ))}
            <Button size="sm" variant="ghost" onClick={addOption}
              className="text-[#D4AF37] text-[10px] h-6">
              <Plus size={12} className="mr-1" /> Add Option
            </Button>
          </div>
        )}

        {q.type === 'true_false' && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-[#64748B]">Correct answer:</span>
            <div className="flex gap-2">
              {['true', 'false'].map(val => (
                <button key={val}
                  onClick={() => update('correct_answer', val)}
                  className={`px-4 py-1.5 rounded text-xs transition-colors ${
                    q.correct_answer === val
                      ? 'bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/30'
                      : 'bg-[#0F172A] text-[#64748B] border border-[#1E293B] hover:text-[#94A3B8]'
                  }`}>
                  {val.charAt(0).toUpperCase() + val.slice(1)}
                </button>
              ))}
            </div>
          </div>
        )}

        {q.type === 'matching' && (
          <div className="space-y-1.5">
            <span className="text-[10px] text-[#64748B]">Matching pairs:</span>
            {(q.matching_pairs || [{ left: '', right: '' }]).map((pair, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  placeholder="Left item"
                  value={pair.left || ''}
                  onChange={(e) => handlePairChange(i, 'left', e.target.value)}
                  className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-xs flex-1"
                />
                <ArrowsLeftRight size={14} className="text-[#64748B] flex-shrink-0" />
                <Input
                  placeholder="Right item"
                  value={pair.right || ''}
                  onChange={(e) => handlePairChange(i, 'right', e.target.value)}
                  className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-xs flex-1"
                />
                {(q.matching_pairs || []).length > 1 && (
                  <button onClick={() => removePair(i)} className="text-[#64748B] hover:text-red-400">
                    <X size={12} />
                  </button>
                )}
              </div>
            ))}
            <Button size="sm" variant="ghost" onClick={addPair}
              className="text-[#D4AF37] text-[10px] h-6">
              <Plus size={12} className="mr-1" /> Add Pair
            </Button>
          </div>
        )}

        {q.type === 'short_answer' && (
          <p className="text-[10px] text-[#64748B] italic">
            Short answer questions require manual grading by the instructor.
          </p>
        )}

        {/* Explanation (optional) */}
        <Input
          placeholder="Explanation (shown after grading, optional)"
          value={q.explanation || ''}
          onChange={(e) => update('explanation', e.target.value)}
          className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-[10px]"
        />
      </CardContent>
    </Card>
  );
}

function QuizBuilder({ courseId, lessonId, existingQuiz, onSaved }) {
  const isEdit = !!existingQuiz;
  const [title, setTitle] = useState(existingQuiz?.title || 'Lesson Quiz');
  const [description, setDescription] = useState(existingQuiz?.description || '');
  const [passThreshold, setPassThreshold] = useState(existingQuiz?.pass_threshold || 70);
  const [maxAttempts, setMaxAttempts] = useState(existingQuiz?.max_attempts || 3);
  const [showAnswers, setShowAnswers] = useState(existingQuiz?.show_correct_answers ?? true);
  const [questions, setQuestions] = useState(
    existingQuiz?.questions?.length > 0
      ? existingQuiz.questions
      : [{ type: 'multiple_choice', text: '', options: ['', '', '', ''], correct_answer: '', points: 1 }]
  );
  const [saving, setSaving] = useState(false);

  const updateQuestion = (idx, q) => {
    const qs = [...questions];
    qs[idx] = q;
    setQuestions(qs);
  };

  const removeQuestion = (idx) => {
    if (questions.length <= 1) return;
    setQuestions(questions.filter((_, i) => i !== idx));
  };

  const addQuestion = () => {
    setQuestions([...questions, { type: 'multiple_choice', text: '', options: ['', '', '', ''], correct_answer: '', points: 1 }]);
  };

  const handleSave = async () => {
    // Validate
    for (let i = 0; i < questions.length; i++) {
      if (!questions[i].text?.trim()) {
        alert(`Question ${i + 1} needs text.`);
        return;
      }
    }
    setSaving(true);
    try {
      const payload = { title, description, questions, pass_threshold: passThreshold, max_attempts: maxAttempts, show_correct_answers: showAnswers };
      if (isEdit) {
        await apiPut(`/api/courses/${courseId}/lessons/${lessonId}/quiz`, payload);
      } else {
        await apiPost(`/api/courses/${courseId}/lessons/${lessonId}/quiz`, payload);
      }
      onSaved?.();
    } catch (e) { alert(e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this quiz and all student attempts?')) return;
    try {
      await apiDelete(`/api/courses/${courseId}/lessons/${lessonId}/quiz`);
      onSaved?.();
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Input placeholder="Quiz title" value={title} onChange={e => setTitle(e.target.value)}
          className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs col-span-2" />
        <Input placeholder="Description (optional)" value={description} onChange={e => setDescription(e.target.value)}
          className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs col-span-2" />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#64748B] whitespace-nowrap">Pass:</span>
          <Input type="number" min={0} max={100} value={passThreshold}
            onChange={e => setPassThreshold(parseInt(e.target.value) || 0)}
            className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs w-16" />
          <span className="text-[10px] text-[#64748B]">%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#64748B] whitespace-nowrap">Max attempts:</span>
          <Input type="number" min={1} max={99} value={maxAttempts}
            onChange={e => setMaxAttempts(parseInt(e.target.value) || 1)}
            className="bg-[#050814] border-[#1E293B] text-[#F8FAFC] text-xs w-16" />
        </div>
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" checked={showAnswers} onChange={e => setShowAnswers(e.target.checked)}
          className="accent-[#D4AF37]" />
        <span className="text-[10px] text-[#94A3B8]">Show correct answers after submission</span>
      </label>

      <div className="space-y-2">
        {questions.map((q, i) => (
          <QuestionEditor key={i} question={q} index={i}
            onChange={(updated) => updateQuestion(i, updated)}
            onRemove={() => removeQuestion(i)} />
        ))}
      </div>

      <Button size="sm" variant="ghost" onClick={addQuestion}
        className="text-[#D4AF37] text-xs w-full border border-dashed border-[#1E293B] hover:border-[#D4AF37]/40">
        <Plus size={14} className="mr-1" /> Add Question
      </Button>

      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={handleSave} disabled={saving}
          className="bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs">
          {saving ? 'Saving...' : (isEdit ? 'Update Quiz' : 'Create Quiz')}
        </Button>
        {isEdit && (
          <Button size="sm" variant="ghost" onClick={handleDelete}
            className="text-red-400 hover:text-red-300 text-xs">
            <Trash size={14} className="mr-1" /> Delete Quiz
          </Button>
        )}
      </div>
    </div>
  );
}

// ───────────────────────── Quiz Taker (Student) ─────────────────────────

function QuizTaker({ quiz, courseId, lessonId, onComplete }) {
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const setAnswer = (qId, val) => setAnswers({ ...answers, [qId]: val });

  const handleSubmit = async () => {
    // Check all questions answered
    const unanswered = quiz.questions.filter(q => !answers[q.id] && answers[q.id] !== false);
    if (unanswered.length > 0 && !window.confirm(`${unanswered.length} question(s) unanswered. Submit anyway?`)) return;
    setSubmitting(true);
    try {
      const result = await apiPost(`/api/courses/${courseId}/lessons/${lessonId}/quiz/submit`, { answers });
      onComplete?.(result);
    } catch (e) { alert(e.message); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="space-y-3">
      {quiz.questions.map((q, i) => (
        <Card key={q.id} className="bg-[#050814] border-[#1E293B]">
          <CardContent className="p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs text-[#F8FAFC]">
                <span className="text-[#D4AF37] mr-1">{i + 1}.</span>
                {q.text}
              </p>
              <span className="text-[10px] text-[#64748B]">{q.points || 1} pt{(q.points || 1) > 1 ? 's' : ''}</span>
            </div>

            {q.type === 'multiple_choice' && (
              <div className="space-y-1">
                {(q.options || []).map((opt, j) => (
                  <button key={j}
                    onClick={() => setAnswer(q.id, opt)}
                    className={`w-full text-left px-3 py-1.5 rounded text-xs transition-colors ${
                      answers[q.id] === opt
                        ? 'bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/30'
                        : 'bg-[#0F172A] text-[#94A3B8] border border-[#1E293B] hover:border-[#D4AF37]/20'
                    }`}>
                    <span className="text-[#64748B] mr-2">{String.fromCharCode(65 + j)}.</span>
                    {opt}
                  </button>
                ))}
              </div>
            )}

            {q.type === 'true_false' && (
              <div className="flex gap-2">
                {['true', 'false'].map(val => (
                  <button key={val}
                    onClick={() => setAnswer(q.id, val)}
                    className={`flex-1 px-3 py-1.5 rounded text-xs transition-colors ${
                      answers[q.id] === val
                        ? 'bg-[#D4AF37]/10 text-[#D4AF37] border border-[#D4AF37]/30'
                        : 'bg-[#0F172A] text-[#94A3B8] border border-[#1E293B] hover:border-[#D4AF37]/20'
                    }`}>
                    {val.charAt(0).toUpperCase() + val.slice(1)}
                  </button>
                ))}
              </div>
            )}

            {q.type === 'short_answer' && (
              <Textarea
                placeholder="Type your answer..."
                value={answers[q.id] || ''}
                onChange={(e) => setAnswer(q.id, e.target.value)}
                className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-xs min-h-[60px]"
              />
            )}

            {q.type === 'matching' && (
              <div className="space-y-1.5">
                {Object.keys(q.correct_answer || q.matching_pairs?.reduce((a, p) => ({ ...a, [p.left]: '' }), {}) || {}).map((left) => (
                  <div key={left} className="flex items-center gap-2">
                    <span className="text-xs text-[#F8FAFC] flex-1">{left}</span>
                    <ArrowsLeftRight size={14} className="text-[#64748B] flex-shrink-0" />
                    <Input
                      placeholder="Match..."
                      value={(answers[q.id] || {})[left] || ''}
                      onChange={(e) => setAnswer(q.id, { ...(answers[q.id] || {}), [left]: e.target.value })}
                      className="bg-[#0F172A] border-[#1E293B] text-[#F8FAFC] text-xs flex-1"
                    />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      ))}

      <Button onClick={handleSubmit} disabled={submitting}
        className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs">
        {submitting ? 'Submitting...' : 'Submit Quiz'}
      </Button>
    </div>
  );
}

// ───────────────────────── Results View ─────────────────────────

function QuizResults({ attempt, quiz }) {
  const passed = attempt.status === 'passed';
  const pending = attempt.status === 'pending_review';

  return (
    <div className="space-y-3">
      <div className={`p-4 rounded-md border text-center ${
        pending ? 'bg-yellow-500/5 border-yellow-500/20' :
        passed ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-red-500/5 border-red-500/20'
      }`}>
        {pending ? (
          <Warning size={32} className="text-yellow-400 mx-auto mb-2" />
        ) : passed ? (
          <Trophy size={32} className="text-emerald-400 mx-auto mb-2" />
        ) : (
          <XCircle size={32} className="text-red-400 mx-auto mb-2" />
        )}
        <p className="text-lg font-light text-[#F8FAFC]">{attempt.score_percentage}%</p>
        <p className="text-xs text-[#94A3B8]">
          {attempt.earned_points} / {attempt.total_points} points
        </p>
        <Badge className={`mt-2 text-[10px] ${
          pending ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
          passed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'
        }`}>
          {pending ? 'Pending Review' : passed ? 'Passed' : 'Not Passed'}
        </Badge>
      </div>

      {attempt.results?.map((r, i) => (
        <div key={r.question_id} className={`p-2.5 rounded border text-xs ${
          r.needs_review ? 'border-yellow-500/20 bg-yellow-500/5' :
          r.is_correct ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'
        }`}>
          <div className="flex items-center gap-2 mb-1">
            {r.needs_review ? (
              <Warning size={14} className="text-yellow-400" />
            ) : r.is_correct ? (
              <CheckCircle size={14} className="text-emerald-400" />
            ) : (
              <XCircle size={14} className="text-red-400" />
            )}
            <span className="text-[#F8FAFC]">Q{i + 1}</span>
            <span className="text-[#64748B]">{r.points_earned}/{r.points_possible} pts</span>
          </div>
          <p className="text-[#94A3B8]">Your answer: {typeof r.user_answer === 'object' ? JSON.stringify(r.user_answer) : String(r.user_answer || '(empty)')}</p>
          {r.correct_answer && !r.needs_review && (
            <p className="text-[#64748B]">Correct: {typeof r.correct_answer === 'object' ? JSON.stringify(r.correct_answer) : String(r.correct_answer)}</p>
          )}
          {r.feedback && <p className="text-[#D4AF37] mt-1">Feedback: {r.feedback}</p>}
        </div>
      ))}
    </div>
  );
}

// ───────────────────────── Main Component ─────────────────────────

export function LessonQuiz({ courseId, lessonId, user, isInstructor }) {
  const [quiz, setQuiz] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('default'); // 'default' | 'build' | 'take' | 'results'
  const [lastAttempt, setLastAttempt] = useState(null);
  const [showAllAttempts, setShowAllAttempts] = useState(false);
  const [allAttempts, setAllAttempts] = useState([]);

  const loadQuiz = async () => {
    try {
      const data = await apiGet(`/api/courses/${courseId}/lessons/${lessonId}/quiz`);
      setQuiz(data);
    } catch (e) {
      setQuiz(null);
    }
    // Load student attempts
    try {
      const attData = await apiGet(`/api/courses/${courseId}/lessons/${lessonId}/quiz/attempts`);
      setAttempts(attData.attempts || []);
      setMaxAttempts(attData.max_attempts || 3);
    } catch (e) { /* no attempts */ }
    setLoading(false);
  };

  useEffect(() => { loadQuiz(); }, [courseId, lessonId]);

  const loadAllAttempts = async () => {
    try {
      const data = await apiGet(`/api/courses/${courseId}/lessons/${lessonId}/quiz/all-attempts`);
      setAllAttempts(data.attempts || []);
      setShowAllAttempts(true);
    } catch (e) { alert(e.message); }
  };

  const handleQuizComplete = (result) => {
    setLastAttempt(result);
    setView('results');
    loadQuiz();
  };

  if (loading) {
    return (
      <div className="flex justify-center py-4">
        <div className="w-5 h-5 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="lesson-quiz">
      <div className="flex items-center justify-between">
        <span className="text-[10px] tracking-[0.15em] uppercase text-[#D4AF37] flex items-center gap-1">
          <Exam size={12} weight="duotone" /> Quiz
        </span>
        {quiz && isInstructor && view !== 'build' && (
          <div className="flex gap-1">
            <Button size="sm" variant="ghost" onClick={() => setView('build')}
              className="text-[#D4AF37] text-[10px] h-6">
              <PencilSimple size={12} className="mr-1" /> Edit
            </Button>
            <Button size="sm" variant="ghost" onClick={loadAllAttempts}
              className="text-[#94A3B8] text-[10px] h-6">
              <Eye size={12} className="mr-1" /> All Attempts
            </Button>
          </div>
        )}
      </div>

      {/* Builder mode */}
      {(view === 'build' || (!quiz && isInstructor)) && (
        <QuizBuilder
          courseId={courseId} lessonId={lessonId}
          existingQuiz={quiz}
          onSaved={() => { setView('default'); loadQuiz(); }}
        />
      )}

      {/* No quiz */}
      {!quiz && !isInstructor && (
        <p className="text-xs text-[#64748B] text-center py-4">No quiz for this lesson yet.</p>
      )}

      {/* Quiz exists — student view */}
      {quiz && view === 'default' && !isInstructor && (
        <div className="space-y-3">
          <Card className="bg-[#050814] border-[#1E293B]">
            <CardContent className="p-3">
              <h4 className="text-sm text-[#F8FAFC] font-medium">{quiz.title}</h4>
              {quiz.description && <p className="text-xs text-[#94A3B8] mt-1">{quiz.description}</p>}
              <div className="flex gap-3 mt-2 text-[10px] text-[#64748B]">
                <span>{quiz.questions?.length || 0} questions</span>
                <span>Pass: {quiz.pass_threshold || 70}%</span>
                <span>Attempts: {attempts.length}/{maxAttempts}</span>
              </div>
            </CardContent>
          </Card>

          {attempts.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] text-[#64748B]">Your attempts:</span>
              {attempts.map(att => (
                <button key={att.id}
                  onClick={() => { setLastAttempt(att); setView('results'); }}
                  className="w-full flex items-center justify-between p-2 rounded bg-[#050814] border border-[#1E293B] hover:border-[#D4AF37]/20 transition-colors text-xs">
                  <span className="text-[#94A3B8]">Attempt {att.attempt_number}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[#F8FAFC]">{att.score_percentage}%</span>
                    <Badge className={`text-[9px] ${
                      att.status === 'passed' ? 'bg-emerald-500/10 text-emerald-400' :
                      att.status === 'pending_review' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>{att.status}</Badge>
                  </div>
                </button>
              ))}
            </div>
          )}

          {attempts.length < maxAttempts && (
            <Button size="sm" onClick={() => setView('take')}
              className="w-full bg-[#D4AF37] text-[#050814] hover:bg-[#F3E5AB] text-xs">
              <ArrowRight size={14} className="mr-1" />
              {attempts.length === 0 ? 'Start Quiz' : 'Retake Quiz'}
            </Button>
          )}
        </div>
      )}

      {/* Quiz exists — instructor summary */}
      {quiz && view === 'default' && isInstructor && (
        <Card className="bg-[#050814] border-[#1E293B]">
          <CardContent className="p-3">
            <h4 className="text-sm text-[#F8FAFC] font-medium">{quiz.title}</h4>
            {quiz.description && <p className="text-xs text-[#94A3B8] mt-1">{quiz.description}</p>}
            <div className="flex gap-3 mt-2 text-[10px] text-[#64748B]">
              <span>{quiz.questions?.length || 0} questions</span>
              <span>Pass: {quiz.pass_threshold || 70}%</span>
              <span>Max attempts: {quiz.max_attempts || 3}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Taking quiz */}
      {quiz && view === 'take' && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm text-[#F8FAFC]">{quiz.title}</h4>
            <Button size="sm" variant="ghost" onClick={() => setView('default')}
              className="text-[#94A3B8] text-[10px] h-6">
              <X size={12} className="mr-1" /> Cancel
            </Button>
          </div>
          <QuizTaker quiz={quiz} courseId={courseId} lessonId={lessonId} onComplete={handleQuizComplete} />
        </div>
      )}

      {/* Results */}
      {view === 'results' && lastAttempt && (
        <div>
          <Button size="sm" variant="ghost" onClick={() => { setView('default'); setLastAttempt(null); }}
            className="text-[#94A3B8] text-[10px] h-6 mb-2">
            <X size={12} className="mr-1" /> Back
          </Button>
          <QuizResults attempt={lastAttempt} quiz={quiz} />
        </div>
      )}

      {/* All attempts (instructor) */}
      {showAllAttempts && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-[#64748B]">All student attempts:</span>
            <button onClick={() => setShowAllAttempts(false)} className="text-[#64748B] hover:text-[#94A3B8]">
              <X size={14} />
            </button>
          </div>
          {allAttempts.length === 0 ? (
            <p className="text-xs text-[#64748B]">No attempts yet.</p>
          ) : (
            <div className="space-y-1">
              {allAttempts.map(att => (
                <div key={att.id}
                  className="flex items-center justify-between p-2 rounded bg-[#050814] border border-[#1E293B] text-xs">
                  <span className="text-[#F8FAFC]">{att.user_name || 'Student'}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[#94A3B8]">#{att.attempt_number}</span>
                    <span className="text-[#F8FAFC]">{att.score_percentage}%</span>
                    <Badge className={`text-[9px] ${
                      att.status === 'passed' ? 'bg-emerald-500/10 text-emerald-400' :
                      att.status === 'pending_review' ? 'bg-yellow-500/10 text-yellow-400' :
                      'bg-red-500/10 text-red-400'
                    }`}>{att.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
