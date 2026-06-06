/**
 * MonitoringPage Component - System monitoring dashboard
 * 
 * Placeholder for future monitoring implementation.
 * Will be implemented in Phase 2 of the architecture.
 */

import { Activity, BarChart3, TrendingUp } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const MonitoringPage: React.FC = () => {
  const { t } = useTranslation('monitoring');

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {t('page.title')}
        </h1>
        <p className="text-gray-600">
          {t('page.subtitle')}
        </p>
      </div>

      {/* Coming soon content */}
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <div className="flex justify-center space-x-4 mb-6">
          <Activity className="h-12 w-12 text-gray-300" />
          <BarChart3 className="h-12 w-12 text-gray-300" />
          <TrendingUp className="h-12 w-12 text-gray-300" />
        </div>

        <h2 className="text-2xl font-semibold text-gray-900 mb-4">
          {t('page.comingSoonTitle')}
        </h2>

        <p className="text-gray-600 max-w-2xl mx-auto mb-6">
          {t('page.comingSoonBody')}
        </p>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-2xl mx-auto">
          <h3 className="font-semibold text-blue-900 mb-2">{t('page.plannedFeaturesTitle')}</h3>
          <ul className="text-sm text-blue-800 text-left space-y-1">
            <li>• {t('features.metrics')}</li>
            <li>• {t('features.health')}</li>
            <li>• {t('features.memory')}</li>
            <li>• {t('features.intent')}</li>
            <li>• {t('features.session')}</li>
            <li>• {t('features.websocket')}</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default MonitoringPage;
