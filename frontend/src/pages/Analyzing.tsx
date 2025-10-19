import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

// Define a more accurate type for the state passed to this page
type AnalyzingState = {
  jobId?: number; // The REAL job ID from the upload page
  originalFileName?: string;
  match?: string;
  competition?: string;
};

export default function Analyzing() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state || {}) as AnalyzingState;
  const { jobId } = state;

  // This progress is now just for show, the real logic is in the polling effect
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // If we land on this page without a jobId, something is wrong. Redirect to upload.
    if (!jobId) {
      navigate("/upload");
      return;
    }

    // This interval will poll the backend for the job status
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`http://127.0.0.1:8000/api/jobs/${jobId}/`);
        if (!response.ok) {
           // Handle network errors
           throw new Error('Network response was not ok');
        }
        const data = await response.json();

        // --- Main Logic ---
        if (data.status === "done") {
          clearInterval(pollInterval); // Stop polling
          setProgress(100);

          // Give a moment to show 100% then navigate to results
          setTimeout(() => {
            navigate("/results", {
              state: {
                ...state, // Pass along original info (filename, match, etc.)
                jobData: data, // Pass the full, final job data from the API
              },
            });
          }, 800);

        } else if (data.status === "failed" || data.status === "error") {
          clearInterval(pollInterval);
          // In a real app, you might navigate to an error page or show a modal
          alert(`Analysis failed: ${data.error || 'Unknown error'}`);
          navigate("/upload");

        } else {
          // It's still "pending" or "processing", so we just update the visual progress bar
          // Don't let the fake progress hit 100%, as that's reserved for a "done" status
          setProgress((p) => Math.min(95, p + 5));
        }
      } catch (error) {
        console.error("Polling error:", error);
        clearInterval(pollInterval); // Stop polling on a network error
        alert("Could not connect to the server to check status.");
        navigate("/upload");
      }
    }, 2000); // Poll the backend every 2 seconds

    // Cleanup function to stop polling if the user navigates away
    return () => clearInterval(pollInterval);
  }, [jobId, navigate, state]); // Effect dependencies

  return (
    <div className="min-h-dvh flex items-center justify-center p-4">
        <div className="w-full max-w-2xl space-y-6">
            <div className="rounded-2xl border border-zinc-200/60 p-6 text-center dark:border-zinc-700/60">
                <h1 className="text-3xl font-bold tracking-tight">Analyzing Your Clip</h1>
                <p className="mt-2 text-zinc-600 dark:text-zinc-300">
                    This may take a moment. Advanced visualizations are being generated.
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
                            {state.match ? `${state.match} • ` : ""} {state.competition || ""}
                        </div>
                    </div>
                </div>

                <div className="mt-6">
                    <div className="h-2 w-full rounded-full bg-zinc-200 dark:bg-zinc-800">
                        <div
                            className="h-2 rounded-full bg-indigo-600 transition-[width] duration-300 dark:bg-indigo-400"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <div className="mt-2 text-right text-xs font-medium text-zinc-500 dark:text-zinc-400">
                        {progress}%
                    </div>
                </div>
            </div>
        </div>
    </div>
  );
}