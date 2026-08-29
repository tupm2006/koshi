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
import { ref, watch, computed, nextTick } from 'vue';
import { api, type TaskComment } from '../services/api';
import { useTaskStore } from '../stores/taskStore';
import { serverIdOf } from '../services/api';
import { MessageSquare, Send, Paperclip, X, ShieldCheck, Loader2, CornerDownRight, AtSign } from 'lucide-vue-next';
import { parseSegments, mentionToken, activeMentionQuery, matchMembers } from '../lib/mentions';
import AuthedMedia from './AuthedMedia.vue';

const props = defineProps<{ taskId: string }>();

const taskStore = useTaskStore();

const comments = ref<TaskComment[]>([]);
const draft = ref('');
const files = ref<File[]>([]);
const isLoading = ref(false);
const isPosting = ref(false);
const errorMsg = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const draftBox = ref<HTMLTextAreaElement | null>(null);

/** Comment being replied to, or null for a new top-level entry. */
const replyTo = ref<TaskComment | null>(null);

// --- @mention autocomplete ------------------------------------------------
// Driven off the caret rather than a keystroke, so it behaves the same whether
// the user typed `@`, pasted it, or moved back into an existing one.
const mentionQuery = ref<{ query: string; from: number } | null>(null);
const mentionIndex = ref(0);

const mentionMatches = computed(() =>
  mentionQuery.value === null ? [] : matchMembers(taskStore.members, mentionQuery.value.query),
);

function syncMentionQuery() {
  const box = draftBox.value;
  if (!box) return;
  mentionQuery.value = activeMentionQuery(draft.value, box.selectionStart ?? draft.value.length);
  mentionIndex.value = 0;
}

async function choose(member: { user_id: number; full_name: string }) {
  const active = mentionQuery.value;
  if (!active) return;

  const box = draftBox.value;
  const caret = box?.selectionStart ?? draft.value.length;
  const token = mentionToken(member.user_id, member.full_name);

  // Replace only the `@query` run, keeping anything the user had typed after
  // the caret — they may be editing the middle of a sentence.
  draft.value = draft.value.slice(0, active.from) + token + ' ' + draft.value.slice(caret);
  mentionQuery.value = null;

  await nextTick();
  const at = active.from + token.length + 1;
  box?.focus();
  box?.setSelectionRange(at, at);
}

/**
 * Keys the menu owns while it is open.
 *
 * Returns nothing; it simply stops the event when it acts, so Enter picking a
 * person does not also insert a newline.
 */
function onDraftKeydown(e: KeyboardEvent) {
  if (mentionQuery.value === null || mentionMatches.value.length === 0) return;

  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    const n = mentionMatches.value.length;
    mentionIndex.value = (mentionIndex.value + (e.key === 'ArrowDown' ? 1 : n - 1)) % n;
  } else if (e.key === 'Enter' || e.key === 'Tab') {
    e.preventDefault();
    choose(mentionMatches.value[mentionIndex.value]!);
  } else if (e.key === 'Escape') {
    // Close the menu without closing the modal around it.
    e.preventDefault();
    e.stopPropagation();
    mentionQuery.value = null;
  }
}

/**
 * Close the menu when focus leaves the box.
 *
 * The menu items use `@mousedown.prevent`, so clicking one never blurs the
 * textarea and this does not race with a pick. It exists for the other exits —
 * tabbing away, clicking elsewhere on the page.
 */
function onDraftBlur() {
  mentionQuery.value = null;
}

/** Top-level comments, each with its replies attached. */
const threaded = computed(() => {
  const tops = comments.value.filter((c) => c.parent_id === null);
  return tops.map((c) => ({
    comment: c,
    replies: comments.value.filter((r) => r.parent_id === c.id),
  }));
});

function startReply(c: TaskComment) {
  replyTo.value = c;
  nextTick(() => draftBox.value?.focus());
}

/** Render a mention with the person's *current* name where we know it. */
function mentionLabel(userId: number, captured: string) {
  return taskStore.members.find((m) => m.user_id === userId)?.full_name ?? captured;
}

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

/**
 * Ctrl+V.
 *
 * Text is left entirely alone — the browser's own paste is correct, respects
 * the caret and the undo stack, and intercepting it would only make it worse.
 * Files are the part the browser cannot handle here: a screenshot on the
 * clipboard has no filename, so it is named from the timestamp and queued
 * exactly like one chosen through Attach.
 *
 * `preventDefault` fires only when a file was actually taken, so pasting an
 * image copied out of a rich-text editor still inserts its accompanying text.
 */
function onPaste(e: ClipboardEvent) {
  const items = Array.from(e.clipboardData?.items ?? []);
  const pasted = items
    .filter((it) => it.kind === 'file')
    .map((it) => it.getAsFile())
    .filter((f): f is File => f !== null);

  if (pasted.length === 0) return;  // plain text: let the browser do it

  e.preventDefault();
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  files.value = [
    ...files.value,
    ...pasted.map((f, i) => {
      // A pasted screenshot arrives as "image.png" or with no name at all;
      // several in a row would be indistinguishable in the pending list.
      const ext = (f.type.split('/')[1] || 'png').replace('jpeg', 'jpg');
      const name = f.name && f.name !== 'image.png'
        ? f.name
        : `pasted-${stamp}${pasted.length > 1 ? `-${i + 1}` : ''}.${ext}`;
      return new File([f], name, { type: f.type });
    }),
  ];
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
      replyTo.value?.id ?? null,
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
    replyTo.value = null;
    mentionQuery.value = null;
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

      <ul v-else class="space-y-2.5 max-h-80 overflow-y-auto pr-1">
        <li v-for="node in threaded" :key="node.comment.id" :data-thread="node.comment.id">
          <!-- Parent -->
          <div
            :data-comment="node.comment.id"
            :data-kind="node.comment.kind"
            class="rounded-lg border p-2.5"
            :class="node.comment.kind === 'EVIDENCE'
              ? 'border-emerald-200 dark:border-emerald-900/50 bg-emerald-50 dark:bg-emerald-950/20'
              : 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/40'"
          >
            <div class="flex items-center gap-1.5 mb-1 text-[10px] font-mono text-slate-500 dark:text-slate-400">
              <ShieldCheck v-if="node.comment.kind === 'EVIDENCE'" class="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span class="font-semibold text-slate-700 dark:text-slate-300">{{ node.comment.author?.full_name || 'Someone' }}</span>
              <span v-if="node.comment.kind === 'EVIDENCE'" class="text-emerald-700 dark:text-emerald-400 font-semibold">evidence</span>
              <span>· {{ when(node.comment.created_at) }}</span>
            </div>

            <!-- Segments, never v-html: a comment body must not be able to
                 become markup. -->
            <p class="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-words">
              <template v-for="(seg, i) in parseSegments(node.comment.content)" :key="i">
                <span
                  v-if="seg.type === 'mention'"
                  :data-mention="seg.userId"
                  class="px-1 rounded font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-300"
                >@{{ mentionLabel(seg.userId, seg.label) }}</span>
                <template v-else>{{ seg.value }}</template>
              </template>
            </p>

            <div v-if="node.comment.attachments.length" class="mt-2 grid grid-cols-2 gap-2">
              <div v-for="a in node.comment.attachments" :key="a.id" :data-attachment="a.id">
                <AuthedMedia
                  v-if="isImage(a.content_type) || isVideo(a.content_type)"
                  :src="a.url"
                  :alt="a.filename"
                  :kind="isVideo(a.content_type) ? 'video' : 'image'"
                />
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

            <button
              type="button"
              :data-reply-to="node.comment.id"
              class="mt-1.5 inline-flex items-center gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer"
              @click="startReply(node.comment)"
            >
              <CornerDownRight class="w-3 h-3" />
              <span>Reply</span>
            </button>
          </div>

          <!-- Replies. Indented once and never further: a deeper tree is
               unreadable in a panel this narrow, and the server flattens
               anyway. -->
          <div v-if="node.replies.length" class="mt-1.5 ml-4 pl-2.5 border-l-2 border-slate-200 dark:border-slate-800 space-y-1.5">
            <div
              v-for="r in node.replies"
              :key="r.id"
              :data-comment="r.id"
              :data-reply="true"
              class="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-2"
            >
              <div class="flex items-center gap-1.5 mb-0.5 text-[10px] font-mono text-slate-500 dark:text-slate-400">
                <span class="font-semibold text-slate-700 dark:text-slate-300">{{ r.author?.full_name || 'Someone' }}</span>
                <span>· {{ when(r.created_at) }}</span>
              </div>
              <p class="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-words">
                <template v-for="(seg, i) in parseSegments(r.content)" :key="i">
                  <span
                    v-if="seg.type === 'mention'"
                    :data-mention="seg.userId"
                    class="px-1 rounded font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-300"
                  >@{{ mentionLabel(seg.userId, seg.label) }}</span>
                  <template v-else>{{ seg.value }}</template>
                </template>
              </p>
              <div v-if="r.attachments.length" class="mt-1.5 grid grid-cols-2 gap-2">
                <div v-for="a in r.attachments" :key="a.id" :data-attachment="a.id">
                  <AuthedMedia
                    v-if="isImage(a.content_type) || isVideo(a.content_type)"
                    :src="a.url"
                    :alt="a.filename"
                    :kind="isVideo(a.content_type) ? 'video' : 'image'"
                  />
                  <a v-else :href="a.url" target="_blank" rel="noopener noreferrer" class="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 underline break-all">{{ a.filename }}</a>
                </div>
              </div>
              <button
                type="button"
                :data-reply-to="r.id"
                class="mt-1 inline-flex items-center gap-1 text-[10px] font-mono text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer"
                @click="startReply(r)"
              >
                <CornerDownRight class="w-3 h-3" />
                <span>Reply</span>
              </button>
            </div>
          </div>
        </li>
      </ul>

      <!-- Composer -->
      <div class="space-y-2 pt-1">
        <div
          v-if="replyTo"
          id="reply-banner"
          class="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/30 text-[11px] font-mono"
        >
          <span class="truncate text-indigo-800 dark:text-indigo-300">
            Replying to {{ replyTo.author?.full_name || 'someone' }}: “{{ replyTo.content.slice(0, 40) }}{{ replyTo.content.length > 40 ? '…' : '' }}”
          </span>
          <button
            type="button"
            id="reply-cancel"
            aria-label="Cancel reply"
            class="p-0.5 text-indigo-500 hover:text-rose-600 cursor-pointer shrink-0"
            @click="replyTo = null"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>

        <div class="relative">
          <textarea
            id="comment-draft"
            ref="draftBox"
            v-model="draft"
            rows="2"
            :placeholder="replyTo ? 'Write a reply… use @ to tag someone' : 'Add a note… use @ to tag someone'"
            class="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
            @input="syncMentionQuery"
            @click="syncMentionQuery"
            @keyup="syncMentionQuery"
            @keydown="onDraftKeydown"
            @paste="onPaste"
            @blur="onDraftBlur"
          ></textarea>

          <!-- Anchored above the box: the composer sits at the bottom of a
               scrolling panel, so a menu below it would be clipped. -->
          <ul
            v-if="mentionQuery !== null && mentionMatches.length > 0"
            id="mention-menu"
            class="absolute bottom-full left-0 mb-1 z-10 w-64 max-h-48 overflow-y-auto rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg py-1"
          >
            <li
              v-for="(m, i) in mentionMatches"
              :key="m.user_id"
              :data-mention-option="m.user_id"
              :data-active="i === mentionIndex"
              class="px-2.5 py-1.5 cursor-pointer flex items-center gap-2"
              :class="i === mentionIndex ? 'bg-indigo-50 dark:bg-indigo-500/15' : 'hover:bg-slate-50 dark:hover:bg-slate-800'"
              @mousedown.prevent="choose(m)"
              @mouseenter="mentionIndex = i"
            >
              <AtSign class="w-3 h-3 text-slate-400 shrink-0" />
              <span class="min-w-0">
                <span class="block text-xs font-medium truncate">{{ m.full_name }}</span>
                <span class="block text-[10px] font-mono text-slate-500 dark:text-slate-400 truncate">{{ m.email }}</span>
              </span>
            </li>
          </ul>
        </div>

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
            <span class="text-slate-400 dark:text-slate-500">or paste</span>
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
