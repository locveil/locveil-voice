/**
 * HandlerList Component - Simplified navigation list for donation handlers
 * 
 * Displays donation handlers with basic status indicators, allows selection for editing.
 * Language selection is handled by the language tabs in the main editor area.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  CheckCircle2,
  Search
} from 'lucide-react';
import { Input as KitInput } from 'locveil-ui-kit';
import Badge from '@/components/ui/Badge';

// Status-hued icon recipes (stylebook §2 — meaning via status tokens, never raw palette).
const persistedText = 'text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]';
const conflictText = 'text-[hsl(var(--lv-status-conflict)_55%_32%)] dark:text-[hsl(var(--lv-status-conflict)_70%_72%)]';
import type { HandlerLanguageListProps } from '@/types';

const HandlerList: React.FC<HandlerLanguageListProps> = ({ 
  handlers, 
  selectedHandler, 
  selectedLanguage: _selectedLanguage,
  onSelect, 
  onLanguageSelect: _onLanguageSelect,
  onCreateLanguage: _onCreateLanguage,
  onDeleteLanguage: _onDeleteLanguage,
  searchQuery,
  onSearchChange,
  filterLanguageCount,
  onFilterLanguageCountChange: _onFilterLanguageCountChange,
  hasChanges: _hasChanges = {}, 
  loading = false,
  error = null
}) => {
  const { t } = useTranslation('donations');

  // Simple filtering logic
  const filteredHandlers = useMemo(() => {
    return handlers.filter(handler => {
      // Text search
      const search = searchQuery.toLowerCase();
      if (search && !handler.handler_name.toLowerCase().includes(search)) {
        return false;
      }
      
      // Language count filter
      const languageCount = handler.languages.length;
      if (filterLanguageCount === 'single' && languageCount !== 1) return false;
      if (filterLanguageCount === 'multiple' && languageCount <= 1) return false;
      
      return true;
    });
  }, [handlers, searchQuery, filterLanguageCount]);

  const getStatusBadge = (handler: any) => {
    const availableLanguages = handler.languages.length;
    
    if (availableLanguages === 0) {
      return <Badge variant="error">{t('handlerList.noLanguages')}</Badge>;
    }
    return <Badge variant="success">{t('handlerList.available')}</Badge>;
  };

  const getStatusIcon = (handler: any) => {
    const availableLanguages = handler.languages.length;
    if (availableLanguages === 0) {
      return <AlertCircle className={`w-4 h-4 ${conflictText}`} />;
    }
    return <CheckCircle2 className={`w-4 h-4 ${persistedText}`} />;
  };

  if (loading) {
    return (
      <div className="w-80 bg-muted border-r border-border flex items-center justify-center">
        <div className="text-muted-foreground">{t('handlerList.loading')}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-80 bg-muted border-r border-border p-4">
        <div className="text-destructive">
          <AlertCircle className="w-5 h-5 inline mr-2" />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-muted border-r border-border flex flex-col">
      {/* Search Header */}
      <div className="p-4 border-b border-border bg-card">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <KitInput
            type="text"
            placeholder={t('handlerList.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Handlers List */}
      <div className="flex-1 overflow-auto">
        {filteredHandlers.length === 0 ? (
          <div className="p-4 text-muted-foreground text-center">
            {searchQuery ? t('handlerList.noMatching') : t('handlerList.noHandlers')}
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {filteredHandlers.map((handler) => (
              <div key={handler.handler_name} className="space-y-1">
                {/* Handler Item */}
                <div
                  onClick={() => onSelect(handler.handler_name)}
                  className={`
                    flex items-center justify-between p-3 rounded-md cursor-pointer transition-colors duration-200
                    ${selectedHandler === handler.handler_name
                      ? 'bg-primary/10 border border-primary text-primary'
                      : 'bg-card border border-border hover:bg-muted/60'
                    }
                  `}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(handler)}
                      <span className="font-medium truncate">{handler.handler_name}</span>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end space-y-1">
                    {getStatusBadge(handler)}
                  </div>
                </div>

              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border bg-card">
        <div className="text-xs text-muted-foreground">
          {t('handlerList.count', { count: filteredHandlers.length })}
        </div>
      </div>
    </div>
  );
};

export default HandlerList;