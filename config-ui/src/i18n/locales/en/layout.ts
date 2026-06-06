/** Header + Sidebar chrome. UI-7. */
export const layout = {
  header: {
    connected: 'Connected to Irene API',
    connectedDetail: 'Connected • {{handlers}} handlers • {{donations}} donations',
    disconnected: 'Disconnected from Irene API',
    connecting: 'Checking connection…',
    refreshTitle: 'Refresh connection status',
    lastCheck: 'Last check: {{time}}',
    cannotConnectTitle: 'Cannot connect to Irene API',
    cannotConnectBody: 'Make sure the Irene Voice Assistant is running and accessible at',
  },
  sidebar: {
    navigation: 'Navigation',
    adminInterface: 'Admin Interface',
    expand: 'Expand sidebar',
    collapse: 'Collapse sidebar',
    footerTitle: 'Irene Admin v1.0.0',
    footerSubtitle: 'Voice Assistant Management',
    sections: {
      overview: { title: 'Overview', description: 'System overview and status' },
      donations: { title: 'Donations', description: 'Edit intent handler donations' },
      templates: { title: 'Templates', description: 'Edit response templates' },
      prompts: { title: 'Prompts', description: 'Edit LLM prompts' },
      localizations: { title: 'Localizations', description: 'Edit localization data' },
      monitoring: { title: 'Monitoring', description: 'System monitoring and metrics' },
      configuration: { title: 'Configuration', description: 'System configuration management' },
    },
  },
} as const;
