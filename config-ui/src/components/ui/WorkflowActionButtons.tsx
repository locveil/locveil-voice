/**
 * WorkflowActionButtons Component - Action buttons for the Test → Validate → Persist workflow
 *
 * Provides persist and rollback functionality for Phase 4.3 workflow integration
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Save, RotateCcw, AlertTriangle, Loader } from 'lucide-react';
import { Button, StatusChip, Icon, cn } from 'locveil-ui-kit';
import { ComponentName } from './TestConfigButton';

interface WorkflowStatus {
  hasChanges: boolean;
  isTested: boolean;
  isPersisted: boolean;
  hasConflicts: boolean;
  canTest: boolean;
  canPersist: boolean;
  testStatus: 'idle' | 'testing' | 'applied' | 'error';
}

interface WorkflowActionButtonsProps {
  component: ComponentName;
  status: WorkflowStatus;
  onPersistTested: (component: ComponentName) => Promise<void>;
  onRollbackToPersisted: (component: ComponentName) => void;
  onRollbackToTested: (component: ComponentName) => void;
  loading?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const kitSize = { sm: 'sm', md: 'default', lg: 'lg' } as const;

export const WorkflowActionButtons: React.FC<WorkflowActionButtonsProps> = ({
  component,
  status,
  onPersistTested,
  onRollbackToPersisted,
  onRollbackToTested,
  loading = false,
  className = '',
  size = 'sm'
}) => {
  const { t } = useTranslation('common');
  const [persisting, setPersisting] = React.useState(false);

  const handlePersist = async () => {
    if (persisting || loading) return;

    setPersisting(true);
    try {
      await onPersistTested(component);
    } catch (error) {
      console.error(`Failed to persist ${component} configuration:`, error);
    } finally {
      setPersisting(false);
    }
  };

  const getComponentDisplayName = () => {
    const names: Record<ComponentName, string> = {
      tts: 'TTS',
      asr: 'ASR',
      audio: 'Audio',
      llm: 'LLM',
      nlu: 'NLU',
      voice_trigger: 'Voice Trigger',
      text_processing: 'Text Processing',
      intent_system: 'Intent System'
    };
    return names[component];
  };

  return (
    <div className={cn('flex items-center gap-1', className)}>
      {/* Persist to TOML Button */}
      {status.canPersist && (
        <Button
          size={kitSize[size]}
          onClick={() => void handlePersist()}
          disabled={persisting || loading || !status.canPersist}
          title={t('workflow.persistTitle', { component: getComponentDisplayName() })}
        >
          {persisting ? <Loader className="animate-spin" /> : <Save />}
          {persisting ? t('workflow.persisting') : t('workflow.persistToToml')}
        </Button>
      )}

      {/* Rollback Buttons */}
      <div className="flex items-center gap-1">
        {/* Rollback to Tested */}
        {status.hasChanges && status.isTested && (
          <Button
            variant="outline"
            size={kitSize[size]}
            onClick={() => onRollbackToTested(component)}
            disabled={loading}
            title={t('workflow.rollbackToTestedTitle', { component: getComponentDisplayName() })}
          >
            <RotateCcw />
            {t('workflow.rollbackToTested')}
          </Button>
        )}

        {/* Rollback to Persisted */}
        {(status.hasChanges || status.isTested) && !status.isPersisted && (
          <Button
            variant="ghost"
            size={kitSize[size]}
            onClick={() => onRollbackToPersisted(component)}
            disabled={loading}
            title={t('workflow.rollbackToTomlTitle', { component: getComponentDisplayName() })}
          >
            <RotateCcw />
            {t('workflow.rollbackToToml')}
          </Button>
        )}
      </div>

      {/* Conflict Indicator */}
      {status.hasConflicts && (
        <StatusChip
          variant="conflict"
          title={t('workflow.conflictTitle', { component: getComponentDisplayName() })}
        >
          <Icon icon={AlertTriangle} className="mr-1" />
          {t('workflow.conflict')}
        </StatusChip>
      )}
    </div>
  );
};

export default WorkflowActionButtons;
