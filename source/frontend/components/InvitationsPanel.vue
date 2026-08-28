<script setup lang="ts">
/**
 * Pending project invitations.
 *
 * Being added to a project is a request, not a fact — the backend keeps the
 * membership PENDING and refuses all access until it is answered. This panel is
 * where it gets answered.
 *
 * It shows the project name and who invited you because you cannot look either
 * up: you are not a member yet, and the API returns 404 for the project itself.
 */
import { ref } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import { Mail, Check, X, Loader2 } from 'lucide-vue-next';

const taskStore = useTaskStore();

/** Which project id is mid-request, so its buttons can be disabled. */
const busy = ref<number | null>(null);
const errorMsg = ref<string | null>(null);

async function respond(projectId: number, accept: boolean) {
  busy.value = projectId;
  errorMsg.value = null;
  try {
    if (accept) {
      await taskStore.acceptInvitation(projectId);
    } else {
      await taskStore.declineInvitation(projectId);
    }
  } catch (e: any) {
    // 409 means somebody already answered it — most likely this user in another
    // tab. Say so rather than leaving a dead button.
    errorMsg.value = /409/.test(e?.message ?? '')
      ? 'That invitation has already been answered.'
      : e?.message || 'Could not respond to the invitation.';
  } finally {
    busy.value = null;
  }
}
</script>

<template>
  <section
    v-if="taskStore.invitations.length > 0"
    id="invitations-panel"
    class="rounded-lg border border-amber-300 dark:border-amber-800/60 bg-amber-50 dark:bg-amber-950/20 p-4 space-y-3"
  >
    <div class="flex items-center gap-2">
      <Mail class="w-4 h-4 text-amber-700 dark:text-amber-400" />
      <h3 class="text-xs font-semibold font-mono text-amber-800 dark:text-amber-300">
        {{ taskStore.invitations.length }}
        project invitation{{ taskStore.invitations.length === 1 ? '' : 's' }}
      </h3>
    </div>

    <p v-if="errorMsg" class="text-[11px] text-rose-700 dark:text-rose-300 font-mono">
      {{ errorMsg }}
    </p>

    <ul class="space-y-2">
      <li
        v-for="invite in taskStore.invitations"
        :key="invite.project_id"
        :data-invitation="invite.project_id"
        class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border border-amber-200 dark:border-amber-900/50 bg-white dark:bg-slate-900 p-3"
      >
        <div class="min-w-0">
          <p class="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">
            {{ invite.project_name }}
          </p>
          <p class="text-[11px] text-slate-600 dark:text-slate-400">
            <span v-if="invite.invited_by_name">{{ invite.invited_by_name }} invited you</span>
            <span v-else>You were invited</span>
            as <span class="font-mono font-medium">{{ invite.role }}</span>
          </p>
          <p
            v-if="invite.project_description"
            class="text-[11px] text-slate-500 dark:text-slate-500 truncate mt-0.5"
          >
            {{ invite.project_description }}
          </p>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button
            type="button"
            :disabled="busy === invite.project_id"
            class="px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-mono text-[11px] cursor-pointer disabled:opacity-50 min-h-[36px] flex items-center gap-1"
            @click="respond(invite.project_id, false)"
          >
            <X class="w-3.5 h-3.5" />
            <span>Decline</span>
          </button>
          <button
            type="button"
            :disabled="busy === invite.project_id"
            class="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-medium text-[11px] cursor-pointer disabled:opacity-50 min-h-[36px] flex items-center gap-1"
            @click="respond(invite.project_id, true)"
          >
            <Loader2 v-if="busy === invite.project_id" class="w-3.5 h-3.5 animate-spin" />
            <Check v-else class="w-3.5 h-3.5" />
            <span>Accept</span>
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
