/** Header + Sidebar chrome (RU). UI-7. */
export const layout = {
  header: {
    connected: 'Подключено к Irene API',
    connectedDetail: 'Подключено • обработчиков: {{handlers}} • донорских файлов: {{donations}}',
    disconnected: 'Нет подключения к Irene API',
    connecting: 'Проверка подключения…',
    refreshTitle: 'Обновить статус подключения',
    lastCheck: 'Последняя проверка: {{time}}',
    cannotConnectTitle: 'Не удаётся подключиться к Irene API',
    cannotConnectBody: 'Убедитесь, что голосовой ассистент Irene запущен и доступен по адресу',
  },
  sidebar: {
    navigation: 'Навигация',
    adminInterface: 'Панель администратора',
    expand: 'Развернуть панель',
    collapse: 'Свернуть панель',
    footerTitle: 'Irene Admin v1.0.0',
    footerSubtitle: 'Управление голосовым ассистентом',
    sections: {
      overview: { title: 'Обзор', description: 'Обзор и состояние системы' },
      donations: { title: 'Доноры', description: 'Редактирование донорских файлов обработчиков' },
      templates: { title: 'Шаблоны', description: 'Редактирование шаблонов ответов' },
      prompts: { title: 'Промпты', description: 'Редактирование промптов для LLM' },
      localizations: { title: 'Локализации', description: 'Редактирование данных локализации' },
      monitoring: { title: 'Мониторинг', description: 'Мониторинг и метрики системы' },
      configuration: { title: 'Конфигурация', description: 'Управление конфигурацией системы' },
    },
  },
} as const;
