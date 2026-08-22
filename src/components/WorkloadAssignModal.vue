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
  <div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 animate-in fade-in duration-100">
    <div class="glass-panel w-full max-w-2xl rounded-2xl p-5 md:p-6 shadow-2xl border border-zinc-700/60 text-zinc-100 flex flex-col max-h-[88vh]">
      <!-- Header -->
      <div class="flex items-center justify-between pb-3 border-b border-zinc-800">
        <div class="flex items-center gap-2.5">
          <div class="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <Users class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-bold text-zinc-100 font-mono">Skill & Workload-Based Assignment Recommendation</h2>
            <p class="text-[11px] text-zinc-400">Mandated Feature C: Workload distribution & smart task routing</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-zinc-200 cursor-pointer" @click="onClose">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto py-4 space-y-4 text-xs">
        <!-- Team Capacity / Workload Grid -->
        <div>
          <h3 class="font-mono text-zinc-400 font-semibold mb-2 uppercase text-[10px] tracking-wider">Current Team Workload & Skills:</h3>
          <div v-if="isLoadingWorkload" class="py-4 text-center text-zinc-500 font-mono">Loading team profiles...</div>
          <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <div
              v-for="w in workloads"
              :key="w.user_id"
              class="p-3 rounded-xl bg-zinc-900 border flex flex-col gap-1.5"
              :class="w.is_overloaded ? 'border-rose-800/80 bg-rose-950/20' : 'border-zinc-800'"
            >
              <div class="flex items-center justify-between">
                <span class="font-bold text-zinc-200 font-mono text-xs">{{ w.full_name }}</span>
                <span v-if="w.is_overloaded" class="flex items-center gap-1 text-[10px] font-mono text-rose-400 font-semibold">
                  <AlertTriangle class="w-3 h-3" /> Overloaded
                </span>
                <span v-else class="flex items-center gap-1 text-[10px] font-mono text-emerald-400 font-medium">
                  <ShieldCheck class="w-3 h-3" /> Optimal
                </span>
              </div>
              <div class="flex items-center gap-3 text-zinc-400 font-mono text-[11px]">
                <span>Tasks: <strong class="text-zinc-200">{{ w.active_tasks_count }}</strong></span>
                <span>Complexity: <strong class="text-zinc-200">{{ w.total_complexity_points }} pts</strong></span>
              </div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="skill in w.skills" :key="skill" class="px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400 text-[10px] font-mono">
                  {{ skill }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Recommendation Inputs -->
        <div class="pt-2 border-t border-zinc-800 space-y-2.5">
          <h3 class="font-mono text-zinc-400 font-semibold uppercase text-[10px] tracking-wider">Test Task Assignment Recommendation:</h3>
          <div>
            <label for="vue-task-assign-title" class="block text-zinc-300 font-mono text-[11px] mb-1 font-medium">Task Title</label>
            <input
              id="vue-task-assign-title"
              v-model="taskTitle"
              type="text"
              class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-amber-500 font-sans"
            />
          </div>
          <div>
            <label for="vue-task-assign-desc" class="block text-zinc-300 font-mono text-[11px] mb-1 font-medium">Task Description & Requirements</label>
            <input
              id="vue-task-assign-desc"
              v-model="taskDesc"
              type="text"
              class="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-amber-500 font-sans"
            />
          </div>
          <button
            type="button"
            class="w-full py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-zinc-950 font-mono font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition disabled:opacity-50"
            @click="handleRecommend"
            :disabled="isLoadingRec || !taskTitle.trim()"
          >
            <RefreshCw v-if="isLoadingRec" class="w-4 h-4 animate-spin text-zinc-950" />
            <Sparkles v-else class="w-4 h-4 text-zinc-950" />
            <span>{{ isLoadingRec ? 'Evaluating Workloads & Skill Graph...' : 'Generate AI Recommendation' }}</span>
          </button>
        </div>

        <!-- Recommendation Result Box -->
        <div v-if="recommendation" class="p-3.5 rounded-xl bg-amber-950/20 border border-amber-800/50 space-y-2 animate-in fade-in">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <UserCheck class="w-4 h-4 text-amber-400" />
              <span class="font-mono text-zinc-400 text-[11px]">Recommended Assignee:</span>
              <strong class="text-amber-300 text-xs font-mono">{{ recommendation.recommended_name }}</strong>
            </div>
          </div>
          <p class="text-zinc-300 text-xs leading-relaxed">{{ recommendation.rationale }}</p>
          <div v-if="recommendation.risk_assessment" class="text-[11px] text-zinc-400 font-mono pt-1 border-t border-amber-900/30">
            <span class="text-amber-400/80">Risk Assessment:</span> {{ recommendation.risk_assessment }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
