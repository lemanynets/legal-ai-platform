"use client";

import React, { useRef, useState } from "react";

import {
  autoProcessDocument,
  getErrorMessage,
  type AutoProcessResponse,
} from "@/lib/api";

type StreamEvent = {
  step?: string;
  status?: string;
  message?: string;
  result?: AutoProcessResponse;
};

export default function AutoProcessPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AutoProcessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
    setResult(null);
    setError(null);
    setEvents([]);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;

    setLoading(true);
    setResult(null);
    setError(null);
    setEvents([]);

    try {
      const response = await autoProcessDocument({ file }, (streamEvent: StreamEvent) => {
        setEvents((prev) => [...prev, streamEvent]);
      });
      setResult(response);
    } catch (nextError: unknown) {
      setError(getErrorMessage(nextError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Автоматична обробка документів
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Завантаж документ, і система спробує визначити тип, провести аналіз та
          підготувати процесуальні документи.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="auto-process-file"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Файл (txt/pdf/docx)
          </label>
          <input
            id="auto-process-file"
            ref={fileInputRef}
            type="file"
            accept=".txt,.pdf,.docx,.doc"
            onChange={handleFileChange}
            aria-label="Файл (txt/pdf/docx)"
            className="block w-full text-sm text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer bg-gray-50 dark:bg-gray-800 focus:outline-none p-2"
          />
        </div>

        <button
          type="submit"
          disabled={!file || loading}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z"
                />
              </svg>
              Обробляємо...
            </>
          ) : (
            "Запустити автообробку"
          )}
        </button>
      </form>

      {events.length > 0 && !result && (
        <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-4 space-y-1 max-h-48 overflow-y-auto">
          {events.map((event, index) => (
            <div
              key={`${event.step || "event"}-${index}`}
              className="text-xs text-gray-600 dark:text-gray-400 font-mono"
            >
              [{event.step ?? "info"}] {event.status ?? ""} {event.message ?? ""}
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 text-sm text-red-700 dark:text-red-300">
          <strong>Помилка:</strong> {error}
        </div>
      )}

      {result && (
        <div className="space-y-5">
          <div className="rounded-lg border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 p-4">
            <h2 className="font-semibold text-green-800 dark:text-green-300 text-sm mb-2">
              Результат обробки: {result.source_file_name}
            </h2>
            <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
              <p>Витягнуто символів: {result.extracted_chars}</p>
              <p>Процесуальний режим: {result.processual_only_mode ? "Так" : "Ні"}</p>
              <p>Згенеровано документів: {result.generated_documents.length}</p>
            </div>
          </div>

          {result.procedural_conclusions.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-2">
                Процесуальні висновки
              </h3>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-700 dark:text-gray-300">
                {result.procedural_conclusions.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {result.recommended_doc_types.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-2">
                Рекомендовані типи документів
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.recommended_doc_types.map((item) => (
                  <span
                    key={item}
                    className="px-2 py-1 bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300 rounded text-xs font-mono"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.generated_documents.length > 0 && (
            <div>
              <h3 className="font-semibold text-gray-800 dark:text-gray-200 text-sm mb-3">
                Згенеровані документи
              </h3>
              <div className="space-y-3">
                {result.generated_documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
                          {doc.title}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono mt-0.5">
                          {doc.doc_type}
                        </p>
                      </div>
                      {doc.used_ai && (
                        <span className="shrink-0 px-2 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded text-xs">
                          AI: {doc.ai_model || "unknown"}
                        </span>
                      )}
                    </div>
                    {doc.preview_text && (
                      <p className="mt-2 text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
                        {doc.preview_text}
                      </p>
                    )}
                    <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                      {new Date(doc.created_at).toLocaleString("uk-UA")}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20 p-4">
              <h3 className="font-semibold text-yellow-800 dark:text-yellow-300 text-sm mb-2">
                Попередження
              </h3>
              <ul className="list-disc list-inside space-y-1 text-sm text-yellow-700 dark:text-yellow-400">
                {result.warnings.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
