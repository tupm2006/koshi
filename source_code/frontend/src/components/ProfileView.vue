<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import {
  ArrowLeft,
  LogOut,
  User as UserIcon,
  Camera,
  CheckCircle2,
  AlertCircle,
  Shield,
  Save,
  Loader2,
  Tag,
  Mail,
  Award
} from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'open-auth'): void;
}>();

const taskStore = useTaskStore();

const fullName = ref(taskStore.currentUser?.full_name || '');
const skills = ref(taskStore.currentUser?.skills || '');
const fileInput = ref<HTMLInputElement | null>(null);

const isSaving = ref(false);
const isUploadingAvatar = ref(false);
const statusMessage = ref<{ type: 'success' | 'error'; text: string } | null>(null);

// Keep form fields synced if currentUser changes
watch(
  () => taskStore.currentUser,
  (user) => {
    if (user) {
      fullName.value = user.full_name || '';
      skills.value = user.skills || '';
    }
  },
  { immediate: true }
);

const skillBadges = computed(() => {
  if (!skills.value) return [];
  return skills.value
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
});

async function handleProfileUpdate() {
  if (!taskStore.currentUser) return;
  statusMessage.value = null;
  isSaving.value = true;
  try {
    const res = await taskStore.updateCurrentUser({
      full_name: fullName.value.trim(),
      skills: skills.value.trim()
    });
    if (res?.success) {
      statusMessage.value = { type: 'success', text: 'Profile updated successfully.' };
    } else {
      statusMessage.value = { type: 'error', text: res?.error || 'Failed to update profile.' };
    }
  } catch (err: any) {
    statusMessage.value = { type: 'error', text: err.message || 'An error occurred while updating profile.' };
  } finally {
    isSaving.value = false;
    setTimeout(() => {
      if (statusMessage.value?.type === 'success') {
        statusMessage.value = null;
      }
    }, 4000);
  }
}

function triggerAvatarUpload() {
  fileInput.value?.click();
}

async function handleAvatarChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  statusMessage.value = null;
  isUploadingAvatar.value = true;
  try {
    const res = await taskStore.uploadCurrentUserAvatar(file);
    if (res?.success) {
      statusMessage.value = { type: 'success', text: 'Avatar uploaded successfully.' };
    } else {
      statusMessage.value = { type: 'error', text: res?.error || 'Failed to upload avatar.' };
    }
  } catch (err: any) {
    statusMessage.value = { type: 'error', text: err.message || 'An error occurred while uploading avatar.' };
  } finally {
    isUploadingAvatar.value = false;
    // Reset file input value so selecting the same file again triggers change
    if (fileInput.value) fileInput.value.value = '';
    setTimeout(() => {
      if (statusMessage.value?.type === 'success') {
        statusMessage.value = null;
      }
    }, 4000);
  }
}
</script>

<template>
  <main class="flex-1 min-h-0 w-full max-w-4xl mx-auto p-3 sm:p-6 md:p-8 overflow-y-auto">
    <!-- Authenticated View -->
    <div
      v-if="taskStore.currentUser"
      class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-4 sm:p-6 md:p-8 shadow-xs space-y-6"
    >
      <!-- Top Action Bar -->
      <div class="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
        <div class="flex items-center gap-3">
          <button
            type="button"
            class="h-8 px-3 inline-flex items-center gap-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-mono font-medium text-slate-800 dark:text-slate-200 cursor-pointer transition-colors shadow-2xs"
            @click="taskStore.setAppView('BOARD')"
            title="Return to Board"
          >
            <ArrowLeft class="w-3.5 h-3.5" />
            <span>Back to Board</span>
          </button>
          <h2 class="text-base font-bold font-mono tracking-wide text-slate-900 dark:text-slate-100">User Profile</h2>
        </div>

        <button
          type="button"
          class="h-8 px-3 inline-flex items-center gap-1.5 rounded-md border border-rose-300 dark:border-rose-800/80 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/60 text-rose-700 dark:text-rose-300 text-xs font-mono font-medium cursor-pointer transition-colors shadow-2xs"
          @click="taskStore.logout()"
          title="Sign Out to Landing"
        >
          <LogOut class="w-3.5 h-3.5" />
          <span>Sign Out</span>
        </button>
      </div>

      <!-- Feedback Alert Banner -->
      <div
        v-if="statusMessage"
        :class="[
          'p-3 rounded-lg border text-xs font-mono flex items-center gap-2 transition-all',
          statusMessage.type === 'success'
            ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
            : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200'
        ]"
      >
        <CheckCircle2 v-if="statusMessage.type === 'success'" class="w-4 h-4 shrink-0" />
        <AlertCircle v-else class="w-4 h-4 shrink-0" />
        <span>{{ statusMessage.text }}</span>
      </div>

      <!-- Profile Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Left: Identity & Avatar Card -->
        <div class="md:col-span-1 flex flex-col items-center text-center p-5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
          <div class="relative group mb-3">
            <img
              v-if="taskStore.currentUser.avatar_url"
              :src="taskStore.currentUser.avatar_url"
              alt="Avatar"
              class="w-24 h-24 rounded-full border-2 border-indigo-500 object-cover shadow-xs"
            />
            <div
              v-else
              class="w-24 h-24 rounded-full border-2 border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-indigo-600 dark:text-indigo-400"
            >
              <UserIcon class="w-12 h-12" />
            </div>

            <!-- Upload Loading Overlay -->
            <div
              v-if="isUploadingAvatar"
              class="absolute inset-0 rounded-full bg-slate-950/60 flex items-center justify-center text-white"
            >
              <Loader2 class="w-6 h-6 animate-spin text-white" />
            </div>

            <!-- Upload Trigger Hover Badge -->
            <button
              type="button"
              class="absolute bottom-0 right-0 p-1.5 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs cursor-pointer transition-transform group-hover:scale-105"
              @click="triggerAvatarUpload"
              title="Change profile picture"
              :disabled="isUploadingAvatar"
            >
              <Camera class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Hidden Native File Input -->
          <input
            ref="fileInput"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            class="hidden"
            @change="handleAvatarChange"
          />

          <button
            type="button"
            class="mt-1 text-xs font-mono text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer inline-flex items-center gap-1"
            @click="triggerAvatarUpload"
            :disabled="isUploadingAvatar"
          >
            <Camera class="w-3 h-3" />
            <span>{{ isUploadingAvatar ? 'Uploading...' : 'Change Avatar' }}</span>
          </button>

          <h3 class="mt-3 font-bold text-slate-900 dark:text-slate-100 text-sm font-sans">
            {{ taskStore.currentUser.full_name }}
          </h3>
          <p class="text-xs font-mono text-slate-600 dark:text-slate-400 flex items-center gap-1 mt-0.5">
            <Mail class="w-3 h-3 text-slate-400" />
            <span>{{ taskStore.currentUser.email }}</span>
          </p>

          <div class="mt-3 flex items-center gap-1.5">
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 border border-indigo-300 dark:border-indigo-800">
              <Shield class="w-3 h-3" />
              <span>{{ taskStore.currentUser.role || 'MEMBER' }}</span>
            </span>
          </div>

          <!-- Skill Badges Strip -->
          <div class="w-full mt-5 pt-4 border-t border-slate-200 dark:border-slate-800 text-left">
            <span class="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Tag class="w-3 h-3" />
              <span>Active Skills</span>
            </span>
            <div v-if="skillBadges.length > 0" class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="badge in skillBadges"
                :key="badge"
                class="px-2 py-0.5 rounded-md bg-white dark:bg-slate-900 text-[11px] font-mono font-medium text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 shadow-2xs"
              >
                {{ badge }}
              </span>
            </div>
            <p v-else class="text-[11px] font-mono text-slate-400 italic mt-1">No skills configured.</p>
          </div>
        </div>

        <!-- Right: Profile Edit Form & System Attributes -->
        <div class="md:col-span-2 space-y-6">
          <form class="p-5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-4" @submit.prevent="handleProfileUpdate">
            <div class="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
              <h4 class="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                Update Identity & Skills
              </h4>
              <span class="text-[10px] font-mono text-slate-400">Self-Service</span>
            </div>

            <!-- Full Name Input -->
            <div>
              <label for="profile-fullname" class="block font-mono text-xs text-slate-800 dark:text-slate-200 mb-1 font-semibold">
                Full Name
              </label>
              <input
                id="profile-fullname"
                v-model="fullName"
                type="text"
                required
                placeholder="e.g., Jane Doe"
                class="h-9 w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-sans"
              />
            </div>

            <!-- Skills Input -->
            <div>
              <label for="profile-skills" class="block font-mono text-xs text-slate-800 dark:text-slate-200 mb-1 font-semibold">
                Skills (comma-separated tags)
              </label>
              <input
                id="profile-skills"
                v-model="skills"
                type="text"
                placeholder="e.g., vue, typescript, python, devops"
                class="h-9 w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono"
              />
              <p class="text-[11px] font-mono text-slate-500 dark:text-slate-400 mt-1">
                Used by the Schema AI Workload & Smart Assignment engine to distribute tasks.
              </p>
            </div>

            <!-- Submit Button -->
            <div class="pt-2 flex justify-end">
              <button
                type="submit"
                class="h-8 px-4 inline-flex items-center gap-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-mono font-medium cursor-pointer shadow-2xs transition-colors disabled:opacity-50"
                :disabled="isSaving"
              >
                <Loader2 v-if="isSaving" class="w-3.5 h-3.5 animate-spin" />
                <Save v-else class="w-3.5 h-3.5" />
                <span>{{ isSaving ? 'Saving...' : 'Save Profile' }}</span>
              </button>
            </div>
          </form>

          <!-- Account Metadata Overview -->
          <div class="p-5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3">
            <h4 class="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              System Metadata
            </h4>
            <div class="grid grid-cols-2 gap-4 text-xs font-mono">
              <div class="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span class="text-slate-400">Database User ID:</span>
                <p class="font-bold text-slate-800 dark:text-slate-200">#{{ taskStore.currentUser.id }}</p>
              </div>
              <div class="p-2.5 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <span class="text-slate-400">Google Subject ID:</span>
                <p class="font-bold text-slate-800 dark:text-slate-200 truncate">
                  {{ taskStore.currentUser.google_id || 'Not linked' }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Unauthenticated Fallback View -->
    <div
      v-else
      class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-8 sm:p-12 text-center shadow-xs space-y-4"
    >
      <div class="w-14 h-14 mx-auto rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500">
        <UserIcon class="w-7 h-7" />
      </div>
      <h3 class="text-base font-bold font-mono text-slate-800 dark:text-slate-200">No Active User Session</h3>
      <p class="text-xs text-slate-500 max-w-sm mx-auto">
        Authenticate using Google Identity or Email credentials to manage your personal profile and avatar.
      </p>
      <div class="pt-2 flex items-center justify-center gap-3">
        <button
          type="button"
          class="h-8 px-4 inline-flex items-center gap-2 rounded-md bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-xs font-medium cursor-pointer shadow-xs"
          @click="emit('open-auth')"
        >
          <Shield class="w-3.5 h-3.5" />
          <span>Sign In</span>
        </button>
        <button
          type="button"
          class="h-8 px-3 inline-flex items-center gap-1.5 rounded-md border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-mono text-xs cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700"
          @click="taskStore.setAppView('LANDING')"
        >
          <span>Landing Page</span>
        </button>
      </div>
    </div>
  </main>
</template>
