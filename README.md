# OMR Scanner — Optik Form Okuyucu + El Yazisi Tanima Sistemi

Sinav kagitlarini telefon kamerasiyla tarayan, optik formu okuyan, el yazisi karakter kutularindan ogrenci bilgilerini cikaran ve sinif listesiyle eslestirerek otomatik notlandiran web tabanli sistem.

**React + FastAPI + OpenCV + OCR**

---

## Ozellikler

- **Optik Form Olusturucu** — A4 PDF formatinda yazdirilabilir sinav formu (ArUco hizalama isaretleri, QR kod, karakter kutulari, balon cevap alanlari)
- **Kamera ile Tarama** — Telefon kamerasini kullanarak optik form okuma (veya fotograf yukleme)
- **OMR Motoru** — OpenCV tabanli balon algilama, adaptif esikleme
- **OCR Motoru** — Karakter kutularindan el yazisi tanima (ad, soyad, ogrenci no)
- **QR Kod Okuma** — Formdan sinav bilgilerini otomatik okuma
- **Sinif Listesi** — Manuel, toplu yapistirma veya PDF yukleme ile ogrenci listesi olusturma
- **Otomatik Eslestirme** — Taranan kagitlari ogrenci numarasi/isim ile sinif listesine eslestirme
- **Manuel Dogrulama** — Dusuk guvenli OCR sonuclarini ogretmenin duzenleyebildigi dogrulama ekrani
- **Otomatik Notlandirma** — Cevap anahtarina gore aninda puanlama
- **Istatistikler** — Sinif ortalamasi, puan dagilimi, soru bazli analiz
- **CSV Disari Aktarma** — Tum sonuclari indirme

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
│  • Sonuclar         │      │  └────────────────────────┘  │
│                     │      │  ┌────────────────────────┐  │
│  Vercel             │      │  │  OCR Engine            │  │
│                     │      │  │  • Karakter tanima      │  │
└─────────────────────┘      │  │  • Sablon eslestirme   │  │
                             │  └────────────────────────┘  │
                             │  ┌────────────────────────┐  │
                             │  │  Form Generator        │  │
                             │  │  (ReportLab + QR)      │  │
                             │  └────────────────────────┘  │
                             │  ┌────────────────────────┐  │
                             │  │  QR Reader (pyzbar)    │  │
                             │  └────────────────────────┘  │
                             │                               │
                             │  Render (Docker)              │
                             └──────────────────────────────┘
```

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

## Kullanim

### 1. Sinav Olusturma

1. **Ayarlar** sekmesine gidin
2. Soru sayisini secin (20 / 40 / 60 / 80)
3. Secenek sayisini belirleyin (A-B-C-D veya A-B-C-D-E)
4. Ders kodunu girin (istege bagli)
5. Cevap anahtarini isaretleyin
6. **"Yazdirilabilir form indir"** ile PDF'i indirin ve A4 kagida yazdirin

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
3. Doldurulan formu cerceve icine hizalayin
4. Yakalama butonuna basin
5. Sonuc aninda gorunur: puan, cevaplar, ogrenci bilgileri

### 4. Dogrulama

1. **Dogrula** sekmesinde dusuk guvenli OCR sonuclari listelenir
2. Form goruntusunu inceleyip ad/soyad/numara duzeltebilirsiniz
3. Onaylayin

### 5. Sonuclar

1. **Sonuclar** sekmesinde tum taranan kagitlar ve puanlar gorulur
2. Sinif listesi yuklediyseniz, eslestirilen ogrencilerin notlari gorulur
3. CSV olarak disari aktarabilirsiniz

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
│                                 (9 ktu)  │
│                                          │
│  [QR KOD]                                │
│  (sinav ID, ders, soru sayisi)           │
│                                          │
│  CEVAPLAR                                │
│   1. (A)(B)(C)(D)(E)  21. (A)(B)(C)(D)(E)│
│   2. (A)(B)(C)(D)(E)  22. (A)(B)(C)(D)(E)│
│   ...         5'li gruplar halinde       │
│                                          │
│ [ArUco 2]                    [ArUco 3]   │
└──────────────────────────────────────────┘
```

## OMR Nasil Calisir

1. **ArUco Algilama** — 4 kose isareti OpenCV ArUco modulu ile bulunur
2. **Perspektif Duzeltme** — Goruntu duz hale getirilir (aci, egiklik duzeltmesi)
3. **Adaptif Esikleme** — Farkli isik kosullarinda calismak icin
4. **Balon Analizi** — Her balon bolgesinin dolulik orani hesaplanir
5. **Karar Mantigi** — Dolulik > %35 ise isaretli; birden fazla isaretlenmisse en yuksek secilir veya belirsiz olarak isaretlenir
6. **OCR** — Karakter kutulasindan sablon eslestirme + kontur analizi ile harf/rakam tanima
7. **QR Okuma** — pyzbar ile formdan sinav bilgileri cikartilir

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
| Kamera | react-webcam |
| Deploy | Render (backend Docker), Vercel (frontend) |

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
└── README.md
```

## API Endpoint'leri

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Sinav oturumu olustur (cevap anahtari ile) |
| `GET` | `/api/sessions/{id}` | Oturum detaylarini getir |
| `GET` | `/api/forms/download/{n}` | Bos form PDF indir |
| `POST` | `/api/forms/generate` | Ozel form olustur |
| `POST` | `/api/scan` | Yuklenen goruntuden tara |
| `POST` | `/api/scan/base64` | Base64 goruntuden tara (kamera) |
| `POST` | `/api/sessions/{id}/roster` | Sinif listesi yukle (JSON) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sinif listesi yukle (PDF) |
| `GET` | `/api/sessions/{id}/roster` | Sinif listesini getir |
| `GET` | `/api/sessions/{id}/review` | Dogrulama bekleyen taramalar |
| `POST` | `/api/sessions/{id}/verify` | OCR sonucunu duzenle/onayla |
| `GET` | `/api/sessions/{id}/stats` | Sinav istatistikleri |
| `GET` | `/api/sessions/{id}/export` | Sonuclari CSV olarak indir |

## Yapilandirma

`omr_engine.py` temel parametreleri:

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `fill_threshold` | 0.35 | Balonun isaretli sayilmasi icin minimum dolulik orani |
| `ambiguity_threshold` | 0.15 | En yuksek iki balon arasindaki minimum fark |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sozluk tipi |

`ocr_engine.py` temel parametreleri:

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `empty_threshold` | 0.03 | Kutunun bos sayilmasi icin esik |
| `REVIEW_THRESHOLD` | 0.6 | Bu guvenden dusuk sonuclar dogrulama gerektirir |

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

## Lisans

MIT Lisansi

---

Ogretmenler icin gelistirilmistir.
