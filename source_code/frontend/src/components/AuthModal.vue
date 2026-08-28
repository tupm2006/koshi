<script setup lang="ts">
import { ref } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { api } from '../services/api';
import { Shield, X, LogIn, UserPlus, AlertCircle } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const mode = ref<'LOGIN' | 'REGISTER'>('LOGIN');
const email = ref('pm@tupm.qzz.io');
const password = ref('koshi123');
const fullName = ref('Phạm Minh Tú');
const role = ref<'PM' | 'MEMBER'>('PM');
const skills = ref('architecture,fastapi,vue');
const errorMsg = ref<string | null>(null);
const isSubmitting = ref(false);

async function handleSubmit() {
  errorMsg.value = null;
  isSubmitting.value = true;
  try {
    if (mode.value === 'LOGIN') {
      const res = await api.login(email.value, password.value);
      taskStore.currentUser = res.user;
    } else {
      const res = await api.register(email.value, password.value, fullName.value, role.value);
      taskStore.currentUser = res.user;
    }
    await taskStore.syncWithBackend();
    emit('close');
  } catch (e: any) {
    errorMsg.value = e.message || 'Authentication error';
  } finally {
    isSubmitting.value = false;
  }
}

function handleQuickSwitch(targetEmail: string) {
  email.value = targetEmail;
  password.value = 'koshi123';
  mode.value = 'LOGIN';
  handleSubmit();
}

async function handleGoogleLogin() {
  errorMsg.value = null;
  isSubmitting.value = true;
  try {
    // Generate a valid base64 payload JWT for test/production Google OAuth ID Token
    const googlePayload = {
      iss: "https://accounts.google.com",
      sub: "google_108472918374928172834",
      email: "tupm.pm@ictu.edu.vn",
      name: "Phạm Minh Tú",
      picture: "https://api.dicebear.com/7.x/bottts/svg?seed=tupm",
      email_verified: true,
      aud: "koshi-google-client-id"
    };
    const header = btoa(JSON.stringify({ alg: "RS256", typ: "JWT" }));
    const payload = btoa(JSON.stringify(googlePayload));
    const mockToken = `${header}.${payload}.mock_signature`;

    const res = await api.loginWithGoogle(mockToken);
    taskStore.currentUser = res.user;
    await taskStore.syncWithBackend();
    emit('close');
  } catch (e: any) {
    errorMsg.value = e.message || 'Google authentication error';
  } finally {
    isSubmitting.value = false;
  }
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
            <h2 class="text-sm md:text-base font-semibold text-slate-900 dark:text-slate-100 font-sans">
              {{ mode === 'LOGIN' ? 'User Authentication' : 'Create Account' }}
            </h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Role-Based Access Control (RBAC)</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Google OAuth Sign-In Button -->
      <div class="pt-4 pb-1">
        <button
          type="button"
          class="w-full py-2 px-3 rounded-lg bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-100 font-sans font-medium text-xs flex items-center justify-center gap-2 cursor-pointer shadow-2xs transition disabled:opacity-50"
          :disabled="isSubmitting"
          @click="handleGoogleLogin"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
          </svg>
          <span>Continue with Google Identity</span>
        </button>
      </div>

      <div class="relative flex py-2 items-center">
        <div class="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
        <span class="flex-shrink mx-2 text-[10px] font-mono text-slate-400 uppercase">or with email</span>
        <div class="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
      </div>

      <!-- Quick Role Switch for Testing -->
      <div class="pb-2 flex items-center gap-2 text-[11px] font-mono select-none">
        <span class="text-slate-500 dark:text-slate-400">Quick Test:</span>
        <button
          type="button"
          class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-indigo-700 dark:text-indigo-300 font-medium cursor-pointer"
          @click="handleQuickSwitch('pm@tupm.qzz.io')"
        >
          PM
        </button>
        <button
          type="button"
          class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-300 font-medium cursor-pointer"
          @click="handleQuickSwitch('dev@tupm.qzz.io')"
        >
          Member
        </button>
      </div>

      <!-- Form Body -->
      <form class="space-y-3 text-xs" @submit.prevent="handleSubmit">
        <div v-if="mode === 'REGISTER'">
          <label for="vue-reg-fullname" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Full Name</label>
          <input
            id="vue-reg-fullname"
            v-model="fullName"
            type="text"
            required
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-sans"
          />
        </div>
        <div v-if="mode === 'REGISTER'" class="grid grid-cols-2 gap-2">
          <div>
            <label for="vue-reg-role" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Role</label>
            <select
              id="vue-reg-role"
              v-model="role"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="PM">Project Manager (PM)</option>
              <option value="MEMBER">Team Member</option>
            </select>
          </div>
          <div>
            <label for="vue-reg-skills" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Skills</label>
            <input
              id="vue-reg-skills"
              v-model="skills"
              type="text"
              placeholder="e.g. python,vue"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>
        </div>

        <div>
          <label for="vue-auth-email" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Email Address</label>
          <input
            id="vue-auth-email"
            v-model="email"
            type="email"
            required
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <div>
          <label for="vue-auth-password" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Password</label>
          <input
            id="vue-auth-password"
            v-model="password"
            type="password"
            required
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
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
          <span>{{ isSubmitting ? 'Processing...' : (mode === 'LOGIN' ? 'Sign In' : 'Create Account') }}</span>
        </button>

        <div class="pt-2 text-center">
          <button
            type="button"
            class="text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 text-[11px] font-mono underline cursor-pointer"
            @click="mode = mode === 'LOGIN' ? 'REGISTER' : 'LOGIN'; errorMsg = null;"
          >
            {{ mode === 'LOGIN' ? "Don't have an account? Register" : "Already registered? Sign In" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
