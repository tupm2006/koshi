<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { api, type ProjectMember, type UserProfile } from '../services/api';
import { useTaskStore } from '../stores/taskStore';
import { Users, X, UserPlus, Trash2, Search, Shield, Check, AlertCircle } from 'lucide-vue-next';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const taskStore = useTaskStore();

const members = ref<ProjectMember[]>([]);
const isLoading = ref(false);
const errorMsg = ref<string | null>(null);
const successMsg = ref<string | null>(null);

// Search & Add state
const searchQuery = ref('');
const searchResults = ref<UserProfile[]>([]);
const isSearching = ref(false);
const selectedUser = ref<UserProfile | null>(null);
const selectedRole = ref<'PM' | 'MEMBER' | 'VIEWER'>('MEMBER');
const isAdding = ref(false);

let searchTimeout: any = null;

async function fetchMembers() {
  isLoading.value = true;
  errorMsg.value = null;
  try {
    const data = await api.getProjectMembers(1);
    members.value = data || [];
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to load project members';
  } finally {
    isLoading.value = false;
  }
}

watch(searchQuery, (newVal) => {
  clearTimeout(searchTimeout);
  if (!newVal || newVal.trim().length === 0) {
    searchResults.value = [];
    isSearching.value = false;
    return;
  }

  isSearching.value = true;
  searchTimeout = setTimeout(async () => {
    try {
      const results = await api.searchUsers(newVal.trim());
      // Filter out users who are already project members
      const existingUserIds = new Set(members.value.map((m) => m.user_id));
      searchResults.value = (results || []).filter((u) => !existingUserIds.has(u.id));
    } catch (e) {
      searchResults.value = [];
    } finally {
      isSearching.value = false;
    }
  }, 250);
});

function selectUser(user: UserProfile) {
  selectedUser.value = user;
  searchQuery.value = user.full_name;
  searchResults.value = [];
}

async function handleAddMember() {
  if (!selectedUser.value) return;
  isAdding.value = true;
  errorMsg.value = null;
  successMsg.value = null;

  try {
    await api.addProjectMember(1, selectedUser.value.id, selectedRole.value);
    successMsg.value = `Added ${selectedUser.value.full_name} as ${selectedRole.value}`;
    selectedUser.value = null;
    searchQuery.value = '';
    await fetchMembers();
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to add member';
  } finally {
    isAdding.value = false;
  }
}

async function handleRoleChange(member: ProjectMember, newRole: string) {
  errorMsg.value = null;
  try {
    await api.updateProjectMemberRole(1, member.user_id, newRole);
    member.role = newRole as any;
    successMsg.value = `Updated role to ${newRole}`;
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to update member role';
    await fetchMembers();
  }
}

async function handleRemoveMember(member: ProjectMember) {
  if (!confirm(`Remove ${member.user?.full_name || 'user'} from this project?`)) return;
  errorMsg.value = null;
  try {
    await api.removeProjectMember(1, member.user_id);
    await fetchMembers();
  } catch (e: any) {
    errorMsg.value = e.message || 'Failed to remove member';
  }
}

onMounted(() => {
  fetchMembers();
});

function getRoleBadge(role: string) {
  switch (role) {
    case 'OWNER':
      return 'bg-purple-100 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-800 font-bold';
    case 'PM':
      return 'bg-indigo-100 dark:bg-indigo-950/60 text-indigo-800 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800 font-semibold';
    case 'VIEWER':
      return 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-700';
    case 'MEMBER':
    default:
      return 'bg-sky-100 dark:bg-sky-950/60 text-sky-800 dark:text-sky-300 border-sky-300 dark:border-sky-800 font-medium';
  }
}
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-xl rounded-lg shadow-2xl border border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[85vh] overflow-hidden">
      <!-- Modal Header -->
      <div class="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between select-none bg-slate-50/50 dark:bg-slate-950/40 shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-indigo-600 dark:text-indigo-400">
            <Users class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold text-slate-900 dark:text-slate-100 font-sans">
              Project Team Members
            </h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Project-Scoped Role & Collaborator Management</p>
          </div>
        </div>
        <button
          type="button"
          class="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
          @click="emit('close')"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body Content -->
      <div class="p-5 md:p-6 overflow-y-auto space-y-5 flex-1 text-xs font-sans">
        <!-- Notification Alerts -->
        <div v-if="errorMsg" class="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-1.5 font-mono text-[11px]">
          <AlertCircle class="w-3.5 h-3.5 shrink-0" />
          <span>{{ errorMsg }}</span>
        </div>

        <div v-if="successMsg" class="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5 font-mono text-[11px]">
          <Check class="w-3.5 h-3.5 shrink-0" />
          <span>{{ successMsg }}</span>
        </div>

        <!-- Add Member Section -->
        <div class="p-3.5 bg-slate-50 dark:bg-slate-950/60 rounded-lg border border-slate-200 dark:border-slate-800/80 space-y-3">
          <h3 class="font-mono text-[11px] font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <UserPlus class="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
            <span>Invite Team Member</span>
          </h3>

          <div class="grid grid-cols-1 sm:grid-cols-12 gap-2">
            <!-- Autocomplete Search Input -->
            <div class="sm:col-span-7 relative">
              <div class="relative">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Search user by name or email..."
                  class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md pl-8 pr-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-sans"
                />
                <Search class="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-400 pointer-events-none" />
              </div>

              <!-- Search Results Dropdown -->
              <div
                v-if="searchResults.length > 0"
                class="absolute left-0 right-0 mt-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg shadow-xl py-1 z-50 max-h-48 overflow-y-auto"
              >
                <button
                  v-for="u in searchResults"
                  :key="u.id"
                  type="button"
                  class="w-full text-left px-3 py-1.5 hover:bg-indigo-50 dark:hover:bg-indigo-950/40 flex items-center justify-between text-xs cursor-pointer"
                  @click="selectUser(u)"
                >
                  <div class="flex items-center gap-2">
                    <img v-if="u.avatar_url" :src="u.avatar_url" class="w-5 h-5 rounded-full object-cover" />
                    <div v-else class="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-[10px]">
                      {{ u.full_name.charAt(0).toUpperCase() }}
                    </div>
                    <div>
                      <div class="font-medium text-slate-900 dark:text-slate-100">{{ u.full_name }}</div>
                      <div class="text-[10px] text-slate-500 font-mono">{{ u.email }}</div>
                    </div>
                  </div>
                  <span class="text-[10px] font-mono text-indigo-600 dark:text-indigo-400">Select</span>
                </button>
              </div>
            </div>

            <!-- Role Selector -->
            <div class="sm:col-span-3">
              <select
                v-model="selectedRole"
                class="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-2 py-1.5 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                <option value="PM">PM</option>
                <option value="MEMBER">Member</option>
                <option value="VIEWER">Viewer</option>
              </select>
            </div>

            <!-- Add Button -->
            <div class="sm:col-span-2">
              <button
                type="button"
                class="w-full h-full py-1.5 px-3 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                :disabled="!selectedUser || isAdding"
                @click="handleAddMember"
              >
                <UserPlus class="w-3 h-3" />
                <span>{{ isAdding ? '...' : 'Add' }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Current Members List -->
        <div class="space-y-2">
          <div class="flex items-center justify-between text-slate-500 dark:text-slate-400 font-mono text-[11px] font-semibold uppercase">
            <span>Project Collaborators ({{ members.length }})</span>
            <span>Project Role</span>
          </div>

          <div v-if="isLoading" class="py-6 text-center text-slate-400 font-mono text-xs">
            Loading team members...
          </div>

          <div v-else-if="members.length === 0" class="py-6 text-center text-slate-400 font-mono text-xs">
            No collaborators found in this project.
          </div>

          <div v-else class="divide-y divide-slate-200 dark:divide-slate-800/80 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
            <div
              v-for="m in members"
              :key="m.id"
              class="p-3 bg-white dark:bg-slate-900 flex items-center justify-between gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/40"
            >
              <!-- User Info -->
              <div class="flex items-center gap-2.5 min-w-0">
                <img
                  v-if="m.user?.avatar_url"
                  :src="m.user.avatar_url"
                  class="w-7 h-7 rounded-full object-cover border border-slate-300 dark:border-slate-700 shrink-0"
                  alt="Avatar"
                />
                <div
                  v-else
                  class="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 flex items-center justify-center font-bold text-xs shrink-0"
                >
                  {{ (m.user?.full_name || 'U').charAt(0).toUpperCase() }}
                </div>
                <div class="min-w-0">
                  <div class="font-medium text-slate-900 dark:text-slate-100 truncate">
                    {{ m.user?.full_name || `User #${m.user_id}` }}
                  </div>
                  <div class="text-[11px] text-slate-500 font-mono truncate">
                    {{ m.user?.email || 'No email' }}
                  </div>
                </div>
              </div>

              <!-- Role Selector & Actions -->
              <div class="flex items-center gap-2 shrink-0">
                <select
                  :value="m.role"
                  class="h-6 pl-2 pr-4 rounded-md border text-[11px] font-mono font-semibold uppercase tracking-wider bg-white dark:bg-slate-900 cursor-pointer focus:outline-none"
                  :class="getRoleBadge(m.role)"
                  @change="handleRoleChange(m, ($event.target as HTMLSelectElement).value)"
                >
                  <option value="OWNER">OWNER</option>
                  <option value="PM">PM</option>
                  <option value="MEMBER">MEMBER</option>
                  <option value="VIEWER">VIEWER</option>
                </select>

                <button
                  type="button"
                  class="p-1 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded cursor-pointer"
                  title="Remove from project"
                  @click="handleRemoveMember(m)"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="px-5 py-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex items-center justify-between text-xs font-mono text-slate-500 shrink-0">
        <span>Project ID: #1 (Core Engine)</span>
        <button
          type="button"
          class="h-7 px-3 rounded-md bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 font-sans font-medium text-xs cursor-pointer shadow-xs"
          @click="emit('close')"
        >
          Done
        </button>
      </div>
    </div>
  </div>
</template>
