/** monitoring page strings. UI-7 — seeded; expanded during retrofit. */
export const monitoring = {
  page: {
    title: 'System Monitoring',
    subtitle: 'Monitor system performance, component health, and real-time metrics.',
    comingSoonTitle: 'Monitoring Dashboard Coming Soon',
    comingSoonBody: 'The monitoring dashboard will provide comprehensive system metrics, component health status, performance analytics, and real-time updates via WebSocket connections. This feature is planned for Phase 2 of the admin interface development.',
    plannedFeaturesTitle: 'Planned Features:',
  },
  features: {
    metrics: 'Real-time system metrics and performance data',
    health: 'Component health status and diagnostics',
    memory: 'Memory usage and cleanup recommendations',
    intent: 'Intent processing analytics and success rates',
    session: 'Session analytics and user satisfaction metrics',
    websocket: 'WebSocket-based live updates',
  },
} as const;
