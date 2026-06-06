/**
 * ValidationIndicator Component - Validation status display
 * 
 * Shows the current validation state with appropriate visual indicators
 * for blocking conflicts, warnings, and successful validation.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle, AlertCircle, AlertTriangle, Clock } from 'lucide-react';
import type { NLUValidationResult } from '@/types';

interface ValidationIndicatorProps {
  result: NLUValidationResult | null;
  isValidating?: boolean;
  className?: string;
}

const ValidationIndicator: React.FC<ValidationIndicatorProps> = ({
  result,
  isValidating = false,
  className = ''
}) => {
  const { t } = useTranslation('common');
  if (isValidating) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Clock className="w-4 h-4 animate-spin text-blue-500" />
        <span className="text-sm text-blue-600">{t('validation.validating')}</span>
      </div>
    );
  }

  if (!result) {
    return (
      <div className={`flex items-center space-x-2 text-gray-500 ${className}`}>
        <div className="w-4 h-4 border border-gray-300 rounded-full"></div>
        <span className="text-sm">{t('validation.notValidated')}</span>
      </div>
    );
  }

  const getValidationStatus = () => {
    if (!result.is_valid || result.has_blocking_conflicts) {
      return {
        icon: AlertCircle,
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        message: t('validation.failed')
      };
    }

    if (result.has_warnings) {
      return {
        icon: AlertTriangle,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        message: t('validation.passedWithWarnings')
      };
    }

    return {
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200',
      message: t('validation.passed')
    };
  };

  const status = getValidationStatus();
  const Icon = status.icon;

  const getConflictSummary = () => {
    if (!result.conflicts || result.conflicts.length === 0) {
      return t('conflicts.status.none');
    }

    const blockers = result.conflicts.filter(c => c.severity === 'blocker').length;
    const warnings = result.conflicts.filter(c => c.severity === 'warning').length;
    const infos = result.conflicts.filter(c => c.severity === 'info').length;

    const parts = [];
    if (blockers > 0) parts.push(t('conflicts.count.blockers', { count: blockers }));
    if (warnings > 0) parts.push(t('conflicts.count.warnings', { count: warnings }));
    if (infos > 0) parts.push(t('conflicts.count.info', { count: infos }));

    return parts.join(', ');
  };

  return (
    <div className={`inline-flex items-center space-x-2 px-3 py-2 rounded-lg border ${status.bgColor} ${status.borderColor} ${className}`}>
      <Icon className={`w-4 h-4 ${status.color}`} />
      <div className="flex flex-col">
        <span className={`text-sm font-medium ${status.color}`}>
          {status.message}
        </span>
        <span className="text-xs text-gray-600">
          {getConflictSummary()}
        </span>
        {result.validation_time_ms && (
          <span className="text-xs text-gray-500">
            {t('validation.validatedIn', { ms: result.validation_time_ms.toFixed(1) })}
          </span>
        )}
      </div>
    </div>
  );
};

export default ValidationIndicator;
