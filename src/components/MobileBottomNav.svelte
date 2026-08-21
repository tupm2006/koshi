<script lang="ts">
  import { Plus, Search, Sparkles, GitFork, GitPullRequest } from 'lucide-svelte';

  interface Props {
    onOpenCreate: () => void;
    onOpenAIDecomposer: () => void;
    onOpenDAG: () => void;
    onOpenGitDiff: () => void;
    onFocusSearch: () => void;
  }

  let { onOpenCreate, onOpenAIDecomposer, onOpenDAG, onOpenGitDiff, onFocusSearch }: Props = $props();
</script>

<!-- Bottom Floating Thumb Bar for Mobile (< md breakpoint) -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-zinc-950/95 border-t border-zinc-800/80 backdrop-blur-xl safe-bottom px-3 py-1.5 shadow-2xl">
  <!-- Main Thumb Controls Grid -->
  <div class="grid grid-cols-5 items-center gap-1">
    <button
      type="button"
      class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 active:bg-zinc-800 transition min-h-[44px] cursor-pointer"
      onclick={onFocusSearch}
      title="Search (/)"
    >
      <Search class="w-4 h-4" />
      <span class="text-[9px] mt-0.5 font-mono">Search</span>
    </button>

    <button
      type="button"
      class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 active:bg-zinc-800 transition min-h-[44px] cursor-pointer"
      onclick={onOpenAIDecomposer}
      title="AI Decomposer (a)"
    >
      <Sparkles class="w-4 h-4" />
      <span class="text-[9px] mt-0.5 font-mono">AI</span>
    </button>

    <!-- Prominent + Create Button in center thumb zone -->
    <div class="flex items-center justify-center">
      <button
        type="button"
        class="w-10 h-10 rounded-xl bg-zinc-100 hover:bg-white text-zinc-950 flex items-center justify-center font-bold cursor-pointer active:scale-95 transition shadow-sm"
        onclick={onOpenCreate}
        title="Create Task (c)"
      >
        <Plus class="w-5 h-5 stroke-[2.5]" />
      </button>
    </div>

    <button
      type="button"
      class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 active:bg-zinc-800 transition min-h-[44px] cursor-pointer"
      onclick={onOpenDAG}
      title="DAG Critical Path (v)"
    >
      <GitFork class="w-4 h-4" />
      <span class="text-[9px] mt-0.5 font-mono">DAG</span>
    </button>

    <button
      type="button"
      class="flex flex-col items-center justify-center p-1.5 rounded-lg hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 active:bg-zinc-800 transition min-h-[44px] cursor-pointer"
      onclick={onOpenGitDiff}
      title="Git Diff (g)"
    >
      <GitPullRequest class="w-4 h-4" />
      <span class="text-[9px] mt-0.5 font-mono">Diff</span>
    </button>
  </div>
</nav>
