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

      <!-- Quick Role Switch -->
      <div class="py-2.5 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 text-[11px] font-mono select-none">
        <span class="text-slate-500 dark:text-slate-400">Quick Test Login:</span>
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
      <form class="py-3 space-y-3 text-xs" @submit.prevent="handleSubmit">
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
