import { useState, useCallback, useRef, useEffect } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import {
  Camera, FileText, BarChart3, Settings, ChevronRight,
  CheckCircle, XCircle, AlertTriangle, Download, Plus,
  Scan, RotateCcw, Users, Trophy, Target, Upload,
  ClipboardList, Eye, Edit3, Check, X, UserPlus, Trash2, Image
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";

function cn(...classes) {
  return classes.filter(Boolean).join(" ");
}

// ============================================================
// Header
// ============================================================

function Header({ page, setPage, session }) {
  const tabs = [
    { id: "setup", label: "Ayarlar", icon: Settings },
    { id: "roster", label: "Sınıf", icon: ClipboardList },
    { id: "scan", label: "Tara", icon: Scan },
    { id: "review", label: "Doğrula", icon: Eye },
    { id: "results", label: "Sonuçlar", icon: BarChart3 },
    { id: "forms", label: "Formlar", icon: Image },
  ];
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4">
        <div className="flex items-center justify-between h-12 sm:h-14">
          <h1 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Scan className="w-5 h-5 text-blue-500" />
            <span className="hidden sm:inline">OMR Scanner</span>
            <span className="sm:hidden">OMR</span>
          </h1>
          {session && (
            <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full">
              {session.course_code ? `${session.course_code} · ` : ""}{session.num_questions}S
            </span>
          )}
        </div>
        <nav className="flex -mb-px overflow-x-auto scrollbar-hide">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setPage(t.id)}
              className={cn(
                "flex items-center gap-1 px-2 sm:px-4 py-2.5 text-[11px] sm:text-sm font-medium border-b-2 transition-colors whitespace-nowrap shrink-0",
                page === t.id
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-slate-500 hover:text-slate-700"
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

// ============================================================
// Setup Page
// ============================================================

function SetupPage({ session, setSession, setPage }) {
  const [numQ, setNumQ] = useState(session?.num_questions || 40);
  const [numOpts, setNumOpts] = useState(session?.num_options || 5);
  const [useBooklet, setUseBooklet] = useState(session?.use_booklet || false);
  const [activeBooklet, setActiveBooklet] = useState("A");
  const [keysA, setKeysA] = useState(session?.answer_key || {});
  const [keysB, setKeysB] = useState(session?.answer_key_b || {});
  const [loading, setLoading] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [courseCode, setCourseCode] = useState(session?.course_code || "");

  const allOptions = ["A", "B", "C", "D", "E"];
  const options = allOptions.slice(0, numOpts);

  const keys = activeBooklet === "A" ? keysA : keysB;
  const setKeys = activeBooklet === "A" ? setKeysA : setKeysB;

  const setAnswer = (q, ans) => {
    setKeys((prev) => ({ ...prev, [String(q)]: ans }));
  };

  const changeOpts = (n) => {
    setNumOpts(n);
    const valid = allOptions.slice(0, n);
    const cleanFn = (prev) => {
      const cleaned = {};
      for (const [q, v] of Object.entries(prev)) {
        if (valid.includes(v)) cleaned[q] = v;
      }
      return cleaned;
    };
    setKeysA(cleanFn);
    setKeysB(cleanFn);
  };

  const fillRandom = () => {
    const k = {};
    for (let i = 1; i <= numQ; i++) {
      k[String(i)] = options[Math.floor(Math.random() * options.length)];
    }
    setKeys(k);
  };

  const createSession = async () => {
    const filledA = Object.keys(keysA).length;
    if (filledA < numQ) {
      alert(`Kitapçık A: Tüm ${numQ} cevabı doldurun. Şu an: ${filledA}`);
      return;
    }
    if (useBooklet) {
      const filledB = Object.keys(keysB).length;
      if (filledB < numQ) {
        alert(`Kitapçık B: Tüm ${numQ} cevabı doldurun. Şu an: ${filledB}`);
        return;
      }
    }
    setLoading(true);
    try {
      const payload = {
        answers: keysA,
        num_questions: numQ,
        num_options: numOpts,
        course_code: courseCode,
      };
      if (useBooklet) {
        payload.answers_b = keysB;
        payload.use_booklet = true;
      }
      const res = await axios.post(`${API}/api/sessions/create`, payload);
      setSession({
        ...res.data,
        answer_key: keysA,
        answer_key_b: useBooklet ? keysB : null,
        use_booklet: useBooklet,
        course_code: courseCode,
        num_options: numOpts,
      });
      setPage("roster");
    } catch (e) {
      alert("Hata: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  const downloadForm = async () => {
    if (!courseCode.trim()) {
      alert("Lütfen önce ders kodunu girin (örn. MAT101)");
      return;
    }
    setFormLoading(true);
    try {
      const optLabels = allOptions.slice(0, numOpts);
      const res = await axios.get(`${API}/api/forms/download/${numQ}`, {
        params: { options: optLabels.join(","), show_booklet: useBooklet, course_code: courseCode.trim() },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `optik_form_${courseCode.trim()}_${numQ}q.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Form indirme hatası");
    }
    setFormLoading(false);
  };

  const filledCount = Object.keys(keys).length;
  const allFilled = filledCount === numQ;
  const bothFilled = !useBooklet || (Object.keys(keysA).length === numQ && Object.keys(keysB).length === numQ);

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 space-y-4 sm:space-y-5">

      {/* Active session banner */}
      {session && (
        <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl px-4 sm:px-5 py-3 flex flex-col sm:flex-row sm:items-center gap-3 sm:justify-between">
          <div>
            <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300">
              Aktif Sınav: {session.course_code || session.session_id}
            </p>
            <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
              {session.num_questions} soru · {session.num_options || 5} şık · Oturum: {session.session_id}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage("scan")}
              className="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-xs font-medium transition-colors"
            >
              Taramaya Git
            </button>
            <button
              onClick={() => { setSession(null); setKeysA({}); setKeysB({}); setCourseCode(""); }}
              className="px-3 py-1.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-50 transition-colors"
            >
              Yeni Sınav
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Exam setup */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="px-5 py-3 bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500 text-white text-xs font-bold">1</span>
            <h2 className="font-semibold text-slate-900 dark:text-white">Sınav Oluşturma</h2>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 ml-8">
            Sınavınızın temel ayarlarını belirleyin. Bu ayarlar optik form ve cevap anahtarı için kullanılacaktır.
          </p>
        </div>

        <div className="p-4 sm:p-5 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Soru Sayısı</label>
              <p className="text-xs text-slate-400 mb-2">Sınavdaki toplam soru sayısını seçin</p>
              <div className="flex gap-2">
                {[20, 40].map((n) => (
                  <button
                    key={n}
                    onClick={() => { setNumQ(n); setKeysA({}); setKeysB({}); }}
                    className={cn(
                      "flex-1 sm:flex-none px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
                      numQ === n
                        ? "bg-blue-500 text-white shadow-md"
                        : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 active:bg-slate-200"
                    )}
                  >
                    {n} Soru
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Şık Sayısı</label>
              <p className="text-xs text-slate-400 mb-2">Her soru için kaç seçenek olacağını belirleyin</p>
              <div className="flex gap-2">
                {[4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => changeOpts(n)}
                    className={cn(
                      "flex-1 sm:flex-none px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
                      numOpts === n
                        ? "bg-blue-500 text-white shadow-md"
                        : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 active:bg-slate-200"
                    )}
                  >
                    {n === 4 ? "A-B-C-D" : "A-B-C-D-E"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Ders Kodu</label>
              <p className="text-xs text-slate-400 mb-2">Sınavın ait olduğu ders</p>
              <input
                type="text"
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
                placeholder="ör: MAT101"
                className="px-3 py-2.5 border border-slate-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white w-full"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Kitapçık A/B</label>
              <p className="text-xs text-slate-400 mb-2">Farklı soru sıralaması için</p>
              <button
                onClick={() => { setUseBooklet(!useBooklet); setActiveBooklet("A"); }}
                className={cn(
                  "w-full sm:w-auto px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
                  useBooklet
                    ? "bg-emerald-500 text-white shadow-md"
                    : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 active:bg-slate-200"
                )}
              >
                {useBooklet ? "Açık — İki ayrı cevap anahtarı" : "Kapalı — Tek kitapçık"}
              </button>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-700">
            <button
              onClick={downloadForm}
              disabled={formLoading || !courseCode.trim()}
              className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-3 sm:py-2.5 text-sm font-medium rounded-lg transition-colors ${
                !courseCode.trim()
                  ? "text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800 cursor-not-allowed"
                  : "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 active:bg-blue-100"
              }`}
            >
              <Download className="w-4 h-4" />
              {formLoading ? "İndiriliyor..." : "Yazdırılabilir Optik Form İndir (PDF)"}
            </button>
            {!courseCode.trim() && (
              <p className="text-xs text-amber-500 dark:text-amber-400 mt-1.5 ml-1">
                Form indirmek için yukarıdan ders kodunu girin.
              </p>
            )}
            <p className="text-xs text-slate-400 mt-1.5 ml-1">
              Formu A4 kağıda yazdırın ve öğrencilere dağıtın. Form üzerinde ArUco işaretleri, QR kod ve cevap balonları bulunur.
            </p>
          </div>
        </div>
      </div>

      {/* Step 2: Answer key */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
        <div className="px-5 py-3 bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500 text-white text-xs font-bold">2</span>
                <h2 className="font-semibold text-slate-900 dark:text-white">Cevap Anahtarı</h2>
                {useBooklet && (
                  <div className="flex gap-1 ml-2">
                    {["A", "B"].map((b) => (
                      <button
                        key={b}
                        onClick={() => setActiveBooklet(b)}
                        className={cn(
                          "px-3 py-1 rounded-lg text-xs font-bold transition-all",
                          activeBooklet === b
                            ? "bg-blue-500 text-white shadow"
                            : "bg-slate-100 dark:bg-slate-700 text-slate-500 hover:bg-slate-200"
                        )}
                      >
                        Kitapçık {b}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 ml-8">
                {useBooklet
                  ? `Her kitapçık için doğru cevapları tek tek işaretleyin. Şu an Kitapçık ${activeBooklet} düzenleniyor.`
                  : "Her soru için doğru cevabı işaretleyin. Tüm soruların doldurulması zorunludur."
                }
              </p>
            </div>
            <button onClick={fillRandom} className="text-xs text-blue-500 hover:underline shrink-0">
              Rastgele doldur (test)
            </button>
          </div>
        </div>

        <div className="p-3 sm:p-5">
          <div className="flex flex-col gap-0.5">
            {Array.from({ length: numQ }, (_, i) => i + 1).map((q) => (
              <div key={q} className={cn(
                "flex items-center gap-2 sm:gap-3 py-2 px-2 rounded-lg transition-colors",
                keys[String(q)] ? "" : "bg-amber-50/50 dark:bg-amber-900/10",
              )}>
                <span className="text-sm font-semibold text-slate-500 w-7 sm:w-8 text-right shrink-0">{q}.</span>
                <div className="flex gap-2 sm:gap-1.5 flex-1">
                  {options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setAnswer(q, opt)}
                      className={cn(
                        "w-10 h-10 sm:w-9 sm:h-9 rounded-full text-sm sm:text-xs font-bold transition-all active:scale-95",
                        keys[String(q)] === opt
                          ? "bg-blue-500 text-white scale-110 shadow"
                          : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 active:bg-slate-200"
                      )}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
                {!keys[String(q)] && (
                  <span className="text-xs text-amber-500 shrink-0">Boş</span>
                )}
              </div>
            ))}
          </div>

          {/* Progress and submit */}
          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-700">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:justify-between">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex-1 h-2 w-32 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all duration-300",
                        allFilled ? "bg-emerald-500" : "bg-blue-500"
                      )}
                      style={{ width: `${(filledCount / numQ) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                    {filledCount}/{numQ}
                  </span>
                </div>
                {useBooklet && (
                  <p className="text-xs text-slate-400">
                    Kitapçık A: {Object.keys(keysA).length}/{numQ} — Kitapçık B: {Object.keys(keysB).length}/{numQ}
                  </p>
                )}
                {!allFilled && (
                  <p className="text-xs text-amber-500 mt-0.5">
                    {numQ - filledCount} soru daha işaretlenmeli
                  </p>
                )}
              </div>
              <button
                onClick={createSession}
                disabled={loading || !bothFilled}
                className={cn(
                  "w-full sm:w-auto px-5 py-3 sm:py-2.5 rounded-xl font-medium text-sm transition-all shadow-md flex items-center justify-center gap-2",
                  bothFilled
                    ? "bg-blue-500 active:bg-blue-600 text-white"
                    : "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
                )}
              >
                {loading ? "Oluşturuluyor..." : "Sınavı Oluştur ve Devam Et"}
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Roster Page (Sınıf Listesi)
// ============================================================

function RosterPage({ session, setSession, setPage }) {
  const [students, setStudents] = useState([]);
  const [name, setName] = useState("");
  const [surname, setSurname] = useState("");
  const [studentNo, setStudentNo] = useState("");
  const [uploading, setUploading] = useState(false);
  const [bulkText, setBulkText] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const [pdfUploading, setPdfUploading] = useState(false);
  const pdfInputRef = useRef(null);

  const addStudent = () => {
    if (!name.trim() || !surname.trim() || !studentNo.trim()) {
      alert("Ad, soyad ve numara zorunlu");
      return;
    }
    setStudents([...students, {
      name: name.toUpperCase().trim(),
      surname: surname.toUpperCase().trim(),
      student_number: studentNo.trim(),
    }]);
    setName("");
    setSurname("");
    setStudentNo("");
  };

  const parseBulk = () => {
    const lines = bulkText.trim().split("\n").filter(Boolean);
    const parsed = [];
    for (const line of lines) {
      const parts = line.split(/[,;\t]+/).map(s => s.trim());
      if (parts.length >= 3) {
        parsed.push({
          name: parts[0].toUpperCase(),
          surname: parts[1].toUpperCase(),
          student_number: parts[2],
        });
      } else if (parts.length === 2) {
        parsed.push({
          name: parts[0].toUpperCase(),
          surname: parts[1].toUpperCase(),
          student_number: "",
        });
      }
    }
    setStudents([...students, ...parsed]);
    setBulkText("");
    setShowBulk(false);
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!session) {
      alert("Önce sınav oluşturun");
      return;
    }
    setPdfUploading(true);

    const _tryPdfUpload = async (sid) => {
      const formData = new FormData();
      formData.append("file", file);
      return axios.post(
        `${API}/api/sessions/${sid}/roster/pdf`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
    };

    try {
      let res;
      try {
        res = await _tryPdfUpload(session.session_id);
      } catch (err) {
        if (err.response?.status === 404) {
          const newSession = await _recreateSession();
          if (newSession) {
            res = await _tryPdfUpload(newSession.session_id);
          } else {
            throw err;
          }
        } else {
          throw err;
        }
      }
      const parsed = res.data.students || [];
      if (parsed.length === 0) {
        alert("PDF'den öğrenci bilgisi çıkarılamadı. Formatı kontrol edin.");
      } else {
        setStudents((prev) => [...prev, ...parsed]);
        alert(`${parsed.length} öğrenci PDF'den eklendi`);
      }
    } catch (e) {
      alert("PDF yükleme hatası: " + (e.response?.data?.detail || e.message));
    }
    setPdfUploading(false);
    if (pdfInputRef.current) pdfInputRef.current.value = "";
  };

  const removeStudent = (idx) => {
    setStudents(students.filter((_, i) => i !== idx));
  };

  const _recreateSession = async () => {
    /* Backend session kaybolmuşsa (Render uyku/restart), yeniden oluştur */
    if (!session) return null;
    try {
      const payload = {
        answers: session.answer_key,
        num_questions: session.num_questions || 40,
        num_options: session.num_options || 5,
        course_code: session.course_code || "",
      };
      if (session.use_booklet && session.answer_key_b) {
        payload.answers_b = session.answer_key_b;
        payload.use_booklet = true;
      }
      const res = await axios.post(`${API}/api/sessions/create`, payload);
      const newSession = {
        ...session,
        session_id: res.data.session_id,
      };
      setSession(newSession);

      // Re-upload roster to the new session if roster was saved
      const rosterData = session._roster || [];
      if (rosterData.length > 0) {
        try {
          await axios.post(`${API}/api/sessions/${res.data.session_id}/roster`, {
            students: rosterData,
          });
        } catch { /* ignore roster re-upload failure */ }
      }

      return newSession;
    } catch {
      return null;
    }
  };

  const uploadRoster = async () => {
    if (!session) {
      alert("Önce sınav oluşturun");
      return;
    }
    if (students.length === 0) {
      setPage("scan");
      return;
    }
    setUploading(true);

    const _uploadRosterToSession = async (sid) => {
      await axios.post(`${API}/api/sessions/${sid}/roster`, { students });
      // Save roster in session state for re-creation
      setSession((prev) => ({ ...prev, _roster: students }));
    };

    try {
      await _uploadRosterToSession(session.session_id);
      setPage("scan");
    } catch (e) {
      if (e.response?.status === 404) {
        const newSession = await _recreateSession();
        if (newSession) {
          try {
            await _uploadRosterToSession(newSession.session_id);
            setPage("scan");
            setUploading(false);
            return;
          } catch (e2) {
            alert("Yükleme hatası: " + (e2.response?.data?.detail || e2.message));
          }
        } else {
          alert("Oturum süresi dolmuş. Lütfen sınavı yeniden oluşturun.");
        }
      } else {
        alert("Yükleme hatası: " + (e.response?.data?.detail || e.message));
      }
    }
    setUploading(false);
  };

  if (!session) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <ClipboardList className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce Ayarlar sekmesinden sınav oluşturun</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 space-y-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
        <h2 className="font-semibold text-slate-900 dark:text-white mb-3">Sınıf Listesi</h2>
        <p className="text-xs text-slate-500 mb-4">
          Öğrenci listesini girin. Tarama sonuçları otomatik eşleştirilecek. (İsteğe bağlı — atlayabilirsiniz)
        </p>

        {/* Single add */}
        <div className="flex gap-2 mb-3 flex-wrap">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ad"
            className="flex-1 min-w-[80px] px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
          />
          <input
            type="text"
            value={surname}
            onChange={(e) => setSurname(e.target.value)}
            placeholder="Soyad"
            className="flex-1 min-w-[80px] px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
          />
          <input
            type="text"
            value={studentNo}
            onChange={(e) => setStudentNo(e.target.value)}
            placeholder="No"
            className="w-24 px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
          />
          <button
            onClick={addStudent}
            className="px-3 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600"
          >
            <UserPlus className="w-4 h-4" />
          </button>
        </div>

        {/* PDF upload + Bulk add */}
        <div className="flex gap-3 mb-3 items-center flex-wrap">
          <button
            onClick={() => pdfInputRef.current?.click()}
            disabled={pdfUploading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
          >
            <Upload className="w-3.5 h-3.5" />
            {pdfUploading ? "PDF okunuyor..." : "PDF'den yükle"}
          </button>
          <input
            ref={pdfInputRef}
            type="file"
            accept=".pdf"
            onChange={handlePdfUpload}
            className="hidden"
          />
          <button
            onClick={() => setShowBulk(!showBulk)}
            className="text-xs text-blue-500 hover:underline"
          >
            {showBulk ? "Kapat" : "Toplu ekle (yapıştır)"}
          </button>
        </div>

        {showBulk && (
          <div className="mb-3">
            <textarea
              value={bulkText}
              onChange={(e) => setBulkText(e.target.value)}
              placeholder={"Ad, Soyad, Numara (her satıra bir öğrenci)\nSENA, KOSE, 214501\nALI, YILMAZ, 214502"}
              rows={5}
              className="w-full px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono"
            />
            <button
              onClick={parseBulk}
              className="mt-2 px-4 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600"
            >
              Ekle ({bulkText.trim().split("\n").filter(Boolean).length} satır)
            </button>
          </div>
        )}

        {/* Student list */}
        {students.length > 0 && (
          <div className="border border-slate-200 dark:border-slate-600 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-700">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">#</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Ad</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Soyad</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">No</th>
                  <th className="px-3 py-2 w-8"></th>
                </tr>
              </thead>
              <tbody>
                {students.map((s, i) => (
                  <tr key={i} className="border-t border-slate-100 dark:border-slate-600">
                    <td className="px-3 py-1.5 text-slate-400">{i + 1}</td>
                    <td className="px-3 py-1.5 text-slate-900 dark:text-white">{s.name}</td>
                    <td className="px-3 py-1.5 text-slate-900 dark:text-white">{s.surname}</td>
                    <td className="px-3 py-1.5 text-slate-600 dark:text-slate-400 font-mono">{s.student_number}</td>
                    <td className="px-3 py-1.5">
                      <button onClick={() => removeStudent(i)} className="text-red-400 hover:text-red-600">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-slate-500">{students.length} öğrenci</span>
          <button
            onClick={uploadRoster}
            disabled={uploading}
            className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium text-sm transition-all shadow-md disabled:opacity-50 flex items-center gap-2"
          >
            {uploading ? "Yükleniyor..." : students.length > 0 ? "Kaydet ve taramaya geç" : "Atla, taramaya geç"}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Scan Step (animated reveal)
// ============================================================

function ScanningOverlay() {
  const steps = [
    { text: "Form algılanıyor", detail: "ArUco işaretçileri aranıyor" },
    { text: "Perspektif düzeltiliyor", detail: "Sayfa hizalanıyor" },
    { text: "Optik okuma başladı", detail: "Baloncuklar taranıyor" },
    { text: "Cevaplar analiz ediliyor", detail: "Doluluk oranları hesaplanıyor" },
    { text: "Ad / Soyad okunuyor", detail: "El yazısı tanınıyor" },
    { text: "Öğrenci numarası okunuyor", detail: "Karakter tanıma yapılıyor" },
    { text: "Puanlama yapılıyor", detail: "Cevap anahtarıyla karşılaştırılıyor" },
    { text: "Sonuçlar hazırlanıyor", detail: "Neredeyse bitti" },
  ];
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((s) => {
        if (s + 1 >= steps.length) {
          setDone(true);
          return s;
        }
        return s + 1;
      });
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 py-12 px-8 text-center shadow-lg">
      <div className="relative w-16 h-16 mx-auto mb-6">
        <div className="absolute inset-0 border-[3px] border-blue-100 dark:border-blue-900 rounded-full" />
        <div className="absolute inset-0 border-[3px] border-transparent border-t-blue-500 rounded-full animate-spin" style={{ animationDuration: "1s" }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <Scan className="w-7 h-7 text-blue-500" />
        </div>
      </div>
      <div key={step} className="animate-fade-in">
        <p className="text-sm font-medium text-blue-600 dark:text-blue-400">
          {steps[step].text}...
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
          {steps[step].detail}
        </p>
      </div>
      {done && (
        <p className="text-xs text-slate-400 mt-4 animate-fade-in">
          Sunucu yanıtı bekleniyor...
        </p>
      )}
      {/* Step indicator */}
      <div className="flex justify-center gap-1.5 mt-5">
        {steps.map((_, i) => (
          <div key={i} className={cn(
            "w-1.5 h-1.5 rounded-full transition-all duration-300",
            i <= step ? "bg-blue-500" : "bg-slate-200 dark:bg-slate-700"
          )} />
        ))}
      </div>
    </div>
  );
}

// ============================================================
// Scan Page
// ============================================================

function ScanPage({ session, setSession, setResults, results }) {
  const webcamRef = useRef(null);
  const fileInputRef = useRef(null);
  const cameraFileRef = useRef(null);
  const [scanning, setScanning] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [useCamera, setUseCamera] = useState(true);
  const [facingMode, setFacingMode] = useState("environment");
  const [cameraError, setCameraError] = useState(false);

  const capture = useCallback(async () => {
    if (!webcamRef.current) return;
    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) return;
    await processImage(imageSrc);
  }, [session]);

  const _ensureSession = async () => {
    /* Make sure backend is awake and session exists. Retry-friendly. */
    if (!session?.session_id) return session;

    // Wake up the backend with a lightweight ping (retry up to 4 times for cold starts)
    let backendAwake = false;
    for (let attempt = 0; attempt < 4; attempt++) {
      try {
        await axios.get(`${API}/api/sessions/${session.session_id}`, { timeout: 45000 });
        return session; // exists and backend is awake
      } catch (e) {
        if (e.response?.status === 404) {
          backendAwake = true; // got a real response — backend is awake
          break;
        }
        if (e.response) {
          backendAwake = true; // any HTTP response means backend is awake
          break;
        }
        // Network error / timeout — backend still waking up, retry
        if (attempt < 3) {
          await new Promise(r => setTimeout(r, 5000));
          continue;
        }
      }
    }

    // Session not found or backend just woke up — recreate session
    try {
      const payload = {
        answers: session.answer_key,
        num_questions: session.num_questions || 40,
        num_options: session.num_options || 5,
        course_code: session.course_code || "",
      };
      if (session.use_booklet && session.answer_key_b) {
        payload.answers_b = session.answer_key_b;
        payload.use_booklet = true;
      }
      const res = await axios.post(`${API}/api/sessions/create`, payload, { timeout: 45000 });
      const newSession = { ...session, session_id: res.data.session_id };

      // Re-upload roster
      const roster = session._roster || [];
      if (roster.length > 0) {
        try {
          await axios.post(`${API}/api/sessions/${res.data.session_id}/roster`, { students: roster }, { timeout: 15000 });
        } catch { /* ignore */ }
      }

      setSession(newSession);
      return newSession;
    } catch {
      return session; // fallback: use old session_id, scan might still work without session
    }
  };

  const processImage = async (base64Image) => {
    setScanning(true);
    try {
      const s = await _ensureSession();
      const formData = new FormData();
      formData.append("image_base64", base64Image);
      formData.append("num_questions", s.num_questions);
      if (s.session_id) formData.append("session_id", s.session_id);
      if (s.answer_key) formData.append("answer_key", JSON.stringify(s.answer_key));

      // Retry scan up to 2 times for cold-start network errors
      let lastErr;
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const res = await axios.post(`${API}/api/scan/base64`, formData, { timeout: 120000 });
          setLastResult(res.data);
          setResults((prev) => [...prev, res.data]);
          setScanning(false);
          return;
        } catch (err) {
          lastErr = err;
          if (err.response) break; // real HTTP error, don't retry
          if (attempt === 0) await new Promise(r => setTimeout(r, 3000));
        }
      }
      const msg = lastErr.response?.data?.detail || lastErr.message;
      let hint = "";
      if (lastErr.code === "ECONNABORTED") hint = " (Zaman aşımı — tekrar deneyin)";
      else if (lastErr.code === "ERR_NETWORK" || !lastErr.response) hint = " (Sunucu uyanıyor olabilir — 10 sn bekleyip tekrar deneyin)";
      setLastResult({ success: false, error: "Tarama başarısız: " + msg + hint });
    } catch (e) {
      setLastResult({ success: false, error: "Tarama başarısız: " + e.message });
    }
    setScanning(false);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanning(true);
    try {
      const s = await _ensureSession();
      const formData = new FormData();
      formData.append("image", file);
      formData.append("num_questions", s.num_questions);
      if (s.session_id) formData.append("session_id", s.session_id);
      if (s.answer_key) formData.append("answer_key", JSON.stringify(s.answer_key));

      // Retry scan up to 2 times for cold-start network errors
      let lastErr;
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const res = await axios.post(`${API}/api/scan`, formData, { timeout: 120000 });
          setLastResult(res.data);
          setResults((prev) => [...prev, res.data]);
          setScanning(false);
          e.target.value = "";
          return;
        } catch (err) {
          lastErr = err;
          if (err.response) break; // real HTTP error, don't retry
          if (attempt === 0) await new Promise(r => setTimeout(r, 3000));
        }
      }
      const msg = lastErr.response?.data?.detail || lastErr.message;
      let hint = "";
      if (lastErr.code === "ECONNABORTED") hint = " (Zaman aşımı — tekrar deneyin)";
      else if (lastErr.code === "ERR_NETWORK" || !lastErr.response) hint = " (Sunucu uyanıyor olabilir — 10 sn bekleyip tekrar deneyin)";
      setLastResult({ success: false, error: "Tarama başarısız: " + msg + hint });
    } catch (e) {
      setLastResult({ success: false, error: "Tarama başarısız: " + e.message });
    }
    setScanning(false);
    e.target.value = "";
  };

  if (!session) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <Scan className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce Ayarlar sekmesinden sınav oluşturun</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 space-y-4">
      {/* Camera / Upload toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => { setUseCamera(true); setCameraError(false); }}
          className={cn(
            "flex-1 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2",
            useCamera ? "bg-blue-500 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
          )}
        >
          <Camera className="w-4 h-4" /> Fotoğraf Çek
        </button>
        <button
          onClick={() => setUseCamera(false)}
          className={cn(
            "flex-1 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2",
            !useCamera ? "bg-blue-500 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
          )}
        >
          <Upload className="w-4 h-4" /> Galeriden Seç
        </button>
      </div>

      {/* Camera */}
      {useCamera ? (
        cameraError ? (
          <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-8 text-center space-y-4">
            <Camera className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-600" />
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Kamera erişimi sağlanamadı</p>
              <p className="text-xs text-slate-500 mt-1">
                Mobilde kamera için HTTPS gereklidir. Bunun yerine aşağıdaki butonla telefon kamerasını açarak fotoğraf çekebilirsiniz.
              </p>
            </div>
            <button
              onClick={() => cameraFileRef.current?.click()}
              className="inline-flex items-center gap-2 px-5 py-3 bg-blue-500 text-white rounded-lg font-medium text-sm active:scale-95 transition-transform"
            >
              <Camera className="w-5 h-5" /> Kamerayı Aç ve Fotoğraf Çek
            </button>
            <input ref={cameraFileRef} type="file" accept="image/*" capture="environment"
              onChange={handleFileUpload} className="hidden" />
            <button
              onClick={() => { setUseCamera(false); }}
              className="block mx-auto text-xs text-slate-400 underline mt-2"
            >
              veya galeriden fotoğraf seç
            </button>
          </div>
        ) : (
          <div className="relative rounded-xl overflow-hidden bg-black aspect-[3/4]">
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              screenshotQuality={0.95}
              videoConstraints={{ facingMode, width: { ideal: 1920 }, height: { ideal: 2560 } }}
              className="w-full h-full object-cover"
              onUserMediaError={() => setCameraError(true)}
            />
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute inset-8 border-2 border-white/30 rounded-lg" />
            </div>
            <div className="absolute bottom-4 inset-x-4 flex items-center justify-center gap-4">
              <button
                onClick={() => setFacingMode(f => f === "environment" ? "user" : "environment")}
                className="p-3 bg-white/20 backdrop-blur rounded-full text-white"
              >
                <RotateCcw className="w-5 h-5" />
              </button>
              <button
                onClick={capture}
                disabled={scanning}
                className="w-16 h-16 bg-white rounded-full shadow-lg flex items-center justify-center disabled:opacity-50"
              >
                {scanning ? (
                  <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                ) : (
                  <div className="w-12 h-12 bg-blue-500 rounded-full" />
                )}
              </button>
              <div className="w-11" />
            </div>
          </div>
        )
      ) : (
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 dark:border-slate-600 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400 active:bg-slate-50 dark:active:bg-slate-800 transition-colors"
        >
          <Upload className="w-10 h-10 mx-auto mb-3 text-slate-400" />
          <p className="text-sm text-slate-500">Galeriden optik form fotoğrafı seçin</p>
          <input ref={fileInputRef} type="file" accept="image/*"
            onChange={handleFileUpload} className="hidden" />
        </div>
      )}

      {/* Scanning overlay */}
      {scanning && <ScanningOverlay />}

      {!scanning && (
        <div className="text-center text-sm text-slate-500">
          {results.filter(r => r.success).length} form tarandı
        </div>
      )}

      {!scanning && lastResult && <ResultCard result={lastResult} answerKey={session.answer_key} />}
    </div>
  );
}

// ============================================================
// Result Card
// ============================================================

function ResultCard({ result, answerKey }) {
  const [expanded, setExpanded] = useState(false);

  if (!result.success) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
        <div className="flex items-center gap-2 text-red-600">
          <XCircle className="w-5 h-5" />
          <span className="font-medium">Tarama başarısız</span>
        </div>
        <p className="text-sm text-red-500 mt-1">{result.error}</p>
      </div>
    );
  }

  const scoreColor =
    result.score >= 70 ? "text-green-600" :
    result.score >= 50 ? "text-amber-600" : "text-red-600";

  const studentName = result.student_name?.text || "";
  const studentSurname = result.student_surname?.text || "";
  const studentNo = result.student_number?.text || result.student_id || "";

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div>
                <p className="text-sm text-slate-500">Öğrenci No</p>
                <p className="text-lg font-mono font-bold text-slate-900 dark:text-white">
                  {studentNo || "Tespit edilemedi"}
                </p>
          </div>
          {result.score != null && (
            <div className="text-right">
              <p className="text-sm text-slate-500">Puan</p>
              <p className={cn("text-3xl font-bold", scoreColor)}>
                {result.score.toFixed(0)}
              </p>
              <p className="text-xs text-slate-500">
                {result.correct_count}/{result.total_questions}
              </p>
            </div>
          )}
        </div>

        {/* Booklet + Review badges */}
        <div className="mt-2 flex gap-2 flex-wrap">
          {result.booklet && (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded-lg">
              Kitapçık {result.booklet}
            </span>
          )}
          {result.needs_review && (
            <div className="flex items-center gap-1.5 text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-lg">
              <AlertTriangle className="w-3.5 h-3.5" />
              Doğrulama gerekiyor
            </div>
          )}
        </div>

        {/* Warnings */}
        {(result.unmarked?.length > 0 || result.multiple_marks?.length > 0) && (
          <div className="mt-2 space-y-1">
            {result.unmarked?.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600">
                <AlertTriangle className="w-3.5 h-3.5" />
                Boş: {result.unmarked.join(", ")}
              </div>
            )}
            {result.multiple_marks?.length > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-red-500">
                <AlertTriangle className="w-3.5 h-3.5" />
                Çoklu işaretleme: {result.multiple_marks.join(", ")}
              </div>
            )}
          </div>
        )}

        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Güven: {(result.confidence * 100).toFixed(0)}%
          </span>
          <div className="flex items-center gap-3">
            {(result.form_image_url || result.form_image_base64) && (
              <a
                href={result.form_image_url || `data:image/jpeg;base64,${result.form_image_base64}`}
                download={`form_${studentNo || "scan"}.jpg`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:underline flex items-center gap-1"
              >
                <Download className="w-3 h-3" />
                Form İndir
              </a>
            )}
            <button onClick={() => setExpanded(!expanded)} className="text-xs text-blue-500 hover:underline">
              {expanded ? "Gizle" : "Cevapları göster"}
            </button>
          </div>
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
                <div key={q} className={cn(
                  "text-center p-1 rounded text-xs font-mono",
                  isEmpty ? "bg-slate-100 text-slate-400" :
                  isCorrect ? "bg-green-100 text-green-700" :
                  "bg-red-100 text-red-700"
                )}>
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

// ============================================================
// Review Page (Doğrulama)
// ============================================================

function ReviewPage({ session, results, setResults }) {
  const [reviews, setReviews] = useState([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [editName, setEditName] = useState("");
  const [editSurname, setEditSurname] = useState("");
  const [editNo, setEditNo] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!session) return;
    const pending = results
      .map((r, i) => ({ ...r, _index: i }))
      .filter(r => r.needs_review);
    setReviews(pending);
    if (pending.length > 0) {
      const r = pending[0];
      setEditName(r.student_name?.text || "");
      setEditSurname(r.student_surname?.text || "");
      setEditNo(r.student_number?.text || "");
    }
  }, [session, results]);

  const loadCurrent = (idx) => {
    if (idx >= 0 && idx < reviews.length) {
      setCurrentIdx(idx);
      const r = reviews[idx];
      setEditName(r.student_name?.text || "");
      setEditSurname(r.student_surname?.text || "");
      setEditNo(r.student_number?.text || "");
    }
  };

  const approve = async () => {
    if (!session || reviews.length === 0) return;
    setLoading(true);
    try {
      const resultIdx = reviews[currentIdx]._index;
      await axios.post(`${API}/api/sessions/${session.session_id}/verify`, {
        result_index: resultIdx,
        student_name: current.student_name?.text || "",
        student_surname: current.student_surname?.text || "",
        student_number: editNo,
        approved: true,
      });
      // Update results state with corrected data
      setResults((prev) => prev.map((r, i) => {
        if (i !== resultIdx) return r;
        return {
          ...r,
          student_number: { ...r.student_number, text: editNo, needs_review: false },
          needs_review: false,
        };
      }));
      // Move to next
      const next = currentIdx + 1;
      if (next < reviews.length) {
        loadCurrent(next);
      } else {
        setReviews(reviews.filter((_, i) => i !== currentIdx));
        setCurrentIdx(0);
      }
    } catch (e) {
      alert("Hata: " + (e.response?.data?.detail || e.message));
    }
    setLoading(false);
  };

  if (!session) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <Eye className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce sınav oluşturun</p>
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
        <p className="font-medium">Doğrulama bekleyen form yok</p>
        <p className="text-xs mt-1">Tüm formlar otomatik okundu veya henüz tarama yapılmadı</p>
      </div>
    );
  }

  const current = reviews[currentIdx];

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 space-y-4">
      {/* Progress */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Doğrulama: {currentIdx + 1} / {reviews.length}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => loadCurrent(currentIdx - 1)}
            disabled={currentIdx === 0}
            className="px-3 py-1 text-sm bg-slate-100 rounded-lg disabled:opacity-30"
          >
            ← Önceki
          </button>
          <button
            onClick={() => loadCurrent(currentIdx + 1)}
            disabled={currentIdx >= reviews.length - 1}
            className="px-3 py-1 text-sm bg-slate-100 rounded-lg disabled:opacity-30"
          >
            Sonraki →
          </button>
        </div>
      </div>

      {/* Form image */}
      {(current.form_image_url || current.form_image_base64) && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <img
            src={current.form_image_url || `data:image/jpeg;base64,${current.form_image_base64}`}
            alt="Taranan form"
            className="w-full"
          />
          <div className="p-2 border-t border-slate-100">
            <a
              href={current.form_image_url || `data:image/jpeg;base64,${current.form_image_base64}`}
              download={`form_${current.student_number?.text || "scan"}.jpg`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg text-sm font-medium transition-colors"
            >
              <Download className="w-4 h-4" />
              Form Resmini İndir
            </a>
          </div>
        </div>
      )}

      {/* Editable fields */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 space-y-3">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-2">Öğrenci Bilgileri</h3>

        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600 w-16">No:</label>
          <input
            type="text"
            value={editNo}
            onChange={(e) => setEditNo(e.target.value)}
            className={cn(
              "flex-1 px-3 py-2 border rounded-lg text-sm font-mono",
              current.student_number?.needs_review
                ? "border-amber-400 bg-amber-50"
                : "border-slate-200 bg-white"
            )}
          />
          {current.student_number && (
            <span className="text-xs text-slate-400">
              %{(current.student_number.confidence * 100).toFixed(0)}
            </span>
          )}
        </div>

        {/* Score display */}
        {current.score != null && (
          <div className="pt-2 border-t border-slate-100">
            <span className="text-sm text-slate-500">Puan: </span>
            <span className="font-bold text-lg">{current.score.toFixed(0)}</span>
            <span className="text-sm text-slate-400 ml-2">
              ({current.correct_count}/{current.total_questions})
            </span>
          </div>
        )}

        <button
          onClick={approve}
          disabled={loading}
          className="w-full py-3 bg-green-500 hover:bg-green-600 text-white rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <Check className="w-4 h-4" />
          {loading ? "Kaydediliyor..." : "Onayla ve devam et"}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// Results Page
// ============================================================

// ============================================================
// Forms Archive Page
// ============================================================

function FormsPage({ session, results }) {
  const [selectedForm, setSelectedForm] = useState(null);

  const formsWithImages = results
    .map((r, i) => ({ ...r, _index: i }))
    .filter(r => r.success && (r.form_image_url || r.form_image_base64));

  if (!session) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <Image className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce sınav oluşturun</p>
      </div>
    );
  }

  if (formsWithImages.length === 0) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <Image className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p className="font-medium">Henüz taranan form yok</p>
        <p className="text-xs mt-1">Formları taradıktan sonra burada görünecek</p>
      </div>
    );
  }

  const imgSrc = (r) => r.form_image_url || `data:image/jpeg;base64,${r.form_image_base64}`;

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
          <Image className="w-5 h-5 text-blue-500" />
          Taranan Formlar ({formsWithImages.length})
        </h2>
      </div>

      {/* Form grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {formsWithImages.map((r) => {
          const studentNo = r.student_number?.text || r.student_id || "—";
          return (
            <div
              key={r._index}
              className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => setSelectedForm(r)}
            >
              <img
                src={imgSrc(r)}
                alt={`Form ${studentNo}`}
                className="w-full aspect-[3/4] object-cover object-top"
              />
              <div className="p-2.5">
                <p className="text-xs font-mono font-bold text-slate-900 dark:text-white truncate">{studentNo}</p>
                <div className="flex items-center justify-between mt-1">
                  {r.score != null && (
                    <span className={cn(
                      "text-sm font-bold",
                      r.score >= 70 ? "text-green-600" : r.score >= 50 ? "text-amber-600" : "text-red-600"
                    )}>
                      {r.score.toFixed(0)} puan
                    </span>
                  )}
                  <a
                    href={imgSrc(r)}
                    download={`form_${studentNo}.jpg`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-blue-500 hover:text-blue-700"
                    title="İndir"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full-size modal */}
      {selectedForm && (
        <div
          className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedForm(null)}
        >
          <div
            className="bg-white dark:bg-slate-800 rounded-2xl overflow-hidden max-w-2xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
              <div>
                <p className="font-mono font-bold text-slate-900 dark:text-white">
                  {selectedForm.student_number?.text || selectedForm.student_id || "—"}
                </p>
                {selectedForm.score != null && (
                  <p className="text-sm text-slate-500">{selectedForm.score.toFixed(0)} puan · {selectedForm.correct_count}/{selectedForm.total_questions}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={imgSrc(selectedForm)}
                  download={`form_${selectedForm.student_number?.text || "scan"}.jpg`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  İndir
                </a>
                <button
                  onClick={() => setSelectedForm(null)}
                  className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  <X className="w-5 h-5 text-slate-500" />
                </button>
              </div>
            </div>
            <div className="overflow-y-auto">
              <img
                src={imgSrc(selectedForm)}
                alt="Form"
                className="w-full"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


function ResultsPage({ session, results, setResults, setSession, setPage }) {
  const [stats, setStats] = useState(null);
  const [roster, setRoster] = useState(null);

  const successResults = results.filter((r) => r.success && r.score != null);

  const deleteResult = async (index) => {
    if (!confirm("Bu tarama sonucunu silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(`${API}/api/sessions/${session.session_id}/results/${index}`);
      setResults((prev) => prev.filter((_, i) => i !== index));
    } catch {
      alert("Silinemedi");
    }
  };

  const deleteExam = async () => {
    if (!confirm("Bu sınavı ve tüm sonuçlarını silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(`${API}/api/sessions/${session.session_id}`);
      setSession(null);
      setResults([]);
      setPage("setup");
    } catch {
      alert("Silinemedi");
    }
  };

  useEffect(() => {
    if (session?.session_id && successResults.length > 0) {
      axios.get(`${API}/api/sessions/${session.session_id}/stats`)
        .then((res) => setStats(res.data))
        .catch(() => {});
      axios.get(`${API}/api/sessions/${session.session_id}/roster`)
        .then((res) => setRoster(res.data))
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
      a.download = `sonuclar_${session.session_id}.csv`;
      a.click();
    } catch (e) {
      alert("Dışa aktarma hatası");
    }
  };

  if (!session) {
    return (
      <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 text-center text-slate-500 mt-20">
        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Henüz sonuç yok</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 py-4 space-y-4">
      {/* Stats */}
      {stats && stats.total_students > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard icon={Users} label="Öğrenci" value={stats.total_students} />
          <StatCard icon={Target} label="Ortalama" value={`${stats.average_score.toFixed(1)}`} />
          <StatCard icon={Trophy} label="En yüksek" value={`${stats.highest_score.toFixed(0)}`} color="text-green-600" />
          <StatCard icon={AlertTriangle} label="En düşük" value={`${stats.lowest_score.toFixed(0)}`} color="text-red-600" />
        </div>
      )}

      {/* Class Roster with scores */}
      {roster && roster.students && roster.students.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700">
            <h3 className="font-semibold text-slate-900 dark:text-white">Sınıf Listesi — Notlar</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-700">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">#</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Ad Soyad</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">No</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-500">Puan</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-slate-500">D/Y</th>
              </tr>
            </thead>
            <tbody>
              {roster.students.map((s, i) => (
                <tr key={i} className="border-t border-slate-100 dark:border-slate-600">
                  <td className="px-3 py-2 text-slate-400">{i + 1}</td>
                  <td className="px-3 py-2 text-slate-900 dark:text-white font-medium">
                    {s.name} {s.surname}
                  </td>
                  <td className="px-3 py-2 text-slate-600 font-mono text-xs">{s.student_number}</td>
                  <td className="px-3 py-2 text-right">
                    {s.score != null ? (
                      <span className={cn(
                        "font-bold",
                        s.score >= 70 ? "text-green-600" :
                        s.score >= 50 ? "text-amber-600" : "text-red-600"
                      )}>
                        {s.score.toFixed(0)}
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-slate-500">
                    {s.score != null ? `${s.correct_count}/${s.total_questions}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Export & Delete exam */}
      <div className="flex gap-2">
        {successResults.length > 0 && (
          <button
            onClick={exportCSV}
            className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-sm font-medium text-slate-700 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            CSV Dışa Aktar
          </button>
        )}
        <button
          onClick={deleteExam}
          className="py-2.5 px-4 bg-red-50 hover:bg-red-100 rounded-xl text-sm font-medium text-red-600 flex items-center justify-center gap-2"
        >
          <Trash2 className="w-4 h-4" />
          Sınavı Sil
        </button>
      </div>

      {/* Individual results */}
      <div className="space-y-3">
        {results.map((r, i) => (
          <div key={i}>
            <ResultCard result={r} answerKey={session.answer_key} />
            <button
              onClick={() => deleteResult(i)}
              className="w-full mt-1 py-1.5 text-xs text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <Trash2 className="w-3 h-3" />
              Sonucu sil
            </button>
          </div>
        ))}
      </div>

      {results.length === 0 && (
        <p className="text-center text-slate-400 text-sm mt-10">
          Sonuçları görmek için form tarayın
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

// ============================================================
// App
// ============================================================

// ============================================================
// Saved Sessions List
// ============================================================

function SavedSessionsList({ onResume, onNew }) {
  const [savedSessions, setSavedSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get(`${API}/api/sessions`)
      .then((res) => setSavedSessions(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const resumeSession = async (s) => {
    try {
      const res = await axios.get(`${API}/api/sessions/${s.session_id}`);
      const data = res.data;
      onResume({
        session: {
          session_id: data.session_id,
          num_questions: data.num_questions,
          num_options: data.num_options || 5,
          use_booklet: data.use_booklet,
          answer_key: data.answer_key,
          answer_key_b: data.answer_key_b,
          course_code: data.course_code || "",
        },
        results: data.results || [],
      });
    } catch (e) {
      alert("Oturum yüklenemedi");
    }
  };

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation(); // Don't trigger resume
    if (!confirm("Bu sınavı silmek istediğinize emin misiniz?")) return;
    try {
      await axios.delete(`${API}/api/sessions/${sessionId}`);
      setSavedSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch {
      alert("Silinemedi");
    }
  };

  if (loading) return <div className="text-center py-8 text-slate-500">Yükleniyor...</div>;
  if (savedSessions.length === 0) return null;

  return (
    <div className="max-w-3xl lg:max-w-6xl mx-auto px-3 sm:px-4 mt-4 sm:mt-6">
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-3 sm:p-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <ClipboardList className="w-4 h-4" />
          Kayıtlı Sınavlar
        </h3>
        <div className="space-y-2">
          {savedSessions.map((s) => (
            <div
              key={s.session_id}
              className="flex items-center gap-2"
            >
              <button
                onClick={() => resumeSession(s)}
                className="flex-1 p-3 sm:p-4 rounded-lg border border-slate-200 dark:border-slate-700 active:bg-blue-50 dark:active:bg-slate-800 transition-colors text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900 dark:text-white">
                    {s.course_code || s.session_id}
                  </span>
                  <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                </div>
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  {s.course_code && (
                    <span className="text-xs text-slate-400">{s.session_id}</span>
                  )}
                  <span className="text-xs text-slate-500">
                    {s.num_questions} soru · {s.num_options || 5} şık
                  </span>
                  {s.scanned_count > 0 && (
                    <span className="bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-2 py-0.5 rounded-full text-xs">
                      {s.scanned_count} tarandı
                    </span>
                  )}
                  {s.roster_count > 0 && (
                    <span className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full text-xs">
                      {s.roster_count} öğrenci
                    </span>
                  )}
                </div>
              </button>
              <button
                onClick={(e) => deleteSession(e, s.session_id)}
                className="p-2.5 rounded-lg text-red-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors shrink-0"
                title="Sınavı sil"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


export default function App() {
  const [page, setPage] = useState("setup");
  const [session, setSession] = useState(null);
  const [results, setResults] = useState([]);
  const [backendStatus, setBackendStatus] = useState("checking");

  // Wake up backend on page load
  useEffect(() => {
    if (!API) { setBackendStatus("ready"); return; }
    let cancelled = false;
    const wake = async () => {
      for (let i = 0; i < 5; i++) {
        try {
          await axios.get(`${API}/health`, { timeout: 50000 });
          if (!cancelled) setBackendStatus("ready");
          return;
        } catch {
          if (!cancelled) setBackendStatus("waking");
          await new Promise(r => setTimeout(r, 5000));
        }
      }
      if (!cancelled) setBackendStatus("error");
    };
    wake();
    return () => { cancelled = true; };
  }, []);

  const handleResume = ({ session: s, results: r }) => {
    setSession(s);
    setResults(r);
    setPage(r.length > 0 ? "results" : "scan");
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {backendStatus === "waking" && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-center text-sm text-amber-700">
          <span className="inline-block animate-spin mr-2">&#9696;</span>
          Sunucu uyanıyor, lütfen bekleyin...
        </div>
      )}
      {backendStatus === "error" && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-center text-sm text-red-700">
          Sunucuya bağlanılamadı. Sayfayı yenileyin veya birkaç dakika sonra tekrar deneyin.
        </div>
      )}
      <Header page={page} setPage={setPage} session={session} />
      <main className="pb-20">
        {page === "setup" && (
          <>
            <SavedSessionsList onResume={handleResume} />
            <SetupPage session={session} setSession={setSession} setPage={setPage} />
          </>
        )}
        {page === "roster" && <RosterPage session={session} setSession={setSession} setPage={setPage} />}
        {page === "scan" && <ScanPage session={session} setSession={setSession} setResults={setResults} results={results} />}
        {page === "review" && <ReviewPage session={session} results={results} setResults={setResults} />}
        {page === "results" && <ResultsPage session={session} results={results} setResults={setResults} setSession={setSession} setPage={setPage} />}
        {page === "forms" && <FormsPage session={session} results={results} />}
      </main>
    </div>
  );
}
