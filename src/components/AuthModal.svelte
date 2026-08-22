<script lang="ts">
  import { taskStore } from '../stores/taskStore.svelte';
  import { api } from '../services/api';
  import { Shield, X, User, LogIn, UserPlus, Check, AlertCircle } from 'lucide-svelte';

  interface Props {
    onClose: () => void;
  }

  let { onClose }: Props = $props();

  let mode = $state<'LOGIN' | 'REGISTER'>('LOGIN');
  let email = $state('pm@felixsu.qzz.io');
  let password = $state('koshi123');
  let fullName = $state('Felix Su');
  let role = $state<'PM' | 'MEMBER'>('PM');
  let skills = $state('architecture,fastapi,svelte');
  let errorMsg = $state<string | null>(null);
  let isSubmitting = $state(false);

  async function handleSubmit() {
    errorMsg = null;
    isSubmitting = true;
    try {
      if (mode === 'LOGIN') {
        const res = await api.login(email, password);
        taskStore.currentUser = res.user;
      } else {
        const res = await api.register(email, password, fullName, role);
        taskStore.currentUser = res.user;
      }
      await taskStore.syncWithBackend();
      onClose();
    } catch (e: any) {
      errorMsg = e.message || 'Authentication error';
    } finally {
      isSubmitting = false;
    }
  }

  function handleQuickSwitch(targetEmail: string) {
    email = targetEmail;
    password = 'koshi123';
    mode = 'LOGIN';
    handleSubmit();
  }
</script>

<div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
  <div class="glass-panel w-full max-w-md rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
          <Shield class="w-5 h-5" />
        </div>
        <div>
          <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">
            {mode === 'LOGIN' ? 'User Authentication' : 'Create Account'}
          </h2>
          <p class="text-[11px] text-zinc-400">Role-Based Access Control (RBAC)</p>
        </div>
      </div>
      <button class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" onclick={onClose}>
        <X class="w-5 h-5" />
      </button>
    </div>

    <!-- Quick Role Switch Pills for Testing -->
    <div class="py-2.5 flex items-center gap-2 border-b border-zinc-800 text-[11px] font-mono select-none">
      <span class="text-zinc-500">Quick Test Login:</span>
      <button
        type="button"
        class="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-indigo-300 cursor-pointer"
        onclick={() => handleQuickSwitch('pm@felixsu.qzz.io')}
      >
        PM
      </button>
      <button
        type="button"
        class="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-sky-300 cursor-pointer"
        onclick={() => handleQuickSwitch('dev@felixsu.qzz.io')}
      >
        Member
      </button>
    </div>

    <!-- Form Body -->
    <form class="py-3 space-y-3 text-xs" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
      {#if mode === 'REGISTER'}
        <div>
          <label for="reg-fullname" class="block font-mono text-zinc-300 mb-1">Full Name</label>
          <input
            id="reg-fullname"
            type="text"
            bind:value={fullName}
            required
            class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500 font-sans"
          />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <label for="reg-role" class="block font-mono text-zinc-300 mb-1">Role</label>
            <select
              id="reg-role"
              bind:value={role}
              class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="PM">Project Manager (PM)</option>
              <option value="MEMBER">Team Member</option>
            </select>
          </div>
          <div>
            <label for="reg-skills" class="block font-mono text-zinc-300 mb-1">Skills</label>
            <input
              id="reg-skills"
              type="text"
              bind:value={skills}
              placeholder="e.g. python,sql"
              class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500 font-sans"
            />
          </div>
        </div>
      {/if}

      <div>
        <label for="auth-email" class="block font-mono text-zinc-300 mb-1">Email Address</label>
        <input
          id="auth-email"
          type="email"
          bind:value={email}
          required
          class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500 font-mono"
        />
      </div>

      <div>
        <label for="auth-password" class="block font-mono text-zinc-300 mb-1">Password</label>
        <input
          id="auth-password"
          type="password"
          bind:value={password}
          required
          class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-indigo-500 font-mono"
        />
      </div>

      {#if errorMsg}
        <div class="p-2.5 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 flex items-center gap-1.5 font-mono text-[11px]">
          <AlertCircle class="w-3.5 h-3.5 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      {/if}

      <button
        type="submit"
        class="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono font-medium text-xs flex items-center justify-center gap-1.5 cursor-pointer transition disabled:opacity-50"
        disabled={isSubmitting}
      >
        {#if mode === 'LOGIN'}
          <LogIn class="w-3.5 h-3.5" />
          <span>{isSubmitting ? 'Authenticating...' : 'Sign In'}</span>
        {:else}
          <UserPlus class="w-3.5 h-3.5" />
          <span>{isSubmitting ? 'Registering...' : 'Create Account'}</span>
        {/if}
      </button>

      <div class="pt-2 text-center">
        <button
          type="button"
          class="text-zinc-400 hover:text-zinc-200 text-[11px] font-mono underline cursor-pointer"
          onclick={() => { mode = mode === 'LOGIN' ? 'REGISTER' : 'LOGIN'; errorMsg = null; }}
        >
          {mode === 'LOGIN' ? "Don't have an account? Register" : "Already registered? Sign In"}
        </button>
      </div>
    </form>
  </div>
</div>
