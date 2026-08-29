<script setup lang="ts">
/**
 * Discussion and completion evidence for one task.
 *
 * Both live in the same thread deliberately. Evidence is a comment that happens
 * to justify a transition; splitting them into two feeds would mean reading two
 * places to follow one task. `kind` changes the label, not the plumbing.
 *
 * The thread is server-only — comments are not cached to IndexedDB and are not
 * writable offline. A shared conversation cannot be reconciled with
 * last-write-wins the way a task field can, so rather than invent a merge
 * strategy it simply says it is unavailable (INV-15's reasoning, applied to a
 * case where even a personal project has nobody to talk to).
 */
import { ref, watch, computed } from 'vue';
import { api, type TaskComment } from '../services/api';
import { useTaskStore } from '../stores/taskStore';
import { serverIdOf } from '../services/api';
import { MessageSquare, Send, Paperclip, X, ShieldCheck, Loader2 } from 'lucide-vue-next';

const props = defineProps<{ taskId: string }>();

const taskStore = useTaskStore();

const comments = ref<TaskComment[]>([]);
const draft = ref('');
const files = ref<File[]>([]);
const isLoading = ref(false);
const isPosting = ref(false);
const errorMsg = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

const canPost = computed(
  () => taskStore.isBackendConnected && (draft.value.trim().length > 0 || files.value.length > 0),
);

async function load() {
  const serverId = serverIdOf(props.taskId);
  if (serverId === null || !taskStore.isBackendConnected) {
    comments.value = [];
    return;
  }
  isLoading.value = true;
  errorMsg.value = null;
  try {
    comments.value = await api.listComments(serverId);
  } catch (e: any) {
    errorMsg.value = e?.message || 'Could not load the discussion.';
  } finally {
    isLoading.value = false;
  }
}

function pickFiles(e: Event) {
  const chosen = Array.from((e.target as HTMLInputElement).files ?? []);
  files.value = [...files.value, ...chosen];
  // Reset so re-picking the same file fires `change` again.
  if (fileInput.value) fileInput.value.value = '';
}

const removeFile = (i: number) => files.value.splice(i, 1);

async function post(kind: 'COMMENT' | 'EVIDENCE' = 'COMMENT') {
  const serverId = serverIdOf(props.taskId);
  if (serverId === null || !canPost.value) return;

  isPosting.value = true;
  errorMsg.value = null;
  try {
    // A comment must exist before anything can hang off it, so the text goes
    // first even when it is only a caption for the files.
    const created = await api.addComment(
      serverId,
      draft.value.trim() || (kind === 'EVIDENCE' ? 'Evidence attached' : 'Attachment'),
      kind,
    );

    const failed: string[] = [];
    for (const f of files.value) {
      try {
        await api.uploadAttachment(created.id, f);
      } catch (e: any) {
        // Report the file that failed rather than the whole post: the comment
        // itself landed, and claiming total failure would invite a duplicate.
        failed.push(`${f.name} (${e?.message || 'upload failed'})`);
      }
    }
    draft.value = '';
    files.value = [];
    await load();

    // After load(), not before: load() clears errorMsg as its own first step,
    // so setting this earlier meant the reload silently wiped the one message
    // telling the user their file never attached.
    if (failed.length > 0) {
      errorMsg.value = `Comment posted, but these files did not upload: ${failed.join(', ')}`;
    }
  } catch (e: any) {
    errorMsg.value = e?.message || 'Could not post.';
  } finally {
    isPosting.value = false;
  }
}

defineExpose({ post, canPost, isPosting });

watch(() => props.taskId, load, { immediate: true });

const isImage = (t: string) => t.startsWith('image/');
const isVideo = (t: string) => t.startsWith('video/');
const kb = (n: number) => (n < 1024 * 1024 ? `${Math.round(n / 1024)} KB` : `${(n / 1048576).toFixed(1)} MB`);
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
</script>

<template>
  <section id="comment-thread" class="space-y-3">
    <h4 class="flex items-center gap-1.5 text-[11px] font-mono font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
      <MessageSquare class="w-3.5 h-3.5" />
      <span>Discussion &amp; evidence</span>
      <span v-if="comments.length" class="text-slate-400 dark:text-slate-500">({{ comments.length }})</span>
    </h4>

    <p v-if="!taskStore.isBackendConnected" class="text-[11px] font-mono text-slate-500 dark:text-slate-400 p-2.5 rounded-lg border border-dashed border-slate-300 dark:border-slate-700">
      Discussion is unavailable offline — it is shared, and there is no safe way
      to merge two people's edits to a conversation.
    </p>

    <template v-else>
      <p v-if="errorMsg" class="text-[11px] font-mono text-rose-700 dark:text-rose-300">{{ errorMsg }}</p>
      <p v-if="isLoading" class="text-[11px] font-mono text-slate-500">Loading…</p>

      <p v-else-if="comments.length === 0" class="text-[11px] font-mono text-slate-500 dark:text-slate-400">
        Nothing yet. Notes here stay with the task.
      </p>

      <ul v-else class="space-y-2.5 max-h-72 overflow-y-auto pr-1">
        <li
          v-for="c in comments"
          :key="c.id"
          :data-comment="c.id"
          :data-kind="c.kind"
          class="rounded-lg border p-2.5"
          :class="c.kind === 'EVIDENCE'
            ? 'border-emerald-200 dark:border-emerald-900/50 bg-emerald-50 dark:bg-emerald-950/20'
            : 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/40'"
        >
          <div class="flex items-center gap-1.5 mb-1 text-[10px] font-mono text-slate-500 dark:text-slate-400">
            <ShieldCheck v-if="c.kind === 'EVIDENCE'" class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span class="font-semibold text-slate-700 dark:text-slate-300">{{ c.author?.full_name || 'Someone' }}</span>
            <span v-if="c.kind === 'EVIDENCE'" class="text-emerald-700 dark:text-emerald-400 font-semibold">evidence</span>
            <span>· {{ when(c.created_at) }}</span>
          </div>

          <p class="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-words">{{ c.content }}</p>

          <div v-if="c.attachments.length" class="mt-2 grid grid-cols-2 gap-2">
            <div v-for="a in c.attachments" :key="a.id" :data-attachment="a.id">
              <!-- Rendered inline where it can be: proof you have to download to
                   look at is proof nobody looks at. -->
              <img
                v-if="isImage(a.content_type)"
                :src="a.url"
                :alt="a.filename"
                class="w-full rounded border border-slate-200 dark:border-slate-800 object-cover max-h-40"
              />
              <video
                v-else-if="isVideo(a.content_type)"
                :src="a.url"
                controls
                preload="metadata"
                class="w-full rounded border border-slate-200 dark:border-slate-800 max-h-40"
              ></video>
              <a
                v-else
                :href="a.url"
                target="_blank"
                rel="noopener noreferrer"
                class="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 underline break-all"
              >{{ a.filename }}</a>
              <p class="text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate mt-0.5">
                {{ a.filename }} · {{ kb(a.size_bytes) }}
              </p>
            </div>
          </div>
        </li>
      </ul>

      <!-- Composer -->
      <div class="space-y-2 pt-1">
        <textarea
          id="comment-draft"
          v-model="draft"
          rows="2"
          placeholder="Add a note…"
          class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
        ></textarea>

        <ul v-if="files.length" class="space-y-1">
          <li
            v-for="(f, i) in files"
            :key="`${f.name}-${i}`"
            data-pending-file
            class="flex items-center justify-between gap-2 text-[11px] font-mono px-2 py-1 rounded bg-slate-100 dark:bg-slate-800"
          >
            <span class="truncate">{{ f.name }} · {{ kb(f.size) }}</span>
            <button type="button" class="p-0.5 text-slate-500 hover:text-rose-600 cursor-pointer" @click="removeFile(i)">
              <X class="w-3.5 h-3.5" />
            </button>
          </li>
        </ul>

        <div class="flex items-center justify-between gap-2">
          <label
            class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 text-[11px] font-mono text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
          >
            <Paperclip class="w-3.5 h-3.5" />
            <span>Attach</span>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept="image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm,video/quicktime"
              class="hidden"
              @change="pickFiles"
            />
          </label>

          <button
            type="button"
            :disabled="!canPost || isPosting"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-950 font-mono font-medium text-[11px] cursor-pointer disabled:opacity-40"
            @click="post('COMMENT')"
          >
            <Loader2 v-if="isPosting" class="w-3.5 h-3.5 animate-spin" />
            <Send v-else class="w-3.5 h-3.5" />
            <span>Post</span>
          </button>
        </div>
      </div>
    </template>
  </section>
</template>
