import type { DecomposedTaskResult, TaskPriority } from '../types/task';

/**
 * Deterministic JSON-schema enforced task decomposition compiler.
 * Transforms raw goals/specifications into structured subtasks with dependencies and acceptance criteria.
 */
export function decomposeGoalDeterministically(rawGoal: string): DecomposedTaskResult {
  const goal = rawGoal.trim();
  const lower = goal.toLowerCase();

  // Pattern detection for typical software / systems engineering goals
  const subtasks: DecomposedTaskResult['subtasks'] = [];

  if (lower.includes('auth') || lower.includes('login') || lower.includes('oauth')) {
    subtasks.push({
      title: 'Define Auth State Machine & Token Schema',
      description: 'Implement JWT/Session schema, token refresh lifecycles, and cryptographic signature verification.',
      priority: 'HIGH' as TaskPriority,
      complexity: 'M',
      acceptanceCriteria: ['Valid JWT signing & verification', 'Auto-refresh on 401 response', 'Secure httpOnly cookie storage'],
    });
    subtasks.push({
      title: 'Build Login / OAuth Handlers & Secure API Endpoints',
      description: 'Implement route guards, rate-limiting middleware, and callback handlers.',
      priority: 'HIGH' as TaskPriority,
      complexity: 'L',
      acceptanceCriteria: ['Rate limiter prevents brute force (>5 req/sec)', 'OAuth callback handles state verification', 'Zero raw secrets in client bundles'],
      dependsOnTitles: ['Define Auth State Machine & Token Schema'],
    });
    subtasks.push({
      title: 'Client-Side Session Cache & Auth Guard Hook',
      description: 'Integrate optimistic session validation and redirect unauthenticated routes.',
      priority: 'MEDIUM' as TaskPriority,
      complexity: 'S',
      acceptanceCriteria: ['Sub-10ms route guard check', 'Proper teardown on logout'],
      dependsOnTitles: ['Build Login / OAuth Handlers & Secure API Endpoints'],
    });
  } else if (lower.includes('api') || lower.includes('backend') || lower.includes('database') || lower.includes('db')) {
    subtasks.push({
      title: 'Schema Migration & Relational Indexing Definition',
      description: 'Draft zero-downtime migration scripts and define foreign key constraints with composite indexes.',
      priority: 'CRITICAL' as TaskPriority,
      complexity: 'M',
      acceptanceCriteria: ['Migrations execute idempotently', 'Indexes cover query hotpaths (<10ms scan)', 'Rollback test succeeds'],
    });
    subtasks.push({
      title: 'Implement Repository Layer & Query Builders',
      description: 'Write type-safe data access routines with connection pool pooling and query telemetry.',
      priority: 'HIGH' as TaskPriority,
      complexity: 'L',
      acceptanceCriteria: ['Zero N+1 query patterns', 'Deterministic error mapping to HTTP 4xx/5xx', 'Unit test coverage > 90%'],
      dependsOnTitles: ['Schema Migration & Relational Indexing Definition'],
    });
    subtasks.push({
      title: 'Expose REST / RPC Endpoints with Strict Validation',
      description: 'Wire up Zod/TypeBox payload schemas and handle rate-limiting with telemetry logging.',
      priority: 'HIGH' as TaskPriority,
      complexity: 'M',
      acceptanceCriteria: ['Invalid inputs rejected with 422 and path-specific errors', 'Structured JSON access logging'],
      dependsOnTitles: ['Implement Repository Layer & Query Builders'],
    });
  } else if (lower.includes('ui') || lower.includes('frontend') || lower.includes('page') || lower.includes('dashboard')) {
    subtasks.push({
      title: 'Core State Store & Direct-DOM Reactive Runes',
      description: 'Implement atomic state stores with zero virtual-DOM overhead and optimistic cache updates.',
      priority: 'HIGH' as TaskPriority,
      complexity: 'M',
      acceptanceCriteria: ['Sub-50ms reactive latency', 'Strict TypeScript typing without any coersions', 'Local storage / IndexedDB sync'],
    });
    subtasks.push({
      title: 'High-Density Component Tree & Keyboard Ergonomics',
      description: 'Build accessible UI components with full Vim keyboard traversal and zero layout shifts.',
      priority: 'HIGH' as TaskPriority,
      complexity: 'L',
      acceptanceCriteria: ['j/k navigation works without mouse', 'Touch hit targets >= 44px', 'Zero CLS (Cumulative Layout Shift)'],
      dependsOnTitles: ['Core State Store & Direct-DOM Reactive Runes'],
    });
    subtasks.push({
      title: 'Mobile Touch Gestures & Safe-Area Polishing',
      description: 'Implement swipe-to-action pointer events, touch-callout suppression, and responsive thumb zones.',
      priority: 'MEDIUM' as TaskPriority,
      complexity: 'M',
      acceptanceCriteria: ['Swipe right marks DONE', 'Swipe left reveals actions', 'Smooth scroll with touch-action: pan-y'],
      dependsOnTitles: ['High-Density Component Tree & Keyboard Ergonomics'],
    });
  } else {
    // Generic high-velocity engineering task breakdown
    const parts = goal.split(/[,;\n]+/).map((s) => s.trim()).filter(Boolean);
    if (parts.length > 1) {
      parts.forEach((part, idx) => {
        subtasks.push({
          title: `Phase ${idx + 1}: ${part}`,
          description: `Execute core deliverable for: ${part}. Ensure strict verification.`,
          priority: (idx === 0 ? 'HIGH' : 'MEDIUM') as TaskPriority,
          complexity: (idx === 0 ? 'M' : 'S'),
          acceptanceCriteria: [`Deliverable verified for ${part}`, 'All edge cases and boundary checks covered'],
          dependsOnTitles: idx > 0 ? [`Phase ${idx}: ${parts[idx - 1]}`] : undefined,
        });
      });
    } else {
      subtasks.push({
        title: `Architectural Specs & Schema for: ${goal}`,
        description: `Define strict machine-parseable data contracts and system invariants for ${goal}.`,
        priority: 'CRITICAL' as TaskPriority,
        complexity: 'M',
        acceptanceCriteria: ['Schema defined with zero undefined states', 'Architecture validated against system constraints'],
      });
      subtasks.push({
        title: `Core Execution & Engine Implementation: ${goal}`,
        description: `Build high-velocity implementation with deterministic state transitions.`,
        priority: 'HIGH' as TaskPriority,
        complexity: 'L',
        acceptanceCriteria: ['All functional paths implemented', 'Optimistic state handling with rollback support'],
        dependsOnTitles: [`Architectural Specs & Schema for: ${goal}`],
      });
      subtasks.push({
        title: `Verification, Benchmarks & E2E Validation: ${goal}`,
        description: `Run latency audits (<50ms), integration tests, and edge case simulations.`,
        priority: 'MEDIUM' as TaskPriority,
        complexity: 'M',
        acceptanceCriteria: ['100% tests passing', 'Sub-50ms interaction benchmarks achieved'],
        dependsOnTitles: [`Core Execution & Engine Implementation: ${goal}`],
      });
    }
  }

  return {
    epicTitle: goal,
    rationale: `Deterministic task graph decomposed into ${subtasks.length} sequentially ordered subtasks with clear dependency bindings and zero boilerplate.`,
    subtasks,
  };
}
