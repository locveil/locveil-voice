/**
 * ConfigurationStatus Component - Shows the status of configuration testing/application
 *
 * Provides visual feedback for different configuration states during the live testing workflow
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, Loader, Clock } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Alert, AlertDescription, Icon, cn } from 'locveil-ui-kit';

export type ConfigurationStatusType = 'testing' | 'applied' | 'pending' | 'error';

interface ConfigurationStatusProps {
  status: ConfigurationStatusType;
  message: string;
  testResult?: any; // The configure response from the API
  className?: string;
}

const statusIcon: Record<ConfigurationStatusType, { icon: LucideIcon; spin?: boolean }> = {
  testing: { icon: Loader, spin: true },
  applied: { icon: CheckCircle },
  pending: { icon: Clock },
  error: { icon: AlertCircle },
};

export const ConfigurationStatus: React.FC<ConfigurationStatusProps> = ({
  status,
  message,
  testResult,
  className = ''
}) => {
  const { t } = useTranslation('common');
  const { icon, spin } = statusIcon[status];

  return (
    <Alert
      variant={status === 'error' ? 'destructive' : 'default'}
      className={className}
    >
      <Icon icon={icon} className={cn(spin && 'animate-spin')} />
      <AlertDescription>
        <div className="text-sm font-medium">{message}</div>
        {testResult && (
          <div className="mt-1 text-xs text-muted-foreground">
            {status === 'applied' && testResult.default_provider && (
              <div>{t('configStatus.defaultProvider', { value: testResult.default_provider })}</div>
            )}
            {status === 'applied' && testResult.enabled_providers && (
              <div>{t('configStatus.enabledProviders', { value: testResult.enabled_providers.join(', ') })}</div>
            )}
            {status === 'applied' && testResult.fallback_providers && testResult.fallback_providers.length > 0 && (
              <div>{t('configStatus.fallbackProviders', { value: testResult.fallback_providers.join(', ') })}</div>
            )}
            {status === 'applied' && testResult.language && (
              <div>{t('configStatus.language', { value: testResult.language })}</div>
            )}
            {status === 'applied' && testResult.confidence_threshold !== undefined && (
              <div>{t('configStatus.confidenceThreshold', { value: testResult.confidence_threshold })}</div>
            )}
            {status === 'applied' && testResult.wake_words && (
              <div>{t('configStatus.wakeWords', {
                value: testResult.wake_words
                  .map((w: any) => (typeof w === 'string' ? w : w?.name ?? ''))
                  .filter(Boolean)
                  .join(', ')
              })}</div>
            )}
            {status === 'applied' && testResult.enabled_handlers && (
              <div>{t('configStatus.handlers', { count: testResult.enabled_handlers.length })}</div>
            )}
            {status === 'applied' && testResult.normalizers && (
              <div>{t('configStatus.normalizers', { value: testResult.normalizers.join(', ') })}</div>
            )}
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
};

export default ConfigurationStatus;
