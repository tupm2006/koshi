<script setup lang="ts">
/**
 * Authentication panel.
 *
 * Three states: signed out (login), signed out (register), and signed in
 * (account summary + sign out). Previously it always rendered the login form
 * pre-filled with the seeded demo credentials, so a user who had just created
 * an account saw someone else's email address staring back at them.
 */
import { ref, computed } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { api } from '../services/api';
import {
  Shield, X, LogIn, UserPlus, AlertCircle, LogOut, Mail, Wrench, FolderKanban,
} from 'lucide-vue-next';

const emit = defineEmits<{ (e: 'close'): void }>();
const taskStore = useTaskStore();

const mode = ref<'LOGIN' | 'REGISTER'>('LOGIN');
const email = ref('');
const password = ref('');
const fullName = ref('');
const skills = ref('');
const errorMsg = ref<string | null>(null);
const isSubmitting = ref(false);

const isSignedIn = computed(() => taskStore.currentUser !== null);
// Seeded demo accounts only exist when the backend ran with SEED_DEMO_DATA,
// which is development-only. Never offer them in a production build.
const showQuickLogin = import.meta.env.DEV;

async function handleSubmit() {
  errorMsg.value = null;
  isSubmitting.value = true;
  try {
    const res = mode.value === 'LOGIN'
      ? await api.login(email.value.trim(), password.value)
      : await api.register(email.value.trim(), password.value, fullName.value.trim(), skills.value.trim() || undefined);

    // One shared post-auth path: loads projects, selects one, and opens the
    // dashboard when the account has none yet.
    await taskStore.onAuthenticated(res.user);

    password.value = '';
    emit('close');
  } catch (e: any) {
    errorMsg.value = e.message || 'Authentication failed';
  } finally {
    isSubmitting.value = false;
  }
}

async function handleSignOut() {
  await taskStore.logout();
  email.value = '';
  password.value = '';
  mode.value = 'LOGIN';
  emit('close');
}

async function handleQuickLogin(targetEmail: string) {
  email.value = targetEmail;
  password.value = 'koshi123';
  mode.value = 'LOGIN';
  await handleSubmit();
}

function switchMode() {
  mode.value = mode.value === 'LOGIN' ? 'REGISTER' : 'LOGIN';
  errorMsg.value = null;
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-md rounded-lg p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400">
            <Shield class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold font-sans">
              {{ isSignedIn ? 'Your Account' : (mode === 'LOGIN' ? 'Sign In' : 'Create Account') }}
            </h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Roles are assigned per project</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- ================= SIGNED IN ================= -->
      <div v-if="isSignedIn" class="py-4 space-y-3 text-xs">
        <div class="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
          <p class="text-sm font-semibold font-sans">{{ taskStore.currentUser?.full_name }}</p>
          <p class="flex items-center gap-1.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
            <Mail class="w-3.5 h-3.5 shrink-0" />
            {{ taskStore.currentUser?.email }}
          </p>
          <p v-if="taskStore.currentUser?.skills" class="flex items-center gap-1.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
            <Wrench class="w-3.5 h-3.5 shrink-0" />
            {{ taskStore.currentUser.skills }}
          </p>
        </div>

        <div class="p-3 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
          <p class="flex items-center gap-1.5 font-mono text-[11px] text-slate-600 dark:text-slate-400">
            <FolderKanban class="w-3.5 h-3.5 shrink-0" />
            <span v-if="taskStore.currentProject">
              {{ taskStore.currentProject.name }} —
              <span class="font-semibold text-indigo-700 dark:text-indigo-300">{{ taskStore.myRole }}</span>
            </span>
            <span v-else>No project selected</span>
          </p>
          <p class="mt-1.5 text-[10px] font-mono text-slate-500 dark:text-slate-400">
            You are in {{ taskStore.projects.length }}
            project{{ taskStore.projects.length === 1 ? '' : 's' }}. Your role can differ in each.
          </p>
        </div>

        <button
          type="button"
          class="w-full py-2 rounded-lg bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer"
          @click="handleSignOut"
        >
          <LogOut class="w-3.5 h-3.5" />
          <span>Sign out</span>
        </button>
      </div>

      <!-- ================= SIGNED OUT ================= -->
      <template v-else>
        <div v-if="showQuickLogin" class="py-2.5 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 text-[11px] font-mono select-none">
          <span class="text-slate-500 dark:text-slate-400">Demo accounts:</span>
          <button
            type="button"
            class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-indigo-700 dark:text-indigo-300 font-medium cursor-pointer"
            @click="handleQuickLogin('pm@tupm.qzz.io')"
          >pm@</button>
          <button
            type="button"
            class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-300 font-medium cursor-pointer"
            @click="handleQuickLogin('dev@tupm.qzz.io')"
          >dev@</button>
        </div>

        <form class="py-3 space-y-3 text-xs" @submit.prevent="handleSubmit">
          <div v-if="mode === 'REGISTER'">
            <label for="vue-reg-fullname" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Full Name</label>
            <input
              id="vue-reg-fullname"
              v-model="fullName"
              type="text"
              required
              autocomplete="name"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>

          <div v-if="mode === 'REGISTER'">
            <label for="vue-reg-skills" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Skills <span class="text-slate-400">(optional)</span></label>
            <input
              id="vue-reg-skills"
              v-model="skills"
              type="text"
              placeholder="e.g. python,vue"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-sans"
            />
            <p class="mt-1.5 text-[10px] font-mono text-slate-500 dark:text-slate-400 leading-relaxed">
              No role needed here. Create a project from your dashboard to become its
              Project Manager, or ask a PM to add you to theirs.
            </p>
          </div>

          <div>
            <label for="vue-auth-email" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Email Address</label>
            <input
              id="vue-auth-email"
              v-model="email"
              type="email"
              required
              autocomplete="email"
              placeholder="you@example.com"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label for="vue-auth-password" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Password</label>
            <input
              id="vue-auth-password"
              v-model="password"
              type="password"
              required
              :autocomplete="mode === 'LOGIN' ? 'current-password' : 'new-password'"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div v-if="errorMsg" class="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-1.5 font-mono text-[11px]">
            <AlertCircle class="w-3.5 h-3.5 shrink-0" />
            <span>{{ errorMsg }}</span>
          </div>

          <button
            type="submit"
            class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            :disabled="isSubmitting"
          >
            <LogIn v-if="mode === 'LOGIN'" class="w-3.5 h-3.5" />
            <UserPlus v-else class="w-3.5 h-3.5" />
            <span>{{ isSubmitting ? 'Processing…' : (mode === 'LOGIN' ? 'Sign In' : 'Create Account') }}</span>
          </button>

          <div class="pt-2 text-center">
            <button
              type="button"
              class="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 text-[11px] font-mono underline cursor-pointer"
              @click="switchMode"
            >
              {{ mode === 'LOGIN' ? "Don't have an account? Register" : 'Already registered? Sign In' }}
            </button>
          </div>
        </form>
      </template>
    </div>
  </div>
</template>
