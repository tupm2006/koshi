<script setup lang="ts">
/**
 * Sign-in / sign-up dialog, opened from the landing page navigation.
 *
 * The landing page is a marketing surface, so the form lives behind a small
 * button rather than occupying half the hero.
 */
import { ref, computed, onMounted } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { useI18nStore } from '../stores/i18nStore';
import { api } from '../services/api';
import { X, LogIn, UserPlus, AlertCircle, Loader2 } from 'lucide-vue-next';

const props = defineProps<{ mode: 'LOGIN' | 'REGISTER' }>();
const emit = defineEmits<{ (e: 'close'): void }>();

const taskStore = useTaskStore();
const i18n = useI18nStore();
const t = computed(() => i18n.t);

const mode = ref<'LOGIN' | 'REGISTER'>(props.mode);
const email = ref('');
const password = ref('');
const fullName = ref('');
const skills = ref('');
const errorMsg = ref<string | null>(null);
const isSubmitting = ref(false);
const emailEl = ref<HTMLInputElement | null>(null);

const isRegister = computed(() => mode.value === 'REGISTER');
const showDemo = import.meta.env.DEV;

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
    errorMsg.value = e.message || t.value('auth.failed');
  } finally {
    isSubmitting.value = false;
  }
}

async function handleDemo(demoEmail: string) {
  email.value = demoEmail;
  password.value = 'koshi123';
  mode.value = 'LOGIN';
  await handleSubmit();
}

onMounted(() => emailEl.value?.focus());
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/50 dark:bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto"
    role="dialog"
    aria-modal="true"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-md rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 p-6 my-8">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-lg font-semibold font-sans">
            {{ isRegister ? t('auth.signUpTitle') : t('auth.signInTitle') }}
          </h2>
          <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {{ isRegister ? t('auth.signUpSub') : t('auth.signInSub') }}
          </p>
        </div>
        <button
          type="button"
          class="p-1.5 -mr-1.5 -mt-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
          :aria-label="t('auth.close')"
          @click="emit('close')"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <form class="mt-5 space-y-3.5 text-xs" @submit.prevent="handleSubmit">
        <div v-if="isRegister">
          <label for="auth-name" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">{{ t('auth.fullName') }}</label>
          <input
            id="auth-name"
            v-model="fullName"
            type="text"
            required
            autocomplete="name"
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2.5 text-xs focus:outline-none focus:border-indigo-500 font-sans"
          />
        </div>

        <div v-if="isRegister">
          <label for="auth-skills" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">
            {{ t('auth.skills') }} <span class="text-slate-400">{{ t('auth.optional') }}</span>
          </label>
          <input
            id="auth-skills"
            v-model="skills"
            type="text"
            placeholder="python, vue"
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2.5 text-xs focus:outline-none focus:border-indigo-500 font-sans"
          />
        </div>

        <div>
          <label for="auth-email" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">{{ t('auth.email') }}</label>
          <input
            id="auth-email"
            ref="emailEl"
            v-model="email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2.5 text-xs focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <div>
          <label for="auth-password" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">{{ t('auth.password') }}</label>
          <input
            id="auth-password"
            v-model="password"
            type="password"
            required
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2.5 text-xs focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>

        <p v-if="isRegister" class="text-[10px] font-mono text-slate-500 dark:text-slate-400 leading-relaxed">
          {{ t('auth.noRoleNote') }}
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
          <span>{{ isSubmitting ? t('auth.working') : (isRegister ? t('auth.submitSignUp') : t('auth.submitSignIn')) }}</span>
        </button>

        <button
          type="button"
          class="w-full text-center text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 text-[11px] font-mono underline cursor-pointer"
          @click="mode = isRegister ? 'LOGIN' : 'REGISTER'; errorMsg = null"
        >
          {{ isRegister ? t('auth.toSignIn') : t('auth.toSignUp') }}
        </button>
      </form>

      <div v-if="showDemo" class="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 text-[11px] font-mono">
        <span class="text-slate-500 dark:text-slate-400">{{ t('auth.demo') }}:</span>
        <button type="button" class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-indigo-700 dark:text-indigo-300 cursor-pointer" @click="handleDemo('pm@tupm.qzz.io')">pm@</button>
        <button type="button" class="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-sky-700 dark:text-sky-300 cursor-pointer" @click="handleDemo('dev@tupm.qzz.io')">dev@</button>
      </div>
    </div>
  </div>
</template>
