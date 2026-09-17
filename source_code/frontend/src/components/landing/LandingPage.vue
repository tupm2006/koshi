<script setup lang="ts">
/**
 * Public marketing page.
 *
 * Structured as a clean, keyboard-driven project management engine landing page:
 * sticky nav, hero, product preview, features grid (DAG/SLA/AI/WAL), Vim shortcuts
 * cheatsheet, how-it-works, use cases, FAQ, closing CTA, and footer.
 */
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18nStore } from '../../stores/i18nStore';
import { useThemeStore } from '../../stores/themeStore';
import { LOCALES, LOCALE_LABELS, type Locale } from '../../lib/i18n/translations';
import {
  Sun, Moon, Menu, X, Check, Keyboard, GitFork, Sparkles,
  WifiOff, Globe, ArrowRight, PlayCircle, ChevronDown, Clock, Shield
} from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'open-auth', mode?: 'LOGIN' | 'REGISTER'): void;
  (e: 'launch'): void;
}>();

const i18n = useI18nStore();
const themeStore = useThemeStore();
const t = computed(() => i18n.t);

const isLangOpen = ref(false);
const isNavOpen = ref(false);
const openFaq = ref<number | null>(0);
const scrolled = ref(false);

const demoVideoUrl = import.meta.env.VITE_DEMO_VIDEO_URL as string | undefined;

const navLinks = [
  { href: '#features', key: 'nav.features' },
  { href: '#keyboard', key: 'nav.how' },
  { href: '#how', key: 'nav.how' },
  { href: '#faq', key: 'nav.faq' },
] as const;

const features = [
  { icon: Keyboard, title: 'features.keyboard.title', body: 'features.keyboard.body', badge: 'Vim 2D' },
  { icon: GitFork, title: 'features.graph.title', body: 'features.graph.body', badge: 'Kahn DAG' },
  { icon: Clock, title: 'features.speed.title', body: 'features.speed.body', badge: 'Dynamic SLA' },
  { icon: Sparkles, title: 'features.ai.title', body: 'features.ai.body', badge: 'Schema AI' },
  { icon: WifiOff, title: 'features.offline.title', body: 'features.offline.body', badge: 'SQLite WAL' },
  { icon: Shield, title: 'features.roles.title', body: 'features.roles.body', badge: 'RBAC Gate' },
] as const;

const shortcuts = [
  { key: 'h / j / k / l', label: 'Vim Navigation', desc: 'Spatial 2D movement across Kanban columns and table rows' },
  { key: 'Space', label: 'Status Cycle', desc: 'TODO → IN_PROGRESS → BLOCKED → DONE single-stroke cycling' },
  { key: 'Shift + H / L', label: 'Translate Column', desc: 'Shift selected task laterally to previous / next column' },
  { key: '1, 2, 3, 4', label: 'Priority Assignment', desc: 'Assign LOW, MEDIUM, HIGH, or CRITICAL priority' },
  { key: 'Enter / i', label: 'Task Inspector', desc: 'Open full-attribute task detail inspector and inline edit' },
  { key: 'n', label: 'Create Task', desc: 'Instant task creation dialog with complexity points' },
  { key: 'v', label: 'DAG Visualizer', desc: 'Topological ordering, cycle detection and critical path graph' },
  { key: 'b', label: 'View Switcher', desc: 'Instant toggle between 2D Kanban Board and Task Table' },
  { key: '?', label: 'Shortcuts Help', desc: 'Open global hotkey reference modal at any time' },
] as const;

const steps = [
  { title: 'how.step1.title', body: 'how.step1.body' },
  { title: 'how.step2.title', body: 'how.step2.body' },
  { title: 'how.step3.title', body: 'how.step3.body' },
] as const;

const cases = [
  { title: 'cases.a.title', body: 'cases.a.body' },
  { title: 'cases.b.title', body: 'cases.b.body' },
  { title: 'cases.c.title', body: 'cases.c.body' },
] as const;

const faqs = [
  { q: 'faq.q1', a: 'faq.a1' },
  { q: 'faq.q2', a: 'faq.a2' },
  { q: 'faq.q3', a: 'faq.a3' },
  { q: 'faq.q4', a: 'faq.a4' },
] as const;

const containerEl = ref<HTMLElement | null>(null);

function pickLocale(locale: Locale) {
  i18n.setLocale(locale);
  isLangOpen.value = false;
}

function closeMenus(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('#lang-menu')) isLangOpen.value = false;
}

function onScroll() {
  const y = containerEl.value ? containerEl.value.scrollTop : window.scrollY;
  scrolled.value = y > 8;
}

onMounted(() => {
  window.addEventListener('click', closeMenus);
  window.addEventListener('scroll', onScroll, { passive: true });
});
onUnmounted(() => {
  window.removeEventListener('click', closeMenus);
  window.removeEventListener('scroll', onScroll);
});
</script>

<template>
  <div ref="containerEl" @scroll.passive="onScroll" class="flex-1 min-h-0 overflow-y-auto w-full bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100">
    <!-- ===================== NAV ===================== -->
    <header
      class="sticky top-0 z-40 bg-white/90 dark:bg-slate-950/90 backdrop-blur border-b"
      :class="scrolled ? 'border-slate-200 dark:border-slate-800' : 'border-transparent'"
    >
      <nav class="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between gap-4">
        <a href="#top" class="text-sm font-bold tracking-wider font-mono shrink-0 cursor-pointer" @click.prevent="emit('launch')">
          KOSHI <span class="text-slate-400 dark:text-slate-600">輿</span>
        </a>

        <ul class="hidden md:flex items-center gap-6 text-xs font-medium">
          <li v-for="l in navLinks" :key="l.href">
            <a :href="l.href" class="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100">
              {{ t(l.key) }}
            </a>
          </li>
        </ul>

        <!-- Right cluster: language, theme, sign-in, primary CTA -->
        <div class="flex items-center gap-1.5 shrink-0">
          <div id="lang-menu" class="relative">
            <button
              type="button"
              class="h-8 px-2 inline-flex items-center gap-1 rounded-md text-xs font-mono text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              :aria-label="t('nav.language')"
              :aria-expanded="isLangOpen"
              @click.stop="isLangOpen = !isLangOpen"
            >
              <Globe class="w-3.5 h-3.5" />
              <span class="hidden sm:inline">{{ i18n.locale.toUpperCase() }}</span>
              <ChevronDown class="w-3 h-3" />
            </button>
            <ul
              v-if="isLangOpen"
              class="absolute right-0 mt-1 w-36 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-lg"
            >
              <li v-for="loc in LOCALES" :key="loc">
                <button
                  type="button"
                  class="w-full text-left px-3 py-1.5 text-xs font-mono flex items-center justify-between cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800"
                  :class="i18n.locale === loc ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : 'text-slate-700 dark:text-slate-300'"
                  @click="pickLocale(loc)"
                >
                  <span>{{ LOCALE_LABELS[loc] }}</span>
                  <Check v-if="i18n.locale === loc" class="w-3.5 h-3.5" />
                </button>
              </li>
            </ul>
          </div>

          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-md text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
            aria-label="Toggle theme"
            @click="themeStore.toggleTheme()"
          >
            <Sun v-if="themeStore.isDark" class="w-4 h-4" />
            <Moon v-else class="w-4 h-4" />
          </button>

          <!-- Quiet sign-in in the top-right corner -->
          <button
            type="button"
            class="h-8 px-3 rounded-md text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
            @click="emit('open-auth', 'LOGIN')"
          >
            {{ t('nav.signIn') }}
          </button>

          <button
            type="button"
            class="hidden sm:inline-flex h-8 px-3 items-center rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium cursor-pointer"
            @click="emit('launch')"
          >
            Launch App
          </button>

          <button
            type="button"
            class="md:hidden h-8 w-8 inline-flex items-center justify-center rounded-md text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
            aria-label="Menu"
            @click="isNavOpen = !isNavOpen"
          >
            <X v-if="isNavOpen" class="w-4 h-4" />
            <Menu v-else class="w-4 h-4" />
          </button>
        </div>
      </nav>

      <ul v-if="isNavOpen" class="md:hidden border-t border-slate-200 dark:border-slate-800 px-5 py-3 space-y-2 bg-white dark:bg-slate-950">
        <li v-for="l in navLinks" :key="l.href">
          <a :href="l.href" class="block py-1 text-xs text-slate-600 dark:text-slate-400" @click="isNavOpen = false">
            {{ t(l.key) }}
          </a>
        </li>
        <li class="pt-2 flex gap-2 border-t border-slate-200 dark:border-slate-800">
          <button
            type="button"
            class="flex-1 h-8 rounded-md bg-indigo-600 text-white text-xs font-medium cursor-pointer"
            @click="isNavOpen = false; emit('launch')"
          >
            Launch App
          </button>
          <button
            type="button"
            class="flex-1 h-8 rounded-md border border-slate-300 dark:border-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 cursor-pointer"
            @click="isNavOpen = false; emit('open-auth', 'LOGIN')"
          >
            {{ t('nav.signIn') }}
          </button>
        </li>
      </ul>
    </header>

    <main id="top">
      <!-- ===================== HERO ===================== -->
      <section class="max-w-6xl mx-auto px-5 pt-16 pb-12 md:pt-24 md:pb-16 text-center">
        <p class="text-[11px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
          {{ t('hero.eyebrow') }}
        </p>
        <h1 class="mt-3 text-3xl md:text-5xl font-bold font-sans tracking-tight max-w-3xl mx-auto leading-[1.1]">
          {{ t('hero.title') }}
        </h1>
        <p class="mt-4 text-sm md:text-base text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed">
          {{ t('hero.subtitle') }}
        </p>
        <div class="mt-7 flex flex-wrap items-center justify-center gap-2.5">
          <button
            type="button"
            class="h-10 px-5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium inline-flex items-center gap-1.5 cursor-pointer"
            @click="emit('launch')"
          >
            Launch App
            <ArrowRight class="w-4 h-4" />
          </button>
          <button
            type="button"
            class="h-10 px-5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium inline-flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-900 cursor-pointer text-slate-800 dark:text-slate-200"
            @click="emit('open-auth', 'LOGIN')"
          >
            {{ t('nav.signIn') }}
          </button>
          <a
            href="#how"
            class="h-10 px-5 rounded-lg border border-slate-300 dark:border-slate-700 text-sm font-medium inline-flex items-center gap-1.5 hover:bg-slate-50 dark:hover:bg-slate-900"
          >
            <PlayCircle class="w-4 h-4" />
            {{ t('hero.ctaSecondary') }}
          </a>
        </div>
      </section>

      <!-- ===================== PRODUCT PREVIEW ===================== -->
      <section class="max-w-5xl mx-auto px-5 pb-16 md:pb-24">
        <div class="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 shadow-xl overflow-hidden">
          <div class="h-8 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex items-center gap-1.5 px-3">
            <span class="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-700"></span>
            <span class="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-700"></span>
            <span class="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-700"></span>
            <span class="ml-2 text-[10px] font-mono text-slate-400 dark:text-slate-600">koshi — board</span>
          </div>
          <div class="grid grid-cols-4 gap-2.5 p-3 md:p-4">
            <div v-for="col in [
              { label: t('preview.todo'), dot: 'bg-slate-400', cards: [t('preview.task1'), t('preview.task2')] },
              { label: t('preview.inProgress'), dot: 'bg-sky-500', cards: [t('preview.task4')] },
              { label: t('preview.blocked'), dot: 'bg-rose-500', cards: [t('preview.task3')] },
              { label: t('preview.done'), dot: 'bg-emerald-500', cards: [] as string[] },
            ]" :key="col.label" class="min-w-0">
              <p class="flex items-center gap-1.5 text-[10px] md:text-[11px] font-mono font-semibold text-slate-600 dark:text-slate-400 mb-2">
                <span class="w-1.5 h-1.5 rounded-full" :class="col.dot"></span>
                <span class="truncate">{{ col.label }}</span>
              </p>
              <div class="space-y-1.5">
                <div
                  v-for="card in col.cards"
                  :key="card"
                  class="rounded-md bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-2"
                >
                  <p class="text-[10px] md:text-[11px] font-sans leading-snug line-clamp-2">{{ card }}</p>
                </div>
                <div v-if="col.cards.length === 0" class="rounded-md border border-dashed border-slate-200 dark:border-slate-800 h-10"></div>
              </div>
            </div>
          </div>
        </div>
        <p class="mt-3 text-center text-[11px] font-mono text-slate-400 dark:text-slate-600">
          {{ t('preview.caption') }}
        </p>
      </section>

      <!-- ===================== FEATURES (DAG & SLA GRID) ===================== -->
      <section id="features" class="border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40">
        <div class="max-w-6xl mx-auto px-5 py-16 md:py-24">
          <p class="text-[11px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400">{{ t('features.eyebrow') }}</p>
          <h2 class="mt-2.5 text-2xl md:text-3xl font-bold font-sans">{{ t('features.title') }}</h2>
          <p class="mt-2 text-sm text-slate-600 dark:text-slate-400 max-w-xl">{{ t('features.subtitle') }}</p>

          <div class="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <div
              v-for="f in features"
              :key="f.title"
              class="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 flex flex-col justify-between"
            >
              <div>
                <div class="flex items-center justify-between">
                  <span class="w-9 h-9 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                    <component :is="f.icon" class="w-4 h-4" />
                  </span>
                  <span class="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                    {{ f.badge }}
                  </span>
                </div>
                <h3 class="mt-3.5 text-sm font-semibold font-sans">{{ t(f.title) }}</h3>
                <p class="mt-1.5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{{ t(f.body) }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ===================== VIM KEYBOARD CHEATSHEET ===================== -->
      <section id="keyboard" class="max-w-6xl mx-auto px-5 py-16 md:py-24 border-t border-slate-200 dark:border-slate-800">
        <div class="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 p-6 md:p-10 shadow-xs">
          <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-8 border-b border-slate-200 dark:border-slate-800">
            <div>
              <p class="text-[11px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
                Spatial Ergonomics
              </p>
              <h2 class="mt-2 text-2xl md:text-3xl font-bold font-sans">
                Vim Keyboard Cheatsheet
              </h2>
            </div>
            <p class="text-xs text-slate-600 dark:text-slate-400 max-w-md font-sans">
              Navigate cards, cycle execution statuses, and resolve dependency hierarchies without moving your hands from home row.
            </p>
          </div>

          <div class="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="s in shortcuts"
              :key="s.key"
              class="p-4 rounded-xl bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-start gap-3"
            >
              <kbd class="px-2 py-1 rounded bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-[11px] font-mono font-bold text-slate-800 dark:text-slate-200 shrink-0">
                {{ s.key }}
              </kbd>
              <div>
                <h3 class="text-xs font-bold font-mono text-slate-900 dark:text-slate-100">{{ s.label }}</h3>
                <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-snug">{{ s.desc }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ===================== HOW IT WORKS ===================== -->
      <section id="how" class="max-w-6xl mx-auto px-5 py-16 md:py-24 border-t border-slate-200 dark:border-slate-800">
        <p class="text-[11px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400">{{ t('how.eyebrow') }}</p>
        <h2 class="mt-2.5 text-2xl md:text-3xl font-bold font-sans">{{ t('how.title') }}</h2>

        <ol class="mt-10 grid md:grid-cols-3 gap-6">
          <li v-for="(s, i) in steps" :key="s.title" class="relative">
            <span class="w-8 h-8 rounded-full bg-indigo-600 text-white text-xs font-mono font-bold flex items-center justify-center">
              {{ i + 1 }}
            </span>
            <h3 class="mt-3.5 text-sm font-semibold font-sans">{{ t(s.title) }}</h3>
            <p class="mt-1.5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{{ t(s.body) }}</p>
          </li>
        </ol>

        <div class="mt-12 rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden bg-slate-50 dark:bg-slate-900">
          <div class="grid md:grid-cols-2">
            <div class="p-6 md:p-8 flex flex-col justify-center">
              <h3 class="text-base font-semibold font-sans">{{ t('how.videoTitle') }}</h3>
              <p class="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{{ t('how.videoBody') }}</p>
            </div>
            <div class="aspect-video bg-slate-200 dark:bg-slate-950 flex items-center justify-center">
              <video
                v-if="demoVideoUrl"
                :src="demoVideoUrl"
                controls
                playsinline
                preload="none"
                class="w-full h-full object-cover"
              />
              <p v-else class="text-[11px] font-mono text-slate-400 dark:text-slate-600 px-4 text-center">
                {{ t('how.videoMissing') }}
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- ===================== USE CASES ===================== -->
      <section class="border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40">
        <div class="max-w-6xl mx-auto px-5 py-16 md:py-24">
          <p class="text-[11px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400">{{ t('cases.eyebrow') }}</p>
          <h2 class="mt-2.5 text-2xl md:text-3xl font-bold font-sans">{{ t('cases.title') }}</h2>

          <div class="mt-10 grid md:grid-cols-3 gap-5">
            <div v-for="c in cases" :key="c.title" class="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5">
              <h3 class="text-sm font-semibold font-sans">{{ t(c.title) }}</h3>
              <p class="mt-1.5 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{{ t(c.body) }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- ===================== FAQ ===================== -->
      <section id="faq" class="border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40">
        <div class="max-w-3xl mx-auto px-5 py-16 md:py-24">
          <h2 class="text-2xl md:text-3xl font-bold font-sans text-center">{{ t('faq.title') }}</h2>
          <div class="mt-10 space-y-2.5">
            <div
              v-for="(f, i) in faqs"
              :key="f.q"
              class="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 overflow-hidden"
            >
              <button
                type="button"
                class="w-full text-left px-5 py-4 flex items-center justify-between gap-3 cursor-pointer"
                :aria-expanded="openFaq === i"
                @click="openFaq = openFaq === i ? null : i"
              >
                <span class="text-sm font-medium font-sans">{{ t(f.q) }}</span>
                <ChevronDown class="w-4 h-4 shrink-0 text-slate-400" :class="openFaq === i ? 'rotate-180' : ''" />
              </button>
              <p v-if="openFaq === i" class="px-5 pb-4 text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {{ t(f.a) }}
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- ===================== CTA ===================== -->
      <section class="max-w-6xl mx-auto px-5 py-16 md:py-24">
        <div class="rounded-2xl bg-slate-900 dark:bg-slate-900 border border-slate-800 px-6 py-12 md:py-16 text-center">
          <h2 class="text-2xl md:text-3xl font-bold font-sans text-white">{{ t('cta.title') }}</h2>
          <p class="mt-2.5 text-sm text-slate-400 max-w-md mx-auto">{{ t('cta.body') }}</p>
          <div class="mt-7 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              class="h-10 px-6 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium inline-flex items-center gap-1.5 cursor-pointer"
              @click="emit('launch')"
            >
              Open Workspace
              <ArrowRight class="w-4 h-4" />
            </button>
            <button
              type="button"
              class="h-10 px-6 rounded-lg border border-slate-700 hover:bg-slate-800 text-white text-sm font-medium inline-flex items-center gap-1.5 cursor-pointer"
              @click="emit('open-auth', 'LOGIN')"
            >
              {{ t('nav.signIn') }}
            </button>
          </div>
        </div>
      </section>
    </main>

    <!-- ===================== FOOTER ===================== -->
    <footer class="border-t border-slate-200 dark:border-slate-800">
      <div class="max-w-6xl mx-auto px-5 py-10 grid sm:grid-cols-3 gap-8">
        <div>
          <p class="text-sm font-bold tracking-wider font-mono">KOSHI 輿</p>
          <p class="mt-2 text-xs text-slate-500 dark:text-slate-400 max-w-xs">{{ t('footer.tagline') }}</p>
        </div>
        <div>
          <p class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{{ t('footer.product') }}</p>
          <ul class="mt-3 space-y-1.5 text-xs">
            <li v-for="l in navLinks" :key="l.href">
              <a :href="l.href" class="text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100">{{ t(l.key) }}</a>
            </li>
          </ul>
        </div>
        <div>
          <p class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{{ t('nav.language') }}</p>
          <ul class="mt-3 space-y-1.5 text-xs">
            <li v-for="loc in LOCALES" :key="loc">
              <button
                type="button"
                class="cursor-pointer"
                :class="i18n.locale === loc ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'"
                @click="i18n.setLocale(loc)"
              >{{ LOCALE_LABELS[loc] }}</button>
            </li>
          </ul>
        </div>
      </div>
      <div class="border-t border-slate-200 dark:border-slate-800 px-5 py-4 text-center text-[10px] font-mono text-slate-400 dark:text-slate-600">
        © {{ new Date().getFullYear() }} Koshi · {{ t('footer.rights') }}
      </div>
    </footer>
  </div>
</template>
