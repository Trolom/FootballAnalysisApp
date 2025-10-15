import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

type ProducedItem = { filename: string };

type ResultState = {
  originalFileName?: string;
  match?: string;
  competition?: string;
  produced?: ProducedItem[];
};

// --- New: Utility to create a friendly title from a filename ---
function deriveFriendlyName(filename: string): string {
  const name = filename.slice(filename.lastIndexOf("__") + 2, filename.lastIndexOf("."));
  return name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

export default function Results() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as ResultState;

  const items = useMemo<ProducedItem[]>(
    () => state.produced || [],
    [state.produced]
  );

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const allSelected = selected.size === items.length && items.length > 0;

  const toggleOne = (name: string) => {
    setError(null);
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const toggleAll = () => {
    setError(null);
    setSelected(allSelected ? new Set() : new Set(items.map(i => i.filename)));
  };

  const handleDownloadSelected = () => {
    if (selected.size === 0) {
      setError("Please select at least one file to download.");
      return;
    }
    setError(null);
    // STUB DOWNLOAD LOGIC
    selected.forEach((name) => {
      const blob = new Blob([`Placeholder for ${name}`], { type: "text/plain" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${name}.placeholder.txt`;
      a.click();
      URL.revokeObjectURL(a.href);
    });
  };

  return (
    <div className="min-h-dvh px-4 py-8 md:py-16">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-zinc-800 dark:text-zinc-100">Analysis Complete</h1>
          <p className="mt-2 text-lg text-zinc-600 dark:text-zinc-400">
            Your visualizations are ready. Select files to download or start a new analysis.
          </p>
          {(state.match || state.competition) && (
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              {state.match ? `${state.match} • ` : ""}{state.competition || ""}
            </p>
          )}
        </div>

        {/* Actions & Error */}
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-4 shadow-sm dark:border-zinc-700/60 bg-white/60 dark:bg-zinc-900/40 backdrop-blur-lg">
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" onClick={toggleAll} className="rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-inset ring-zinc-300 hover:bg-zinc-100 dark:ring-zinc-600 dark:hover:bg-zinc-800">
              {allSelected ? "Deselect All" : "Select All"}
            </button>
            <button type="button" onClick={handleDownloadSelected} disabled={selected.size === 0} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed">
              Download Selected ({selected.size})
            </button>
          </div>
          <button type="button" onClick={() => navigate("/upload")} className="rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-inset ring-zinc-300 hover:bg-zinc-100 dark:ring-zinc-600 dark:hover:bg-zinc-800">
            Analyze Another Clip
          </button>
        </div>
        {error && <div className="rounded-lg border border-red-300/60 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800/60 dark:bg-red-900/20 dark:text-red-200">{error}</div>}

        {/* Results Grid */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div key={item.filename} className="group relative overflow-hidden rounded-2xl border dark:border-zinc-700/60 transition-all duration-300">
              <div className="absolute top-3 right-3 z-10">
                <input type="checkbox" checked={selected.has(item.filename)} onChange={() => toggleOne(item.filename)} className="h-5 w-5 rounded border-zinc-400/50 text-indigo-600 focus:ring-indigo-500" />
              </div>

              {/* Video Placeholder */}
              <div className="aspect-video w-full bg-zinc-200 dark:bg-zinc-800 flex items-center justify-center">
                  <svg className="h-12 w-12 text-zinc-400 dark:text-zinc-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="m15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z" />
                  </svg>
              </div>

              {/* Info */}
              <div className="p-4 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm">
                <h3 className="font-medium truncate">{deriveFriendlyName(item.filename)}</h3>
                <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate">{item.filename}</p>
              </div>
            </div>
          ))}
          {items.length === 0 && <p className="col-span-full text-center text-zinc-500">No results found.</p>}
        </div>

      </div>
    </div>
  );
}