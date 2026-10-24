<script setup lang="ts">
import { Keyboard, X } from 'lucide-vue-next';
import type { TranslationKey } from '../lib/translations';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const SHORTCUTS = [
  { key: 'b', desc: 'sc.b' as TranslationKey },
  { key: 'h / j / k / l', desc: 'sc.hjkl' as TranslationKey },
  { key: 'H / L', desc: 'sc.HL' as TranslationKey },
  { key: 'Space', desc: 'sc.space' as TranslationKey },
  { key: 'Enter', desc: 'sc.enter' as TranslationKey },
  { key: 'i', desc: 'sc.i' as TranslationKey },
  { key: 'n', desc: 'sc.n' as TranslationKey },
  { key: 'd / Backspace', desc: 'sc.d' as TranslationKey },
  { key: '1, 2, 3, 4', desc: 'sc.1234' as TranslationKey },
  { key: '/', desc: 'sc.slash' as TranslationKey },
  { key: 'a', desc: 'sc.a' as TranslationKey },
  { key: 'g', desc: 'sc.g' as TranslationKey },
  { key: 'v', desc: 'sc.v' as TranslationKey },
  { key: 't', desc: 'sc.t' as TranslationKey },
  { key: '?', desc: 'sc.q' as TranslationKey },
  { key: 'Esc', desc: 'sc.esc' as TranslationKey },
];
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6"
    @click.self="emit('close')"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-lg rounded-lg p-5 md:p-6 shadow-2xl border border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200">
            <Keyboard class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold text-slate-900 dark:text-slate-100 font-sans">{{ $t('sc.title') }}</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">{{ $t('sc.subtitle') }}</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="emit('close')">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="py-4 space-y-2 text-xs divide-y divide-slate-100 dark:divide-slate-800/60 max-h-[60vh] overflow-y-auto">
        <div
          v-for="s in SHORTCUTS"
          :key="s.key"
          class="pt-2 flex items-center justify-between font-mono"
        >
          <kbd class="h-6 px-2 inline-flex items-center justify-center rounded-md bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-200 text-[11px] font-bold">
            {{ s.key }}
          </kbd>
          <span class="text-slate-600 dark:text-slate-400 font-sans text-xs">{{ $t(s.desc) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
