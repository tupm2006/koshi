import type { ProjectMember } from '../services/api';

/**
 * The `@[Display Name](userId)` token used inside comment bodies.
 *
 * The id is what a mention *means*; the label is only what it looked like when
 * written. Rendering resolves the id against the current roster and falls back
 * to the captured label when it cannot — someone who has since left the project
 * still reads as a name rather than a broken token.
 *
 * Kept in step with `source/backend/app/services/mentions.py`. The pattern is
 * duplicated because the two sides genuinely both need it; if it changes, both
 * change, and `mentions.test.ts` pins the shape either would have to break.
 */
export const MENTION_RE = /@\[([^\]]{1,100})\]\((\d{1,10})\)/g;

export interface MentionSegment {
  type: 'mention';
  userId: number;
  /** The label captured at write time. */
  label: string;
}

export interface TextSegment {
  type: 'text';
  value: string;
}

export type Segment = MentionSegment | TextSegment;

/**
 * Split a comment body into text and mention runs, for rendering.
 *
 * Returning segments rather than HTML is deliberate: the template renders each
 * one as a normal Vue node, so a comment body can never become markup. Building
 * an HTML string here and feeding it to `v-html` would make every comment a
 * stored-XSS vector.
 */
export function parseSegments(content: string): Segment[] {
  const out: Segment[] = [];
  let last = 0;

  // `matchAll` on a /g regex without mutating lastIndex across calls.
  for (const m of content.matchAll(MENTION_RE)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ type: 'text', value: content.slice(last, at) });
    out.push({ type: 'mention', label: m[1]!, userId: Number(m[2]) });
    last = at + m[0].length;
  }
  if (last < content.length) out.push({ type: 'text', value: content.slice(last) });
  return out;
}

/** Build the token a composer inserts when somebody is picked. */
export const mentionToken = (userId: number, fullName: string) =>
  // A closing bracket in a name would end the label early, so it is dropped
  // rather than escaped: no display name legitimately contains one, and an
  // escaping scheme is a second thing to keep in step with the server.
  `@[${fullName.replace(/[[\]]/g, '')}](${userId})`;

/**
 * Find an in-progress `@query` immediately before the caret.
 *
 * Returns null unless the caret sits at the end of a plausible mention — an `@`
 * that begins a word, followed by no more than a short run without newlines.
 * The word-boundary rule is what stops an email address opening the picker.
 */
export function activeMentionQuery(
  text: string,
  caret: number,
): { query: string; from: number } | null {
  const upTo = text.slice(0, caret);
  const at = upTo.lastIndexOf('@');
  if (at === -1) return null;

  // Must start a word: "a@b.com" is an address, not a mention.
  const before = at === 0 ? '' : upTo[at - 1]!;
  if (before && !/\s/.test(before)) return null;

  const query = upTo.slice(at + 1);
  // A newline or an over-long run means the user moved on and left an `@`
  // behind; the picker should not reappear.
  if (/[\n\r]/.test(query) || query.length > 40) return null;

  return { query, from: at };
}

/** Roster entries matching a query, by name or email, capped for the menu. */
export function matchMembers(
  members: ProjectMember[],
  query: string,
  limit = 6,
): ProjectMember[] {
  const q = query.trim().toLowerCase();
  const pool = members.filter((m) => m.status === 'ACCEPTED');
  if (!q) return pool.slice(0, limit);
  return pool
    .filter((m) => m.full_name.toLowerCase().includes(q) || m.email.toLowerCase().includes(q))
    .slice(0, limit);
}
