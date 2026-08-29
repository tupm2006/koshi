<script setup lang="ts">
/**
 * An image or video whose bytes need a bearer token.
 *
 * `<img src="/api/...">` is a plain browser request: it carries cookies, but it
 * cannot carry an `Authorization` header. Every attachment and avatar therefore
 * rendered as a broken image, because the route answered 401 (F-45). The route
 * was never wrong — the tests and the manual checks all sent the header, and an
 * `<img>` tag is the one caller that cannot.
 *
 * So fetch it ourselves and hand the browser a `blob:` URL instead. The
 * alternatives were worse: putting the token in the query string writes it into
 * proxy and server logs, and switching these routes to cookie auth would mean
 * two authentication schemes in one API.
 *
 * The object URL is revoked when this component goes away or the source
 * changes. Without that, every scroll through a thread leaks a copy of every
 * image for the lifetime of the tab.
 */
import { ref, watch, onBeforeUnmount } from 'vue';
import { api } from '../services/api';

const props = withDefaults(
  defineProps<{
    src: string;
    alt?: string;
    kind?: 'image' | 'video';
  }>(),
  { alt: '', kind: 'image' },
);

const objectUrl = ref<string | null>(null);
const failed = ref(false);
const isLoading = ref(false);

function release() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value);
    objectUrl.value = null;
  }
}

async function load(src: string) {
  release();
  failed.value = false;
  if (!src) return;

  isLoading.value = true;
  // Captured so a slow response for a previous src cannot overwrite a newer
  // one — the thread re-renders whenever a comment is posted.
  const wanted = src;
  try {
    const blob = await api.fetchBlob(src);
    if (wanted !== props.src) {
      // Superseded while in flight; drop it rather than showing the wrong image.
      return;
    }
    objectUrl.value = URL.createObjectURL(blob);
  } catch {
    failed.value = true;
  } finally {
    if (wanted === props.src) isLoading.value = false;
  }
}

watch(() => props.src, load, { immediate: true });
onBeforeUnmount(release);
</script>

<template>
  <div
    v-if="isLoading"
    data-media-loading
    class="w-full h-24 rounded border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-800 animate-pulse"
  ></div>

  <p
    v-else-if="failed"
    data-media-failed
    class="text-[11px] font-mono text-slate-500 dark:text-slate-400 p-2 rounded border border-dashed border-slate-300 dark:border-slate-700"
  >
    Could not load this file.
  </p>

  <video
    v-else-if="kind === 'video' && objectUrl"
    :src="objectUrl"
    controls
    preload="metadata"
    class="w-full rounded border border-slate-200 dark:border-slate-800 max-h-40"
  ></video>

  <img
    v-else-if="objectUrl"
    :src="objectUrl"
    :alt="alt"
    class="w-full rounded border border-slate-200 dark:border-slate-800 object-cover max-h-40"
  />
</template>
