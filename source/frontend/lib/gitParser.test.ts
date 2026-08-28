/**
 * Tests for the Git diff analyser (D5 GAP-03).
 *
 * These are characterisation tests: they pin what this function does today,
 * including the parts that are weaker than the docstring suggests. The retired
 * SRS claimed a test file for this module that never existed, so nothing here
 * was ever verified — several assertions below exist specifically to record
 * behaviour that a reader would otherwise assume was better than it is.
 *
 * The module is security-adjacent (it flags hardcoded secrets) and its output
 * drives destructive UI: GitDiffModal maps `resolvedTaskIds` straight onto
 * "Apply Status Transitions", which writes DONE. So the boundaries of the
 * matching are worth stating explicitly.
 */
import { describe, it, expect } from 'vitest';
import { parseGitDiff } from './gitParser';
import type { Task } from '../types/task';

const task = (over: Partial<Task> = {}): Task => ({
  id: 'TSK-1',
  title: 'Implement the parser',
  status: 'TODO',
  priority: 'MEDIUM',
  createdAt: 0,
  updatedAt: 0,
  ...over,
});

/** Added lines in a unified diff carry a single leading '+'. */
const added = (...lines: string[]) => lines.map((l) => `+${l}`).join('\n');

describe('PR title', () => {
  it('falls back to a generic label when the first line is unremarkable', () => {
    expect(parseGitDiff('diff --git a/x b/x', []).prTitle).toBe('PR / Commit Diff Analysis');
  });

  it('takes a markdown heading as the title, stripped of its hashes', () => {
    expect(parseGitDiff('## Add the parser\n+code', []).prTitle).toBe('Add the parser');
  });

  it('takes a conventional-commit subject', () => {
    expect(parseGitDiff('feat: add the parser', []).prTitle).toBe('feat: add the parser');
    expect(parseGitDiff('fix: stop the crash', []).prTitle).toBe('fix: stop the crash');
  });

  it('skips leading blank lines to find the subject', () => {
    expect(parseGitDiff('\n\n   \n# Real title', []).prTitle).toBe('Real title');
  });

  it('does NOT recognise a scoped conventional commit', () => {
    // `feat(auth): ...` is the more common spelling in this very repo, and the
    // prefix check is a literal `startsWith('feat:')`, so it misses.
    expect(parseGitDiff('feat(auth): rotate the secret', []).prTitle)
      .toBe('PR / Commit Diff Analysis');
  });

  it('does not recognise other conventional-commit types', () => {
    // Only feat and fix are listed; chore/refactor/test/docs all fall through.
    expect(parseGitDiff('refactor: split the module', []).prTitle)
      .toBe('PR / Commit Diff Analysis');
  });
});

describe('explicit issue closing', () => {
  const tasks = [task({ id: 'TSK-1' }), task({ id: 'TSK-2', title: 'Second' })];

  it('resolves a task named by a closing keyword', () => {
    expect(parseGitDiff('closes #TSK-1', tasks).resolvedTaskIds).toEqual(['TSK-1']);
  });

  it('accepts the keyword variants and matches case-insensitively', () => {
    for (const phrase of ['close TSK-1', 'closed #TSK-1', 'fix TSK-1', 'fixes TSK-1',
                          'fixed TSK-1', 'resolve TSK-1', 'resolves #TSK-1', 'RESOLVED tsk-1']) {
      expect(parseGitDiff(phrase, tasks).resolvedTaskIds, phrase).toEqual(['TSK-1']);
    }
  });

  it('returns the task\'s own id casing, not the casing found in the diff', () => {
    // Matching is done on a lowercased key; the output must still be the real id
    // or the store lookup that follows would miss.
    expect(parseGitDiff('closes #tsk-1', tasks).resolvedTaskIds).toEqual(['TSK-1']);
  });

  it('ignores ids that match no known task', () => {
    expect(parseGitDiff('closes #TSK-999', tasks).resolvedTaskIds).toEqual([]);
  });

  it('finds several closings in one diff, without duplicates', () => {
    const res = parseGitDiff('closes #TSK-1, fixes #TSK-2 and closes #TSK-1 again', tasks);
    expect(res.resolvedTaskIds.sort()).toEqual(['TSK-1', 'TSK-2']);
  });

  it('reads the whole diff, not only the commit message', () => {
    // The regex runs over the raw text, so a closing keyword inside a code
    // comment in the patch body counts just as much as one in the subject.
    expect(parseGitDiff('diff --git a/x b/x\n+// fixes TSK-1\n', tasks).resolvedTaskIds)
      .toEqual(['TSK-1']);
  });

  it('does not resolve a task merely mentioned without a keyword', () => {
    expect(parseGitDiff('see TSK-1 for context', tasks).resolvedTaskIds).toEqual([]);
  });
});

describe('BLOCKED task auto-resolution', () => {
  // F-30. This is the most consequential behaviour in the module and the least
  // obvious: a BLOCKED task is marked resolved when *any* word longer than
  // three characters from its title appears in the diff. No closing keyword is
  // required. The modal then offers to write DONE.
  it('resolves a blocked task on a bare word match, with no closing keyword', () => {
    const blocked = task({ id: 'TSK-5', title: 'Waiting on migration', status: 'BLOCKED' });
    const res = parseGitDiff('+ ran the migration locally', [blocked]);
    expect(res.resolvedTaskIds).toEqual(['TSK-5']);
  });

  it('leaves non-blocked tasks alone under the same word match', () => {
    const todo = task({ id: 'TSK-5', title: 'Waiting on migration', status: 'TODO' });
    expect(parseGitDiff('+ ran the migration locally', [todo]).resolvedTaskIds).toEqual([]);
  });

  it('ignores short words, so a title of only short words never matches', () => {
    const blocked = task({ id: 'TSK-6', title: 'Fix db', status: 'BLOCKED' });
    expect(parseGitDiff('+ fix the db now', [blocked]).resolvedTaskIds).toEqual([]);
  });

  it('requires a whole word, not a substring', () => {
    // Before F-30 this used a bare `includes()`, so a task blocked on "store"
    // was auto-resolved by any diff touching `taskStore.ts`. The match is still
    // a heuristic — see OQ-08 — but it no longer fires on fragments.
    const blocked = task({ id: 'TSK-7', title: 'Migrate the store', status: 'BLOCKED' });
    expect(parseGitDiff('+ import { useTaskStore } from "./taskStore"', [blocked]).resolvedTaskIds)
      .toEqual([]);
    expect(parseGitDiff('+ the store is migrated', [blocked]).resolvedTaskIds).toEqual(['TSK-7']);
  });

  it('matches case-insensitively', () => {
    const blocked = task({ id: 'TSK-8', title: 'Waiting on Migration', status: 'BLOCKED' });
    expect(parseGitDiff('+ MIGRATION applied', [blocked]).resolvedTaskIds).toEqual(['TSK-8']);
  });
});

describe('architectural concerns', () => {
  it('flags TODO, FIXME, HACK and XXX markers on added lines', () => {
    for (const marker of ['TODO', 'FIXME', 'HACK', 'XXX', 'todo']) {
      const res = parseGitDiff(added(`// ${marker}: come back to this`), []);
      expect(res.architecturalConcerns.join(' '), marker).toContain(marker);
    }
  });

  it('ignores markers on context and removed lines', () => {
    // Only additions are the author's new debt; a FIXME being deleted is good news.
    const diff = '- // FIXME: old debt\n  // TODO: untouched context';
    expect(parseGitDiff(diff, []).architecturalConcerns).toEqual([]);
  });

  it('ignores the +++ file header', () => {
    expect(parseGitDiff('+++ b/TODO.md', []).architecturalConcerns).toEqual([]);
  });

  it('flags an empty catch block, in both spellings', () => {
    expect(parseGitDiff(added('} catch (e) {}'), []).architecturalConcerns)
      .toContain('Empty catch block detected (silent failure risk).');
    expect(parseGitDiff(added('} catch {}'), []).architecturalConcerns)
      .toContain('Empty catch block detected (silent failure risk).');
  });

  it('does not flag a catch block that handles the error', () => {
    expect(parseGitDiff(added('} catch (e) { log(e); }'), []).architecturalConcerns).toEqual([]);
  });

  it('flags an `any` annotation', () => {
    expect(parseGitDiff(added('const x: any = y;'), []).architecturalConcerns)
      .toContain('TypeScript unsafe `any` coercion detected in diff.');
  });

  it('reports each single-fire concern once however many lines trigger it', () => {
    const res = parseGitDiff(added('a: any', 'b: any', 'c: any'), []);
    expect(res.architecturalConcerns.filter((c) => c.includes('any'))).toHaveLength(1);
  });

  it('caps the list at five entries', () => {
    const res = parseGitDiff(added(...Array.from({ length: 12 }, (_, i) => `// TODO ${i}`)), []);
    expect(res.architecturalConcerns).toHaveLength(5);
  });

  it('truncates a long offending line in the message', () => {
    const res = parseGitDiff(added(`// TODO ${'x'.repeat(200)}`), []);
    expect(res.architecturalConcerns[0]!.length).toBeLessThan(120);
  });
});

describe('hardcoded secret detection', () => {
  const SECRET = 'Potential hardcoded secret or token detected in addition lines.';

  it('flags an assigned api key, secret, password or bearer token', () => {
    for (const name of ['api_key', 'API_KEY', 'secret', 'password', 'bearer']) {
      expect(parseGitDiff(added(`${name} = "sk_live_abcdefgh"`), []).architecturalConcerns, name)
        .toContain(SECRET);
    }
  });

  it('accepts single quotes and surrounding whitespace variants', () => {
    expect(parseGitDiff(added("const secret='abcdefghij'"), []).architecturalConcerns)
      .toContain(SECRET);
  });

  it('ignores a value shorter than eight characters', () => {
    expect(parseGitDiff(added('password = "short"'), []).architecturalConcerns).not.toContain(SECRET);
  });

  it('ignores a reference that assigns no literal', () => {
    expect(parseGitDiff(added('password = os.environ["PW"]'), []).architecturalConcerns)
      .not.toContain(SECRET);
  });

  // The following record real blind spots. They are not "wrong" tests: they
  // state the limits of the check so nobody treats a clean report as proof that
  // a diff contains no credentials (D6 §7.1).
  it('MISSES the colon form used by JSON, YAML and object literals', () => {
    expect(parseGitDiff(added('  "api_key": "sk_live_abcdefgh"'), []).architecturalConcerns)
      .not.toContain(SECRET);
  });

  it('MISSES an Authorization header literal', () => {
    expect(parseGitDiff(added('headers["Authorization"] = "Bearer eyJhbGciOi"'), []).architecturalConcerns)
      .not.toContain(SECRET);
  });

  it('MISSES a token under any other name', () => {
    expect(parseGitDiff(added('privateKey = "abcdefghijklmnop"'), []).architecturalConcerns)
      .not.toContain(SECRET);
  });

  it('MISSES a name that merely contains a keyword', () => {
    // The keyword must sit immediately before the `=`. `JWT_SECRET = "..."`
    // is caught; `JWT_SECRET_VALUE = "..."` is not, because "_VALUE" comes
    // between. That is the exact shape of the secret this repo leaked.
    expect(parseGitDiff(added('JWT_SECRET = "koshi_super_secret_key_2026"'), []).architecturalConcerns)
      .toContain(SECRET);
    expect(parseGitDiff(added('JWT_SECRET_VALUE = "koshi_super_secret_key_2026"'), []).architecturalConcerns)
      .not.toContain(SECRET);
  });
});

describe('result shape', () => {
  it('reports the line and task counts it worked from', () => {
    const res = parseGitDiff('a\nb\nc', [task(), task({ id: 'TSK-2' })]);
    expect(res.summary).toContain('3 lines');
    expect(res.summary).toContain('2 tracked tasks');
  });

  it('always returns an empty blockedTaskIds', () => {
    // F-29: nothing ever populates this. The type promises `{id, reason}[]` and
    // GitDiffModal loops over it to write BLOCKED, but the loop is dead code.
    const blocked = task({ status: 'BLOCKED', title: 'Waiting on migration' });
    expect(parseGitDiff('+ migration done\nclose #TSK-1', [blocked]).blockedTaskIds).toEqual([]);
  });

  it('handles an empty diff and an empty board without throwing', () => {
    const res = parseGitDiff('', []);
    expect(res.resolvedTaskIds).toEqual([]);
    expect(res.architecturalConcerns).toEqual([]);
    expect(res.prTitle).toBe('PR / Commit Diff Analysis');
  });

  it('is pure — it does not mutate the tasks it was given', () => {
    const tasks = [task({ status: 'BLOCKED', title: 'Waiting on migration' })];
    const before = JSON.stringify(tasks);
    parseGitDiff('+ migration landed', tasks);
    expect(JSON.stringify(tasks)).toBe(before);
  });
});
