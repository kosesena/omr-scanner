import { useState, useCallback, useRef, useEffect } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import {
  Camera, FileText, BarChart3, Settings, ChevronRight,
  CheckCircle, XCircle, AlertTriangle, Download, Plus,
  Scan, RotateCcw, Users, Trophy, Target, Upload
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

// ============================================================
// Utility
// ============================================================
function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

// ============================================================
// Components
// ============================================================

function Header({ page, setPage, session }) {
  const tabs = [
    { id: "setup", label: "Setup", icon: Settings },
    { id: "scan", label: "Scan", icon: Scan },
    { id: "results", label: "Results", icon: BarChart3 },
  ];
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="max-w-2xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <h1 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Scan className="w-5 h-5 text-blue-500" />
            OMR Scanner
          </h1>
          {session && (
            <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full">
              {session.num_questions}Q
            </span>
          )}
        </div>
        <nav className="flex gap-1 -mb-px">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setPage(t.id)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
                page === t.id
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              )}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}

// ==================== SETUP PAGE ====================

function SetupPage({ session, setSession, setPage }) {
  const [numQ, setNumQ] = useState(40);
  const [keys, setKeys] = useState({});
  const [loading, setLoading] = useState(false);
  const [formLoading, setFormLoading] = useState(false);

  const options = ["A", "B", "C", "D", "E"];

  const setAnswer = (q, ans) => {
    setKeys((prev) => ({ ...prev, [String(q)]: ans }));
  };

  const fillRandom = () => {
    const k = {};
    for (let i = 1; i <= numQ; i++) {
      k[String(i)] = options[Math.floor(Math.random() * options.length)];
    }
    setKeys(k);
  };

  const createSession = async () => {
    const filled = Object.keys(keys).length;
    if (filled < numQ) {
      alert(`Please fill all ${numQ} answers. Currently: ${filled}`);
      return;
    }
    setLoading(true);
    try {
      const res = await axios.post(`${API}/api/sessions/create`, {
        answers: keys,
        num_questions: numQ,
      });
      setSession({ ...res.data, answer_key: keys });
      setPage("scan");
    } catch (e) {
      alert("Error creating session: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const downloadForm = async () => {
    setFormLoading(true);
    try {
      const res = await axios.get(`${API}/api/forms/download/${numQ}`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `optik_form_${numQ}q.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Error downloading form");
    }
    setFormLoading(false);
  };

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-6">
      {/* Question count */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
        <h2 className="font-semibold text-slate-900 dark:text-white mb-3">Exam setup</h2>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="text-sm text-slate-600 dark:text-slate-400">Questions:</label>
          <div className="flex gap-2">
            {[20, 40, 60, 80, 100].map((n) => (
              <button
                key={n}
                onClick={() => { setNumQ(n); setKeys({}); }}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
                  numQ === n
                    ? "bg-blue-500 text-white shadow-md"
                    : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={downloadForm}
          disabled={formLoading}
          className="mt-3 flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          <Download className="w-4 h-4" />
          {formLoading ? "Downloading..." : "Download printable form (PDF)"}
        </button>
      </div>

      {/* Answer key */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-900 dark:text-white">Answer key</h2>
          <button
            onClick={fillRandom}
            className="text-xs text-blue-500 hover:underline"
          >
            Fill random (for testing)
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {Array.from({ length: numQ }, (_, i) => i + 1).map((q) => (
            <div key={q} className="flex items-center gap-1">
              <span className="text-xs text-slate-500 w-6 text-right">{q}.</span>
              <div className="flex gap-0.5">
                {options.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setAnswer(q, opt)}
                    className={cn(
                      "w-7 h-7 rounded-full text-xs font-bold transition-all",
                      keys[String(q)] === opt
                        ? "bg-blue-500 text-white scale-110 shadow"
                        : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200"
                    )}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-slate-500">
            {Object.keys(keys).length}/{numQ} filled
          </span>
          <button
            onClick={createSession}
            disabled={loading}
            className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium text-sm transition-all shadow-md hover:shadow-lg disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? "Creating..." : "Start scanning"}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ==================== SCAN PAGE ====================

function ScanPage({ session, setResults, results }) {
  const webcamRef = useRef(null);
  const fileInputRef = useRef(null);
  const [scanning, setScanning] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [useCamera, setUseCamera] = useState(true);
  const [facingMode, setFacingMode] = useState("environment");

  const capture = useCallback(async () => {
    if (!webcamRef.current) return;
    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) return;
    await processImage(imageSrc);
  }, [session]);

  const processImage = async (base64Image) => {
    setScanning(true);
    try {
      const formData = new FormData();
      formData.append("image_base64", base64Image);
      formData.append("num_questions", session.num_questions);
      if (session.session_id) {
        formData.append("session_id", session.session_id);
      }
      if (session.answer_key) {
        formData.append("answer_key", JSON.stringify(session.answer_key));
      }

      const res = await axios.post(`${API}/api/scan/base64`, formData);
      setLastResult(res.data);
      setResults((prev) => [...prev, res.data]);
    } catch (e) {
      setLastResult({
        success: false,
        error: e.response?.data?.detail || e.message,
      });
    }
    setScanning(false);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanning(true);
    try {
      const formData = new FormData();
      formData.append("image", file);
      formData.append("num_questions", session.num_questions);
      if (session.session_id) {
        formData.append("session_id", session.session_id);
      }
      if (session.answer_key) {
        formData.append("answer_key", JSON.stringify(session.answer_key));
      }

      const res = await axios.post(`${API}/api/scan`, formData);
      setLastResult(res.data);
      setResults((prev) => [...prev, res.data]);
    } catch (e) {
      setLastResult({
        success: false,
        error: e.response?.data?.detail || e.message,
      });
    }
    setScanning(false);
    e.target.value = "";
  };

  if (!session) {
    return (
      <div className="max-w-2xl mx-auto p-4 text-center text-slate-500 mt-20">
        <Scan className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Create a session first in Setup tab</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-4">
      {/* Camera / Upload toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setUseCamera(true)}
          className={cn(
            "flex-1 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all",
            useCamera
              ? "bg-blue-500 text-white"
              : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
          )}
        >
          <Camera className="w-4 h-4" /> Camera
        </button>
        <button
          onClick={() => setUseCamera(false)}
          className={cn(
            "flex-1 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all",
            !useCamera
              ? "bg-blue-500 text-white"
              : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
          )}
        >
          <Upload className="w-4 h-4" /> Upload
        </button>
      </div>

      {/* Camera view */}
      {useCamera ? (
        <div className="relative rounded-xl overflow-hidden bg-black aspect-[3/4]">
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            screenshotQuality={0.95}
            videoConstraints={{
              facingMode,
              width: { ideal: 1920 },
              height: { ideal: 2560 },
            }}
            className="w-full h-full object-cover"
          />
          {/* Overlay guide */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute inset-8 border-2 border-white/40 rounded-lg" />
            <div className="absolute top-10 left-10 w-8 h-8 border-t-3 border-l-3 border-blue-400 rounded-tl-md" />
            <div className="absolute top-10 right-10 w-8 h-8 border-t-3 border-r-3 border-blue-400 rounded-tr-md" />
            <div className="absolute bottom-10 left-10 w-8 h-8 border-b-3 border-l-3 border-blue-400 rounded-bl-md" />
            <div className="absolute bottom-10 right-10 w-8 h-8 border-b-3 border-r-3 border-blue-400 rounded-br-md" />
          </div>

          {/* Controls */}
          <div className="absolute bottom-4 inset-x-4 flex items-center justify-center gap-4">
            <button
              onClick={() => setFacingMode(f => f === "environment" ? "user" : "environment")}
              className="p-3 bg-white/20 backdrop-blur rounded-full text-white hover:bg-white/30"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
            <button
              onClick={capture}
              disabled={scanning}
              className="w-16 h-16 bg-white rounded-full shadow-lg flex items-center justify-center hover:scale-105 transition-transform disabled:opacity-50"
            >
              {scanning ? (
                <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              ) : (
                <div className="w-12 h-12 bg-blue-500 rounded-full" />
              )}
            </button>
            <div className="w-11" /> {/* spacer */}
          </div>
        </div>
      ) : (
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400 transition-colors"
        >
          <Upload className="w-10 h-10 mx-auto mb-3 text-slate-400" />
          <p className="text-sm text-slate-500">Tap to select a photo of the answer sheet</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileUpload}
            className="hidden"
          />
        </div>
      )}

      {/* Scan count */}
      <div className="text-center text-sm text-slate-500">
        {results.filter(r => r.success).length} sheets scanned
      </div>

      {/* Last result */}
      {lastResult && <ResultCard result={lastResult} answerKey={session.answer_key} />}
    </div>
  );
}

function ResultCard({ result, answerKey }) {
  const [expanded, setExpanded] = useState(false);

  if (!result.success) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
        <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
          <XCircle className="w-5 h-5" />
          <span className="font-medium">Scan failed</span>
        </div>
        <p className="text-sm text-red-500 mt-1">{result.error}</p>
      </div>
    );
  }

  const scoreColor =
    result.score >= 70 ? "text-green-600" :
    result.score >= 50 ? "text-amber-600" : "text-red-600";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500">Student ID</p>
            <p className="text-lg font-mono font-bold text-slate-900 dark:text-white">
              {result.student_id || "Not detected"}
            </p>
          </div>
          {result.score != null && (
            <div className="text-right">
              <p className="text-sm text-slate-500">Score</p>
              <p className={cn("text-3xl font-bold", scoreColor)}>
                {result.score.toFixed(0)}
              </p>
              <p className="text-xs text-slate-500">
                {result.correct_count}/{result.total_questions}
              </p>
            </div>
          )}
        </div>

        {/* Warnings */}
        {(result.unmarked.length > 0 || result.multiple_marks.length > 0) && (
          <div className="mt-3 space-y-1">
            {result.unmarked.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600">
                <AlertTriangle className="w-3.5 h-3.5" />
                Unmarked: {result.unmarked.join(", ")}
              </div>
            )}
            {result.multiple_marks.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-red-500">
                <AlertTriangle className="w-3.5 h-3.5" />
                Multiple marks: {result.multiple_marks.join(", ")}
              </div>
            )}
          </div>
        )}

        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Confidence: {(result.confidence * 100).toFixed(0)}%
          </span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-500 hover:underline"
          >
            {expanded ? "Hide" : "Show"} answers
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-100 dark:border-slate-700 p-4">
          <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5">
            {Object.entries(result.answers).map(([q, ans]) => {
              const correct = answerKey?.[q];
              const isCorrect = correct && ans.toUpperCase() === correct.toUpperCase();
              const isEmpty = !ans || ans === "?";
              return (
                <div
                  key={q}
                  className={cn(
                    "text-center p-1 rounded text-xs font-mono",
                    isEmpty ? "bg-slate-100 dark:bg-slate-700 text-slate-400" :
                    isCorrect ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400" :
                    "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                  )}
                >
                  <div className="text-[10px] text-slate-400">{q}</div>
                  <div className="font-bold">{ans || "-"}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ==================== RESULTS PAGE ====================

function ResultsPage({ session, results }) {
  const [stats, setStats] = useState(null);

  const successResults = results.filter((r) => r.success && r.score != null);

  useEffect(() => {
    if (session?.session_id && successResults.length > 0) {
      axios.get(`${API}/api/sessions/${session.session_id}/stats`)
        .then((res) => setStats(res.data))
        .catch(() => {});
    }
  }, [session, successResults.length]);

  const exportCSV = async () => {
    if (!session) return;
    try {
      const res = await axios.get(
        `${API}/api/sessions/${session.session_id}/export`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `results_${session.session_id}.csv`;
      a.click();
    } catch (e) {
      alert("Export error");
    }
  };

  if (!session) {
    return (
      <div className="max-w-2xl mx-auto p-4 text-center text-slate-500 mt-20">
        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>No results yet</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-4">
      {/* Stats overview */}
      {stats && stats.total_students > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard icon={Users} label="Students" value={stats.total_students} />
          <StatCard icon={Target} label="Average" value={`${stats.average_score.toFixed(1)}`} />
          <StatCard icon={Trophy} label="Highest" value={`${stats.highest_score.toFixed(0)}`} color="text-green-600" />
          <StatCard icon={AlertTriangle} label="Lowest" value={`${stats.lowest_score.toFixed(0)}`} color="text-red-600" />
        </div>
      )}

      {/* Export button */}
      {successResults.length > 0 && (
        <button
          onClick={exportCSV}
          className="w-full py-2.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-300 flex items-center justify-center gap-2 transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      )}

      {/* Individual results */}
      <div className="space-y-3">
        {results.map((r, i) => (
          <ResultCard key={i} result={r} answerKey={session.answer_key} />
        ))}
      </div>

      {results.length === 0 && (
        <p className="text-center text-slate-400 text-sm mt-10">
          Scan answer sheets to see results here
        </p>
      )}
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color = "text-slate-900 dark:text-white" }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-3 shadow-sm border border-slate-200 dark:border-slate-700">
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4 text-slate-400" />
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <span className={cn("text-2xl font-bold", color)}>{value}</span>
    </div>
  );
}

// ==================== APP ====================

export default function App() {
  const [page, setPage] = useState("setup");
  const [session, setSession] = useState(null);
  const [results, setResults] = useState([]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Header page={page} setPage={setPage} session={session} />
      <main className="pb-20">
        {page === "setup" && (
          <SetupPage session={session} setSession={setSession} setPage={setPage} />
        )}
        {page === "scan" && (
          <ScanPage session={session} setResults={setResults} results={results} />
        )}
        {page === "results" && (
          <ResultsPage session={session} results={results} />
        )}
      </main>
    </div>
  );
}
