/**
 * ConflictStatusBar Component - Real-time status indicator for NLU analysis
 * 
 * Displays the current analysis status and provides a summary of detected conflicts
 * with appropriate visual indicators for different severity levels.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import Badge from '@/components/ui/Badge';
import type { ConflictReport } from '@/types';

interface ConflictStatusBarProps {
  conflicts: ConflictReport[];
  status: 'idle' | 'analyzing' | 'complete' | 'error';
  className?: string;
}

const ConflictStatusBar: React.FC<ConflictStatusBarProps> = ({
  conflicts,
  status,
  className = ''
}) => {
  const { t } = useTranslation('common');
  const blockers = conflicts.filter(c => c.severity === 'blocker');
  const warnings = conflicts.filter(c => c.severity === 'warning');
  const infos = conflicts.filter(c => c.severity === 'info');

  const getStatusIcon = () => {
    switch (status) {
      case 'analyzing':
        return <Clock className="w-4 h-4 animate-spin text-primary" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-destructive" />;
      case 'complete':
        if (blockers.length > 0) {
          return <AlertCircle className="w-4 h-4 text-destructive" />;
        } else if (warnings.length > 0) {
          return <AlertTriangle className="w-4 h-4 text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]" />;
        } else {
          return <CheckCircle className="w-4 h-4 text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]" />;
        }
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'analyzing':
        return t('conflicts.status.analyzing');
      case 'error':
        return t('conflicts.status.failed');
      case 'complete':
        if (blockers.length > 0) {
          return t('conflicts.status.blockingDetected', { count: blockers.length });
        } else if (warnings.length > 0) {
          return t('conflicts.status.warningsDetected', { count: warnings.length });
        } else if (infos.length > 0) {
          return t('conflicts.status.infoDetected', { count: infos.length });
        } else {
          return t('conflicts.status.none');
        }
      default:
        return t('conflicts.status.ready');
    }
  };

  return (
    <div className={`flex items-center justify-between p-3 border border-border bg-card rounded-lg ${className}`}>
      <div className="flex items-center space-x-2">
        {getStatusIcon()}
        <span className="text-sm font-medium text-foreground">
          {getStatusText()}
        </span>
      </div>

      {status === 'complete' && conflicts.length > 0 && (
        <div className="flex items-center space-x-2 text-xs">
          {blockers.length > 0 && (
            <Badge variant="error" className="text-xs">
              {t('conflicts.count.blockers', { count: blockers.length })}
            </Badge>
          )}
          {warnings.length > 0 && (
            <Badge variant="warning" className="text-xs">
              {t('conflicts.count.warnings', { count: warnings.length })}
            </Badge>
          )}
          {infos.length > 0 && (
            <Badge variant="info" className="text-xs">
              {t('conflicts.count.info', { count: infos.length })}
            </Badge>
          )}
        </div>
      )}
    </div>
  );
};

export default ConflictStatusBar;
