# OMR Scanner — Optik Form Okuyucu + El Yazisi Tanima Sistemi

Sinav kagitlarini telefon kamerasiyla tarayan, optik formu okuyan, el yazisi karakter kutularindan ogrenci bilgilerini cikaran ve sinif listesiyle eslestirerek otomatik notlandiran web tabanli sistem.

**React + FastAPI + OpenCV + OCR + SQLite**

---

## Ozellikler

### Form Olusturma
- **Optik Form Olusturucu** — A4 PDF formatinda yazdirilabilir sinav formu (ArUco hizalama isaretleri, QR kod, karakter kutulari, balon cevap alanlari)
- **Esnek Soru Sayisi** — 20 ve 40 soru destegi
- **Secenek Ayari** — A-B-C-D (4 sik) veya A-B-C-D-E (5 sik)
- **Kitapcik A/B Destegi** — Opsiyonel kitapcik secici, kapaliysa formda gosterilmez
- **Ders Kodu** — Formun basliginda ve QR kodunda ders kodu bilgisi

### Tarama ve Tanima
- **Kamera ile Tarama** — Telefon kamerasini kullanarak optik form okuma (veya fotograf yukleme)
- **OMR Motoru** — OpenCV tabanli balon algilama, ArUco kose isaretleri ile perspektif duzeltme, adaptif esikleme
- **OCR Motoru** — Karakter kutularindan el yazisi tanima (ad, soyad, ogrenci no)
- **QR Kod Okuma** — Formdan sinav bilgilerini (sinav ID, ders, soru sayisi) otomatik okuma
- **Kitapcik Algilama** — Taranan formda A/B kitapcik balonunu otomatik tespit ederek dogru cevap anahtariyla notlandirma
- **Form Gorseli Kaydetme** — Her taranan ogrencinin optik form gorseli kaydedilir, sonradan incelenebilir

### Sinif Yonetimi
- **Sinif Listesi** — Manuel, toplu yapistirma veya PDF yukleme ile ogrenci listesi olusturma
- **Otomatik Eslestirme** — Taranan kagitlari ogrenci numarasi/isim ile sinif listesine eslestirme
- **Manuel Dogrulama** — Dusuk guvenli OCR sonuclarini ogretmenin duzenleyebildigi dogrulama ekrani

### Notlandirma ve Analiz
- **Otomatik Notlandirma** — Cevap anahtarina gore aninda puanlama
- **Istatistikler** — Sinif ortalamasi, en yuksek/en dusuk puan, puan dagilimi, soru bazli dogru orani analizi
- **CSV Disari Aktarma** — Tum sonuclari (ogrenci bilgileri, puanlar, cevaplar) CSV dosyasi olarak indirme

### Veri Yonetimi
- **Kalici Depolama** — Sinav oturumlari, cevap anahtarlari, sinif listeleri, tarama sonuclari ve form gorselleri SQLite veritabaninda saklanir; sunucu yeniden baslatilsa bile veriler korunur
- **Kayitli Sinavlara Devam** — Daha once olusturulan sinavlar ders koduyla listelenir, tek tikla kaldigi yerden devam edilir
- **Coklu Sinav Destegi** — Ayni anda birden fazla sinav oturumu olusturulabilir ve yonetilebilir

---

## Mimari

```
┌─────────────────────┐      ┌──────────────────────────────┐
│   React + Vite      │      │   FastAPI Backend             │
│   (Frontend)        │      │                               │
│                     │      │  ┌────────────────────────┐  │
│  • Ayarlar          │      │  │  OMR Engine (OpenCV)   │  │
│  • Sinif Listesi    │ API  │  │  • ArUco algilama      │  │
│  • Tarama           │◄────►│  │  • Perspektif duzeltme │  │
│  • Dogrulama        │      │  │  • Balon okuma         │  │
│  • Sonuclar         │      │  │  • Kitapcik algilama   │  │
│                     │      │  └────────────────────────┘  │
│  Vercel             │      │  ┌────────────────────────┐  │
│                     │      │  │  OCR Engine            │  │
└─────────────────────┘      │  │  • Karakter tanima      │  │
                             │  │  • Sablon eslestirme   │  │
                             │  └────────────────────────┘  │
                             │  ┌────────────────────────┐  │
                             │  │  Form Generator        │  │
                             │  │  (ReportLab + QR)      │  │
                             │  └────────────────────────┘  │
                             │  ┌────────────────────────┐  │
                             │  │  QR Reader (pyzbar)    │  │
                             │  └────────────────────────┘  │
                             │  ┌────────────────────────┐  │
                             │  │  SQLite Storage        │  │
                             │  │  • Oturumlar           │  │
                             │  │  • Sonuclar            │  │
                             │  │  • Form gorselleri     │  │
                             │  └────────────────────────┘  │
                             │                               │
                             │  Render (Docker)              │
                             └──────────────────────────────┘
```

---

## Hizli Baslangic

### Yerel Kurulum

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Tarayicida **http://localhost:5173** adresini acin.

### Docker

```bash
cd backend
docker build -t omr-backend .
docker run -p 8000:8000 omr-backend
```

### Ortam Degiskenleri

| Degisken | Varsayilan | Aciklama |
|----------|-----------|----------|
| `VITE_API_URL` | `""` (ayni origin) | Frontend icin backend API adresi |
| `OMR_DATA_DIR` | `/tmp/omr_data` | SQLite veritabani dizini |

---

## Kullanim

### 1. Sinav Olusturma

1. **Ayarlar** sekmesine gidin
2. Soru sayisini secin (20 veya 40)
3. Secenek sayisini belirleyin (A-B-C-D veya A-B-C-D-E)
4. Ders kodunu girin (ornegin MAT101)
5. Kitapcik A/B kullanacaksaniz toggle'i acin
6. Cevap anahtarini isaretleyin (kitapcik aciksa her iki kitapcik icin ayri ayri)
7. **"Yazdirilabilir form indir"** ile PDF'i indirin ve A4 kagida yazdirin
8. **"Devam et"** ile sinav oturumunu olusturun

### 2. Sinif Listesi (Istege Bagli)

1. **Sinif Listesi** sekmesine gidin
2. Ogrenci eklemek icin uc yontem:
   - **Tek tek ekleme** — Ad, Soyad, No alanlarina yazin
   - **Toplu yapistirma** — Excel'den kopyala-yapistir (Ad, Soyad, No formatinda)
   - **PDF yukleme** — Sinif listesi PDF dosyasi yukleyin, otomatik ayiklanir
3. **"Kaydet ve taramaya gec"** butonuna basin

### 3. Tarama

1. **Tara** sekmesine gidin
2. Telefon kamerasini acin veya fotograf yukleyin
3. Doldurulan formu cerceve icine hizalayin (4 kose isareti gorunmeli)
4. Yakalama butonuna basin
5. Sonuc aninda gorunur: puan, cevaplar, ogrenci bilgileri
6. Her taranan formun gorseli otomatik kaydedilir

### 4. Dogrulama

1. **Dogrula** sekmesinde dusuk guvenli OCR sonuclari listelenir
2. Taranan form goruntusunu inceleyip ad/soyad/numara duzeltebilirsiniz
3. Onaylayinca ogrenci sinif listesiyle yeniden eslestirilir

### 5. Sonuclar ve Analiz

1. **Sonuclar** sekmesinde:
   - Sinif ortalamasi, en yuksek/en dusuk puan
   - Puan dagilimi
   - Soru bazli dogru orani analizi
   - Sinif listesi yuklediyseniz, her ogrencinin notu
   - Tum taranan kagitlarin detayli sonuclari
2. **CSV olarak disari aktarabilirsiniz** (ogrenci bilgileri + puanlar)

### 6. Kayitli Sinava Devam Etme

1. **Ayarlar** sekmesinde **"Kayitli Sinavlar"** listesi gorunur
2. Ders kodu, soru sayisi, taranan ogrenci sayisi gosterilir
3. Tiklayarak sinava kaldigi yerden devam edebilirsiniz
4. Tum veriler (cevap anahtari, sinif listesi, tarama sonuclari, form gorselleri) korunur

---

## Optik Form Yapisi

```
┌──────────────────────────────────────────┐
│ [ArUco 0]                    [ArUco 1]   │
│                                          │
│          SINAV OPTIK FORMU               │
│          Ders: MAT101                    │
│                                          │
│  AD      [_][_][_][_][_]...[_]  (20 ktu) │
│  SOYAD   [_][_][_][_][_]...[_]  (20 ktu) │
│  NO      [_][_][_][_][_][_][_][_][_]     │
│                        KITAPCIK: (A)(B)  │
│                                          │
│  [QR KOD]                                │
│  (sinav ID, ders, soru sayisi)           │
│                                          │
│        A   B   C   D   E                 │
│   1.  (A) (B) (C) (D) (E)               │
│   2.  (A) (B) (C) (D) (E)               │
│   ...         5'li gruplar halinde       │
│                                          │
│ [ArUco 2]                    [ArUco 3]   │
└──────────────────────────────────────────┘
```

**Form ozellikleri:**
- Sutun basliklari (A B C D E) her zaman gorunur
- 5'li gruplar halinde satir ayiricilari
- Alternatif satir arka planlari (kolay okuma icin)
- Kitapcik secici opsiyonel (kapaliysa formda gosterilmez)
- Footer: "Made by Sena Kose"

---

## OMR Nasil Calisir

1. **ArUco Algilama** — 4 kose isareti OpenCV ArUco modulu ile bulunur
2. **Perspektif Duzeltme** — Goruntu duz hale getirilir (aci, egiklik duzeltmesi)
3. **Adaptif Esikleme** — Farkli isik kosullarinda calismak icin
4. **Balon Analizi** — Her balon bolgesinin dolulik orani hesaplanir
5. **Karar Mantigi** — Dolulik > %35 ise isaretli; birden fazla isaretlenmisse en yuksek secilir veya belirsiz olarak isaretlenir
6. **Kitapcik Algilama** — NO satirindaki A/B balonlari okunarak dogru cevap anahtari secilir
7. **OCR** — Karakter kutulasindan sablon eslestirme + kontur analizi ile harf/rakam tanima
8. **QR Okuma** — pyzbar ile formdan sinav bilgileri cikartilir

---

## Teknoloji

| Bilesen | Teknoloji |
|---------|-----------|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python 3.11, FastAPI |
| OMR Motoru | OpenCV 4.10 (ArUco + adaptif esikleme) |
| OCR Motoru | OpenCV sablon eslestirme + kontur analizi |
| QR Kod | qrcode (olusturma), pyzbar (okuma) |
| PDF Olusturma | ReportLab (DejaVuSans font — Turkce destek) |
| PDF Ayiklama | pdfplumber (sinif listesi PDF okuma) |
| Veritabani | SQLite (kalici oturum/sonuc depolama) |
| Kamera | react-webcam |
| Deploy | Render (backend Docker), Vercel (frontend) |

---

## Proje Yapisi

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI endpoint'leri
│   │   ├── omr_engine.py       # OpenCV OMR isleme
│   │   ├── ocr_engine.py       # Karakter tanima motoru
│   │   ├── qr_reader.py        # QR kod okuyucu
│   │   ├── form_generator.py   # PDF form olusturucu
│   │   ├── storage.py          # SQLite kalici depolama
│   │   └── models.py           # Pydantic semalari
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Ana React uygulama
│   │   ├── main.jsx            # Giris noktasi
│   │   └── index.css           # Tailwind stilleri
│   ├── package.json
│   └── vercel.json
├── sample_forms/               # Ornek optik formlar (20q, 40q)
└── README.md
```

---

## API Endpoint'leri

### Oturum Yonetimi

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Sinav oturumu olustur (cevap anahtari, ders kodu, kitapcik ayari ile) |
| `GET` | `/api/sessions` | Tum kayitli sinavlari listele (ders kodu, soru sayisi, taranan/ogrenci sayisi) |
| `GET` | `/api/sessions/{id}` | Oturum detaylarini getir (cevap anahtari, sonuclar, sinif listesi dahil) |

### Form Olusturma

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | Bos form PDF indir (secenek sayisi, kitapcik gosterme parametreleri) |
| `POST` | `/api/forms/generate` | Ozel form olustur (baslik, ders kodu, kutu sayilari vs.) |

### Tarama

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Yuklenen goruntuden tara (dosya yukleme) |
| `POST` | `/api/scan/base64` | Base64 goruntuden tara (kamera yakalama) |

### Sinif Listesi

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sinif listesi yukle (JSON formatinda) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sinif listesi yukle (PDF dosyasindan otomatik ayiklama) |
| `GET` | `/api/sessions/{id}/roster` | Sinif listesini getir (notlar dahil) |

### Dogrulama

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Dogrulama bekleyen taramalar |
| `POST` | `/api/sessions/{id}/verify` | OCR sonucunu duzenle/onayla |

### Sonuclar ve Analiz

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/stats` | Sinav istatistikleri (ortalama, dagilim, soru analizi) |
| `GET` | `/api/sessions/{id}/export` | Sonuclari CSV olarak indir |

---

## Yapilandirma

### OMR Motoru (`omr_engine.py`)

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `fill_threshold` | 0.35 | Balonun isaretli sayilmasi icin minimum dolulik orani |
| `ambiguity_threshold` | 0.15 | En yuksek iki balon arasindaki minimum fark |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sozluk tipi |

### OCR Motoru (`ocr_engine.py`)

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `empty_threshold` | 0.03 | Kutunun bos sayilmasi icin esik |
| `REVIEW_THRESHOLD` | 0.6 | Bu guvenden dusuk sonuclar dogrulama gerektirir |

### Form Olusturucu (`form_generator.py`)

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `num_questions` | 40 | Soru sayisi (20 veya 40) |
| `options` | A,B,C,D,E | Secenek listesi |
| `show_booklet` | true | Kitapcik secicisini goster/gizle |
| `name_boxes` | 20 | Ad icin karakter kutusu sayisi |
| `surname_boxes` | 20 | Soyad icin karakter kutusu sayisi |
| `student_no_boxes` | 9 | Ogrenci no icin kutu sayisi |

---

## Sorun Giderme

**"4 isaret bulunamadi"**
- 4 kose isaretinin tamaminin goruntuye girdiginden emin olun
- Isaretler uzerinde golge olmasin
- Kamerayi yaklasik 30cm yukseklikten sabit tutun

**Dusuk dogruluk**
- Koyu kalem/tukenmez ile balonlari tamamen doldurun
- Iyi ve duz aydinlatma saglayin
- Burusuk veya katlanmis kagit kullanmayin

**Kamera calismiyor**
- Tarayicida kamera iznini verin
- HTTPS veya localhost kullanin (kamera guvenli baglam gerektirir)

**Turkce karakterler formda gorunmuyor**
- Backend'de `fonts-dejavu-core` paketinin yuklu oldugunu kontrol edin
- Docker kullaniyorsaniz Dockerfile'da zaten mevcut

**Veriler kayboldu**
- `OMR_DATA_DIR` ortam degiskeninin kalici bir dizine isaret ettiginden emin olun
- Docker kullaniyorsaniz volume mount yapin: `-v /host/path:/tmp/omr_data`

---

## Lisans

MIT Lisansi

---

Ogretmenler icin gelistirilmistir.
