import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import UploadClip from "./pages/UploadClip";
import Analyzing from "./pages/Analyzing";
import Results from "./pages/Results";

export default function App() {
  return (
    <BrowserRouter>
      <main className="min-h-dvh">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadClip />} />
          <Route path="/analyzing" element={<Analyzing />} />
          <Route path="/results" element={<Results />} />
          <Route path="*" element={<Navigate to="/upload" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}