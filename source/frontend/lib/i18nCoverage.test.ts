/**
 * Every user-visible word in a component template must come from
 * translations.ts. Mixed English/Vietnamese UI came back twice because nothing
 * failed when someone typed a literal; this makes it fail.
 *
 * Heuristic, deliberately: it reads template source, not rendered DOM, and
 * allows short tokens (keyboard keys, initials) and product/brand terms that
 * are the same in both languages.
 */
import { describe, it, expect } from 'vitest';

// Raw sources through Vite, so the test needs no Node typings.
const SOURCES = import.meta.glob(['../components/*.vue', '../App.vue'], { query: '?raw', import: 'default', eager: true }) as Record<string, string>;

const ALLOWED = new Set([
  'KOSHI', 'Koshi', 'Scrum', 'DAG', 'AI', 'Kanban', 'Sprint', 'Burndown', 'Velocity', 'Retrospective',
  'PM', 'Esc', 'Diff', 'dev@', 'KOSHI 輿', 'koshi — board', 'Enter', 'Space', 'Backspace', 'Git', 'GitHub', 'Google', 'JSON', 'h/j/k/l', 'H/L', '1-4',
]);

function literals(src: string): string[] {
  const start = src.indexOf('<template>');
  if (start < 0) return [];
  const tpl = src.slice(start).replace(/<!--[\s\S]*?-->/g, '').replace(/\{\{[\s\S]*?\}\}/g, ' ');
  const out: string[] = [];
  for (const m of tpl.matchAll(/>([^<>]*)</g)) {
    const text = m[1].replace(/\{\{[\s\S]*?\}\}/g, ' ').replace(/&[a-z]+;/g, ' ').trim();
    for (const piece of text.split(/\s{2,}|\n/)) {
      const t = piece.trim().replace(/^[·•→—:*()\-–,.!?|/\s\d]+|[·•→—:*()\-–,.!?|/\s\d]+$/g, '');
      if (t.length <= 3 || ALLOWED.has(t) || !/[A-Za-zÀ-ỹ]/.test(t)) continue;
      out.push(t);
    }
  }
  for (const m of tpl.matchAll(/\s(?:title|placeholder|aria-label|alt)="([^"]*[A-Za-zÀ-ỹ][^"]*)"/g)) {
    // Example addresses and skill lists read the same in either language.
    if (!ALLOWED.has(m[1]) && m[1].length > 3 && !m[1].includes('@') && !m[1].includes(',')) out.push(`@${m[1]}`);
  }
  return out;
}

describe('i18n coverage', () => {
  it('found the components', () => expect(Object.keys(SOURCES).length).toBeGreaterThan(20));
  for (const [file, src] of Object.entries(SOURCES)) {
    it(`${file.split('/').pop()} has no hard-coded UI text`, () => {
      expect(literals(src)).toEqual([]);
    });
  }
});
