<script setup lang="ts">
/**
 * The small overlapping faces on a task card.
 *
 * Initials rather than a generic silhouette: a placeholder that is the same for
 * everybody tells you a task is assigned but not to whom, which is the only
 * thing the avatar is there to say.
 *
 * Colour is derived from the user id, so the same person is always the same
 * colour on every card — the point is recognition at a glance, and a random or
 * name-hashed colour would move when somebody is renamed.
 */
import { computed } from 'vue';
import type { TaskAssignee } from '../types/task';
import AuthedAvatar from './AuthedAvatar.vue';

const props = withDefaults(
  defineProps<{
    assignees?: TaskAssignee[];
    /** Beyond this, the rest collapse into a "+N". */
    max?: number;
    size?: 'xs' | 'sm';
  }>(),
  { assignees: () => [], max: 3, size: 'sm' },
);

/**
 * Fixed palette rather than a computed hue: these have to stay legible against
 * both themes, and generated colours do not.
 */
const PALETTE = [
  'bg-indigo-500', 'bg-emerald-600', 'bg-amber-600', 'bg-rose-500',
  'bg-sky-600', 'bg-violet-500', 'bg-teal-600', 'bg-orange-600',
];

const shown = computed(() => props.assignees.slice(0, props.max));
const overflow = computed(() => Math.max(0, props.assignees.length - props.max));

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  // First and last: "Phạm Minh Tú" reads better as PT than PM, and a single
  // name still gives one letter rather than an empty badge.
  const first = parts[0]![0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1]![0] ?? '' : '';
  return (first + last).toUpperCase();
}

const colourOf = (id: number) => PALETTE[Math.abs(id) % PALETTE.length];

const dims = computed(() =>
  props.size === 'xs' ? 'w-4 h-4 text-[8px]' : 'w-5 h-5 text-[9px]',
);
</script>

<template>
  <div v-if="assignees.length > 0" class="flex items-center -space-x-1.5" data-assignees>
    <span
      v-for="a in shown"
      :key="a.id"
      :data-assignee="a.id"
      :title="a.full_name"
      class="relative inline-flex items-center justify-center rounded-full ring-1 ring-white dark:ring-slate-900 overflow-hidden shrink-0"
      :class="[dims, a.avatar_url ? '' : colourOf(a.id)]"
    >
      <!-- Initials sit underneath: if the picture fails to load, the badge
           still says who this is rather than showing a broken-image icon. -->
      <span class="absolute inset-0 flex items-center justify-center font-bold text-white leading-none select-none">
        {{ initials(a.full_name) }}
      </span>
      <AuthedAvatar
        v-if="a.avatar_url"
        :src="a.avatar_url"
        class="relative w-full h-full object-cover"
      />
    </span>

    <span
      v-if="overflow > 0"
      :title="assignees.slice(max).map((a) => a.full_name).join(', ')"
      class="inline-flex items-center justify-center rounded-full ring-1 ring-white dark:ring-slate-900 bg-slate-400 dark:bg-slate-600 font-bold text-white shrink-0 select-none"
      :class="dims"
    >+{{ overflow }}</span>
  </div>
</template>
