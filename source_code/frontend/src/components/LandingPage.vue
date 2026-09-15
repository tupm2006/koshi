<script setup lang="ts">
import { useThemeStore } from '../stores/themeStore';
import {
  LayoutGrid,
  Database,
  Sparkles,
  ArrowRight,
  Sun,
  Moon,
  Shield,
  Zap,
  CheckCircle2,
  GitFork,
  Clock,
  Command,
  Layers,
  Flame
} from 'lucide-vue-next';

defineEmits<{
  (e: 'open-auth'): void;
}>();

const themeStore = useThemeStore();

const features = [
  {
    title: '2D Spatial Kanban',
    badge: '2D Kanban',
    icon: LayoutGrid,
    iconColor: 'text-indigo-600 dark:text-indigo-400',
    borderColor: 'border-indigo-200 dark:border-indigo-900/60',
    bgBadge: 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300',
    description: 'Modal-less keyboard traversal via h/j/k/l with one-keystroke Space status cycling and deterministic 4-column lane transitions.',
    bullets: [
      'Vim-style h/j/k/l spatial navigation',
      'One-press Space status cycling',
      'Shift+H/L lateral column translation'
    ]
  },
  {
    title: 'Local-First Architecture',
    badge: 'Local-First',
    icon: Database,
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    borderColor: 'border-emerald-200 dark:border-emerald-900/60',
    bgBadge: 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300',
    description: 'Offline-ready IndexedDB cache paired with SQLite WAL concurrency and online hot snapshots. Work uninterrupted on unreliable networks.',
    bullets: [
      'Sub-5ms IndexedDB client boot',
      'SQLite WAL concurrency & hot backups',
      'Optimistic mutations with conflict resolution'
    ]
  },
  {
    title: 'Schema-Driven AI',
    badge: 'Schema AI',
    icon: Sparkles,
    iconColor: 'text-purple-600 dark:text-purple-400',
    borderColor: 'border-purple-200 dark:border-purple-900/60',
    bgBadge: 'bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300',
    description: 'Cascaded multi-tier AI heuristics for agile teams: user story decomposition, meeting minutes synthesis, and workload load-balancing.',
    bullets: [
      'Goal & story task decomposition',
      'Smart meeting minutes & action extraction',
      'OpenAI primary with local Ollama fallback'
    ]
  }
];

const capabilities = [
  {
    icon: GitFork,
    name: 'Topological DAG Sorter',
    detail: "Kahn's algorithm resolves dependencies and pins the critical path chain."
  },
  {
    icon: Clock,
    name: 'Dynamic SLA Engine',
    detail: 'Evaluates slip days in real-time without stale caching or cron latency.'
  },
  {
    icon: Shield,
    name: 'Role-Based Governance',
    detail: 'Developer priority proposals with mandatory PM/Owner sign-off gates.'
  }
];
</script>

<template>
  <div class="min-h-screen w-full flex flex-col bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans overflow-y-auto">
    <!-- Navigation Header -->
    <header class="h-14 border-b border-slate-300 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md px-4 sm:px-8 flex items-center justify-between shrink-0 sticky top-0 z-30 shadow-2xs">
      <div class="w-full max-w-6xl mx-auto flex items-center justify-between">
        <!-- Logo -->
        <div class="flex items-center gap-2.5">
          <span class="text-base sm:text-lg font-bold tracking-wider font-mono text-slate-900 dark:text-slate-100">
            KOSHI
          </span>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300">
            v1.0.0
          </span>
        </div>

        <!-- Action cluster -->
        <div class="flex items-center gap-2">
          <!-- Theme toggle -->
          <button
            type="button"
            class="h-8 w-8 inline-flex items-center justify-center rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 cursor-pointer shadow-2xs transition-colors"
            @click="themeStore.toggleTheme()"
            title="Toggle theme (t)"
          >
            <Sun class="w-4 h-4 text-amber-500" v-if="themeStore.isDark" />
            <Moon class="w-4 h-4 text-slate-700 dark:text-slate-300" v-else />
          </button>

          <!-- Primary Sign In button -->
          <button
            type="button"
            class="h-8 inline-flex items-center gap-1.5 px-3 rounded-md bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-950 font-mono text-xs font-semibold cursor-pointer shadow-xs transition-colors"
            @click="$emit('open-auth')"
          >
            <Shield class="w-3.5 h-3.5" />
            <span>Sign In</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <section class="max-w-5xl mx-auto px-4 sm:px-6 pt-12 sm:pt-20 pb-12 sm:pb-16 text-center flex flex-col items-center">
      <!-- Eyebrow badge -->
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 text-indigo-700 dark:text-indigo-300 text-xs font-mono font-semibold mb-6 shadow-2xs">
        <Zap class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
        <span>High-Velocity · Local-First · Zero Latency</span>
      </div>

      <!-- Main Headline -->
      <h1 class="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50 font-sans max-w-4xl leading-tight">
        The Keyboard-Native Project Management Engine
      </h1>

      <!-- Subtitle Value Proposition -->
      <p class="mt-5 sm:mt-6 text-sm sm:text-lg text-slate-600 dark:text-slate-400 max-w-2xl font-sans leading-relaxed">
        Modal-less spatial Kanban navigation, instant DAG dependency resolution, and deterministic critical path tracking backed by SQLite WAL persistence.
      </p>

      <!-- Primary CTA Button -->
      <div class="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center gap-3">
        <button
          type="button"
          class="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-mono font-semibold text-sm sm:text-base cursor-pointer shadow-lg shadow-indigo-600/25 transition-all hover:scale-[1.02]"
          @click="$emit('open-auth')"
        >
          <span>Launch Workspace / Sign In</span>
          <ArrowRight class="w-4 h-4" />
        </button>
      </div>

      <p class="mt-3.5 text-xs font-mono text-slate-400 dark:text-slate-500">
        Demo credentials &amp; Google Single Sign-On available out of the box
      </p>
    </section>

    <!-- Feature Badges Section (2D Kanban, Local-First, Schema AI) -->
    <section class="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10 w-full">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6">
        <div
          v-for="feat in features"
          :key="feat.badge"
          :class="[
            'p-6 rounded-xl bg-white dark:bg-slate-900 border shadow-xs flex flex-col justify-between transition-all hover:shadow-md',
            feat.borderColor
          ]"
        >
          <div>
            <!-- Header with Icon & Badge -->
            <div class="flex items-center justify-between mb-4">
              <div class="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
                <component :is="feat.icon" :class="['w-5 h-5', feat.iconColor]" />
              </div>
              <span :class="['px-2 py-0.5 rounded text-[11px] font-mono font-semibold', feat.bgBadge]">
                {{ feat.badge }}
              </span>
            </div>

            <!-- Title & Description -->
            <h2 class="text-base font-bold font-sans text-slate-900 dark:text-slate-100">
              {{ feat.title }}
            </h2>
            <p class="mt-2 text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-sans">
              {{ feat.description }}
            </p>
          </div>

          <!-- Bullet highlights -->
          <ul class="mt-5 space-y-2 pt-4 border-t border-slate-200 dark:border-slate-800">
            <li
              v-for="b in feat.bullets"
              :key="b"
              class="flex items-start gap-2 text-xs font-mono text-slate-700 dark:text-slate-300"
            >
              <CheckCircle2 class="w-3.5 h-3.5 mt-0.5 text-emerald-500 shrink-0" />
              <span>{{ b }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Technical Architecture Capabilities Strip -->
    <section class="max-w-5xl mx-auto px-4 sm:px-6 py-8 w-full">
      <div class="p-6 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 shadow-xs">
        <h3 class="text-xs font-mono font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-4">
          Core Engine Specifications
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div
            v-for="cap in capabilities"
            :key="cap.name"
            class="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800/80"
          >
            <component :is="cap.icon" class="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <h4 class="text-xs font-bold font-mono text-slate-900 dark:text-slate-100">
                {{ cap.name }}
              </h4>
              <p class="text-[11px] text-slate-500 dark:text-slate-400 mt-1 font-sans leading-relaxed">
                {{ cap.detail }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Call to Action Banner -->
    <section class="max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
      <div class="rounded-xl bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950 dark:from-slate-900 dark:via-slate-900 dark:to-indigo-950/80 border border-slate-800 p-8 text-center text-white shadow-md">
        <h3 class="text-xl sm:text-2xl font-bold font-sans">
          Ready to experience modal-less project velocity?
        </h3>
        <p class="mt-2 text-xs sm:text-sm text-slate-400 max-w-md mx-auto font-sans">
          Open Koshi in your browser with zero build setup. Fast, deterministic, and local-first.
        </p>
        <button
          type="button"
          class="mt-6 inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-semibold cursor-pointer shadow-xs transition-colors"
          @click="$emit('open-auth')"
        >
          <span>Launch Workspace / Sign In</span>
          <ArrowRight class="w-3.5 h-3.5" />
        </button>
      </div>
    </section>

    <!-- Minimal Footer -->
    <footer class="mt-auto border-t border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900 py-6 px-4 text-center shrink-0">
      <p class="text-xs font-mono text-slate-500 dark:text-slate-400">
        KOSHI · High-Velocity Local-First Project Management · Academic Edition
      </p>
    </footer>
  </div>
</template>
