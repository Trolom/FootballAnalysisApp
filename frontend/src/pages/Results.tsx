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

  // Debugging: View this in F12 console if it fails
  console.log("Results received state:", state);

  const items = useMemo(() => {
    if (!jobData?.outputs) return [];
    
    return Object.entries(jobData.outputs).map(([key, path]) => {
      const filename = path.split('/').pop() || path;
      // Ensure path doesn't double up on /media/
      const cleanPath = path.startsWith('media/') ? path.replace('media/', '') : path;
      const url = `${API_BASE}/media/${cleanPath}`;

      return {
        key: key,
        filename: filename,
        url: url 
      };
    });
  }, [jobData]);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const videoRefs = useRef<Record<string, HTMLVideoElement | null>>({});

  // Initialize selection once items are loaded
  useEffect(() => {
    if (items.length > 0 && selected.size === 0) {
      setSelected(new Set(items.map(i => i.key)));
    }
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

  const handleDownloadSelected = async () => {
    // FIX: Check if jobData exists and has an ID
    if (!jobData?.id) {
      setError("Job ID missing. Cannot process download.");
      return;
    }
    if (selected.size === 0) {
      setError("Please select at least one file to download.");
      return;
    }

    const selectedKeys = Array.from(selected);
    const downloadUrl = `${API_BASE}/api/jobs/${jobData.id}/download/?which=${selectedKeys.join(',')}`;

    try {
      const res = await fetch(downloadUrl);
      if (!res.ok) throw new Error(`Download failed (${res.status})`);

      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = selectedKeys.length === 1 ? `${selectedKeys[0]}.mp4` : `analysis_results.zip`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(objectUrl);
      a.remove();
    } catch (e) {
      window.open(downloadUrl, "_blank");
    }
  };

  return (
    <div className="min-h-dvh px-4 py-8 md:py-16 bg-zinc-50 dark:bg-zinc-950">
      <div className="mx-auto w-full max-w-5xl space-y-6">
        <div>
          <h1 className="text-4xl font-bold text-zinc-800 dark:text-zinc-100">Analysis Complete</h1>
          <p className="mt-2 text-lg text-zinc-600 dark:text-zinc-400">
            Preview your generated visualizations below.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-4 shadow-sm bg-white dark:bg-zinc-900 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <button onClick={toggleAll} className="px-4 py-2 text-sm border rounded-xl dark:border-zinc-700">
              {allSelected ? "Deselect All" : "Select All"}
            </button>
            <button
              onClick={handleDownloadSelected}
              disabled={selected.size === 0}
              className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
            >
              Download Selected ({selected.size})
            </button>
          </div>
          <button onClick={() => navigate("/upload")} className="px-4 py-2 text-sm border rounded-xl dark:border-zinc-700">
            New Analysis
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-100 text-red-700 rounded-xl text-sm border border-red-200">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <div key={item.key} className="group relative overflow-hidden rounded-2xl border dark:border-zinc-800 bg-white dark:bg-zinc-900">
              <div className="absolute top-3 right-3 z-10">
                <input
                  type="checkbox"
                  checked={selected.has(item.key)}
                  onChange={() => toggleOne(item.key)}
                  className="h-5 w-5 rounded text-indigo-600"
                />
              </div>
              <video
                ref={(el) => { videoRefs.current[item.key] = el }}
                src={item.url}
                muted
                loop
                onMouseEnter={() => videoRefs.current[item.key]?.play()}
                onMouseLeave={() => videoRefs.current[item.key]?.pause()}
                className="aspect-video w-full object-cover bg-black"
              />
              <div className="p-4">
                <h3 className="font-bold text-zinc-800 dark:text-zinc-200">{deriveFriendlyName(item.key)}</h3>
                <p className="text-xs text-zinc-500">{item.filename}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}