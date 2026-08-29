import { describe, it, expect } from 'vitest';
import { parseSegments, mentionToken, activeMentionQuery, matchMembers } from './mentions';
import type { ProjectMember } from '../services/api';

const member = (over: Partial<ProjectMember> = {}): ProjectMember => ({
  user_id: 1, project_id: 1, role: 'MEMBER', status: 'ACCEPTED',
  full_name: 'Ada Lovelace', email: 'ada@example.com', skills: '',
  avatar_url: null, active_tasks_count: 0, wip_points: 0, ...over,
});

describe('parseSegments', () => {
  it('splits text around a mention', () => {
    expect(parseSegments('hi @[Ada](3) there')).toEqual([
      { type: 'text', value: 'hi ' },
      { type: 'mention', label: 'Ada', userId: 3 },
      { type: 'text', value: ' there' },
    ]);
  });

  it('handles a body that is only a mention', () => {
    expect(parseSegments('@[Ada](3)')).toEqual([{ type: 'mention', label: 'Ada', userId: 3 }]);
  });

  it('handles several mentions', () => {
    const seg = parseSegments('@[Ada](3) and @[Bob](7)');
    expect(seg.filter((s) => s.type === 'mention')).toHaveLength(2);
  });

  it('leaves a bare @ as text', () => {
    // Guessing at "@ada" would tag the wrong person the moment two people share
    // a first name.
    expect(parseSegments('ping @ada')).toEqual([{ type: 'text', value: 'ping @ada' }]);
  });

  it('leaves an email address alone', () => {
    expect(parseSegments('write to a@b.com')).toEqual([{ type: 'text', value: 'write to a@b.com' }]);
  });

  it('returns nothing for an empty body', () => {
    expect(parseSegments('')).toEqual([]);
  });

  it('does not treat markup in the text as anything but text', () => {
    // Segments are rendered as Vue nodes, never as HTML — this pins that the
    // parser has no notion of markup to begin with.
    const seg = parseSegments('<script>alert(1)</script>');
    expect(seg).toEqual([{ type: 'text', value: '<script>alert(1)</script>' }]);
  });

  it('is not confused by a second call (no lastIndex leak)', () => {
    // A /g regex reused across calls silently skips matches if lastIndex is
    // carried over. matchAll avoids it; this asserts it stays avoided.
    const input = '@[Ada](3)';
    expect(parseSegments(input)).toEqual(parseSegments(input));
  });
});

describe('mentionToken', () => {
  it('embeds the id, which is what the mention means', () => {
    expect(mentionToken(3, 'Ada Lovelace')).toBe('@[Ada Lovelace](3)');
  });

  it('drops brackets from a name rather than inventing an escape scheme', () => {
    // A bracket would end the label early. No real display name contains one,
    // and an escaping rule is a second thing to keep in step with the server.
    expect(mentionToken(3, 'Ada [The Countess]')).toBe('@[Ada The Countess](3)');
  });

  it('round-trips through the parser', () => {
    const seg = parseSegments(`hello ${mentionToken(12, 'Phạm Minh Tú')}`);
    expect(seg[1]).toEqual({ type: 'mention', label: 'Phạm Minh Tú', userId: 12 });
  });
});

describe('activeMentionQuery', () => {
  const at = (text: string) => activeMentionQuery(text, text.length);

  it('opens on a fresh @', () => {
    expect(at('hello @')).toEqual({ query: '', from: 6 });
  });

  it('captures what has been typed since', () => {
    expect(at('hello @ad')).toEqual({ query: 'ad', from: 6 });
  });

  it('opens at the very start of the box', () => {
    expect(at('@a')).toEqual({ query: 'a', from: 0 });
  });

  it('does not open inside an email address', () => {
    expect(at('write to ada@example')).toBeNull();
  });

  it('closes once the line ends', () => {
    expect(at('hello @ada\nnext line')).toBeNull();
  });

  it('gives up on an over-long run, so a stray @ does not reopen it', () => {
    expect(at(`hi @${'x'.repeat(50)}`)).toBeNull();
  });

  it('returns null when there is no @ at all', () => {
    expect(at('nothing here')).toBeNull();
  });

  it('tracks the caret, not the end of the text', () => {
    const text = 'hi @ad more words';
    expect(activeMentionQuery(text, 6)).toEqual({ query: 'ad', from: 3 });
  });
});

describe('matchMembers', () => {
  const roster = [
    member({ user_id: 1, full_name: 'Ada Lovelace', email: 'ada@example.com' }),
    member({ user_id: 2, full_name: 'Grace Hopper', email: 'grace@navy.mil' }),
    member({ user_id: 3, full_name: 'Alan Turing', email: 'alan@example.com' }),
  ];

  it('offers everybody for an empty query', () => {
    expect(matchMembers(roster, '')).toHaveLength(3);
  });

  it('matches on name, case-insensitively', () => {
    expect(matchMembers(roster, 'ada').map((m) => m.user_id)).toEqual([1]);
  });

  it('matches on email too', () => {
    expect(matchMembers(roster, 'navy').map((m) => m.user_id)).toEqual([2]);
  });

  it('matches anywhere in the name, not only the start', () => {
    expect(matchMembers(roster, 'turing').map((m) => m.user_id)).toEqual([3]);
  });

  it('excludes people who have only been invited', () => {
    // They cannot read the thread, so tagging them is a message nobody gets —
    // and the server refuses it anyway.
    const withPending = [...roster, member({ user_id: 9, full_name: 'Invited Person', status: 'PENDING' })];
    expect(matchMembers(withPending, 'Invited')).toEqual([]);
  });

  it('caps the menu length', () => {
    const many = Array.from({ length: 20 }, (_, i) => member({ user_id: i, full_name: `User ${i}` }));
    expect(matchMembers(many, '')).toHaveLength(6);
  });

  it('returns nothing when nobody matches', () => {
    expect(matchMembers(roster, 'zzz')).toEqual([]);
  });
});
