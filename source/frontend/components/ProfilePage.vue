<script setup lang="ts">
/**
 * Full-page account view.
 *
 * Replaces the small popover that previously served as the account panel: it
 * could show a name and an email and nothing else, with no way to edit either.
 * This page owns profile editing, the list of project memberships with the
 * caller's role in each, and sign-out.
 */
import { ref, computed, onMounted } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import {
  ArrowLeft, Mail, Wrench, Shield, User as UserIcon, LogOut, Save,
  AlertCircle, Check, CalendarDays, FolderKanban, Loader2, Camera,
} from 'lucide-vue-next';

const taskStore = useTaskStore();

const fullName = ref('');
const skills = ref('');
const errorMsg = ref<string | null>(null);
const noticeMsg = ref<string | null>(null);
const isSaving = ref(false);
const isUploadingAvatar = ref(false);
const avatarError = ref<string | null>(null);

/** Matches the server ceiling, so an oversized file is refused before upload. */
const AVATAR_MAX_BYTES = 2 * 1024 * 1024;

async function onPickAvatar(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';  // so re-picking the same file fires `change` again
  if (!file) return;

  // The size check lives in uploadAvatarFile, shared with the paste path.
  // Checked here as well as server-side: a courtesy, so a 5 MB photo fails
  // instantly instead of after the upload.
  await uploadAvatarFile(file);
}

/**
 * Paste a picture straight onto the profile.
 *
 * Bound to the whole page rather than an input, because there is no obvious
 * field to focus first — you copy an image and press Ctrl+V. Ignored while a
 * name or skills field has focus, where a paste means text.
 */
async function onPagePaste(e: ClipboardEvent) {
  const target = e.target as HTMLElement | null;
  if (target && /^(INPUT|TEXTAREA)$/.test(target.tagName)) return;

  const file = Array.from(e.clipboardData?.items ?? [])
    .filter((it) => it.kind === 'file')
    .map((it) => it.getAsFile())
    .find((f): f is File => f !== null && f.type.startsWith('image/'));

  if (!file) return;
  e.preventDefault();
  await uploadAvatarFile(file);
}

/** Shared by the file picker and the paste handler. */
async function uploadAvatarFile(file: File) {
  avatarError.value = null;

  if (file.size > AVATAR_MAX_BYTES) {
    avatarError.value = 'That image is over 2 MB. Please pick a smaller one.';
    return;
  }

  isUploadingAvatar.value = true;
  try {
    await taskStore.uploadAvatar(file);
  } catch (err: any) {
    avatarError.value = err?.message || 'Could not upload that picture.';
  } finally {
    isUploadingAvatar.value = false;
  }
}

async function removeAvatar() {
  avatarError.value = null;
  isUploadingAvatar.value = true;
  try {
    await taskStore.removeAvatar();
  } catch (err: any) {
    avatarError.value = err?.message || 'Could not remove the picture.';
  } finally {
    isUploadingAvatar.value = false;
  }
}

const user = computed(() => taskStore.currentUser);

const initials = computed(() => {
  const name = user.value?.full_name?.trim() || user.value?.email || '';
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('') || '?';
});

const memberSince = computed(() => {
  const raw = (user.value as { created_at?: string } | null)?.created_at;
  if (!raw) return null;
  const d = new Date(raw);
  return Number.isNaN(d.getTime())
    ? null
    : d.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
});

const pmCount = computed(() => taskStore.projects.filter((p) => p.my_role === 'PM').length);

const isDirty = computed(() =>
  fullName.value.trim() !== (user.value?.full_name ?? '')
  || skills.value.trim() !== (user.value?.skills ?? ''));

function resetForm() {
  fullName.value = user.value?.full_name ?? '';
  skills.value = user.value?.skills ?? '';
}

async function handleSave() {
  if (!isDirty.value) return;
  errorMsg.value = null;
  noticeMsg.value = null;
  isSaving.value = true;
  try {
    await taskStore.updateProfile({
      full_name: fullName.value.trim(),
      skills: skills.value.trim(),
    });
    noticeMsg.value = 'Profile saved.';
    setTimeout(() => { noticeMsg.value = null; }, 2500);
  } catch (e: any) {
    errorMsg.value = e.message || 'Could not save your profile';
  } finally {
    isSaving.value = false;
  }
}

async function handleSignOut() {
  await taskStore.logout();
}

function openProject(projectId: number) {
  taskStore.selectProject(projectId);
  taskStore.showBoard();
}

onMounted(() => {
  resetForm();
  taskStore.loadProjects();
});
</script>

<template>
  <div
    class="min-h-screen min-h-[100dvh] bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col"
    @paste="onPagePaste"
  >
    <!-- Header -->
    <header class="h-12 shrink-0 px-4 md:px-6 flex items-center justify-between border-b border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900">
      <button
        type="button"
        class="h-8 inline-flex items-center gap-1.5 px-3 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 text-xs font-mono cursor-pointer"
        @click="taskStore.showBoard()"
      >
        <ArrowLeft class="w-3.5 h-3.5" />
        <span>Back to board</span>
      </button>
      <h1 class="text-sm font-bold tracking-wider font-mono">KOSHI</h1>
    </header>

    <main class="flex-1 w-full max-w-4xl mx-auto px-5 py-8 space-y-6 overflow-y-auto">
      <!-- Identity -->
      <section class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-6">
        <div class="flex items-center gap-4">
          <!-- The picture is also the control. A separate "upload" button
               elsewhere on the page would make you look in two places for one
               thing. -->
          <div class="relative shrink-0 group">
            <img
              v-if="user?.avatar_url"
              :src="user.avatar_url"
              alt=""
              class="w-16 h-16 rounded-full border border-slate-300 dark:border-slate-700 object-cover"
            />
            <div
              v-else
              class="w-16 h-16 rounded-full bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-lg font-semibold font-sans"
            >{{ initials }}</div>

            <label
              id="avatar-upload"
              class="absolute inset-0 rounded-full flex items-center justify-center bg-slate-900/60 text-white opacity-0 group-hover:opacity-100 focus-within:opacity-100 cursor-pointer transition-opacity"
              :class="isUploadingAvatar && 'opacity-100'"
              title="Change your picture — or paste an image anywhere on this page"
            >
              <Loader2 v-if="isUploadingAvatar" class="w-5 h-5 animate-spin" />
              <Camera v-else class="w-5 h-5" />
              <span class="sr-only">Change profile picture</span>
              <input
                type="file"
                accept="image/png,image/jpeg,image/gif,image/webp"
                class="hidden"
                :disabled="isUploadingAvatar"
                @change="onPickAvatar"
              />
            </label>
          </div>

          <div class="min-w-0">
            <h2 class="text-lg font-semibold font-sans truncate">{{ user?.full_name }}</h2>
            <p v-if="avatarError" id="avatar-error" class="text-[11px] font-mono text-rose-700 dark:text-rose-300">
              {{ avatarError }}
            </p>
            <button
              v-if="user?.avatar_url && !isUploadingAvatar"
              id="avatar-remove"
              type="button"
              class="text-[11px] font-mono text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 underline cursor-pointer"
              @click="removeAvatar"
            >Remove picture</button>
            <p class="flex items-center gap-1.5 text-xs font-mono text-slate-500 dark:text-slate-400 truncate">
              <Mail class="w-3.5 h-3.5 shrink-0" />
              {{ user?.email }}
            </p>
            <p v-if="memberSince" class="mt-0.5 flex items-center gap-1.5 text-[11px] font-mono text-slate-400 dark:text-slate-500">
              <CalendarDays class="w-3 h-3 shrink-0" />
              Member since {{ memberSince }}
            </p>
          </div>
        </div>

        <dl class="mt-5 grid grid-cols-3 gap-3 text-center">
          <div class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 py-3">
            <dt class="text-[10px] font-mono uppercase tracking-wide text-slate-500 dark:text-slate-400">Projects</dt>
            <dd class="text-lg font-semibold font-sans">{{ taskStore.projects.length }}</dd>
          </div>
          <div class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 py-3">
            <dt class="text-[10px] font-mono uppercase tracking-wide text-slate-500 dark:text-slate-400">Managing</dt>
            <dd class="text-lg font-semibold font-sans">{{ pmCount }}</dd>
          </div>
          <div class="rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 py-3">
            <dt class="text-[10px] font-mono uppercase tracking-wide text-slate-500 dark:text-slate-400">Open tasks</dt>
            <dd class="text-lg font-semibold font-sans">{{ taskStore.metrics.total - taskStore.metrics.done }}</dd>
          </div>
        </dl>
      </section>

      <!-- Editable details -->
      <section class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-6">
        <h3 class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Account details
        </h3>

        <form class="mt-4 space-y-4 text-xs" @submit.prevent="handleSave">
          <div>
            <label for="profile-name" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Full name</label>
            <input
              id="profile-name"
              v-model="fullName"
              type="text"
              required
              class="w-full max-w-sm bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>

          <div>
            <label for="profile-skills" class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">
              <span class="inline-flex items-center gap-1.5"><Wrench class="w-3.5 h-3.5" /> Skills</span>
            </label>
            <input
              id="profile-skills"
              v-model="skills"
              type="text"
              placeholder="e.g. python,vue,postgres"
              class="w-full max-w-sm bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-sans"
            />
            <p class="mt-1.5 text-[10px] font-mono text-slate-500 dark:text-slate-400">
              Comma-separated. Used by the assignment recommender to match you to work.
            </p>
          </div>

          <div>
            <label class="block font-mono text-slate-700 dark:text-slate-300 mb-1 font-medium">Email address</label>
            <input
              :value="user?.email"
              type="email"
              disabled
              class="w-full max-w-sm bg-slate-100 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-500 dark:text-slate-500 font-mono cursor-not-allowed"
            />
            <p class="mt-1.5 text-[10px] font-mono text-slate-500 dark:text-slate-400">
              Your email identifies the account and cannot be changed here.
            </p>
          </div>

          <div v-if="errorMsg" class="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-1.5 font-mono text-[11px]">
            <AlertCircle class="w-3.5 h-3.5 shrink-0" />
            <span>{{ errorMsg }}</span>
          </div>
          <div v-if="noticeMsg" class="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5 font-mono text-[11px]">
            <Check class="w-3.5 h-3.5 shrink-0" />
            <span>{{ noticeMsg }}</span>
          </div>

          <div class="flex items-center gap-2">
            <button
              type="submit"
              :disabled="!isDirty || isSaving"
              class="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Loader2 v-if="isSaving" class="w-3.5 h-3.5 animate-spin" />
              <Save v-else class="w-3.5 h-3.5" />
              <span>Save changes</span>
            </button>
            <button
              v-if="isDirty"
              type="button"
              class="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 font-mono text-xs cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800"
              @click="resetForm"
            >Discard</button>
          </div>
        </form>
      </section>

      <!-- Memberships -->
      <section class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-6">
        <h3 class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Project memberships
        </h3>
        <p class="mt-1 text-[11px] font-mono text-slate-500 dark:text-slate-400">
          Your role is set per project, so it can differ in each.
        </p>

        <p v-if="taskStore.projects.length === 0" class="mt-4 text-xs text-slate-500 dark:text-slate-400">
          You are not a member of any project yet.
        </p>

        <ul v-else class="mt-4 space-y-1.5">
          <li v-for="p in taskStore.projects" :key="p.id">
            <button
              type="button"
              class="w-full text-left px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 hover:border-slate-300 dark:hover:border-slate-700 flex items-center justify-between gap-2 cursor-pointer"
              @click="openProject(p.id)"
            >
              <span class="min-w-0">
                <span class="block text-xs font-medium font-sans truncate">{{ p.name }}</span>
                <span class="block text-[10px] font-mono text-slate-500 dark:text-slate-400">
                  {{ p.member_count }} member{{ p.member_count === 1 ? '' : 's' }}
                </span>
              </span>
              <span
                class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold inline-flex items-center gap-1"
                :class="p.my_role === 'PM'
                  ? 'bg-indigo-100 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300'
                  : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'"
              >
                <Shield v-if="p.my_role === 'PM'" class="w-3 h-3" />
                <UserIcon v-else class="w-3 h-3" />
                {{ p.my_role }}
              </span>
            </button>
          </li>
        </ul>

        <button
          type="button"
          class="mt-4 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-mono text-xs inline-flex items-center gap-1.5 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800"
          @click="taskStore.isDashboardOpen = true"
        >
          <FolderKanban class="w-3.5 h-3.5" />
          <span>Manage projects &amp; teams</span>
        </button>
      </section>

      <!-- Session -->
      <section class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-6">
        <h3 class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Session
        </h3>
        <p class="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
          Signing out clears your session on this device and returns you to the
          welcome page.
        </p>
        <button
          type="button"
          class="mt-4 px-3 py-2 rounded-lg bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 text-white font-mono font-medium text-xs inline-flex items-center gap-1.5 cursor-pointer"
          @click="handleSignOut"
        >
          <LogOut class="w-3.5 h-3.5" />
          <span>Sign out</span>
        </button>
      </section>
    </main>
  </div>
</template>
