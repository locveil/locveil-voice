/**
 * MonitoringPage Component - System monitoring dashboard
 * 
 * Placeholder for future monitoring implementation.
 * Will be implemented in Phase 2 of the architecture.
 */

import { Activity, BarChart3, TrendingUp, Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Alert, AlertTitle, AlertDescription } from 'locveil-ui-kit';

const MonitoringPage: React.FC = () => {
  const { t } = useTranslation('monitoring');

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          {t('page.title')}
        </h1>
        <p className="text-muted-foreground">
          {t('page.subtitle')}
        </p>
      </div>

      {/* Coming soon content */}
      <div className="bg-card rounded-lg border border-border p-12 text-center">
        <div className="flex justify-center space-x-4 mb-6">
          <Activity className="h-12 w-12 text-muted-foreground/50" />
          <BarChart3 className="h-12 w-12 text-muted-foreground/50" />
          <TrendingUp className="h-12 w-12 text-muted-foreground/50" />
        </div>

        <h2 className="text-2xl font-semibold text-foreground mb-4">
          {t('page.comingSoonTitle')}
        </h2>

        <p className="text-muted-foreground max-w-2xl mx-auto mb-6">
          {t('page.comingSoonBody')}
        </p>

        <Alert variant="accent" className="max-w-2xl mx-auto text-left">
          <Info />
          <div>
            <AlertTitle>{t('page.plannedFeaturesTitle')}</AlertTitle>
            <AlertDescription>
              <ul className="space-y-1">
                <li>• {t('features.metrics')}</li>
                <li>• {t('features.health')}</li>
                <li>• {t('features.memory')}</li>
                <li>• {t('features.intent')}</li>
                <li>• {t('features.session')}</li>
                <li>• {t('features.websocket')}</li>
              </ul>
            </AlertDescription>
          </div>
        </Alert>
      </div>
    </div>
  );
};

export default MonitoringPage;
