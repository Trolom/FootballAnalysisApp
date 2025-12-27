import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export default function Analyzing() {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId, originalFileName, match, competition } = (location.state || {}) as any;

  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("Connecting to server...");

  useEffect(() => {
    // 1. Safety check: if no Job ID, we can't track anything
    if (!jobId) {
      navigate("/upload");
      return;
    }

    // 2. Establish WebSocket connection
    // We connect to the 'backend' service via localhost since the browser is outside Docker
    const socket = new WebSocket(`ws://127.0.0.1:8000/ws/jobs/${jobId}/`);

    socket.onopen = () => {
      setStatusText("Initializing analysis...");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Update the progress bar percentage
      if (data.progress !== undefined) {
        setProgress(data.progress);
      }
      
      // Update descriptive text based on backend progress
      if (data.status === "processing") {
        if (data.progress < 30) setStatusText("Reading video frames...");
        else if (data.progress < 60) setStatusText("Detecting players and ball...");
        else if (data.progress < 80) setStatusText("Assigning teams...");
        else setStatusText("Generating visualizations...");
      }

      // Handle Completion
      if (data.status === "done") {
        setProgress(100);
        setTimeout(() => {
          navigate("/results", {
            state: {
              ...location.state,
              jobData: {
                id: jobId,           // CRITICAL: Ensure this is here
                outputs: data.outputs,
                status: data.status
              },
            },
          });
        }, 800);
      }

      // Handle Failure
      if (data.status === "failed") {
        alert(`Analysis failed: ${data.error || "Unknown error"}`);
        navigate("/upload");
      }
    };

    socket.onerror = (err) => {
      console.error("WebSocket Error:", err);
      setStatusText("Connection error. Retrying...");
    };

    // 3. Cleanup: Close socket if user leaves the page
    return () => {
      socket.close();
    };
  }, [jobId, navigate, location.state]);

  return (
    <div className="min-h-dvh flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4">
      <div className="w-full max-w-lg">
        {/* Header Section */}
        <div className="text-center mb-8 space-y-2">
          <h2 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            Analyzing Footage
          </h2>
          <div className="flex flex-col items-center text-zinc-500 dark:text-zinc-400">
            <span className="font-medium text-zinc-700 dark:text-zinc-300">
              {originalFileName || "video_clip.mp4"}
            </span>
            <span className="text-sm">
              {match ? `${match} ` : ""}{competition ? `• ${competition}` : ""}
            </span>
          </div>
        </div>

        {/* Main Status Card */}
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-8 shadow-xl shadow-zinc-200/50 dark:shadow-none">
          <div className="flex justify-between items-end mb-4">
            <div className="flex items-center gap-3">
              {/* Spinning Loader */}
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
              <span className="text-sm font-semibold text-indigo-600 dark:text-indigo-400">
                {statusText}
              </span>
            </div>
            <span className="text-4xl font-black text-zinc-900 dark:text-zinc-100">
              {progress}%
            </span>
          </div>

          {/* Intuitive Progress Bar */}
          <div className="relative h-4 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
            {/* Animated Gradient Fill */}
            <div
              className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-500 bg-[length:200%_100%] animate-shimmer transition-all duration-700 ease-out rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
          
          <div className="mt-8 grid grid-cols-2 gap-4 text-center text-xs text-zinc-400 border-t border-zinc-100 dark:border-zinc-800 pt-6">
            <div>
              <p className="font-bold text-zinc-500 dark:text-zinc-300 uppercase tracking-widest">Device</p>
              <p>GPU Accelerated</p>
            </div>
            <div>
              <p className="font-bold text-zinc-500 dark:text-zinc-300 uppercase tracking-widest">Status</p>
              <p>Live Streamed</p>
            </div>
          </div>
        </div>

        <p className="mt-6 text-center text-sm text-zinc-400">
          Please do not refresh the page while processing is active.
        </p>
      </div>
    </div>
  );
}