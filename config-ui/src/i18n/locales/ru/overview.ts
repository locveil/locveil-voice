/** overview page strings (RU). UI-7 — seeded; expanded during retrofit. */
export const overview = {
  page: {
    title: 'Обзор системы',
    subtitle: 'Отслеживайте состояние системы и управляйте компонентами',
    loadError: 'Не удалось загрузить состояние системы',
  },
  cards: {
    intentSystem: 'Система интентов',
    handlersLoaded: 'Загружено обработчиков',
    donationsLoaded: 'Загружено donations',
    intentHandlers: 'Обработчики интентов',
    totalHandlers: 'Всего обработчиков',
    system: 'Система',
    systemRunning: 'Система работает',
    statusLine: 'Статус: {{status}}',
  },
  status: {
    active: 'Активна',
    routingEnabled: 'Маршрутизация включена',
    routingDisabled: 'Маршрутизация отключена',
  },
  quickActions: {
    title: 'Быстрые действия',
    donations: {
      title: 'Управление donations',
      description: 'Редактирование donations и конфигураций обработчиков интентов',
    },
    monitoring: {
      title: 'Мониторинг системы',
      description: 'Просмотр состояния системы и метрик производительности',
    },
    configuration: {
      title: 'Конфигурация',
      description: 'Системные настройки и управление конфигурацией',
    },
  },
  recentActivity: {
    title: 'Недавняя активность',
    monitoringTitle: 'Мониторинг активности',
    monitoringBody: 'Отслеживание активности будет доступно на панели мониторинга',
    goToMonitoring: 'Перейти к мониторингу',
  },
} as const;
