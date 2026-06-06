/**
 * DonationValidationPanel (UI-5) — surfaces the QUAL-42 backend services for one handler:
 *   - the contract↔code WIRING report (GET /donations/validation): unwired methods (fatal, normally caught at
 *     boot) + soft warnings (declared-but-unread params, undeclared handler methods);
 *   - LLM translation VALIDATION (POST .../validate-translation): meaning/consistency QA across languages;
 *   - the LLM translation SERVICE (POST .../translate): draft target-language phrases from a source language.
 *
 * Both LLM actions degrade gracefully: when no API-keyed LLM is configured the backend returns
 * llm_available=false with a "validate/translate manually" message, which we show as-is.
 */

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, AlertCircle, AlertTriangle, CheckCircle2, Languages } from 'lucide-react';
import apiClient from '@/utils/apiClient';
import type {
  ContractWiringReport, TranslationIssue, TranslatedMethod,
} from '@/types';

interface DonationValidationPanelProps {
  handlerName: string;
  sourceLanguage: string;
  availableLanguages: string[];
  disabled?: boolean;
}

export default function DonationValidationPanel({
  handlerName, sourceLanguage, availableLanguages, disabled = false,
}: DonationValidationPanelProps) {
  const [wiring, setWiring] = useState<ContractWiringReport | null>(null);
  const [wiringLoading, setWiringLoading] = useState(false);

  const [target, setTarget] = useState<string>('');
  const [llmBusy, setLlmBusy] = useState(false);
  const [llmMessage, setLlmMessage] = useState<string | null>(null);
  const [issues, setIssues] = useState<TranslationIssue[] | null>(null);
  const [drafts, setDrafts] = useState<TranslatedMethod[] | null>(null);

  const loadWiring = useCallback(async () => {
    setWiringLoading(true);
    try {
      const report = await apiClient.getContractValidation();
      setWiring((report.handlers ?? []).find((h) => h.handler_name === handlerName) ?? null);
    } catch {
      setWiring(null);
    } finally {
      setWiringLoading(false);
    }
  }, [handlerName]);

  useEffect(() => { void loadWiring(); }, [loadWiring]);

  // Default the translation target to the first language that isn't the source.
  useEffect(() => {
    if (!target || target === sourceLanguage) {
      setTarget(availableLanguages.find((l) => l !== sourceLanguage) ?? '');
    }
  }, [availableLanguages, sourceLanguage, target]);

  const runValidate = useCallback(async () => {
    setLlmBusy(true); setIssues(null); setDrafts(null); setLlmMessage(null);
    try {
      const res = await apiClient.validateTranslation(handlerName);
      setLlmMessage(res.message);
      setIssues(res.llm_available ? (res.issues ?? []) : null);
    } catch (e) {
      setLlmMessage(e instanceof Error ? e.message : 'Translation validation failed');
    } finally {
      setLlmBusy(false);
    }
  }, [handlerName]);

  const runTranslate = useCallback(async () => {
    if (!target) return;
    setLlmBusy(true); setIssues(null); setDrafts(null); setLlmMessage(null);
    try {
      const res = await apiClient.translateDonation(handlerName, {
        sourceLanguage, targetLanguage: target,
      });
      setLlmMessage(res.message);
      setDrafts(res.llm_available ? (res.translations ?? []) : null);
    } catch (e) {
      setLlmMessage(e instanceof Error ? e.message : 'Translation failed');
    } finally {
      setLlmBusy(false);
    }
  }, [handlerName, sourceLanguage, target]);

  const errors = wiring?.errors ?? [];
  const warnings = wiring?.warnings ?? [];

  return (
    <div className="border rounded-xl bg-white p-4 space-y-4">
      {/* Wiring (contract <-> code) */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm font-semibold text-gray-900">Contract ↔ code wiring</div>
          <button
            className="inline-flex items-center gap-1 text-xs px-2 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
            onClick={() => void loadWiring()} disabled={wiringLoading} title="Refresh"
          >
            <RefreshCw className={`w-3 h-3 ${wiringLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
        {errors.length === 0 && warnings.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-green-700">
            <CheckCircle2 className="w-4 h-4" /> Methods and parameters are wired to the handler.
          </div>
        ) : (
          <div className="space-y-1">
            {errors.map((e, i) => (
              <div key={`e${i}`} className="flex items-start gap-2 text-sm text-red-700">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" /> <span>{e}</span>
              </div>
            ))}
            {warnings.map((w, i) => (
              <div key={`w${i}`} className="flex items-start gap-2 text-sm text-amber-700">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /> <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* LLM translation validation + drafting */}
      <div className="border-t pt-3">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <Languages className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-semibold text-gray-900">Translation (LLM)</span>
          <span className="text-xs text-gray-500">from <b>{sourceLanguage}</b> to</span>
          <select
            className="border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            value={target} onChange={(e) => setTarget(e.target.value)} disabled={disabled || llmBusy}
          >
            {availableLanguages.filter((l) => l !== sourceLanguage).map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
          <button
            className="text-xs px-3 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-50"
            onClick={() => void runValidate()} disabled={disabled || llmBusy}
          >
            Validate quality
          </button>
          <button
            className="text-xs px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            onClick={() => void runTranslate()} disabled={disabled || llmBusy || !target}
          >
            Draft translations
          </button>
          {llmBusy ? <RefreshCw className="w-4 h-4 animate-spin text-gray-400" /> : null}
        </div>

        {llmMessage ? <div className="text-sm text-gray-600 mb-2">{llmMessage}</div> : null}

        {issues && issues.length > 0 ? (
          <div className="space-y-1">
            {issues.map((it, i) => (
              <div key={i} className="flex items-start gap-2 text-sm text-amber-700">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span><b>{it.language}</b>{it.method_key ? ` · ${it.method_key}` : ''}: {it.message}</span>
              </div>
            ))}
          </div>
        ) : null}

        {drafts && drafts.length > 0 ? (
          <div className="space-y-2">
            {drafts.map((d, i) => (
              <div key={i} className="border rounded-lg p-2">
                <div className="text-xs font-mono text-gray-600 mb-1">{d.method_key}</div>
                <ul className="list-disc list-inside text-sm text-gray-800">
                  {(d.suggested_phrases ?? []).map((p, j) => <li key={j}>{p}</li>)}
                </ul>
              </div>
            ))}
            <p className="text-xs text-gray-500">Drafts are suggestions — copy the ones you want into the phrasing editor.</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
