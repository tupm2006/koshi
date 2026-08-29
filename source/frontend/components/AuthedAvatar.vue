<script setup lang="ts">
/**
 * A profile picture fetched with the bearer token.
 *
 * Same reason as `AuthedMedia`: an `<img>` tag cannot send an `Authorization`
 * header, so an avatar served from `/api/users/{id}/avatar` renders broken
 * (F-45). Separate from `AuthedMedia` because an avatar is always an image and
 * always inherits the caller's shape and rounding — it takes a `class` from its
 * parent rather than imposing one.
 *
 * A cache shared across every instance, because the same faces appear on every
 * card of every board. Without it, a board with twenty tasks would fetch the
 * same three avatars twenty times.
 */
import { ref, watch, onBeforeUnmount } from 'vue';
import { api } from '../services/api';

const props = defineProps<{ src: string }>();

/**
 * src -> object URL. Deliberately never evicted: the entries are small, an
 * avatar URL carries a version segment so a changed picture is a different key,
 * and a tab does not live long enough for this to matter. The one cost is that
 * object URLs here are not revoked — which is why individual components must
 * not create their own.
 */
const cache = new Map<string, Promise<string>>();

const resolved = ref<string | null>(null);
const failed = ref(false);

function fetchAvatar(src: string): Promise<string> {
  let entry = cache.get(src);
  if (!entry) {
    entry = api.fetchBlob(src).then((blob) => URL.createObjectURL(blob));
    // A failure must not be cached, or one flaky request breaks the face for
    // the rest of the session.
    entry.catch(() => cache.delete(src));
    cache.set(src, entry);
  }
  return entry;
}

async function load(src: string) {
  resolved.value = null;
  failed.value = false;
  if (!src) return;

  const wanted = src;
  try {
    const url = await fetchAvatar(src);
    if (wanted === props.src) resolved.value = url;
  } catch {
    if (wanted === props.src) failed.value = true;
  }
}

watch(() => props.src, load, { immediate: true });

// No revoke: the URL belongs to the shared cache, not to this instance.
onBeforeUnmount(() => {
  resolved.value = null;
});
</script>

<template>
  <img v-if="resolved" :src="resolved" alt="" data-authed-avatar />
  <!-- Nothing on failure: the caller renders initials behind this, and a broken
       image icon is worse than the fallback it would sit on top of. -->
</template>
