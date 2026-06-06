/**
 * ChoiceSurfacesEditor (UI-5) — localize the spoken forms of a choice/entity parameter's options.
 *
 * The canonical tokens are language-neutral identifiers from the contract (`choices`) and are NEVER translated.
 * Here, per language, we map each canonical token to the spoken surface forms a user might say for it
 * (e.g. canonical `quiet` → ru: ["тихо", "потише", "тихий режим"]). A canonical without surfaces is
 * unrecognisable when spoken in that language — the cross-language validator flags those.
 */

import { useTranslation } from 'react-i18next';
import ArrayOfStringsEditor from '@/components/editors/ArrayOfStringsEditor';

interface ChoiceSurfacesEditorProps {
  canonicalChoices: string[];
  value: Record<string, string[]>;
  onChange: (value: Record<string, string[]>) => void;
  disabled?: boolean;
}

export default function ChoiceSurfacesEditor({
  canonicalChoices, value, onChange, disabled = false,
}: ChoiceSurfacesEditorProps) {
  const { t } = useTranslation('donations');
  if (canonicalChoices.length === 0) return null;

  return (
    <div className="border rounded-xl p-3">
      <div className="text-sm font-medium mb-2">{t('choices.title')}</div>
      <div className="space-y-3">
        {canonicalChoices.map((canonical) => (
          <div key={canonical} className="grid grid-cols-1 md:grid-cols-[140px,1fr] gap-3 items-start">
            <div className="text-sm font-mono bg-gray-50 border rounded-lg px-2 py-2 break-all">{canonical}</div>
            <ArrayOfStringsEditor
              label=""
              value={value[canonical] ?? []}
              onChange={(forms) => onChange({ ...value, [canonical]: forms })}
              disabled={disabled}
              placeholder={t('choices.spokenFormPlaceholder')}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
