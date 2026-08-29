<script setup lang="ts">
/**
 * Prompt for proof when a task is completed.
 *
 * Opened by the store whenever a task enters DONE, from any path — the kanban
 * arrows, the status cycle, the keyboard, the inspector.
 *
 * **Skipping is allowed, and the task is already DONE either way.** The
 * transition is never blocked on this dialog: work that is finished is
 * finished, and a modal that could strand a task in IN_PROGRESS because an
 * upload failed would cost more than the evidence is worth. This is a prompt,
 * not a gate.
 */
import { computed, ref } from 'vue';
import { useTaskStore } from '../stores/taskStore';
import CommentThread from './CommentThread.vue';
import { CheckCircle2, X } from 'lucide-vue-next';

const taskStore = useTaskStore();

const thread = ref<InstanceType<typeof CommentThread> | null>(null);

const task = computed(() =>
  taskStore.tasks.find((t) => t.id === taskStore.evidenceForTaskId) ?? null,
);

async function submit() {
  // Delegates to the thread so there is one code path for posting a comment
  // with files, whether it came from here or from the inspector.
  await thread.value?.post('EVIDENCE');
  taskStore.dismissEvidencePrompt();
}
</script>

<template>
  <div
    v-if="task"
    id="evidence-modal"
    role="dialog"
    aria-modal="true"
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6"
    @click.self="taskStore.dismissEvidencePrompt()"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-lg rounded-lg shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[90vh]">
      <div class="flex items-center justify-between p-5 pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5 min-w-0">
          <div class="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400">
            <CheckCircle2 class="w-5 h-5" />
          </div>
          <div class="min-w-0">
            <h2 class="text-sm md:text-base font-semibold font-sans">Marked done — add evidence?</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {{ task.id }} · {{ task.title }}
            </p>
          </div>
        </div>
        <button
          type="button"
          aria-label="Close"
          class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer shrink-0"
          @click="taskStore.dismissEvidencePrompt()"
        >
          <X class="w-5 h-5" />
        </button>
      </div>

      <div class="p-5 overflow-y-auto flex-1">
        <p class="text-[11px] text-slate-600 dark:text-slate-400 mb-3">
          A note, a screenshot or a short clip — whatever shows the work is
          actually finished. Optional: the task is already done.
        </p>
        <CommentThread ref="thread" :task-id="task.id" />
      </div>

      <div class="p-5 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-end gap-2">
        <button
          type="button"
          id="evidence-skip"
          class="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-900 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 font-mono text-xs cursor-pointer min-h-[40px]"
          @click="taskStore.dismissEvidencePrompt()"
        >
          Skip
        </button>
        <button
          type="button"
          id="evidence-save"
          :disabled="!thread?.canPost || thread?.isPosting"
          class="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-medium text-xs cursor-pointer disabled:opacity-40 min-h-[40px] flex items-center gap-1.5"
          @click="submit"
        >
          <CheckCircle2 class="w-4 h-4" />
          <span>Save evidence</span>
        </button>
      </div>
    </div>
  </div>
</template>
