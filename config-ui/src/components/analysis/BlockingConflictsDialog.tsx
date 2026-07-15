/**
 * BlockingConflictsDialog Component - Dialog for blocking conflicts
 * 
 * Displays blocking conflicts that prevent saving with detailed information
 * and resolution options for each conflict.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, ArrowRight } from 'lucide-react';
import {
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from 'locveil-ui-kit';
import ConflictBadge from './ConflictBadge';
import ConflictTooltip from './ConflictTooltip';
import type { ConflictReport } from '@/types';

interface BlockingConflictsDialogProps {
  conflicts: ConflictReport[];
  onResolve?: (conflictId: string) => void;
  onClose: () => void;
  className?: string;
}

const BlockingConflictsDialog: React.FC<BlockingConflictsDialogProps> = ({
  conflicts,
  onResolve,
  onClose,
  className = ''
}) => {
  const { t } = useTranslation('common');
  const blockingConflicts = conflicts.filter(c => c.severity === 'blocker');

  if (blockingConflicts.length === 0) {
    return null;
  }

  const getConflictId = (conflict: ConflictReport): string => {
    return `${conflict.intent_a}-${conflict.intent_b}-${conflict.conflict_type}`;
  };

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className={`max-w-2xl max-h-[80vh] overflow-hidden ${className}`}>
        {/* Header */}
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <span>{t('conflicts.blockingTitle')}</span>
          </DialogTitle>
        </DialogHeader>

        {/* Content */}
        <div>
          <div className="mb-4">
            <p className="text-sm text-muted-foreground">
              {t('conflicts.mustResolve', { count: blockingConflicts.length })}
            </p>
          </div>

          <div className="space-y-4 max-h-96 overflow-y-auto">
            {blockingConflicts.map((conflict, index) => {
              const conflictId = getConflictId(conflict);

              return (
                <div key={conflictId} className="border border-border rounded-lg bg-muted/40 p-4">
                  {/* Conflict Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span className="text-sm font-medium text-destructive">
                          {t('conflicts.conflictNumber', { index: index + 1 })}
                        </span>
                        <ConflictBadge conflict={conflict} />
                      </div>

                      <div className="flex items-center space-x-2 text-sm">
                        <span className="bg-background px-2 py-1 rounded border border-border text-muted-foreground">
                          {conflict.intent_a}
                        </span>
                        <ArrowRight className="w-4 h-4 text-muted-foreground" />
                        <span className="bg-background px-2 py-1 rounded border border-border text-muted-foreground">
                          {conflict.intent_b}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Conflict Details */}
                  <div className="bg-background rounded border border-border p-3 mb-3">
                    <ConflictTooltip conflict={conflict} className="border-0 shadow-none p-0 max-w-none bg-transparent" />
                  </div>

                  {/* Actions */}
                  {conflict.suggestions.length > 0 && (
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-destructive mb-2">
                        {t('conflicts.suggestedResolutions')}
                      </div>
                      {conflict.suggestions.slice(0, 2).map((suggestion, suggestionIndex) => (
                        <div key={suggestionIndex} className="bg-background border border-border rounded p-2 text-sm text-muted-foreground">
                          <div className="mb-2">{suggestion}</div>
                          {onResolve && (
                            <Button size="sm" onClick={() => onResolve(conflictId)}>
                              {t('conflicts.applyThisFix')}
                            </Button>
                          )}
                        </div>
                      ))}
                      {conflict.suggestions.length > 2 && (
                        <div className="text-xs text-muted-foreground italic">
                          {t('conflicts.andMoreSuggestionsAvailable', { count: conflict.suggestions.length - 2 })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <DialogFooter className="items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {t('conflicts.resolveAllToSave')}
          </div>
          <Button variant="outline" onClick={onClose}>
            {t('actions.close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default BlockingConflictsDialog;
