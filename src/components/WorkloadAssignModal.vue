<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api } from '../services/api';
import { Users, X, Sparkles, UserCheck, AlertTriangle, ShieldCheck, RefreshCw } from 'lucide-vue-next';

defineProps<{
  onClose: () => void;
}>();

const taskTitle = ref<string>('Implement Redis Distributed Caching Layer');
const taskDesc = ref<string>('Configure Redis cluster with cache invalidation rules and hit-rate telemetry.');
const workloads = ref<any[]>([]);
const recommendation = ref<any | null>(null);
const isLoadingRec = ref<boolean>(false);
const isLoadingWorkload = ref<boolean>(true);

async function loadWorkloads() {
  isLoadingWorkload.value = true;
  try {
    workloads.value = await api.getWorkloads();
  } catch (e) {
    console.error(e);
  } finally {
    isLoadingWorkload.value = false;
  }
}

async function handleRecommend() {
  if (!taskTitle.value.trim()) return;
  isLoadingRec.value = true;
  try {
    const res = await api.recommendAssignment(taskTitle.value, taskDesc.value, 1);
    recommendation.value = res.recommendation;
  } catch (e) {
    console.error(e);
  } finally {
    isLoadingRec.value = false;
  }
}

onMounted(() => {
  loadWorkloads();
  handleRecommend();
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100"
    @click.self="onClose"
  >
    <div class="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-lg p-5 md:p-6 shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col max-h-[88vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 text-amber-600 dark:text-amber-400">
            <Users class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-slate-900 dark:text-slate-100 font-mono">Workload & Smart Assignment</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">Team capacity analysis and assignment recommendations</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer" @click="onClose">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
        <!-- Team Capacity / Workload Grid -->
        <div>
          <h3 class="font-mono text-slate-500 dark:text-slate-400 font-semibold mb-2 uppercase text-[10px] tracking-wider">Current Team Workload & Skills:</h3>
          <div v-if="isLoadingWorkload" class="py-4 text-center text-slate-500 dark:text-slate-500 font-mono">Loading team profiles...</div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div
              v-for="w in workloads"
              :key="w.user_id"
              class="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border flex flex-col gap-1.5"
              :class="w.is_overloaded ? 'border-rose-300 dark:border-rose-800/80 bg-rose-50 dark:bg-rose-950/20' : 'border-slate-200 dark:border-slate-800'"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-slate-800 dark:text-slate-200 font-mono text-xs">{{ w.full_name }}</span>
                <span v-if="w.is_overloaded" class="flex items-center gap-1 text-[10px] font-mono text-rose-600 dark:text-rose-400 font-semibold">
                  <AlertTriangle class="w-3 h-3" /> Overloaded
                </span>
                <span v-else class="flex items-center gap-1 text-[10px] font-mono text-emerald-600 dark:text-emerald-400 font-medium">
                  <ShieldCheck class="w-3 h-3" /> Optimal
                </span>
              </div>
              <div class="flex items-center gap-3 text-slate-600 dark:text-slate-400 font-mono text-[11px]">
                <span>Tasks: <strong class="text-slate-900 dark:text-slate-200">{{ w.active_tasks_count }}</strong></span>
                <span>Complexity: <strong class="text-slate-900 dark:text-slate-200">{{ w.total_complexity_points }} pts</strong></span>
              </div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="skill in w.skills" :key="skill" class="px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 text-[10px] font-mono">
                  {{ skill }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Recommendation Inputs -->
        <div class="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2.5">
          <h3 class="font-mono text-slate-500 dark:text-slate-400 font-semibold uppercase text-[10px] tracking-wider">Test Task Assignment Recommendation:</h3>
          <div>
            <label for="vue-task-assign-title" class="block text-slate-700 dark:text-slate-300 font-mono text-[11px] mb-1 font-medium">Task Title</label>
            <input
              id="vue-task-assign-title"
              v-model="taskTitle"
              type="text"
              class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-amber-500 font-sans"
            />
          </div>
          <div>
            <label for="vue-task-assign-desc" class="block text-slate-700 dark:text-slate-300 font-mono text-[11px] mb-1 font-medium">Task Description & Requirements</label>
            <input
              id="vue-task-assign-desc"
              v-model="taskDesc"
              type="text"
              class="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-amber-500 font-sans"
            />
          </div>
          <button
            type="button"
            class="h-8 w-full rounded-md bg-amber-600 hover:bg-amber-500 text-white font-mono font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition disabled:opacity-50"
            :disabled="isLoadingRec || !taskTitle.trim()"
            @click="handleRecommend"
          >
            <RefreshCw v-if="isLoadingRec" class="w-3.5 h-3.5 animate-spin" />
            <Sparkles v-else class="w-3.5 h-3.5" />
            <span>{{ isLoadingRec ? 'Analyzing Skills & Capacity...' : 'Recommend Assignee' }}</span>
          </button>
        </div>

        <!-- Recommendation Result Box -->
        <div v-if="recommendation" class="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/50 space-y-2 animate-in fade-in">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UserCheck class="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span class="font-mono text-slate-600 dark:text-slate-400 text-[11px]">Recommended Assignee:</span>
              <strong class="text-amber-700 dark:text-amber-300 text-xs font-mono">{{ recommendation.recommended_name }}</strong>
            </div>
          </div>
          <p class="text-slate-700 dark:text-slate-300 text-xs leading-relaxed">{{ recommendation.rationale }}</p>
          <div v-if="recommendation.risk_assessment" class="text-[11px] text-slate-500 dark:text-slate-400 font-mono pt-1 border-t border-amber-200 dark:border-amber-900/30">
            <span class="text-amber-700 dark:text-amber-400/80 font-medium">Risk Assessment:</span> {{ recommendation.risk_assessment }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
