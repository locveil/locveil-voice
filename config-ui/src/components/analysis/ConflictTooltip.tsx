/**
 * ConflictTooltip Component - Detailed conflict information display
 * 
 * Provides comprehensive conflict details including evidence, suggestions,
 * and technical analysis information in a structured tooltip format.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, AlertTriangle, Info, ArrowRight } from 'lucide-react';
import type { ConflictReport } from '@/types';

interface ConflictTooltipProps {
  conflict: ConflictReport;
  className?: string;
}

const ConflictTooltip: React.FC<ConflictTooltipProps> = ({
  conflict,
  className = ''
}) => {
  const { t } = useTranslation('common');
  const getSeverityIcon = () => {
    switch (conflict.severity) {
      case 'blocker':
        return <AlertCircle className="w-4 h-4 text-destructive" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]" />;
      case 'info':
        return <Info className="w-4 h-4 text-[hsl(var(--lv-status-tested)_55%_32%)] dark:text-[hsl(var(--lv-status-tested)_70%_72%)]" />;
      default:
        return <Info className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const formatConflictType = (type: string): string => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const renderSignalValue = (value: any): React.ReactNode => {
    if (Array.isArray(value)) {
      if (value.length === 0) return <span className="text-muted-foreground italic">{t('status.none')}</span>;
      return (
        <div className="space-y-1">
          {value.slice(0, 3).map((item, index) => (
            <div key={index} className="text-xs bg-muted px-2 py-1 rounded">
              {typeof item === 'string' ? item : JSON.stringify(item)}
            </div>
          ))}
          {value.length > 3 && (
            <div className="text-xs text-muted-foreground italic">
              {t('conflicts.andMore', { count: value.length - 3 })}
            </div>
          )}
        </div>
      );
    }

    if (typeof value === 'object' && value !== null) {
      return (
        <div className="text-xs bg-muted px-2 py-1 rounded font-mono">
          {JSON.stringify(value, null, 2)}
        </div>
      );
    }

    return <span className="text-sm">{String(value)}</span>;
  };

  return (
    <div className={`bg-popover text-popover-foreground border border-border rounded-lg shadow-lg p-4 max-w-sm ${className}`}>
      {/* Header */}
      <div className="flex items-start space-x-2 mb-3">
        {getSeverityIcon()}
        <div className="flex-1">
          <div className="font-medium text-sm">
            {formatConflictType(conflict.conflict_type)}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {t('conflicts.scoreLanguage', { score: (conflict.score * 100).toFixed(1), language: conflict.language.toUpperCase() })}
          </div>
        </div>
      </div>

      {/* Intent Conflict */}
      <div className="mb-3">
        <div className="text-xs font-medium text-muted-foreground mb-1">{t('conflicts.conflictingIntents')}</div>
        <div className="flex items-center space-x-2 text-sm">
          <span className="bg-muted px-2 py-1 rounded text-xs">
            {conflict.intent_a}
          </span>
          <ArrowRight className="w-3 h-3 text-muted-foreground" />
          <span className="bg-muted px-2 py-1 rounded text-xs">
            {conflict.intent_b}
          </span>
        </div>
      </div>

      {/* Evidence/Signals */}
      {Object.keys(conflict.signals).length > 0 && (
        <div className="mb-3">
          <div className="text-xs font-medium text-muted-foreground mb-2">{t('conflicts.evidence')}</div>
          <div className="space-y-2">
            {Object.entries(conflict.signals).slice(0, 3).map(([key, value]) => (
              <div key={key}>
                <div className="text-xs font-medium text-muted-foreground mb-1">
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </div>
                {renderSignalValue(value)}
              </div>
            ))}
            {Object.keys(conflict.signals).length > 3 && (
              <div className="text-xs text-muted-foreground italic">
                {t('conflicts.andMoreSignals', { count: Object.keys(conflict.signals).length - 3 })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Suggestions */}
      {conflict.suggestions.length > 0 && (
        <div>
          <div className="text-xs font-medium text-muted-foreground mb-2">{t('conflicts.suggestionsLabel')}</div>
          <div className="space-y-1">
            {conflict.suggestions.slice(0, 2).map((suggestion, index) => (
              <div key={index} className="text-xs text-muted-foreground bg-muted p-2 rounded">
                • {suggestion}
              </div>
            ))}
            {conflict.suggestions.length > 2 && (
              <div className="text-xs text-muted-foreground italic">
                {t('conflicts.andMoreSuggestions', { count: conflict.suggestions.length - 2 })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ConflictTooltip;
