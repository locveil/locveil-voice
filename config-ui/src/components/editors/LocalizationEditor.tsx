/**
 * LocalizationEditor Component - Multi-type value editor for localization data
 * 
 * Provides structured editing for localization YAML files with support for
 * strings, arrays, and objects. Includes domain-specific validation and preview.
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Eye, Code, Layout, Globe, AlertCircle } from 'lucide-react';
import { Button, Alert, AlertTitle, AlertDescription, Tabs, TabsList, TabsTrigger } from 'locveil-ui-kit';
import LocalizationKeyEditor from './LocalizationKeyEditor';
import Section from '@/components/ui/Section';
import TextArea from '@/components/ui/TextArea';
import Badge from '@/components/ui/Badge';

interface LocalizationEditorProps {
  value: Record<string, any>;
  onChange: (value: Record<string, any>) => void;
  domain?: string;
  schema?: Record<string, any>;
  onValidationChange?: (isValid: boolean, errors: string[]) => void;
}

type ViewMode = 'structured' | 'yaml' | 'preview';

const LocalizationEditor: React.FC<LocalizationEditorProps> = ({
  value,
  onChange,
  domain,
  schema,
  onValidationChange
}) => {
  const { t } = useTranslation('localizations');
  const [viewMode, setViewMode] = useState<ViewMode>('structured');
  const [yamlContent, setYamlContent] = useState('');
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Convert object to YAML string (simple implementation)
  const objectToYaml = (obj: Record<string, any>): string => {
    const yamlLines: string[] = [];
    
    const processValue = (val: any, indent: string = ''): string => {
      if (typeof val === 'string') {
        // Handle multiline strings
        if (val.includes('\n')) {
          return `|\n${val.split('\n').map(line => `${indent}  ${line}`).join('\n')}`;
        }
        return `"${val.replace(/"/g, '\\"')}"`;
      }
      
      if (Array.isArray(val)) {
        if (val.length === 0) return '[]';
        return '\n' + val.map(item => `${indent}- ${processValue(item, indent + '  ')}`).join('\n');
      }
      
      if (typeof val === 'object' && val !== null) {
        if (Object.keys(val).length === 0) return '{}';
        return '\n' + Object.entries(val).map(([k, v]) => 
          `${indent}${k}: ${processValue(v, indent + '  ')}`
        ).join('\n');
      }
      
      return String(val);
    };

    Object.entries(obj).forEach(([key, val]) => {
      yamlLines.push(`${key}: ${processValue(val)}`);
    });

    return yamlLines.join('\n');
  };

  // Parse YAML string to object (simple implementation)
  const yamlToObject = (yamlStr: string): Record<string, any> => {
    try {
      // Simple YAML parser - in production, use a proper YAML library
      const lines = yamlStr.split('\n').filter(line => line.trim() && !line.trim().startsWith('#'));
      const result: Record<string, any> = {};
      let currentKey = '';
      let currentArray: string[] = [];
      let inArray = false;

      for (const line of lines) {
        const trimmed = line.trim();
        
        if (trimmed.startsWith('- ')) {
          // Array item
          if (inArray) {
            currentArray.push(trimmed.substring(2).trim().replace(/^"(.*)"$/, '$1'));
          }
        } else if (trimmed.includes(':')) {
          // Key-value pair
          if (inArray && currentKey) {
            result[currentKey] = currentArray;
            currentArray = [];
            inArray = false;
          }
          
          const [key, ...valueParts] = trimmed.split(':');
          const value = valueParts.join(':').trim();
          currentKey = key.trim();
          
          if (value) {
            if (value.startsWith('[') && value.endsWith(']')) {
              // Inline array
              result[currentKey] = value.slice(1, -1).split(',').map(item => item.trim().replace(/^"(.*)"$/, '$1'));
            } else if (value.startsWith('{') && value.endsWith('}')) {
              // Inline object (simplified)
              result[currentKey] = {};
            } else {
              // String value
              result[currentKey] = value.replace(/^"(.*)"$/, '$1');
            }
          } else {
            // Multi-line value starts
            inArray = true;
            currentArray = [];
          }
        }
      }
      
      // Handle final array
      if (inArray && currentKey) {
        result[currentKey] = currentArray;
      }

      return result;
    } catch (error) {
      throw new Error(t('editor.yamlParseError', { message: error instanceof Error ? error.message : 'Unknown error' }));
    }
  };

  // Update YAML content when value changes
  useEffect(() => {
    if (viewMode === 'yaml') {
      setYamlContent(objectToYaml(value));
    }
  }, [value, viewMode]);

  // Domain-specific validation
  const validateLocalizationData = (data: Record<string, any>): string[] => {
    const errors: string[] = [];
    
    // Basic validation
    if (!data || typeof data !== 'object') {
      errors.push(t('editor.validation.mustBeObject'));
      return errors;
    }

    // Domain-specific validation
    if (domain === 'datetime') {
      const requiredFields = ['weekdays', 'months'];
      requiredFields.forEach(field => {
        if (!data[field]) {
          errors.push(t('editor.validation.missingDatetimeField', { field }));
        } else if (!Array.isArray(data[field])) {
          errors.push(t('editor.validation.fieldMustBeArray', { field }));
        }
      });
    } else if (domain === 'components') {
      if (!data.component_mappings || typeof data.component_mappings !== 'object') {
        errors.push(t('editor.validation.missingComponentMappings'));
      }
    } else if (domain === 'commands') {
      if (!data.stop_patterns || !Array.isArray(data.stop_patterns)) {
        errors.push(t('editor.validation.missingStopPatterns'));
      }
    }

    // Check for empty values
    Object.entries(data).forEach(([key, value]) => {
      if (value === null || value === undefined || value === '') {
        errors.push(t('editor.validation.emptyValue', { key }));
      }
    });

    return errors;
  };

  // Validate current data
  useEffect(() => {
    const errors = validateLocalizationData(value);
    setValidationErrors(errors);
    onValidationChange?.(errors.length === 0, errors);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional scoped/mount load (load fns are not memoized)
  }, [value, domain, onValidationChange]);

  const handleYamlChange = (newYaml: string) => {
    setYamlContent(newYaml);
    setYamlError(null);

    try {
      const parsed = yamlToObject(newYaml);
      onChange(parsed);
    } catch (error) {
      setYamlError(error instanceof Error ? error.message : t('editor.parseError'));
    }
  };

  const handleAddKey = () => {
    const newKey = `new_key_${Date.now()}`;
    onChange({
      ...value,
      [newKey]: getDomainDefaultValue()
    });
  };

  const getDomainDefaultValue = (): any => {
    if (domain === 'datetime') {
      return ['Item 1', 'Item 2'];
    } else if (domain === 'components') {
      return { 'new_component': 'mapped_value' };
    } else if (domain === 'commands') {
      return ['command_pattern'];
    }
    return 'New value';
  };

  const handleKeyChange = (oldKey: string, newKey: string, newValue: any) => {
    const newData = { ...value };
    delete newData[oldKey];
    newData[newKey] = newValue;
    onChange(newData);
  };

  const handleDeleteKey = (key: string) => {
    const newData = { ...value };
    delete newData[key];
    onChange(newData);
  };

  const getViewModeIcon = (mode: ViewMode) => {
    switch (mode) {
      case 'structured': return <Layout className="w-4 h-4" />;
      case 'yaml': return <Code className="w-4 h-4" />;
      case 'preview': return <Eye className="w-4 h-4" />;
    }
  };

  const renderPreview = () => {
    return (
      <div className="space-y-4">
        <div className="p-4 bg-muted rounded-lg">
          <h4 className="font-medium text-muted-foreground mb-2 flex items-center gap-2">
            <Globe className="w-4 h-4" />
            {t('editor.previewDomain', { domain: domain || t('editor.unknownDomain') })}
          </h4>
          <div className="text-sm text-muted-foreground">
            {schema?.domain_description || t('editor.domainDescriptionFallback', { domain })}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h5 className="font-medium text-muted-foreground mb-2">{t('editor.keysHeading', { count: Object.keys(value).length })}</h5>
            <div className="space-y-1">
              {Object.keys(value).map(key => (
                <div key={key} className="flex items-center gap-2">
                  <Badge variant="default">{key}</Badge>
                  <span className="text-sm text-muted-foreground">
                    {Array.isArray(value[key]) ? t('editor.typeArray', { count: value[key].length }) :
                     typeof value[key] === 'object' ? t('editor.typeObject', { count: Object.keys(value[key]).length }) :
                     t('editor.typeString')}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h5 className="font-medium text-muted-foreground mb-2">{t('editor.validationHeading')}</h5>
            {validationErrors.length === 0 ? (
              <div className="text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)] text-sm">{t('editor.noValidationErrors')}</div>
            ) : (
              <div className="space-y-1">
                {validationErrors.map((error, index) => (
                  <div key={index} className="text-destructive text-sm">{t('editor.validationErrorItem', { error })}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* View Mode Selector */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground">{t('editor.view')}</span>
        <Tabs value={viewMode} onValueChange={(mode) => setViewMode(mode as ViewMode)}>
          <TabsList>
            {(['structured', 'yaml', 'preview'] as ViewMode[]).map((mode) => (
              <TabsTrigger key={mode} value={mode} className="gap-2">
                {getViewModeIcon(mode)}
                {t(`editor.viewModes.${mode}`)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <Alert variant="destructive">
          <AlertCircle />
          <div>
            <AlertTitle>{t('editor.validationErrors')}</AlertTitle>
            <AlertDescription>
              <ul className="space-y-1">
                {validationErrors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </AlertDescription>
          </div>
        </Alert>
      )}

      {/* Content based on view mode */}
      {viewMode === 'structured' && (
        <Section title={t('editor.entriesSection')} className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="text-sm text-muted-foreground">
              {t('editor.entriesCount', { count: Object.keys(value).length })}
            </div>
            <Button size="sm" onClick={handleAddKey}>
              <Plus />
              {t('editor.addEntry')}
            </Button>
          </div>
          
          <div className="space-y-3">
            {Object.entries(value).map(([key, val]) => (
              <LocalizationKeyEditor
                key={key}
                keyName={key}
                value={val}
                onChange={(newKey, newValue) => handleKeyChange(key, newKey, newValue)}
                onDelete={() => handleDeleteKey(key)}
                domain={domain}
              />
            ))}
          </div>
          
          {Object.keys(value).length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <Globe className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>{t('editor.noEntries')}</p>
              <p className="text-sm mt-1">{t('editor.noEntriesHint')}</p>
            </div>
          )}
        </Section>
      )}

      {viewMode === 'yaml' && (
        <Section title={t('editor.yamlEditor')}>
          <div className="space-y-2">
            {yamlError && (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertDescription>{yamlError}</AlertDescription>
              </Alert>
            )}
            <TextArea
              value={yamlContent}
              onChange={handleYamlChange}
              rows={20}
              className="font-mono text-sm"
              placeholder={t('editor.yamlPlaceholder')}
            />
          </div>
        </Section>
      )}

      {viewMode === 'preview' && (
        <Section title={t('editor.preview')}>
          {renderPreview()}
        </Section>
      )}
    </div>
  );
};

export default LocalizationEditor;
