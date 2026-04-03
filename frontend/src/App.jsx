import { useState, useCallback, useRef, useEffect } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import {
  Camera, FileText, BarChart3, Settings, ChevronRight,
  CheckCircle, XCircle, AlertTriangle, Download, Plus,
  Scan, RotateCcw, Users, Trophy, Target, Upload,
  ClipboardList, Eye, Edit3, Check, X, UserPlus
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
    { id: "roster", label: "Sınıf Listesi", icon: ClipboardList },
    { id: "scan", label: "Tara", icon: Scan },
    { id: "review", label: "Doğrula", icon: Eye },
    { id: "results", label: "Sonuçlar", icon: BarChart3 },
  ];
  return (
    <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50">
      <div className="max-w-3xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          <h1 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Scan className="w-5 h-5 text-blue-500" />
            OMR Scanner
          </h1>
          {session && (
            <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-full">
              {session.course_code ? `${session.course_code} · ` : ""}{session.num_questions}S
            </span>
          )}
        </div>
        <nav className="flex gap-0.5 -mb-px overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setPage(t.id)}
              className={cn(
                "flex items-center gap-1 px-3 py-2 text-xs font-medium border-b-2 transition-colors whitespace-nowrap",
                page === t.id
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              )}
            >
              <t.icon className="w-3.5 h-3.5" />
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
  const [numQ, setNumQ] = useState(40);
  const [numOpts, setNumOpts] = useState(5);
  const [useBooklet, setUseBooklet] = useState(false);
  const [activeBooklet, setActiveBooklet] = useState("A");
  const [keysA, setKeysA] = useState({});
  const [keysB, setKeysB] = useState({});
  const [loading, setLoading] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [courseCode, setCourseCode] = useState("");

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
    setFormLoading(true);
    try {
      const optLabels = allOptions.slice(0, numOpts);
      const res = await axios.get(`${API}/api/forms/download/${numQ}`, {
        params: { options: optLabels.join(","), show_booklet: useBooklet },
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `optik_form_${numQ}q.pdf`;
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
    <div className="max-w-3xl mx-auto p-4 space-y-5">

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

        <div className="p-5 space-y-4">
          <div className="flex items-start gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Soru Sayısı</label>
              <p className="text-xs text-slate-400 mb-2">Sınavdaki toplam soru sayısını seçin</p>
              <div className="flex gap-2">
                {[20, 40].map((n) => (
                  <button
                    key={n}
                    onClick={() => { setNumQ(n); setKeysA({}); setKeysB({}); }}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                      numQ === n
                        ? "bg-blue-500 text-white shadow-md"
                        : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                    )}
                  >
                    {n} Soru
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Şık Sayısı</label>
              <p className="text-xs text-slate-400 mb-2">Her soru için kaç seçenek olacağını belirleyin</p>
              <div className="flex gap-2">
                {[4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => changeOpts(n)}
                    className={cn(
                      "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                      numOpts === n
                        ? "bg-blue-500 text-white shadow-md"
                        : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                    )}
                  >
                    {n === 4 ? "A-B-C-D" : "A-B-C-D-E"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex items-start gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Ders Kodu</label>
              <p className="text-xs text-slate-400 mb-2">Sınavın ait olduğu ders (formda ve kayıtlarda görünür)</p>
              <input
                type="text"
                value={courseCode}
                onChange={(e) => setCourseCode(e.target.value.toUpperCase())}
                placeholder="ör: MAT101"
                className="px-3 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-slate-900 dark:text-white w-full max-w-[180px]"
              />
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300 block mb-1.5">Kitapçık A/B</label>
              <p className="text-xs text-slate-400 mb-2">Farklı soru sıralaması olan iki kitapçık kullanıyorsanız açın</p>
              <button
                onClick={() => { setUseBooklet(!useBooklet); setActiveBooklet("A"); }}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                  useBooklet
                    ? "bg-emerald-500 text-white shadow-md"
                    : "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200"
                )}
              >
                {useBooklet ? "Açık — İki ayrı cevap anahtarı" : "Kapalı — Tek kitapçık"}
              </button>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-slate-700">
            <button
              onClick={downloadForm}
              disabled={formLoading}
              className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
            >
              <Download className="w-4 h-4" />
              {formLoading ? "İndiriliyor..." : "Yazdırılabilir Optik Form İndir (PDF)"}
            </button>
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

        <div className="p-5">
          <div className="flex flex-col gap-1">
            {Array.from({ length: numQ }, (_, i) => i + 1).map((q) => (
              <div key={q} className={cn(
                "flex items-center gap-3 py-1.5 px-2 rounded-lg transition-colors",
                keys[String(q)] ? "" : "bg-amber-50/50 dark:bg-amber-900/10",
                "hover:bg-slate-50 dark:hover:bg-slate-700/50"
              )}>
                <span className="text-sm font-semibold text-slate-500 w-8 text-right shrink-0">{q}.</span>
                <div className="flex gap-1.5">
                  {options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setAnswer(q, opt)}
                      className={cn(
                        "w-9 h-9 rounded-full text-xs font-bold transition-all",
                        keys[String(q)] === opt
                          ? "bg-blue-500 text-white scale-110 shadow"
                          : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200"
                      )}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
                {!keys[String(q)] && (
                  <span className="text-xs text-amber-500">Boş</span>
                )}
              </div>
            ))}
          </div>

          {/* Progress and submit */}
          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-700">
            <div className="flex items-center justify-between">
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
                  "px-5 py-2.5 rounded-xl font-medium text-sm transition-all shadow-md flex items-center gap-2",
                  bothFilled
                    ? "bg-blue-500 hover:bg-blue-600 text-white"
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

function RosterPage({ session, setPage }) {
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
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await axios.post(
        `${API}/api/sessions/${session.session_id}/roster/pdf`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
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

  const uploadRoster = async () => {
    if (!session) {
      alert("Önce sınav oluşturun");
      return;
    }
    if (students.length === 0) {
      // Skip roster, go directly to scan
      setPage("scan");
      return;
    }
    setUploading(true);
    try {
      await axios.post(`${API}/api/sessions/${session.session_id}/roster`, {
        students: students,
      });
      setPage("scan");
    } catch (e) {
      alert("Yükleme hatası: " + (e.response?.data?.detail || e.message));
    }
    setUploading(false);
  };

  if (!session) {
    return (
      <div className="max-w-3xl mx-auto p-4 text-center text-slate-500 mt-20">
        <ClipboardList className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce Ayarlar sekmesinden sınav oluşturun</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
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
// Scan Page
// ============================================================

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
      if (session.session_id) formData.append("session_id", session.session_id);
      if (session.answer_key) formData.append("answer_key", JSON.stringify(session.answer_key));

      const res = await axios.post(`${API}/api/scan/base64`, formData);
      setLastResult(res.data);
      setResults((prev) => [...prev, res.data]);
    } catch (e) {
      setLastResult({ success: false, error: e.response?.data?.detail || e.message });
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
      if (session.session_id) formData.append("session_id", session.session_id);
      if (session.answer_key) formData.append("answer_key", JSON.stringify(session.answer_key));

      const res = await axios.post(`${API}/api/scan`, formData);
      setLastResult(res.data);
      setResults((prev) => [...prev, res.data]);
    } catch (e) {
      setLastResult({ success: false, error: e.response?.data?.detail || e.message });
    }
    setScanning(false);
    e.target.value = "";
  };

  if (!session) {
    return (
      <div className="max-w-3xl mx-auto p-4 text-center text-slate-500 mt-20">
        <Scan className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce Ayarlar sekmesinden sınav oluşturun</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
      {/* Camera / Upload toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setUseCamera(true)}
          className={cn(
            "flex-1 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2",
            useCamera ? "bg-blue-500 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-600"
          )}
        >
          <Camera className="w-4 h-4" /> Kamera
        </button>
        <button
          onClick={() => setUseCamera(false)}
          className={cn(
            "flex-1 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2",
            !useCamera ? "bg-blue-500 text-white" : "bg-slate-100 dark:bg-slate-700 text-slate-600"
          )}
        >
          <Upload className="w-4 h-4" /> Yükle
        </button>
      </div>

      {/* Camera */}
      {useCamera ? (
        <div className="relative rounded-xl overflow-hidden bg-black aspect-[3/4]">
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            screenshotQuality={0.95}
            videoConstraints={{ facingMode, width: { ideal: 1920 }, height: { ideal: 2560 } }}
            className="w-full h-full object-cover"
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
      ) : (
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 rounded-xl p-12 text-center cursor-pointer hover:border-blue-400"
        >
          <Upload className="w-10 h-10 mx-auto mb-3 text-slate-400" />
          <p className="text-sm text-slate-500">Optik form fotoğrafı seçin</p>
          <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
            onChange={handleFileUpload} className="hidden" />
        </div>
      )}

      <div className="text-center text-sm text-slate-500">
        {results.filter(r => r.success).length} form tarandı
      </div>

      {lastResult && <ResultCard result={lastResult} answerKey={session.answer_key} />}
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
            {(studentName || studentSurname) ? (
              <>
                <p className="text-lg font-bold text-slate-900 dark:text-white">
                  {studentName} {studentSurname}
                </p>
                <p className="text-sm text-slate-500 font-mono">{studentNo}</p>
              </>
            ) : (
              <>
                <p className="text-sm text-slate-500">Öğrenci No</p>
                <p className="text-lg font-mono font-bold text-slate-900 dark:text-white">
                  {studentNo || "Tespit edilemedi"}
                </p>
              </>
            )}
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
          <button onClick={() => setExpanded(!expanded)} className="text-xs text-blue-500 hover:underline">
            {expanded ? "Gizle" : "Cevapları göster"}
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

function ReviewPage({ session, results }) {
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
      await axios.post(`${API}/api/sessions/${session.session_id}/verify`, {
        result_index: reviews[currentIdx]._index,
        student_name: editName,
        student_surname: editSurname,
        student_number: editNo,
        approved: true,
      });
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
      <div className="max-w-3xl mx-auto p-4 text-center text-slate-500 mt-20">
        <Eye className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Önce sınav oluşturun</p>
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="max-w-3xl mx-auto p-4 text-center text-slate-500 mt-20">
        <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
        <p className="font-medium">Doğrulama bekleyen form yok</p>
        <p className="text-xs mt-1">Tüm formlar otomatik okundu veya henüz tarama yapılmadı</p>
      </div>
    );
  }

  const current = reviews[currentIdx];

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
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
      {current.form_image_base64 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <img
            src={`data:image/jpeg;base64,${current.form_image_base64}`}
            alt="Taranan form"
            className="w-full"
          />
        </div>
      )}

      {/* Editable fields */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 space-y-3">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-2">Öğrenci Bilgileri</h3>

        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600 w-16">Ad:</label>
          <input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value.toUpperCase())}
            className={cn(
              "flex-1 px-3 py-2 border rounded-lg text-sm font-mono",
              current.student_name?.needs_review
                ? "border-amber-400 bg-amber-50"
                : "border-slate-200 bg-white"
            )}
          />
          {current.student_name && (
            <span className="text-xs text-slate-400">
              %{(current.student_name.confidence * 100).toFixed(0)}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600 w-16">Soyad:</label>
          <input
            type="text"
            value={editSurname}
            onChange={(e) => setEditSurname(e.target.value.toUpperCase())}
            className={cn(
              "flex-1 px-3 py-2 border rounded-lg text-sm font-mono",
              current.student_surname?.needs_review
                ? "border-amber-400 bg-amber-50"
                : "border-slate-200 bg-white"
            )}
          />
          {current.student_surname && (
            <span className="text-xs text-slate-400">
              %{(current.student_surname.confidence * 100).toFixed(0)}
            </span>
          )}
        </div>

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

function ResultsPage({ session, results }) {
  const [stats, setStats] = useState(null);
  const [roster, setRoster] = useState(null);

  const successResults = results.filter((r) => r.success && r.score != null);

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
      <div className="max-w-3xl mx-auto p-4 text-center text-slate-500 mt-20">
        <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Henüz sonuç yok</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-4 space-y-4">
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

      {/* Export */}
      {successResults.length > 0 && (
        <button
          onClick={exportCSV}
          className="w-full py-2.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-sm font-medium text-slate-700 flex items-center justify-center gap-2"
        >
          <Download className="w-4 h-4" />
          CSV Dışa Aktar
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

  if (loading) return <div className="text-center py-8 text-slate-500">Yükleniyor...</div>;
  if (savedSessions.length === 0) return null;

  return (
    <div className="max-w-3xl mx-auto px-4 mt-6">
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <ClipboardList className="w-4 h-4" />
          Kayıtlı Sınavlar
        </h3>
        <div className="space-y-2">
          {savedSessions.map((s) => (
            <button
              key={s.session_id}
              onClick={() => resumeSession(s)}
              className="w-full flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-blue-50 dark:hover:bg-slate-800 transition-colors text-left"
            >
              <div>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {s.course_code || s.session_id}
                </span>
                {s.course_code && (
                  <span className="text-xs text-slate-400 ml-1">({s.session_id})</span>
                )}
                <span className="text-xs text-slate-500 ml-2">
                  {s.num_questions} soru · {s.num_options || 5} şık
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                {s.scanned_count > 0 && (
                  <span className="bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-2 py-0.5 rounded-full">
                    {s.scanned_count} tarandı
                  </span>
                )}
                {s.roster_count > 0 && (
                  <span className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
                    {s.roster_count} öğrenci
                  </span>
                )}
                <ChevronRight className="w-4 h-4" />
              </div>
            </button>
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

  const handleResume = ({ session: s, results: r }) => {
    setSession(s);
    setResults(r);
    setPage(r.length > 0 ? "results" : "scan");
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <Header page={page} setPage={setPage} session={session} />
      <main className="pb-20">
        {page === "setup" && (
          <>
            <SavedSessionsList onResume={handleResume} />
            <SetupPage session={session} setSession={setSession} setPage={setPage} />
          </>
        )}
        {page === "roster" && <RosterPage session={session} setPage={setPage} />}
        {page === "scan" && <ScanPage session={session} setResults={setResults} results={results} />}
        {page === "review" && <ReviewPage session={session} results={results} />}
        {page === "results" && <ResultsPage session={session} results={results} />}
      </main>
    </div>
  );
}
