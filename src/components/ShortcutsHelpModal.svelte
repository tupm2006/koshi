<script lang="ts">
  import { Keyboard, X, Smartphone, MousePointer } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onClose()} />

<div class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel glass-panel-glow w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[90vh] overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between pb-4 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-zinc-800 border border-zinc-700 text-zinc-200">
          <Keyboard class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-base font-bold text-zinc-100">Keyboard & Touch Ergonomics Guide</h2>
          <p class="text-xs text-zinc-400">Modal-less Vim velocity & mobile swipe gestures</p>
        </div>
      </div>
      <button class="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer min-h-[40px]" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto py-4 space-y-5 text-xs">
      <!-- Vim Shortcuts -->
      <div>
        <div class="flex items-center gap-2 font-mono uppercase text-indigo-400 font-semibold mb-2.5 text-[11px] tracking-wider">
          <Keyboard class="w-4 h-4" />
          <span>Vim / Linear Keyboard Navigation</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Navigate down / up</span>
            <div class="flex gap-1">
              <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">j</kbd>
              <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">k</kbd>
            </div>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Cycle status</span>
            <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">Space</kbd>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Inline rename title</span>
            <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">Enter</kbd>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Create new task</span>
            <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">c</kbd>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Delete selected task</span>
            <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">d</kbd>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Focus search filter</span>
            <kbd class="px-2 py-1 rounded bg-zinc-800 border border-zinc-700 font-mono text-[11px]">/</kbd>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">Set Priority (Low..Crit)</span>
            <div class="flex gap-1">
              <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px]">1</kbd>
              <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px]">2</kbd>
              <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px]">3</kbd>
              <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px]">4</kbd>
            </div>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 flex items-center justify-between">
            <span class="text-zinc-300">AI Decomposer / Git Diff</span>
            <div class="flex gap-1">
              <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px]">a</kbd>
              <kbd class="px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 font-mono text-[10px]">g</kbd>
            </div>
          </div>
        </div>
      </div>

      <!-- Mobile & Pointer -->
      <div>
        <div class="flex items-center gap-2 font-mono uppercase text-emerald-400 font-semibold mb-2.5 text-[11px] tracking-wider">
          <Smartphone class="w-4 h-4" />
          <span>Mobile Touch & Desktop Pointer Ergonomics</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
            <div class="font-semibold text-zinc-200">Swipe Right (> 80px)</div>
            <p class="text-zinc-400">Instantly marks task as <span class="text-emerald-400">DONE</span> with optimistic updates.</p>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
            <div class="font-semibold text-zinc-200">Swipe Left (> 80px)</div>
            <p class="text-zinc-400">Toggles <span class="text-amber-400">BLOCKED</span> state or quick delete.</p>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
            <div class="font-semibold text-zinc-200">Double Click Title</div>
            <p class="text-zinc-400">Enters inline non-blocking text editing mode.</p>
          </div>
          <div class="p-2.5 rounded-xl bg-zinc-900/60 border border-zinc-800 space-y-1">
            <div class="font-semibold text-zinc-200">Right Click (Context Menu)</div>
            <p class="text-zinc-400">1-click direct menu for status & priority changes without opening dialogs.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="pt-4 border-t border-zinc-800 flex justify-end">
      <button class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold cursor-pointer min-h-[44px]" onclick={onClose}>
        Got It
      </button>
    </div>
  </div>
</div>
