import { useCallback, useMemo, useState, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

type SelectedFile = { file: File; id: string };

const VideoPreview = ({ previewUrl, onClear }: { previewUrl: string; onClear: () => void }) => (
  <div className="relative w-full h-full">
    <video src={previewUrl} controls className="object-contain w-full h-full rounded-xl shadow-lg" />
    <button
      type="button"
      onClick={onClear}
      className="absolute top-2.5 right-2.5 z-10 flex items-center justify-center w-8 h-8 transition duration-300 bg-black/60 rounded-full text-white/80 hover:bg-black/80 hover:scale-110"
      aria-label="Remove video"
    >
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
);

const IconWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 flex items-center justify-center">
    <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      {children}
    </svg>
  </div>
);

const ProTips = () => (
  <motion.div
    initial={{ opacity: 0, x: 20 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: 20 }}
    transition={{ duration: 0.3 }}
  >
    <h3 className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">Pro-Tips for Best Results</h3>
    <ul className="mt-4 space-y-4 text-sm text-zinc-600 dark:text-zinc-300">
      <li className="flex items-start gap-3">
        <IconWrapper><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></IconWrapper>
        <div>
          <span className="font-medium text-zinc-800 dark:text-zinc-100">Use Shorter Clips</span>
          <p className="mt-0.5">Clips between 10–30s process much faster.</p>
        </div>
      </li>
      <li className="flex items-start gap-3">
        <IconWrapper><path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.811 7.58 2 8.52 2 9.75v5.5C2 16.48 2.81 17.42 4.052 17.575c.377.063.754.121 1.134.175.603.086 1.21.149 1.83.188l.43.033a1.875 1.875 0 001.98-1.708V9.308a1.875 1.875 0 00-1.98-1.708l-.43.033c-.62.039-1.227.102-1.83.188zM19 11.25a.75.75 0 01.75-.75h.008a.75.75 0 01.75.75v.008a.75.75 0 01-.75.75h-.008a.75.75 0 01-.75-.75v-.008z" /></IconWrapper>
        <div>
          <span className="font-medium text-zinc-800 dark:text-zinc-100">Stable Camera Angle</span>
          <p className="mt-0.5">Broadcast-style views from the side-lines work best.</p>
        </div>
      </li>
      <li className="flex items-start gap-3">
        <IconWrapper><path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /><path strokeLinecap="round" strokeLinejoin="round" d="M15.91 11.672a.375.375 0 010 .656l-5.603 3.113a.375.375 0 01-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112z" /></IconWrapper>
        <div>
          <span className="font-medium text-zinc-800 dark:text-zinc-100">High Quality Video</span>
          <p className="mt-0.5">1080p, 60fps video significantly improves tracking.</p>
        </div>
      </li>
    </ul>
  </motion.div>
);

export default function UploadClip() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [meta, setMeta] = useState({ match: "", competition: "" });
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (files.length > 0) {
      const url = URL.createObjectURL(files[0].file);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [files]);

  const handleFiles = (newFiles: File[]) => {
    setError(null);
    if (!newFiles || newFiles.length === 0) return;
    const videoFile = newFiles[0];
    if (!videoFile.type.startsWith("video/")) {
      setError("Only video files are allowed.");
      setFiles([]);
      return;
    }
    setFiles([{ file: videoFile, id: `${videoFile.name}-${videoFile.size}-${videoFile.lastModified}` }]);
  };

  const onDrop = useCallback((accepted: File[]) => handleFiles(accepted), []);

  const { getRootProps, getInputProps, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: { "video/*": [] },
    multiple: false,
    maxFiles: 1,
  });

  const hasFile = files.length > 0 && previewUrl;

  const dropClasses = useMemo(() => {
    const base = "group relative flex h-full min-h-[20rem] w-full cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed transition-all duration-300";
    if (hasFile) return "p-0 border-transparent";
    const neutral = "border-zinc-300/70 dark:border-zinc-700/60 bg-white/40 dark:bg-zinc-900/30 backdrop-blur-sm";
    const accept = isDragAccept ? "border-emerald-500 bg-emerald-500/20 scale-105 shadow-xl" : "";
    const reject = isDragReject ? "border-red-500 bg-red-500/20 scale-105 shadow-xl" : "";
    const hover = "hover:border-indigo-400/80 dark:hover:border-indigo-400/70";
    return [base, neutral, accept, reject, hover].join(" ");
  }, [isDragAccept, isDragReject, hasFile]);

  const clearSelection = () => {
    setFiles([]);
    setError(null);
    setMeta({ match: "", competition: "" });
  };

  return (
    <div className="relative min-h-dvh px-4 py-8 md:py-16 flex items-center justify-center">
      {/* ===== NEW SIMPLE DOT-GRID BACKGROUND ===== */}
      <div
        className="absolute inset-0 -z-10 [background-image:radial-gradient(circle_at_1px_1px,theme(colors.zinc.300/50)_1px,transparent_0)] dark:[background-image:radial-gradient(circle_at_1px_1px,theme(colors.zinc.700/50)_1px,transparent_0)] [background-size:1.5rem_1.5rem]"
        aria-hidden="true"
      />

      {/* Main content card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="mx-auto w-full max-w-5xl rounded-2xl border p-6 shadow-lg lg:p-8 dark:border-zinc-700/60 bg-white/60 dark:bg-zinc-900/40 backdrop-blur-lg"
      >
        <div className="text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl text-zinc-700 dark:text-zinc-200">
            Analyze Your Match
          </h1>
          <p className="mt-3 text-lg text-zinc-600 dark:text-zinc-300">
            Upload a video clip to generate advanced tactical visualizations.
          </p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2 lg:items-start">
          {/* Left Column: Uploader / Preview */}
          <div className="w-full">
            <div {...getRootProps({ className: dropClasses })}>
              <input {...getInputProps()} />
              <AnimatePresence>
                {hasFile ? (
                  <motion.div key="preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="w-full h-full p-2">
                    <VideoPreview previewUrl={previewUrl!} onClear={clearSelection} />
                  </motion.div>
                ) : (
                  <div className="text-center px-6">
                    <svg className="mx-auto h-20 w-20 text-zinc-400 transition-transform duration-300 group-hover:scale-105 group-hover:text-indigo-400" aria-hidden="true" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9A2.25 2.25 0 0013.5 5.25h-9A2.25 2.25 0 002.25 7.5v9A2.25 2.25 0 004.5 18.75z" />
                    </svg>
                    <p className="mt-4 font-semibold text-zinc-700 dark:text-zinc-200">Drop video here or click to select</p>
                    <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Only a single video file is accepted.</p>
                  </div>
                )}
              </AnimatePresence>
            </div>
            {error && (
              <div className="mt-4 text-center rounded-lg border border-red-300/60 bg-red-50/80 px-3 py-2 text-sm text-red-700 dark:border-red-800/60 dark:bg-red-900/30 dark:text-red-200 backdrop-blur-sm">
                {error}
              </div>
            )}
          </div>

          {/* Right Column: Meta Form / Tips */}
          <div className="relative">
            <AnimatePresence initial={false} mode="wait">
              {hasFile ? (
                <motion.div key="meta-form" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.3 }}>
                  <h2 className="text-lg font-medium text-zinc-800 dark:text-zinc-100">Add Clip Details (Optional)</h2>
                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <div>
                      <label htmlFor="match-input" className="text-sm font-medium text-zinc-700 dark:text-zinc-200">Match</label>
                      <input
                        id="match-input"
                        type="text"
                        placeholder="Team A vs Team B"
                        value={meta.match}
                        onChange={(e) => setMeta((m) => ({ ...m, match: e.target.value }))}
                        className="mt-2 block w-full rounded-lg border bg-zinc-100/50 dark:bg-zinc-800/50 px-3 py-2 text-sm dark:border-zinc-700/60 focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition"
                      />
                    </div>
                    <div>
                      <label htmlFor="competition-input" className="text-sm font-medium text-zinc-700 dark:text-zinc-200">Competition</label>
                      <input
                        id="competition-input"
                        type="text"
                        placeholder="League / Cup"
                        value={meta.competition}
                        onChange={(e) => setMeta((m) => ({ ...m, competition: e.target.value }))}
                        className="mt-2 block w-full rounded-lg border bg-zinc-100/50 dark:bg-zinc-800/50 px-3 py-2 text-sm dark:border-zinc-700/60 focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition"
                      />
                    </div>
                  </div>
                  <div className="mt-6 flex flex-wrap items-center gap-4">
                    <button
                      type="button"
                      disabled={!hasFile}
                      onClick={() =>
                        navigate("/analyzing", {
                          state: { originalFileName: files[0].file.name, match: meta.match, competition: meta.competition },
                        })
                      }
                      className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-indigo-500 to-emerald-500 bg-[length:200%_auto] hover:bg-right focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      Upload & Analyze
                    </button>
                    <button
                      type="button"
                      onClick={clearSelection}
                      className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium ring-1 ring-inset ring-zinc-300 text-zinc-700 dark:text-zinc-200 transition hover:bg-zinc-100 dark:ring-zinc-600 dark:hover:bg-zinc-800"
                    >
                       <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0011.667 0l3.181-3.183m-4.991-2.691V5.006h-4.992v-.001M7.007 14.655L3.826 11.473a8.25 8.25 0 0111.667 0l3.181 3.183" />
                      </svg>
                      Change video
                    </button>
                  </div>
                </motion.div>
              ) : (
                <ProTips key="pro-tips" />
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  );
}