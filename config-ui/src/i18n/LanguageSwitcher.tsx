/**
 * LanguageSwitcher (UI-7) — toggles the UI-chrome language and persists the choice. This is the *interface* language
 * axis only; it is orthogonal to the donation content language chosen via LanguageTabs.
 */
import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';
import { SUPPORTED_LNGS, STORAGE_KEY, LANG_LABELS, isUiLang, type UiLang } from './config';

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation('common');
  const current: UiLang = isUiLang(i18n.language) ? i18n.language : SUPPORTED_LNGS[0];

  const change = (lng: UiLang): void => {
    void i18n.changeLanguage(lng);
    try {
      localStorage.setItem(STORAGE_KEY, lng);
    } catch {
      /* storage blocked — selection still applies for this session */
    }
  };

  return (
    <div className="flex items-center gap-1" title={t('language.label')}>
      <Languages className="w-4 h-4 text-gray-400" aria-hidden="true" />
      <div className="flex rounded-lg border border-gray-300 overflow-hidden" role="group" aria-label={t('language.label')}>
        {SUPPORTED_LNGS.map((lng) => (
          <button
            key={lng}
            type="button"
            onClick={() => change(lng)}
            aria-pressed={current === lng}
            className={`px-2 py-1 text-xs font-medium transition-colors ${
              current === lng ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {LANG_LABELS[lng]}
          </button>
        ))}
      </div>
    </div>
  );
}
