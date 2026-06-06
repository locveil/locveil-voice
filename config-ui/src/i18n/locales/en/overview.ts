/** overview page strings. UI-7 — seeded; expanded during retrofit. */
export const overview = {
  page: {
    title: 'System Overview',
    subtitle: 'Monitor system health and manage components',
    loadError: 'Failed to load system status',
  },
  cards: {
    intentSystem: 'Intent System',
    handlersLoaded: 'Handlers Loaded',
    donationsLoaded: 'Donations Loaded',
    intentHandlers: 'Intent Handlers',
    totalHandlers: 'Total Handlers',
    system: 'System',
    systemRunning: 'System Running',
    statusLine: 'Status: {{status}}',
  },
  status: {
    active: 'Active',
    routingEnabled: 'Routing enabled',
    routingDisabled: 'Routing disabled',
  },
  quickActions: {
    title: 'Quick Actions',
    donations: {
      title: 'Manage Donations',
      description: 'Edit intent handler donations and configurations',
    },
    monitoring: {
      title: 'System Monitoring',
      description: 'View system health and performance metrics',
    },
    configuration: {
      title: 'Configuration',
      description: 'System settings and configuration management',
    },
  },
  recentActivity: {
    title: 'Recent Activity',
    monitoringTitle: 'Activity Monitoring',
    monitoringBody: 'Activity tracking will be available in the monitoring dashboard',
    goToMonitoring: 'Go to Monitoring',
  },
} as const;
