/**
 * PatternTester (UI-3, UI-1 §6) — "does this actually work?". Runs a sample sentence through the REAL recognizer
 * (POST /nlu/recognize — the same path production uses, no JS re-implementation) and shows what was recognized and
 * which values were filled, so the author validates phrasings by example.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, CheckCircle2, XCircle } from 'lucide-react';
import { Button, Input } from 'locveil-ui-kit';
import apiClient from '@/utils/apiClient';
import type { RecognizeResponse } from '@/types';

// Status-hued text/icon recipes (stylebook §2 — meaning via status tokens, never raw palette).
const persistedText = 'text-[hsl(var(--lv-status-persisted)_55%_32%)] dark:text-[hsl(var(--lv-status-persisted)_70%_72%)]';
const editedText = 'text-[hsl(var(--lv-status-edited)_55%_32%)] dark:text-[hsl(var(--lv-status-edited)_70%_72%)]';
const conflictText = 'text-[hsl(var(--lv-status-conflict)_55%_32%)] dark:text-[hsl(var(--lv-status-conflict)_70%_72%)]';

interface PatternTesterProps {
  /** The intent this method should produce, e.g. "timer.set" — used to show a match/no-match badge. */
  expectedIntent?: string;
  placeholder?: string;
}

export default function PatternTester({ expectedIntent, placeholder }: PatternTesterProps) {
  const { t } = useTranslation(['donations', 'common']);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RecognizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (): Promise<void> => {
    if (!text.trim()) return;
    setBusy(true); setResult(null); setError(null);
    try {
      setResult(await apiClient.recognizeText(text.trim()));
    } catch (e) {
      // 422 = nothing recognized; surface it plainly.
      setError(e instanceof Error ? e.message : t('tester.recognitionFailed'));
    } finally {
      setBusy(false);
    }
  };

  const entities = result?.entities ?? {};
  const matched = result && expectedIntent ? result.name === expectedIntent : undefined;

  return (
    <div className="border border-border rounded-xl p-3 bg-muted/40">
      <div className="flex items-center gap-2">
        <Input
          className="flex-1"
          placeholder={placeholder ?? t('tester.placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void run(); }}
        />
        <Button
          type="button"
          onClick={() => void run()} disabled={busy || !text.trim()}
        >
          <Play /> {t('common:actions.test')}
        </Button>
      </div>

      {error && <div className={`mt-2 text-sm ${editedText}`}>{error}</div>}

      {result && (
        <div className="mt-2 text-sm">
          <div className="flex items-center gap-2">
            {matched === true && <CheckCircle2 className={`w-4 h-4 ${persistedText}`} />}
            {matched === false && <XCircle className={`w-4 h-4 ${conflictText}`} />}
            <span>
              {t('tester.recognized')} <b>{result.name}</b>
              {typeof result.confidence === 'number' && (
                <span className="text-muted-foreground"> ({Math.round(result.confidence * 100)}%)</span>
              )}
              {matched === false && expectedIntent && (
                <span className="text-destructive"> {t('tester.expected', { intent: expectedIntent })}</span>
              )}
            </span>
          </div>
          {Object.keys(entities).length > 0 && (
            <div className="mt-1 text-muted-foreground">
              {t('tester.values')}{' '}
              {Object.entries(entities).map(([k, v]) => (
                <span key={k} className="inline-block mr-2">
                  <span className="font-mono text-muted-foreground">{k}</span>=<b>{String(v)}</b>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
