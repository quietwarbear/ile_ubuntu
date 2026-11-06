// Course visibility choices as teachers see them. The backend's
// VISIBILITIES (routes/courses.py) is the source of truth for the values.
export const VISIBILITY_OPTIONS = [
  { value: 'listed', label: 'Listed', explain: 'Shows in the course catalog and search; anyone can join.' },
  { value: 'unlisted', label: 'Invite-only', explain: 'Hidden from the catalog; people join with the link or an invite code.' },
  { value: 'village', label: 'Village only', explain: 'Only members of this course’s village can see and join it.' },
  { value: 'private', label: 'Private', explain: 'Hidden everywhere. No one can join on their own — only people you enroll get in.' },
];

// Courses created before visibility existed have no field and are listed.
export function currentVisibility(course) {
  return course?.visibility || 'listed';
}

// "Village only" is offered only to a course that belongs to a village.
export function visibilityOptionsFor(course) {
  return VISIBILITY_OPTIONS.filter(o => o.value !== 'village' || course?.village_id);
}

export function visibilityExplanation(value) {
  return VISIBILITY_OPTIONS.find(o => o.value === value)?.explain || '';
}

export function certificatesEnabled(course) {
  return course?.certificates_enabled !== false;
}
