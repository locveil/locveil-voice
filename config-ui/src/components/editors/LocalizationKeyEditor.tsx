/**
 * LocalizationKeyEditor Component - Type-aware editor for localization values
 * 
 * Handles editing of different value types (strings, arrays, objects) for localization data.
 * Provides appropriate UI controls based on the value type and domain context.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Trash2, Plus, Type, List, Hash, ChevronDown, ChevronRight } from 'lucide-react';
import { Button, Alert, AlertDescription, Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from 'locveil-ui-kit';
import Input from '@/components/ui/Input';
import TextArea from '@/components/ui/TextArea';
import Badge from '@/components/ui/Badge';
import { safeDisplayValue, safeArrayItemStringify } from '@/utils/safeStringify';

interface LocalizationKeyEditorProps {
  keyName: string;
  value: any;
  onChange: (newKey: string, newValue: any) => void;
  onDelete: () => void;
  domain?: string;
}

type ValueType = 'string' | 'array' | 'object';

const LocalizationKeyEditor: React.FC<LocalizationKeyEditorProps> = ({
  keyName,
  value,
  onChange,
  onDelete,
  domain
}) => {
  const { t } = useTranslation('localizations');
  const [isExpanded, setIsExpanded] = useState(true);
  const [currentKey, setCurrentKey] = useState(keyName);

  const getValueType = (val: any): ValueType => {
    if (Array.isArray(val)) return 'array';
    if (typeof val === 'object' && val !== null) return 'object';
    return 'string';
  };

  const [valueType, setValueType] = useState<ValueType>(getValueType(value));

  const handleKeyChange = (newKey: string) => {
    setCurrentKey(newKey);
    onChange(newKey, value);
  };

  const handleValueChange = (newValue: any) => {
    onChange(currentKey, newValue);
  };

  const handleTypeChange = (newType: ValueType) => {
    setValueType(newType);
    let newValue: any;
    
    switch (newType) {
      case 'string':
        newValue = Array.isArray(value) ? value.join(', ') : 
                   typeof value === 'object' ? JSON.stringify(value) : 
                   safeDisplayValue(value);
        break;
      case 'array':
        newValue = Array.isArray(value) ? value : 
                   typeof value === 'string' ? value.split(',').map(s => s.trim()) :
                   [safeDisplayValue(value)];
        break;
      case 'object':
        newValue = typeof value === 'object' && !Array.isArray(value) ? value :
                   Array.isArray(value) ? value.reduce((obj, item, index) => ({ ...obj, [`item_${index}`]: item }), {}) :
                   { value: safeDisplayValue(value) };
        break;
    }
    
    handleValueChange(newValue);
  };

  const renderStringEditor = () => {
    const stringValue = safeDisplayValue(value);
    
    if (stringValue.length > 100 || stringValue.includes('\n')) {
      return (
        <TextArea
          value={stringValue}
          onChange={handleValueChange}
          rows={3}
          className="text-sm"
          placeholder={t('keyEditor.stringPlaceholder')}
        />
      );
    }

    return (
      <Input
        value={stringValue}
        onChange={handleValueChange}
        placeholder={t('keyEditor.stringPlaceholder')}
        className="text-sm"
      />
    );
  };

  const renderArrayEditor = () => {
    const arrayValue = Array.isArray(value) ? value : [safeDisplayValue(value)];
    
    const handleArrayChange = (newArray: string[]) => {
      handleValueChange(newArray);
    };

    const addArrayItem = () => {
      handleArrayChange([...arrayValue, '']);
    };

    const updateArrayItem = (index: number, newValue: string) => {
      const newArray = [...arrayValue];
      newArray[index] = newValue;
      handleArrayChange(newArray);
    };

    const removeArrayItem = (index: number) => {
      const newArray = arrayValue.filter((_, i) => i !== index);
      handleArrayChange(newArray);
    };

    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{t('keyEditor.items', { count: arrayValue.length })}</span>
          <Button variant="ghost" size="sm" onClick={addArrayItem} className="text-primary">
            <Plus />
            {t('keyEditor.addItem')}
          </Button>
        </div>
        
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {arrayValue.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-6">{index}</span>
              <Input
                value={safeArrayItemStringify(item)}
                onChange={(newValue) => updateArrayItem(index, newValue)}
                placeholder={t('keyEditor.itemPlaceholder', { index: index + 1 })}
                className="text-sm flex-1"
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => removeArrayItem(index)}
                className="text-destructive"
              >
                <Trash2 />
              </Button>
            </div>
          ))}
        </div>
        
        {arrayValue.length === 0 && (
          <div className="text-center py-4 text-muted-foreground text-sm">
            {t('keyEditor.noItems')}
          </div>
        )}
      </div>
    );
  };

  const renderObjectEditor = () => {
    const objectValue = typeof value === 'object' && !Array.isArray(value) && value !== null ? 
                       value : 
                       { value: safeDisplayValue(value) };
    
    const handleObjectChange = (newObject: Record<string, any>) => {
      handleValueChange(newObject);
    };

    const addObjectKey = () => {
      const newKey = `new_key_${Date.now()}`;
      handleObjectChange({
        ...objectValue,
        [newKey]: ''
      });
    };

    const updateObjectEntry = (oldKey: string, newKey: string, newValue: string) => {
      const newObject = { ...objectValue };
      delete newObject[oldKey];
      newObject[newKey] = newValue;
      handleObjectChange(newObject);
    };

    const removeObjectKey = (key: string) => {
      const newObject = { ...objectValue };
      delete newObject[key];
      handleObjectChange(newObject);
    };

    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">{t('keyEditor.properties', { count: Object.keys(objectValue).length })}</span>
          <Button variant="ghost" size="sm" onClick={addObjectKey} className="text-primary">
            <Plus />
            {t('keyEditor.addProperty')}
          </Button>
        </div>
        
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {Object.entries(objectValue).map(([key, val]) => (
            <div key={key} className="grid grid-cols-2 gap-2">
              <Input
                value={key}
                onChange={(newKey) => updateObjectEntry(key, newKey, safeDisplayValue(val))}
                placeholder={t('keyEditor.propertyName')}
                className="text-sm"
              />
              <div className="flex items-center gap-2">
                <Input
                  value={safeDisplayValue(val)}
                  onChange={(newValue) => updateObjectEntry(key, key, newValue)}
                  placeholder={t('keyEditor.propertyValue')}
                  className="text-sm flex-1"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => removeObjectKey(key)}
                  className="text-destructive"
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
          ))}
        </div>
        
        {Object.keys(objectValue).length === 0 && (
          <div className="text-center py-4 text-muted-foreground text-sm">
            {t('keyEditor.noProperties')}
          </div>
        )}
      </div>
    );
  };

  const getTypeIcon = (type: ValueType) => {
    switch (type) {
      case 'string': return <Type className="w-3 h-3" />;
      case 'array': return <List className="w-3 h-3" />;
      case 'object': return <Hash className="w-3 h-3" />;
    }
  };


  const getDomainHint = () => {
    if (domain === 'datetime' && keyName === 'weekdays') {
      return t('keyEditor.domainHints.weekdays');
    } else if (domain === 'datetime' && keyName === 'months') {
      return t('keyEditor.domainHints.months');
    } else if (domain === 'components' && keyName === 'component_mappings') {
      return t('keyEditor.domainHints.componentMappings');
    } else if (domain === 'commands' && keyName === 'stop_patterns') {
      return t('keyEditor.domainHints.stopPatterns');
    }
    return null;
  };

  const domainHint = getDomainHint();

  return (
    <div className="border border-border rounded-lg p-4 bg-card">
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-muted-foreground"
        >
          {isExpanded ? <ChevronDown /> : <ChevronRight />}
        </Button>
        
        <div className="flex-1">
          <Input
            value={currentKey}
            onChange={handleKeyChange}
            className="text-sm font-medium"
            placeholder={t('keyEditor.keyNamePlaceholder')}
          />
        </div>
        
        <div className="flex items-center gap-2">
          {/* Type selector */}
          <Select
            value={valueType}
            onValueChange={(newType) => handleTypeChange(newType as ValueType)}
          >
            <SelectTrigger className="h-8 w-auto text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="string">{t('keyEditor.valueTypes.string')}</SelectItem>
              <SelectItem value="array">{t('keyEditor.valueTypes.array')}</SelectItem>
              <SelectItem value="object">{t('keyEditor.valueTypes.object')}</SelectItem>
            </SelectContent>
          </Select>

          <Badge variant="default" className="text-xs">
            {getTypeIcon(valueType)}
            {t(`keyEditor.valueTypes.${valueType}`)}
          </Badge>

          <Button
            variant="ghost"
            size="icon"
            onClick={onDelete}
            className="text-destructive"
          >
            <Trash2 />
          </Button>
        </div>
      </div>

      {/* Domain hint */}
      {domainHint && (
        <Alert variant="accent" className="mb-3">
          <AlertDescription>💡 {domainHint}</AlertDescription>
        </Alert>
      )}

      {/* Value editor */}
      {isExpanded && (
        <div className="space-y-2">
          {valueType === 'string' && renderStringEditor()}
          {valueType === 'array' && renderArrayEditor()}
          {valueType === 'object' && renderObjectEditor()}
        </div>
      )}
    </div>
  );
};

export default LocalizationKeyEditor;
