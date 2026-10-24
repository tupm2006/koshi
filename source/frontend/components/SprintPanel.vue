<script setup lang="ts">
/**
 * Scrum panel (DEC-028): sprint lifecycle, backlog planning, burndown, velocity.
 *
 * Talks to the API directly rather than through the task store: sprint
 * membership is server state the board does not need, and keeping it out of
 * `types/task.ts` avoids an IndexedDB key bump. After any planning change the
 * board is re-synced so it never shows stale data.
 *
 * PM-only controls are hidden for members, but the server is the boundary —
 * every lifecycle route calls require_project_pm.
 */
import { ref, computed, onMounted, watch } from 'vue';
import { api, type Sprint, type Burndown, type VelocityEntry, type SprintRetro } from '../services/api';
import { useTaskStore } from '../stores/taskStore';
import { useI18nStore } from '../stores/i18nStore';
import { X, Play, CheckCircle2, Trash2, Plus, ArrowRight, ArrowLeft, Timer, AlertCircle, Sparkles } from 'lucide-vue-next';

const emit = defineEmits<{ (e: 'close'): void }>();
const taskStore = useTaskStore();
const i18n = useI18nStore();
const t = computed(() => i18n.t);

type Tab = 'SPRINTS' | 'PLANNING' | 'BURNDOWN' | 'VELOCITY' | 'RETRO';
const tab = ref<Tab>('SPRINTS');
const sprints = ref<Sprint[]>([]);
const serverTasks = ref<any[]>([]);
const selectedSprintId = ref<number | null>(null);
const burndown = ref<Burndown | null>(null);
const velocity = ref<VelocityEntry[]>([]);
const errorMsg = ref<string | null>(null);
const busy = ref(false);
const moveTarget = ref<number | null>(null);
const retro = ref<SprintRetro | null>(null);
const retroLoading = ref(false);

// Any member may ask for a retrospective: it reads, it writes nothing.
async function runRetro() {
  if (selectedSprintId.value === null) return;
  retro.value = null;
  retroLoading.value = true;
  const r = await run(() => api.sprintRetro(selectedSprintId.value!));
  retroLoading.value = false;
  if (r) retro.value = r;
}

const today = new Date();
const iso = (d: Date) => d.toISOString().slice(0, 10);
const form = ref({ name: '', goal: '', start: iso(today), end: iso(new Date(today.getTime() + 13 * 864e5)) });

const projectId = computed(() => taskStore.currentProjectId);
const isPM = computed(() => taskStore.isProjectManager);
const canEdit = computed(() => isPM.value && taskStore.canMutate);

const selectedSprint = computed(() => sprints.value.find((s) => s.id === selectedSprintId.value) ?? null);
const backlog = computed(() => serverTasks.value.filter((x) => x.sprint_id === null && x.status !== 'DONE'));
const sprintItems = computed(() => serverTasks.value.filter((x) => x.sprint_id === selectedSprintId.value));
const pts = (list: any[]) => list.reduce((n, x) => n + (x.complexity_points || 0), 0);
const openTargets = computed(() => sprints.value.filter((s) => s.state === 'PLANNED' && s.id !== selectedSprintId.value));

async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
  errorMsg.value = null;
  busy.value = true;
  try {
    return await fn();
  } catch (e: any) {
    errorMsg.value = e?.message || String(e);
  } finally {
    busy.value = false;
  }
}

async function load() {
  if (projectId.value === null) return;
  await run(async () => {
    const [s, tasks, v] = await Promise.all([
      api.listSprints(projectId.value!),
      api.getTasks(projectId.value!),
      api.getVelocity(projectId.value!),
    ]);
    sprints.value = s.sort((a, b) => a.start_date.localeCompare(b.start_date));
    serverTasks.value = tasks;
    velocity.value = v;
    if (selectedSprintId.value === null || !s.some((x) => x.id === selectedSprintId.value)) {
      selectedSprintId.value = (s.find((x) => x.state === 'ACTIVE') ?? s.find((x) => x.state === 'PLANNED') ?? s[0])?.id ?? null;
    }
  });
  await loadBurndown();
}

async function loadBurndown() {
  burndown.value = null;
  if (selectedSprintId.value === null) return;
  const b = await run(() => api.getBurndown(selectedSprintId.value!));
  if (b) burndown.value = b;
}

watch(selectedSprintId, loadBurndown);

async function createSprint() {
  if (!form.value.name.trim() || projectId.value === null) return;
  const s = await run(() => api.createSprint({
    project_id: projectId.value!,
    name: form.value.name.trim(),
    goal: form.value.goal.trim(),
    start_date: new Date(form.value.start).toISOString(),
    end_date: new Date(form.value.end).toISOString(),
  }));
  if (s) {
    form.value.name = '';
    form.value.goal = '';
    selectedSprintId.value = s.id;
    await load();
  }
}

async function startSprint(id: number) {
  if (await run(() => api.startSprint(id))) await load();
}

async function completeSprint(id: number) {
  if (await run(() => api.completeSprint(id, moveTarget.value))) {
    moveTarget.value = null;
    await load();
    await taskStore.syncWithBackend(projectId.value!);
  }
}

async function deleteSprint(id: number) {
  if ((await run(() => api.deleteSprint(id))) !== undefined) await load();
}

async function plan(taskId: number, sprintId: number | null) {
  if (!canEdit.value) return;
  if (await run(() => api.setTaskSprint(taskId, sprintId))) {
    await load();
    await taskStore.syncWithBackend(projectId.value!);
  }
}

// --- burndown chart geometry (inline SVG, no chart library) ---
const W = 560;
const H = 220;
const P = 32;
const chart = computed(() => {
  const b = burndown.value;
  if (!b || b.days.length === 0) return null;
  const max = Math.max(b.total_points, 1);
  const n = Math.max(b.days.length - 1, 1);
  const x = (i: number) => P + (i / n) * (W - 2 * P);
  const y = (v: number) => H - P - (v / max) * (H - 2 * P);
  const ideal = b.days.map((d, i) => `${x(i)},${y(d.ideal)}`).join(' ');
  const actualPts = b.days.map((d, i) => (d.remaining === null ? null : { x: x(i), y: y(d.remaining), v: d.remaining })).filter(Boolean) as { x: number; y: number; v: number }[];
  const actual = actualPts.map((p) => `${p.x},${p.y}`).join(' ');
  const labels = b.days.map((d, i) => ({ x: x(i), text: d.date.slice(5) })).filter((_, i, arr) => arr.length <= 8 || i % Math.ceil(arr.length / 8) === 0 || i === arr.length - 1);
  return { ideal, actual, actualPts, labels, max, y };
});

const velocityMax = computed(() => Math.max(1, ...velocity.value.map((v) => Math.max(v.committed_points, v.completed_points))));
const velocityAvg = computed(() => velocity.value.length ? Math.round(velocity.value.reduce((n, v) => n + v.completed_points, 0) / velocity.value.length * 10) / 10 : 0);

const stateClass: Record<string, string> = {
  PLANNED: 'bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  ACTIVE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300',
  COMPLETED: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300',
};

onMounted(load);
</script>

<template>
  <div class="fixed inset-0 z-50 bg-slate-900/40 dark:bg-black/75 flex items-start md:items-center justify-center p-0 md:p-6 overflow-y-auto" data-testid="sprint-panel" @click.self="emit('close')">
    <div class="bg-white dark:bg-slate-900 w-full max-w-4xl md:rounded-lg shadow-2xl border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 flex flex-col min-h-screen md:min-h-0 md:max-h-[90vh]">
      <div class="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 dark:border-slate-800">
        <div class="flex items-center gap-2.5">
          <div class="w-9 h-9 rounded-lg bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <Timer class="w-5 h-5" />
          </div>
          <div>
            <h2 class="text-sm md:text-base font-semibold">{{ t('scrum.title') }}</h2>
            <p class="text-[11px] text-slate-500 dark:text-slate-400">{{ taskStore.currentProject?.name }} · {{ t('scrum.subtitle') }}</p>
          </div>
        </div>
        <button type="button" class="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-400 cursor-pointer" @click="emit('close')"><X class="w-5 h-5" /></button>
      </div>

      <div class="flex gap-1 px-5 pt-3 border-b border-slate-200 dark:border-slate-800 overflow-x-auto">
        <button v-for="k in (['SPRINTS','PLANNING','BURNDOWN','VELOCITY','RETRO'] as Tab[])" :key="k" type="button"
          class="px-3 py-2 text-xs font-mono border-b-2 -mb-px cursor-pointer whitespace-nowrap"
          :class="tab === k ? 'border-emerald-600 text-emerald-700 dark:text-emerald-300 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'"
          :data-tab="k" @click="tab = k">
          {{ t(k === 'SPRINTS' ? 'scrum.tabSprints' : k === 'PLANNING' ? 'scrum.tabPlanning' : k === 'BURNDOWN' ? 'scrum.tabBurndown' : k === 'VELOCITY' ? 'scrum.tabVelocity' : 'scrum.retro') }}
        </button>
      </div>

      <div v-if="errorMsg" class="mx-5 mt-3 p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 flex items-center gap-1.5 font-mono text-[11px]" data-testid="scrum-error">
        <AlertCircle class="w-3.5 h-3.5 shrink-0" /> {{ errorMsg }}
      </div>
      <p v-if="!isPM" class="mx-5 mt-3 text-[11px] text-slate-500">{{ t('scrum.pmOnly') }}</p>
      <p v-else-if="!taskStore.canMutate" class="mx-5 mt-3 text-[11px] text-amber-600">{{ t('scrum.readOnly') }}</p>

      <div class="p-5 overflow-y-auto flex-1 text-xs">
        <!-- SPRINTS -->
        <div v-if="tab === 'SPRINTS'" class="space-y-4">
          <form v-if="canEdit" class="grid grid-cols-1 md:grid-cols-5 gap-2 p-3 rounded-lg border border-dashed border-slate-300 dark:border-slate-700" data-testid="sprint-form" @submit.prevent="createSprint">
            <input v-model="form.name" :placeholder="t('scrum.name')" class="md:col-span-1 h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-transparent" />
            <input v-model="form.goal" :placeholder="t('scrum.goal')" class="md:col-span-2 h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-transparent" />
            <div class="flex gap-1 md:col-span-1">
              <input v-model="form.start" type="date" :aria-label="t('scrum.start')" class="w-full h-8 px-1 rounded border border-slate-300 dark:border-slate-700 bg-transparent" />
              <input v-model="form.end" type="date" :aria-label="t('scrum.end')" class="w-full h-8 px-1 rounded border border-slate-300 dark:border-slate-700 bg-transparent" />
            </div>
            <button type="submit" :disabled="busy || !form.name.trim()" class="h-8 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-mono inline-flex items-center justify-center gap-1 cursor-pointer">
              <Plus class="w-3.5 h-3.5" /> {{ t('scrum.newSprint') }}
            </button>
          </form>

          <p v-if="sprints.length === 0" class="text-slate-500">{{ t('scrum.noSprints') }}</p>
          <div v-for="s in sprints" :key="s.id" class="p-3 rounded-lg border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row md:items-center gap-2" :data-sprint="s.id">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-sm truncate">{{ s.name }}</span>
                <span class="px-1.5 py-0.5 rounded text-[10px] font-mono" :class="stateClass[s.state]">{{ t(`scrum.${s.state}` as const) }}</span>
              </div>
              <p class="text-slate-500 mt-0.5 truncate">{{ s.goal }}</p>
              <p class="text-slate-400 font-mono mt-0.5">{{ s.start_date.slice(0,10) }} → {{ s.end_date.slice(0,10) }}
                · {{ pts(serverTasks.filter(x => x.sprint_id === s.id)) }} {{ t('scrum.points') }}
                <template v-if="s.committed_points !== null"> · {{ t('scrum.committed') }} {{ s.committed_points }}</template>
              </p>
            </div>
            <div v-if="canEdit" class="flex items-center gap-1.5 flex-wrap">
              <button v-if="s.state === 'PLANNED'" type="button" :disabled="busy" class="h-7 px-2 rounded bg-emerald-600 text-white inline-flex items-center gap-1 cursor-pointer disabled:opacity-50" data-action="start" @click="startSprint(s.id)">
                <Play class="w-3 h-3" /> {{ t('scrum.startSprint') }}
              </button>
              <template v-if="s.state === 'ACTIVE'">
                <select v-model="moveTarget" class="h-7 px-1 rounded border border-slate-300 dark:border-slate-700 bg-transparent" :aria-label="t('scrum.moveTo')">
                  <option :value="null">{{ t('scrum.moveTo') }}: {{ t('scrum.toBacklog') }}</option>
                  <option v-for="o in sprints.filter(x => x.state === 'PLANNED')" :key="o.id" :value="o.id">{{ t('scrum.moveTo') }}: {{ o.name }}</option>
                </select>
                <button type="button" :disabled="busy" class="h-7 px-2 rounded bg-indigo-600 text-white inline-flex items-center gap-1 cursor-pointer disabled:opacity-50" data-action="complete" @click="completeSprint(s.id)">
                  <CheckCircle2 class="w-3 h-3" /> {{ t('scrum.completeSprint') }}
                </button>
              </template>
              <button v-if="s.state !== 'COMPLETED'" type="button" :disabled="busy" class="h-7 px-2 rounded border border-rose-300 text-rose-600 inline-flex items-center gap-1 cursor-pointer" data-action="delete" @click="deleteSprint(s.id)">
                <Trash2 class="w-3 h-3" /> {{ t('scrum.delete') }}
              </button>
            </div>
          </div>
        </div>

        <!-- PLANNING -->
        <div v-else-if="tab === 'PLANNING'" class="space-y-3">
          <select v-model="selectedSprintId" class="h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-transparent" :aria-label="t('scrum.selectSprint')">
            <option :value="null" disabled>{{ t('scrum.selectSprint') }}</option>
            <option v-for="s in sprints.filter(x => x.state !== 'COMPLETED')" :key="s.id" :value="s.id">{{ s.name }} ({{ t(`scrum.${s.state}` as const) }})</option>
          </select>
          <div class="grid md:grid-cols-2 gap-3">
            <div class="rounded-lg border border-slate-200 dark:border-slate-800">
              <div class="px-3 py-2 border-b border-slate-200 dark:border-slate-800 font-semibold flex justify-between">
                <span>{{ t('scrum.backlog') }}</span><span class="font-mono text-slate-500">{{ pts(backlog) }} {{ t('scrum.points') }}</span>
              </div>
              <p v-if="backlog.length === 0" class="p-3 text-slate-400">{{ t('scrum.empty') }}</p>
              <div v-for="x in backlog" :key="x.id" class="px-3 py-2 flex items-center gap-2 border-b last:border-0 border-slate-100 dark:border-slate-800" data-backlog-task>
                <span class="font-mono text-slate-400">{{ x.key }}</span>
                <span class="flex-1 truncate">{{ x.title }}</span>
                <span class="font-mono text-slate-500">{{ x.complexity_points }}</span>
                <button v-if="canEdit && selectedSprint && selectedSprint.state !== 'COMPLETED'" type="button" class="p-1 rounded hover:bg-emerald-50 dark:hover:bg-emerald-500/10 text-emerald-600 cursor-pointer" :title="selectedSprint.name" @click="plan(x.id, selectedSprintId)">
                  <ArrowRight class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div class="rounded-lg border border-slate-200 dark:border-slate-800">
              <div class="px-3 py-2 border-b border-slate-200 dark:border-slate-800 font-semibold flex justify-between">
                <span>{{ t('scrum.sprintItems') }}<template v-if="selectedSprint">: {{ selectedSprint.name }}</template></span><span class="font-mono text-slate-500">{{ pts(sprintItems) }} {{ t('scrum.points') }}</span>
              </div>
              <p v-if="sprintItems.length === 0" class="p-3 text-slate-400">{{ t('scrum.empty') }}</p>
              <div v-for="x in sprintItems" :key="x.id" class="px-3 py-2 flex items-center gap-2 border-b last:border-0 border-slate-100 dark:border-slate-800" data-sprint-task>
                <button v-if="canEdit && x.status !== 'DONE'" type="button" class="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 cursor-pointer" @click="plan(x.id, null)">
                  <ArrowLeft class="w-3.5 h-3.5" />
                </button>
                <span class="font-mono text-slate-400">{{ x.key }}</span>
                <span class="flex-1 truncate" :class="x.status === 'DONE' ? 'line-through text-slate-400' : ''">{{ x.title }}</span>
                <span class="font-mono text-[10px] text-slate-500">{{ x.status }}</span>
                <span class="font-mono text-slate-500">{{ x.complexity_points }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- BURNDOWN -->
        <div v-else-if="tab === 'BURNDOWN'" class="space-y-3">
          <select v-model="selectedSprintId" class="h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-transparent" :aria-label="t('scrum.selectSprint')">
            <option v-for="s in sprints" :key="s.id" :value="s.id">{{ s.name }} ({{ t(`scrum.${s.state}` as const) }})</option>
          </select>
          <p v-if="!chart" class="text-slate-500">{{ t('scrum.empty') }}</p>
          <svg v-else :viewBox="`0 0 ${W} ${H}`" class="w-full max-w-2xl" role="img" data-testid="burndown">
            <line :x1="P" :y1="H-P" :x2="W-P" :y2="H-P" class="stroke-slate-300 dark:stroke-slate-700" />
            <line :x1="P" :y1="P" :x2="P" :y2="H-P" class="stroke-slate-300 dark:stroke-slate-700" />
            <text :x="P-6" :y="chart.y(chart.max)+4" text-anchor="end" class="fill-slate-400 text-[10px]">{{ chart.max }}</text>
            <text :x="P-6" :y="H-P+4" text-anchor="end" class="fill-slate-400 text-[10px]">0</text>
            <text v-for="l in chart.labels" :key="l.x" :x="l.x" :y="H-P+14" text-anchor="middle" class="fill-slate-400 text-[9px]">{{ l.text }}</text>
            <polyline :points="chart.ideal" fill="none" stroke-dasharray="4 4" class="stroke-slate-400" stroke-width="1.5" />
            <polyline v-if="chart.actualPts.length" :points="chart.actual" fill="none" class="stroke-emerald-600" stroke-width="2.5" />
            <circle v-for="p in chart.actualPts" :key="p.x" :cx="p.x" :cy="p.y" r="3" class="fill-emerald-600"><title>{{ p.v }}</title></circle>
          </svg>
          <div class="flex gap-4 text-[11px] text-slate-500">
            <span class="inline-flex items-center gap-1"><span class="w-4 border-t-2 border-dashed border-slate-400"></span>{{ t('scrum.ideal') }}</span>
            <span class="inline-flex items-center gap-1"><span class="w-4 border-t-2 border-emerald-600"></span>{{ t('scrum.remaining') }}</span>
          </div>
        </div>

        <!-- RETRO -->
        <div v-else-if="tab === 'RETRO'" class="space-y-3">
          <div class="flex flex-wrap gap-2 items-center">
            <select v-model="selectedSprintId" class="h-8 px-2 rounded border border-slate-300 dark:border-slate-700 bg-transparent" :aria-label="t('scrum.selectSprint')">
              <option v-for="s in sprints.filter(x => x.state !== 'PLANNED')" :key="s.id" :value="s.id">{{ s.name }} ({{ t(`scrum.${s.state}` as const) }})</option>
            </select>
            <button type="button" :disabled="retroLoading || selectedSprintId === null" class="h-8 px-3 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-mono inline-flex items-center gap-1 cursor-pointer" data-action="retro" @click="runRetro">
              <Sparkles class="w-3.5 h-3.5" /> {{ retroLoading ? '…' : t('scrum.retroRun') }}
            </button>
          </div>
          <div v-if="retro" class="grid md:grid-cols-3 gap-3" data-testid="retro">
            <div v-for="[key, list, cls] in ([['scrum.wentWell', retro.went_well, 'border-emerald-300'], ['scrum.toImprove', retro.to_improve, 'border-amber-300'], ['scrum.actions', retro.action_items, 'border-indigo-300']] as const)" :key="key" class="rounded-lg border-l-4 border p-3 border-slate-200 dark:border-slate-800" :class="cls">
              <h4 class="font-semibold mb-1.5">{{ t(key) }}</h4>
              <ul class="space-y-1 list-disc pl-4"><li v-for="(x, i) in list" :key="i">{{ x }}</li></ul>
            </div>
          </div>
        </div>

        <!-- VELOCITY -->
        <div v-else class="space-y-3">
          <p v-if="velocity.length === 0" class="text-slate-500">{{ t('scrum.noVelocity') }}</p>
          <template v-else>
            <p class="font-mono">{{ t('scrum.average') }}: <b data-testid="velocity-avg">{{ velocityAvg }}</b> {{ t('scrum.points') }}</p>
            <div v-for="v in velocity" :key="v.sprint_id" class="space-y-1">
              <div class="flex justify-between"><span class="truncate">{{ v.sprint_name }}</span><span class="font-mono text-slate-500">{{ v.completed_points }} / {{ v.committed_points }}</span></div>
              <div class="h-2 rounded bg-slate-100 dark:bg-slate-800 relative overflow-hidden">
                <div class="absolute inset-y-0 left-0 bg-slate-300 dark:bg-slate-600" :style="{ width: `${v.committed_points / velocityMax * 100}%` }"></div>
                <div class="absolute inset-y-0 left-0 bg-emerald-600" :style="{ width: `${v.completed_points / velocityMax * 100}%` }"></div>
              </div>
            </div>
            <div class="flex gap-4 text-[11px] text-slate-500">
              <span class="inline-flex items-center gap-1"><span class="w-3 h-2 bg-slate-300"></span>{{ t('scrum.committed') }}</span>
              <span class="inline-flex items-center gap-1"><span class="w-3 h-2 bg-emerald-600"></span>{{ t('scrum.completed') }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
