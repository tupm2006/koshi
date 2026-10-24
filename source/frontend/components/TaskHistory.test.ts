// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({ apiMock: { getToken: vi.fn(() => null), getTaskHistory: vi.fn() } }));
vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});

import TaskHistory from './TaskHistory.vue';
import { mountWithPinia, stubIcons } from './testing';

const mountIt = () => mountWithPinia(TaskHistory, { props: { taskId: 'TSK-7' }, global: { stubs: stubIcons(['History']) } });

beforeEach(() => vi.clearAllMocks());

describe('TaskHistory', () => {
  it('loads nothing until opened, then fetches by server id', async () => {
    apiMock.getTaskHistory.mockResolvedValue([]);
    const w = mountIt();
    expect(apiMock.getTaskHistory).not.toHaveBeenCalled();
    await w.find('button').trigger('click');
    await flushPromises();
    expect(apiMock.getTaskHistory).toHaveBeenCalledWith(7);
  });

  it('shows who changed which field from what to what, as text', async () => {
    apiMock.getTaskHistory.mockResolvedValue([
      { id: 3, field: 'status', old_value: 'TODO', new_value: 'DONE', actor: { id: 1, full_name: 'Tú' }, created_at: '2026-10-24T11:00:00' },
      { id: 2, field: 'title', old_value: 'a', new_value: '<b>DONE</b>', actor: { id: 1, full_name: 'Tú' }, created_at: '2026-10-24T10:00:00' },
      { id: 1, field: 'created', old_value: null, new_value: 'x', actor: null, created_at: '2026-10-24T09:00:00' },
    ]);
    const w = mountIt();
    await w.find('button').trigger('click');
    await flushPromises();
    const rows = w.findAll('[data-history-event]');
    expect(rows).toHaveLength(3);
    expect(rows[0].text()).toContain('Tú');
    // Status codes are shown as the UI's labels, not raw enum values.
    expect(rows[0].text()).toContain('To Do');
    expect(rows[0].text()).toContain('Done');
    expect(rows[1].html()).not.toContain('<b>DONE</b>');  // never rendered as markup
    expect(rows[1].text()).toContain('<b>DONE</b>');
  });

  it('surfaces a failed load', async () => {
    apiMock.getTaskHistory.mockRejectedValue(new Error('boom'));
    const w = mountIt();
    await w.find('button').trigger('click');
    await flushPromises();
    expect(w.text()).toContain('boom');
  });
});
