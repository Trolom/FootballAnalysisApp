import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

type UploadState = {
  originalFileName?: string;
  match?: string;
  competition?: string;
};

function deriveProduced(original?: string) {
  const base =
    (original && original.includes("."))
      ? original.slice(0, original.lastIndexOf("."))
      : (original || "clip");
  return [
    { filename: `${base}__tactical_overlays.mp4` },
    { filename: `${base}__ball_tracking.mp4` },
    { filename: `${base}__voronoi_control.mp4` },
  ];
}

export default function Analyzing() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as UploadState;

  const [progress, setProgress] = useState(0);

  // Simulate progress to 100%, then navigate to /results with produced file names.
  useEffect(() => {
    const id = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) return 100;
        return Math.min(100, p + 5);
      });
    }, 300);
    return () => clearInterval(id);
  }, []);

  // When progress completes, redirect to /results with state
  const produced = useMemo(() => deriveProduced(state.originalFileName), [state.originalFileName]);

  useEffect(() => {
    if (progress >= 100) {
      const timer = setTimeout(() => {
        navigate("/results", {
          state: {
            originalFileName: state.originalFileName,
            match: state.match,
            competition: state.competition,
            produced,
          },
        });
      }, 800); // small pause to show 100%
      return () => clearTimeout(timer);
    }
  }, [progress, navigate, produced, state.originalFileName, state.match, state.competition]);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-zinc-200/60 p-6 dark:border-zinc-700/60">
        <h1 className="text-2xl font-semibold">Analyzing…</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-300">
          Processing your clip.
        </p>
      </div>

      <div className="rounded-2xl border p-6 dark:border-zinc-700/60">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-300 border-t-transparent dark:border-zinc-700 dark:border-t-transparent" />
          <div className="min-w-0">
            <div className="truncate text-sm font-medium">
              {state.originalFileName || "clip.mp4"}
            </div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              {state.match ? `${state.match} • ` : ""}
              {state.competition || ""}
            </div>
          </div>
        </div>

        <div className="mt-6">
          <div className="h-2 w-full rounded-full bg-zinc-200 dark:bg-zinc-800">
            <div
              className="h-2 rounded-full bg-zinc-600 transition-[width] dark:bg-zinc-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="mt-2 text-right text-xs text-zinc-500 dark:text-zinc-400">
            {progress}%
          </div>
        </div>
      </div>
    </div>
  );
}
