<script setup lang="ts">
/**
 * Personal dashboard: the user's projects, project creation, and per-project
 * role assignment.
 *
 * Roles shown here are scoped to a single project — the same account can be PM
 * of one project and MEMBER of another. PM-only controls are hidden when the
 * caller is not a PM of the selected project, and the server enforces the same
 * rule independently (see D4 §4.3).
 */
import { ref, computed, onMounted, watch } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { api, type ProjectMember, type ProjectRole } from '../services/api';
import InvitationsPanel from './InvitationsPanel.vue';
import {
  X, FolderPlus, Users, Shield, User as UserIcon, Trash2,
  AlertCircle, Check, LayoutGrid, Loader2,
} from 'lucide-vue-next';
import { tr } from '../lib/i18nPlugin';

const emit = defineEmits<{ (e: 'close'): void }>();
const taskStore = useTaskStore();

const newProjectName = ref('');
const newProjectDesc = ref('');
const inviteEmail = ref('');
const inviteRole = ref<ProjectRole>('MEMBER');

const members = ref<ProjectMember[]>([]);
const isLoadingMembers = ref(false);
const isCreating = ref(false);
const isInviting = ref(false);
const errorMsg = ref<string | null>(null);
const noticeMsg = ref<string | null>(null);

const selectedId = computed(() => taskStore.currentProjectId);
const isPM = computed(() => taskStore.isProjectManager);

function flashNotice(msg: string) {
  noticeMsg.value = msg;
  setTimeout(() => { if (noticeMsg.value === msg) noticeMsg.value = null; }, 2500);
}

async function refreshMembers() {
  if (selectedId.value === null) {
    members.value = [];
    return;
  }
  isLoadingMembers.value = true;
  try {
    members.value = await api.listMembers(selectedId.value);
  } catch (e: any) {
    errorMsg.value = e.message || tr('pd.loadFail');
  } finally {
    isLoadingMembers.value = false;
  }
}

async function handleCreateProject() {
  const name = newProjectName.value.trim();
  if (!name) return;
  errorMsg.value = null;
  isCreating.value = true;
  try {
    await taskStore.createProject(name, newProjectDesc.value.trim());
    newProjectName.value = '';
    newProjectDesc.value = '';
    await refreshMembers();
    flashNotice(tr('pd.created', { name }));
  } catch (e: any) {
    errorMsg.value = e.message || tr('pd.createFail');
  } finally {
    isCreating.value = false;
  }
}

async function handleSelect(projectId: number) {
  errorMsg.value = null;
  await taskStore.selectProject(projectId);
  await refreshMembers();
}

async function handleInvite() {
  const email = inviteEmail.value.trim();
  if (!email || selectedId.value === null) return;
  errorMsg.value = null;
  isInviting.value = true;
  try {
    await api.addMember(selectedId.value, email, inviteRole.value);
    inviteEmail.value = '';
    await refreshMembers();
    await taskStore.loadProjects();
    // Not "added": they are not in the project until they accept. Saying
    // "added" would be a lie the roster immediately contradicts.
    flashNotice(tr('pd.invited', { email }));
  } catch (e: any) {
    errorMsg.value = e.message || tr('pd.addFail');
  } finally {
    isInviting.value = false;
  }
}

async function handleRoleChange(member: ProjectMember, role: ProjectRole) {
  if (selectedId.value === null || member.role === role) return;
  errorMsg.value = null;
  try {
    await api.updateMemberRole(selectedId.value, member.user_id, role);
    await refreshMembers();
    // The caller may have just changed their own role in this project.
    await taskStore.loadProjects();
    flashNotice(tr('pd.roleChanged', { name: member.full_name, role: tr(`role.${role}` as const) }));
  } catch (e: any) {
    errorMsg.value = e.message || tr('pd.roleFail');
  }
}

async function handleRemove(member: ProjectMember) {
  if (selectedId.value === null) return;
  errorMsg.value = null;
  try {
    await api.removeMember(selectedId.value, member.user_id);
    await refreshMembers();
    await taskStore.loadProjects();
    flashNotice(tr('pd.removed', { name: member.full_name }));
  } catch (e: any) {
    errorMsg.value = e.message || tr('pd.removeFail');
  }
}

watch(selectedId, refreshMembers);
onMounted(async () => {
  await taskStore.loadProjects();
  await refreshMembers();
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 flex items-start md:items-center justify-center p-0 md:p-6 overflow-y-auto"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-4xl md:rounded-lg shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col min-h-screen md:min-h-0">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400">
            <LayoutGrid class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold font-sans">{{ $t('pd.title') }}</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">
              {{ taskStore.currentUser?.full_name || $t('pd.notSignedIn') }} · {{ $t('pd.rolesPerProject') }}
            </p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <div v-if="errorMsg" class="mx-5 mt-3 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-1.5 font-mono text-[11px]">
        <AlertCircle class="w-3.5 h-3.5 shrink-0" />
        <span>{{ errorMsg }}</span>
      </div>
      <div v-if="noticeMsg" class="mx-5 mt-3 p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5 font-mono text-[11px]">
        <Check class="w-3.5 h-3.5 shrink-0" />
        <span>{{ noticeMsg }}</span>
      </div>

      <!-- Invitations first: they are the only thing here that is waiting on
           the user rather than the other way round. -->
      <div v-if="taskStore.invitations.length > 0" class="px-5 pt-4">
        <InvitationsPanel />
      </div>

      <div class="grid md:grid-cols-2 gap-0 md:gap-5 p-5">
        <!-- Projects -->
        <section class="space-y-3">
          <h3 class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {{ $t('pd.projects', { n: taskStore.projects.length }) }}
          </h3>

          <div v-if="taskStore.projects.length === 0" class="p-4 rounded-lg border border-dashed border-slate-300 dark:border-slate-700 text-center">
            <p class="text-xs text-slate-500 dark:text-slate-400">
              {{ $t('pd.noProjects') }}
            </p>
          </div>

          <ul class="space-y-1.5">
            <li v-for="p in taskStore.projects" :key="p.id">
              <button
                type="button"
                class="w-full text-left px-3 py-2 rounded-lg border cursor-pointer flex items-center justify-between gap-2"
                :class="p.id === selectedId
                  ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-800'
                  : 'bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'"
                @click="handleSelect(p.id)"
              >
                <span class="min-w-0">
                  <span class="block text-xs font-medium font-sans truncate">{{ p.name }}</span>
                  <span class="block text-[10px] font-mono text-slate-500 dark:text-slate-400">
                    {{ p.member_count === 1 ? $t('pd.member1') : $t('pd.members', { n: p.member_count }) }}
                  </span>
                </span>
                <span
                  class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold flex items-center gap-1"
                  :class="p.my_role === 'PM'
                    ? 'bg-indigo-100 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'"
                >
                  <Shield v-if="p.my_role === 'PM'" class="w-3 h-3" />
                  <UserIcon v-else class="w-3 h-3" />
                  {{ p.my_role ? $t(`role.${p.my_role}` as const) : "—" }}
                </span>
              </button>
            </li>
          </ul>

          <form class="pt-2 space-y-2 border-t border-slate-200 dark:border-slate-800" @submit.prevent="handleCreateProject">
            <label for="new-project-name" class="block text-[11px] font-mono font-medium text-slate-700 dark:text-slate-300 pt-2">{{ $t('pd.newProject') }}</label>
            <input
              id="new-project-name"
              v-model="newProjectName"
              type="text"
              required
              :placeholder="$t('pd.namePh')"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-sans"
            />
            <input
              v-model="newProjectDesc"
              type="text"
              :placeholder="$t('pd.descPh')"
              class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-sans"
            />
            <button
              type="submit"
              :disabled="isCreating || !newProjectName.trim()"
              class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Loader2 v-if="isCreating" class="w-3.5 h-3.5 animate-spin" />
              <FolderPlus v-else class="w-3.5 h-3.5" />
              <span>{{ $t('pd.create') }}</span>
            </button>
          </form>
        </section>

        <!-- Members -->
        <section class="space-y-3 mt-6 md:mt-0 pt-6 md:pt-0 border-t md:border-t-0 md:border-l border-slate-200 dark:border-slate-800 md:pl-5">
          <h3 class="text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
            <Users class="w-3.5 h-3.5" />
            {{ $t('pd.team') }}
          </h3>

          <p v-if="selectedId === null" class="text-xs text-slate-500 dark:text-slate-400">
            {{ $t('pd.selectHint') }}
          </p>

          <template v-else>
            <p v-if="!isPM" class="text-[11px] font-mono text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-lg px-2.5 py-1.5">
              {{ $t('pd.memberNotice') }}
            </p>

            <p v-if="isLoadingMembers" class="text-xs text-slate-500 dark:text-slate-400">{{ $t('common.loading') }}</p>

            <ul v-else class="space-y-1.5">
              <li
                v-for="m in members"
                :key="m.user_id"
                class="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2"
              >
                <span class="min-w-0">
                  <span class="flex items-center gap-1.5">
                    <span class="text-xs font-medium font-sans truncate" :class="m.status !== 'ACCEPTED' && 'text-slate-500 dark:text-slate-500'">
                      {{ m.full_name }}
                    </span>
                    <!-- An invited person is not a member. Saying so plainly
                         stops a PM assigning work to somebody who cannot see
                         the project. -->
                    <span
                      v-if="m.status === 'PENDING'"
                      class="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-amber-100 dark:bg-amber-500/15 text-amber-700 dark:text-amber-300 shrink-0"
                    >{{ $t('pd.invitedBadge') }}</span>
                    <span
                      v-else-if="m.status === 'DECLINED'"
                      class="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-300 shrink-0"
                    >{{ $t('pd.declinedBadge') }}</span>
                  </span>
                  <span class="block text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate">
                    <template v-if="m.status === 'ACCEPTED'">
                      {{ $t('pd.workload', { email: m.email, n: m.active_tasks_count, pts: m.wip_points }) }}
                    </template>
                    <template v-else-if="m.status === 'PENDING'">
                      {{ $t('pd.awaiting', { email: m.email }) }}
                    </template>
                    <template v-else>
                      {{ $t('pd.declined', { email: m.email }) }}
                    </template>
                  </span>
                </span>

                <span class="flex items-center gap-1.5 shrink-0">
                  <select
                    v-if="isPM"
                    :value="m.role"
                    class="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded px-1.5 py-1 text-[10px] font-mono focus:outline-none focus:border-indigo-500 cursor-pointer"
                    @change="handleRoleChange(m, ($event.target as HTMLSelectElement).value as ProjectRole)"
                  >
                    <option value="PM">{{ $t('role.PM') }}</option>
                    <option value="MEMBER">{{ $t('role.MEMBER') }}</option>
                  </select>
                  <span
                    v-else
                    class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold"
                    :class="m.role === 'PM'
                      ? 'bg-indigo-100 dark:bg-indigo-500/15 text-indigo-700 dark:text-indigo-300'
                      : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'"
                  >{{ $t(`role.${m.role}` as const) }}</span>

                  <button
                    v-if="isPM"
                    type="button"
                    :title="$t('pd.removeHint')"
                    class="p-1 rounded text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-200 dark:hover:bg-slate-800 cursor-pointer"
                    @click="handleRemove(m)"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </span>
              </li>
            </ul>

            <form v-if="isPM" class="pt-2 space-y-2 border-t border-slate-200 dark:border-slate-800" @submit.prevent="handleInvite">
              <label for="invite-email" class="block text-[11px] font-mono font-medium text-slate-700 dark:text-slate-300 pt-2">
                {{ $t('pd.addByEmail') }}
              </label>
              <div class="flex gap-1.5">
                <input
                  id="invite-email"
                  v-model="inviteEmail"
                  type="email"
                  required
                  placeholder="teammate@example.com"
                  class="flex-1 min-w-0 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-indigo-500 font-mono"
                />
                <select
                  v-model="inviteRole"
                  class="bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-2 py-1.5 text-[11px] font-mono focus:outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="MEMBER">{{ $t('role.MEMBER') }}</option>
                  <option value="PM">{{ $t('role.PM') }}</option>
                </select>
              </div>
              <button
                type="submit"
                :disabled="isInviting || !inviteEmail.trim()"
                class="w-full py-2 rounded-lg bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                <Loader2 v-if="isInviting" class="w-3.5 h-3.5 animate-spin" />
                <Users v-else class="w-3.5 h-3.5" />
                <span>{{ $t('pd.add') }}</span>
              </button>
              <p class="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                {{ $t('pd.mustHaveAccount') }}
              </p>
            </form>
          </template>
        </section>
      </div>
    </div>
  </div>
</template>
