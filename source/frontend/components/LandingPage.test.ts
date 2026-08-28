// @vitest-environment jsdom
/**
 * Tests for the marketing landing page (D5 GAP-10).
 *
 * Beyond rendering, these pin two content commitments that are easy to erode:
 * no fabricated social proof, and no demo video unless one is really
 * configured (D6 P14, FR-MKT-04/05).
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getToken: vi.fn(() => null),
    logout: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    listProjects: vi.fn(async () => [] as any[]),
    getTasks: vi.fn(async () => [] as any[]),
  },
}));

vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof import('../services/api')>('../services/api');
  return { ...actual, api: apiMock };
});
vi.mock('idb-keyval', () => ({ get: vi.fn(async () => undefined), set: vi.fn(async () => {}) }));

import LandingPage from './LandingPage.vue';
import { useI18nStore } from '../stores/i18nStore';
import { MESSAGES } from '../lib/translations';
import { mountWithPinia } from './testing';

function open() {
  return mountWithPinia(LandingPage);
}

const buttonWith = (w: any, text: string) =>
  w.findAll('button').find((b: any) => b.text().trim() === text);

beforeEach(() => vi.clearAllMocks());

describe('structure', () => {
  it('renders every marketing section', () => {
    const w = open();
    for (const id of ['features', 'how', 'pricing', 'faq']) {
      expect(w.find(`#${id}`).exists(), `missing section #${id}`).toBe(true);
    }
  });

  it('puts sign-in in the navigation, not the hero', () => {
    // The ask was a small sign-in in the top-right corner rather than a form
    // occupying half the fold (FR-MKT-02).
    const w = open();
    const nav = w.find('header');
    expect(nav.text()).toContain(MESSAGES.en['nav.signIn']);
    // No credential fields anywhere until the dialog is opened.
    expect(w.find('input[type="password"]').exists()).toBe(false);
    expect(w.find('input[type="email"]').exists()).toBe(false);
  });

  it('shows the three pricing tiers', () => {
    const w = open();
    const text = w.text();
    for (const key of ['pricing.free.name', 'pricing.team.name', 'pricing.business.name'] as const) {
      expect(text).toContain(MESSAGES.en[key]);
    }
  });

  it('expands one FAQ answer at a time', async () => {
    const w = open();
    // The first is open by default; the second is not.
    expect(w.text()).toContain(MESSAGES.en['faq.a1']);
    expect(w.text()).not.toContain(MESSAGES.en['faq.a2']);

    await buttonWith(w, MESSAGES.en['faq.q2'])!.trigger('click');
    expect(w.text()).toContain(MESSAGES.en['faq.a2']);
    expect(w.text()).not.toContain(MESSAGES.en['faq.a1']);
  });
});

describe('content commitments', () => {
  it('renders no demo video when none is configured', () => {
    // FR-MKT-04: a fake player would imply a tour that does not exist.
    const w = open();
    expect(w.find('video').exists()).toBe(false);
    expect(w.text()).toContain(MESSAGES.en['how.videoMissing']);
  });

  it('carries no testimonials or invented customer proof', () => {
    // D6 P14 / FR-MKT-05. Fabricated social proof is not a copy decision.
    const text = open().text().toLowerCase();
    for (const word of ['testimonial', 'trusted by', 'loved by', 'customers say', 'join 10,000']) {
      expect(text, `landing page should not claim: ${word}`).not.toContain(word);
    }
  });
});

describe('authentication entry points', () => {
  it('opens the dialog in sign-in mode from the nav', async () => {
    const w = open();
    await buttonWith(w, MESSAGES.en['nav.signIn'])!.trigger('click');
    expect(w.find('[role="dialog"]').exists()).toBe(true);
    expect(w.find('#auth-name').exists()).toBe(false); // login has no name field
  });

  it('opens the dialog in sign-up mode from the primary CTA', async () => {
    const w = open();
    await buttonWith(w, MESSAGES.en['nav.getStarted'])!.trigger('click');
    expect(w.find('#auth-name').exists()).toBe(true);
  });

  it('opens sign-up from a pricing tier', async () => {
    const w = open();
    // Scoped to #pricing: the nav CTA shares the same label, so an unscoped
    // query would find four buttons rather than one per tier.
    const ctas = w.find('#pricing').findAll('button')
      .filter((b) => b.text().trim() === MESSAGES.en['pricing.cta']);
    expect(ctas.length).toBe(3);

    await ctas[0]!.trigger('click');
    expect(w.find('#auth-name').exists()).toBe(true);
  });

  it('closes the dialog again', async () => {
    const w = open();
    await buttonWith(w, MESSAGES.en['nav.signIn'])!.trigger('click');
    await w.find('[role="dialog"]').trigger('click'); // backdrop
    await flushPromises();
    expect(w.find('[role="dialog"]').exists()).toBe(false);
  });
});

describe('localisation', () => {
  it('renders English by default', () => {
    expect(open().text()).toContain(MESSAGES.en['hero.title']);
  });

  it('translates the whole page when the locale changes', async () => {
    const w = open();
    const i18n = useI18nStore();

    i18n.setLocale('vi');
    await w.vm.$nextTick();

    const text = w.text();
    // Hero, a feature, pricing and FAQ all follow the locale — not just the nav.
    expect(text).toContain(MESSAGES.vi['hero.title']);
    expect(text).toContain(MESSAGES.vi['features.keyboard.title']);
    expect(text).toContain(MESSAGES.vi['pricing.title']);
    expect(text).toContain(MESSAGES.vi['faq.q1']);
    expect(text).not.toContain(MESSAGES.en['hero.title']);
  });

  it('offers both locales in the language menu', async () => {
    const w = open();
    await w.find('#lang-menu button').trigger('click');
    const text = w.find('#lang-menu').text();
    expect(text).toContain('English');
    expect(text).toContain('Tiếng Việt');
  });

  it('switches locale from the menu', async () => {
    const w = open();
    const i18n = useI18nStore();
    await w.find('#lang-menu button').trigger('click');
    await buttonWith(w, 'Tiếng Việt')!.trigger('click');

    expect(i18n.locale).toBe('vi');
  });
});
