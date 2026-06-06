/**
 * SpacyValueEditor - Specialized input components for different SpaCy attribute value types
 * 
 * Provides appropriate input controls based on the SpaCy attribute structure,
 * ensuring proper editing while maintaining the underlying data integrity.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { SpacyAttributeStructure, getOperatorOptions } from '@/utils/spacyAttributeHelpers';

type OperatorKey =
  | 'zeroOrOne' | 'zeroOrMore' | 'oneOrMore' | 'negation'
  | 'exactly2' | 'between2And4' | 'twoOrMore' | 'upTo4' | 'custom';

const OPERATOR_KEYS: Record<string, OperatorKey> = {
  '?': 'zeroOrOne',
  '*': 'zeroOrMore',
  '+': 'oneOrMore',
  '!': 'negation',
  '{2}': 'exactly2',
  '{2,4}': 'between2And4',
  '{2,}': 'twoOrMore',
  '{,4}': 'upTo4',
};

interface SpacyValueEditorProps {
  structure: SpacyAttributeStructure;
  onChange: (newValue: any) => void;
  disabled?: boolean;
}

const SpacyValueEditor: React.FC<SpacyValueEditorProps> = ({
  structure,
  onChange,
  disabled = false
}) => {
  const { t } = useTranslation('donations');
  const { valueType, editableValue } = structure;

  // String input for simple text values and regex patterns
  const renderStringInput = (placeholder?: string) => (
    <input
      type="text"
      value={editableValue || ''}
      onChange={(e) => onChange(e.target.value)}
      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      placeholder={placeholder}
      disabled={disabled}
    />
  );

  // Boolean toggle for true/false values
  const renderBooleanInput = () => (
    <select
      value={String(editableValue)}
      onChange={(e) => onChange(e.target.value === 'true')}
      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      disabled={disabled}
    >
      <option value="true">{t('editors.spacyValue.true')}</option>
      <option value="false">{t('editors.spacyValue.false')}</option>
    </select>
  );

  // Number input for numeric values
  const renderNumberInput = () => (
    <input
      type="number"
      value={editableValue || ''}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
      disabled={disabled}
    />
  );

  // Operator dropdown for OP attribute
  const renderOperatorInput = () => {
    const operators = getOperatorOptions();
    
    return (
      <select
        value={editableValue || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        disabled={disabled}
      >
        <option value="">{t('editors.spacyValue.selectOperator')}</option>
        {operators.map(op => (
          <option key={op} value={op}>
            {op} - {t(`editors.spacyValue.operator.${OPERATOR_KEYS[op] ?? 'custom'}` as const)}
          </option>
        ))}
      </select>
    );
  };

  // Array editor for IN/NOT_IN lists
  const renderListInput = () => {
    const listValue: string[] = Array.isArray(editableValue) ? editableValue : [];
    
    const addItem = () => {
      onChange([...listValue, '']);
    };

    const updateItem = (index: number, newValue: string) => {
      const newList = [...listValue];
      newList[index] = newValue;
      onChange(newList);
    };

    const removeItem = (index: number) => {
      const newList = listValue.filter((_, i) => i !== index);
      onChange(newList);
    };

    return (
      <div className="space-y-2">
        <div className="space-y-2">
          {listValue.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-6">{index + 1}.</span>
              <input
                type="text"
                value={item}
                onChange={(e) => updateItem(index, e.target.value)}
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={t('editors.spacyValue.itemPlaceholder', { index: index + 1 })}
                disabled={disabled}
              />
              <button
                type="button"
                onClick={() => removeItem(index)}
                className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                disabled={disabled}
                title={t('editors.spacyValue.removeItem')}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
        
        <button
          type="button"
          onClick={addItem}
          className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors"
          disabled={disabled}
        >
          <Plus className="w-4 h-4" />
          {t('editors.spacyValue.addItem')}
        </button>

        {listValue.length === 0 && (
          <div className="text-sm text-gray-500 italic">
            {t('editors.spacyValue.noItems')}
          </div>
        )}
      </div>
    );
  };

  // JSON editor for unknown/custom structures
  const renderJsonInput = () => (
    <div className="space-y-2">
      <div className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded p-2">
        {t('editors.spacyValue.jsonWarning')}
      </div>
      <textarea
        value={editableValue || ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        rows={3}
        placeholder={t('editors.spacyValue.jsonPlaceholder')}
        disabled={disabled}
      />
    </div>
  );

  // Main render logic based on value type
  switch (valueType) {
    case 'string':
      return renderStringInput();
    
    case 'regex':
      return renderStringInput(t('editors.spacyValue.regexPlaceholder'));
    
    case 'boolean':
      return renderBooleanInput();
    
    case 'number':
      return renderNumberInput();
    
    case 'operator':
      return renderOperatorInput();
    
    case 'list':
      return renderListInput();
    
    case 'unknown':
      return renderJsonInput();
    
    default:
      return renderStringInput();
  }
};

export default SpacyValueEditor;
