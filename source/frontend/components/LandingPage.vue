<script setup lang="ts">
/**
 * First screen for an unauthenticated visitor, and where signing out returns to.
 *
 * Replaces the old AuthModal: a signed-out user previously landed straight on a
 * board full of sample tasks with a small sign-in popover, which gave no sense
 * of what the product was or that an account was expected.
 */
import { ref, computed } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { useThemeStore } from '../stores/themeStore';
import { api } from '../services/api';
import {
  LogIn, UserPlus, AlertCircle, Loader2, Sun, Moon,
  Keyboard, GitFork, Sparkles, WifiOff, ArrowRight,
} from 'lucide-vue-next';

const taskStore = useTaskStore();
const themeStore = useThemeStore();

const mode = ref<'LOGIN' | 'REGISTER'>('LOGIN');
const email = ref('');
const password = ref('');
const fullName = ref('');
const skills = ref('');
const errorMsg = ref<string | null>(null);
const isSubmitting = ref(false);

const showDemoAccounts = import.meta.env.DEV;
const isRegister = computed(() => mode.value === 'REGISTER');

const highlights = [
  { icon: Keyboard, title: 'Keyboard-first', body: 'Navigate, create and re-prioritise without touching the mouse.' },
  { icon: GitFork, title: 'Dependency-aware', body: 'Topological ordering and a weighted critical path, computed live.' },
  { icon: Sparkles, title: 'Structured AI', body: 'Summaries and meeting minutes as schema-checked data, not chat.' },
  { icon: WifiOff, title: 'Local-first', body: 'Every change lands locally first, so the network never blocks you.' },
];

async function handleSubmit() {
  errorMsg.value = null;
  isSubmitting.value = true;
  try {
    const res = isRegister.value
      ? await api.register(email.value.trim(), password.value, fullName.value.trim(), skills.value.trim() || undefined)
      : await api.login(email.value.trim(), password.value);

    await taskStore.onAuthenticated(res.user);
    password.value = '';
  } catch (e: any) {
    errorMsg.value = e.message || 'Authentication failed';
  } finally {
    isSubmitting.value = false;
  }
}

async function handleDemoLogin(demoEmail: string) {
  email.value = demoEmail;
  password.value = 'koshi123';
  mode.value = 'LOGIN';
  await handleSubmit();
}

function switchMode() {
  mode.value = isRegister.value ? 'LOGIN' : 'REGISTER';
  errorMsg.value = null;
}
</script>

<template>
  <div class="min-h-screen min-h-[100dvh] bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col">
    <!-- Header -->
    <header class="h-12 shrink-0 px-4 md:px-6 flex items-center justify-between border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
      <h1 class="text-sm font-bold tracking-wider font-mono">KOSHI <span class="text-slate-400 dark:text-slate-600">輿</span></h1>
      <button
        type="button"
        class="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 cursor-pointer"
        :title="`Toggle theme (currently ${themeStore.isDark ? 'dark' : 'light'})`"
        @click="themeStore.toggleTheme()"
      >
        <Sun v-if="themeStore.isDark" class="w-4 h-4" />
        <Moon v-else class="w-4 h-4" />
      </button>
    </header>

    <main class="flex-1 w-full max-w-6xl mx-auto px-5 py-8 md:py-14 grid md:grid-cols-2 gap-10 md:gap-14 items-center">
      <!-- Pitch -->
      <section>
        <p class="text-[11px] font-mono uppercase tracking-widest text-indigo-600 dark:text-indigo-400">
          Project management engine
        </p>
        <h2 class="mt-2.5 text-2xl md:text-4xl font-bold font-sans leading-tight">
          Track work at the speed you think.
        </h2>
        <p class="mt-3 text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-md">
          Koshi is a local-first, keyboard-driven tracker for small software teams.
          Four states, real dependency maths, and AI that returns structured data
          instead of paragraphs.
        </p>

        <ul class="mt-7 space-y-3.5">
          <li v-for="h in highlights" :key="h.title" class="flex gap-3">
            <span class="mt-0.5 shrink-0 w-7 h-7 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <component :is="h.icon" class="w-3.5 h-3.5" />
            </span>
            <span>
              <span class="block text-xs font-semibold font-sans">{{ h.title }}</span>
              <span class="block text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{{ h.body }}</span>
            </span>
          </li>
        </ul>
      </section>

      <!-- Auth card -->
      <section class="w-full max-w-md md:justify-self-end">
        <div class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl shadow-sm p-6">
          <div class="flex items-center gap-1 p-1 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <button
              type="button"
              class="flex-1 py-1.5 rounded-md text-xs font-mono font-medium cursor-pointer"
              :class="!isRegister ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-2xs' : 'text-slate-500 dark:text-slate-400'"
              @click="mode = 'LOGIN'; errorMsg = null"
            >Sign in</button>
            <button
              type="button"
              class="flex-1 py-1.5 rounded-md text-xs font-mono font-medium cursor-pointer"
              :class="isRegister ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-2xs' : 'text-slate-500 dark:text-slate-400'"
              @click="mode = 'REGISTER'; errorMsg = null"
            >Create account</button>
          </div>

          <form class="mt-5 space-y-3.5 text-xs" @submit.prevent="handleSubmit">
            <div v-if="isRegister">
              <label for="landing-name" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Full name</label>
              <input
                id="landing-name"
                v-model="fullName"
                type="text"
                required
                autocomplete="name"
                class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-sans"
              />
            </div>

            <div v-if="isRegister">
              <label for="landing-skills" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">
                Skills <span class="text-slate-400">(optional)</span>
              </label>
              <input
                id="landing-skills"
                v-model="skills"
                type="text"
                placeholder="e.g. python,vue"
                class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-sans"
              />
            </div>

            <div>
              <label for="landing-email" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Email address</label>
              <input
                id="landing-email"
                v-model="email"
                type="email"
                required
                autocomplete="email"
                placeholder="you@example.com"
                class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label for="landing-password" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Password</label>
              <input
                id="landing-password"
                v-model="password"
                type="password"
                required
                :autocomplete="isRegister ? 'new-password' : 'current-password'"
                class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <p v-if="isRegister" class="text-[10px] font-mono text-slate-500 dark:text-slate-400 leading-relaxed">
              No role to pick. Create a project and you are its Project Manager;
              roles are set per project.
            </p>

            <div v-if="errorMsg" class="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-1.5 font-mono text-[11px]">
              <AlertCircle class="w-3.5 h-3.5 shrink-0" />
              <span>{{ errorMsg }}</span>
            </div>

            <button
              type="submit"
              :disabled="isSubmitting"
              class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Loader2 v-if="isSubmitting" class="w-3.5 h-3.5 animate-spin" />
              <LogIn v-else-if="!isRegister" class="w-3.5 h-3.5" />
              <UserPlus v-else class="w-3.5 h-3.5" />
              <span>{{ isSubmitting ? 'Working…' : (isRegister ? 'Create account' : 'Sign in') }}</span>
            </button>

            <button
              type="button"
              class="w-full text-center text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 text-[11px] font-mono underline cursor-pointer"
              @click="switchMode"
            >
              {{ isRegister ? 'Already have an account? Sign in' : "Don't have an account? Create one" }}
            </button>
          </form>

          <div v-if="showDemoAccounts" class="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 text-[11px] font-mono">
            <span class="text-slate-500 dark:text-slate-400">Demo:</span>
            <button type="button" class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-indigo-700 dark:text-indigo-300 cursor-pointer" @click="handleDemoLogin('pm@tupm.qzz.io')">pm@</button>
            <button type="button" class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-300 cursor-pointer" @click="handleDemoLogin('dev@tupm.qzz.io')">dev@</button>
          </div>
        </div>

        <!-- Guest escape hatch: preserves the local-first promise (FR-PERS-02) -->
        <button
          type="button"
          class="mt-3 w-full text-center text-[11px] font-mono text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 cursor-pointer inline-flex items-center justify-center gap-1"
          @click="taskStore.continueAsGuest()"
        >
          <span>Explore the demo board without an account</span>
          <ArrowRight class="w-3 h-3" />
        </button>
        <p class="mt-1 text-center text-[10px] font-mono text-slate-400 dark:text-slate-600">
          Stored only in this browser. No projects or teammates.
        </p>
      </section>
    </main>

    <footer class="shrink-0 px-5 py-4 text-center text-[10px] font-mono text-slate-400 dark:text-slate-600">
      Koshi · MIT licensed
    </footer>
  </div>
</template>
