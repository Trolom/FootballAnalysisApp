import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

type ResultState = {
  jobData?: {
    id: number;
    outputs: { [key: string]: string };
  };
  originalFileName?: string;
  match?: string;
  competition?: string;
};

function deriveFriendlyName(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

const API_BASE = "http://127.0.0.1:8000";

export default function Results() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as ResultState;
  const { jobData } = state;

  // --- THIS BLOCK IS CORRECTED ---
  const items = useMemo<{ filename: string; key: string; url: string }[]>(() => {
    if (!jobData?.outputs) return [];
    
    return Object.entries(jobData.outputs).map(([key, path]) => {
      const filename = path.split('/').pop() || path;
      
      // THE FIX: We construct the URL by adding the "/media/" prefix.
      const url = `${API_BASE}/media/${path}`;

      return {
        key: key,
        filename: filename,
        url: url 
      };
    });
  }, [jobData]);

  const [selected, setSelected] = useState<Set<string>>(new Set(items.map(i => i.key)));
  const [error, setError] = useState<string | null>(null);
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  useEffect(() => {
    setSelected((prev) => {
      const next = new Set<string>();
      const allowed = new Set(items.map((i) => i.key));
      for (const k of prev) if (allowed.has(k)) next.add(k);
      return next.size > 0 ? next : new Set(items.map(i => i.key)); // Select all by default
    });
  }, [items]);

  const allSelected = selected.size === items.length && items.length > 0;

  const toggleOne = (key: string) => {
    setError(null);
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const toggleAll = () => {
    setError(null);
    setSelected(allSelected ? new Set() : new Set(items.map((i) => i.key)));
  };

  function filenameFromContentDisposition(cd: string | null): string | null {
    if (!cd) return null;
    const matchStar = /filename\*\s*=\s*UTF-8''([^;]+)$/i.exec(cd);
    if (matchStar) return decodeURIComponent(matchStar[1]);
    const matchQuoted = /filename\s*=\s*"([^"]+)"/i.exec(cd);
    if (matchQuoted) return matchQuoted[1];
    const matchBare = /filename\s*=\s*([^;]+)/i.exec(cd);
    if (matchBare) return matchBare[1].trim();
    return null;
  }

  const handleDownloadSelected = async () => {
    if (selected.size === 0 || !jobData) {
      setError("Please select at least one file to download.");
      return;
    }
    setError(null);

    const selectedKeys = Array.from(selected);
    const downloadUrl = `${API_BASE}/api/jobs/${jobData.id}/download/?which=${selectedKeys.join(',')}`;

    try {
      const res = await fetch(downloadUrl);
      if (!res.ok) {
        throw new Error(`Download failed (${res.status})`);
      }

      const blob = await res.blob();
      const cd = filenameFromContentDisposition(res.headers.get("Content-Disposition"));
      const defaultName = selectedKeys.length === 1
          ? items.find((i) => i.key === selectedKeys[0])?.filename || "download.mp4"
          : `job_${jobData.id}_assets.zip`;
      const finalName = cd || defaultName;

      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = finalName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (e: any) {
      console.warn("Direct fetch failed, falling back to window.open:", e);
      const w = window.open(downloadUrl, "_blank", "noopener,noreferrer");
      if (!w) {
        setError("Popup blocked. Please allow popups for this site.");
      }
    }
  };

  return (
    <div className="min-h-dvh px-4 py-8 md:py-16">
      <div className="mx-auto w-full max-w-5xl space-y-6">
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

        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-4 shadow-sm dark:border-zinc-700/60 bg-white/60 dark:bg-zinc-900/40 backdrop-blur-lg">
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={toggleAll}
              className="rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-inset ring-zinc-300 hover:bg-zinc-100 dark:ring-zinc-600 dark:hover:bg-zinc-800"
            >
              {allSelected ? "Deselect All" : "Select All"}
            </button>
            <button
              type="button"
              onClick={handleDownloadSelected}
              disabled={selected.size === 0}
              className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Download Selected ({selected.size})
            </button>
          </div>
          <button
            type="button"
            onClick={() => navigate("/upload")}
            className="rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-inset ring-zinc-300 hover:bg-zinc-100 dark:ring-zinc-600 dark:hover:bg-zinc-800"
          >
            Analyze Another Clip
          </button>
        </div>

        {error && (
          <div className="rounded-lg border border-red-300/60 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800/60 dark:bg-red-900/20 dark:text-red-200">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => {
            return (
              <div
                key={item.key}
                className="group relative overflow-hidden rounded-2xl border dark:border-zinc-700/60"
              >
                <div className="absolute top-3 right-3 z-10">
                  <input
                    type="checkbox"
                    checked={selected.has(item.key)}
                    onChange={() => toggleOne(item.key)}
                    className="h-5 w-5 rounded border-zinc-400/50 text-indigo-600 focus:ring-indigo-500"
                  />
                </div>

                <div
                  className="aspect-video w-full bg-zinc-900"
                  onMouseEnter={() => videoRefs.current[item.key]?.play()}
                  onMouseLeave={() => videoRefs.current[item.key]?.pause()}
                >
                  <video
                    ref={(el) => { videoRefs.current[item.key] = el }}
                    src={item.url}
                    loop
                    muted
                    playsInline
                    preload="metadata"
                    className="aspect-video w-full object-cover"
                  />
                </div>

                <div className="p-4 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm">
                  <h3 className="font-medium truncate">{deriveFriendlyName(item.key)}</h3>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate">{item.filename}</p>
                </div>
              </div>
            );
          })}

          {items.length === 0 && (
            <div className="col-span-full text-center py-12">
              <h3 className="text-lg font-semibold text-zinc-700 dark:text-zinc-200">No Results Found</h3>
              <p className="mt-1 text-sm text-zinc-500">The analysis did not produce any output files.</p>
              <button
                type="button"
                onClick={() => navigate("/upload")}
                className="mt-4 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-700"
              >
                Start a New Analysis
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}