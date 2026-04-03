# OMR Scanner

**Optik Form Okuyucu ve El Yazisi Tanima Sistemi**

Sinav kagitlarini telefon kamerasiyla tarayan, optik formu okuyan, el yazisi karakter kutularindan ogrenci bilgilerini cikaran ve sinif listesiyle eslestirerek otomatik notlandiran web tabanli sistem.

`React` · `FastAPI` · `OpenCV` · `Supabase` · `OCR`

---

## Ozellikler

### Form Olusturma

- **Optik Form Olusturucu** — A4 PDF formatinda yazdirilabilir sinav formu. ArUco hizalama isaretleri, QR kod, karakter kutulari ve balon cevap alanlari icerir.
- **Esnek Soru Sayisi** — 5 ile 200 arasi soru destegi
- **Sik Secenegi** — A-B-C-D (4 sik) veya A-B-C-D-E (5 sik)
- **Kitapcik A/B Destegi** — Opsiyonel kitapcik secici; kapaliysa formda gosterilmez
- **Ders Kodu** — Formun basliginda ve QR kodunda ders kodu bilgisi

### Tarama ve Tanima

- **Kamera ile Tarama** — Telefon kamerasini kullanarak optik form okuma veya fotograf yukleme
- **OMR Motoru** — OpenCV tabanli balon algilama, ArUco kose isaretleri ile perspektif duzeltme ve adaptif esikleme
- **Gelismis Marker Algilama** — 8 farkli on-isleme stratejisi (CLAHE, blur, golge normalizasyon, adaptif esik, Otsu, keskinlestirme) ve coklu olcek (0.5x, 0.75x, 1.0x, 1.25x) ile yuksek basari orani
- **OCR Motoru** — Karakter kutularindan el yazisi tanima (ad, soyad, ogrenci no)
- **QR Kod Okuma** — Formdan sinav bilgilerini (sinav ID, ders kodu, soru sayisi) otomatik okuma
- **Kitapcik Algilama** — Taranan formda A/B kitapcik balonunu otomatik tespit ederek dogru cevap anahtariyla notlandirma
- **Manuel Kitapcik Duzeltme** — Dogrulama ekraninda kitapcik A/B manuel degistirilebilir, otomatik yeniden notlandirma yapilir
- **Form Gorseli Kaydetme** — Her taranan ogrencinin optik form gorseli Supabase Storage'da kalici olarak saklanir

### Sinif Yonetimi

- **Sinif Listesi** — Manuel giris, toplu yapistirma veya PDF yukleme ile ogrenci listesi olusturma
- **Otomatik Eslestirme** — Taranan kagitlari ogrenci numarasi veya isim ile sinif listesine eslestirme
- **Manuel Dogrulama** — Tum taramalar ogretmen onayindan gecer; ad, soyad, numara ve kitapcik duzenlenebilir

### Notlandirma ve Analiz

- **Otomatik Notlandirma** — Cevap anahtarina gore anlik puanlama
- **Istatistikler** — Sinif ortalamasi, en yuksek ve en dusuk puan, puan dagilimi, soru bazli dogru orani analizi
- **CSV Disa Aktarma** — Tum sonuclari (ogrenci bilgileri, puanlar, cevaplar) CSV dosyasi olarak indirme

### Veri Yonetimi

- **Supabase Entegrasyonu** — Sinav oturumlari PostgreSQL'de, form gorselleri Supabase Storage'da kalici olarak saklanir. Sunucu yeniden baslatilsa veya deploy edilse bile veriler korunur.
- **SQLite Fallback** — Supabase yapilandirilmamissa yerel SQLite veritabani kullanilir (gelistirme modu)
- **Kayitli Sinavlara Devam** — Daha once olusturulan sinavlar ders koduyla listelenir, tek tikla kaldigi yerden devam edilir
- **Coklu Sinav Destegi** — Ayni anda birden fazla sinav oturumu olusturulabilir ve yonetilebilir
- **Sinav ve Sonuc Silme** — Sinavlar tamamen silinebilir veya tek tek tarama sonuclari kaldirilabilir

### Formlar Galerisi

- **Formlar Sayfasi** — Taranan tum optik formlarin grid gorunumunde listelenmesi
- **Buyuk Goruntuleme** — Forma tiklayarak tam boyut modal goruntusu
- **Form Indirme** — Her form gorseli ayri ayri indirilebilir

### Mobil Uyumlu Tasarim

- **Responsive Arayuz** — Masaustunde genis tablo, mobilde kart tabanli gorunum
- **Mobil Sinif Listesi** — Kucuk ekranlarda ozel kart layout'u ile ogrenci listesi
- **Responsive Istatistikler** — Mobilde kompakt stat kartlari

---

## Mimari

```
┌─────────────────────────┐        ┌────────────────────────────────┐
│                         │        │                                │
│   React + Vite          │        │   FastAPI Backend              │
│   Frontend              │        │                                │
│                         │        │   ┌────────────────────────┐   │
│   · Ayarlar             │        │   │  OMR Engine            │   │
│   · Sinif Listesi       │  REST  │   │  OpenCV · ArUco        │   │
│   · Tarama              │◄──────►│   │  Perspektif duzeltme   │   │
│   · Dogrulama           │        │   │  Balon okuma           │   │
│   · Sonuclar            │        │   │  Kitapcik algilama     │   │
│   · Formlar             │        │   └────────────────────────┘   │
│                         │        │   ┌────────────────────────┐   │
│   Vercel                │        │   │  OCR Engine            │   │
│                         │        │   │  Karakter tanima       │   │
└─────────────────────────┘        │   │  Sablon eslestirme     │   │
                                   │   └────────────────────────┘   │
┌─────────────────────────┐        │   ┌────────────────────────┐   │
│                         │        │   │  Form Generator        │   │
│   Supabase              │        │   │  ReportLab + QR Code   │   │
│                         │        │   └────────────────────────┘   │
│   · PostgreSQL          │◄───────│   ┌────────────────────────┐   │
│     (oturumlar)         │        │   │  QR Reader (pyzbar)    │   │
│   · Storage             │        │   └────────────────────────┘   │
│     (form gorselleri)   │        │                                │
│                         │        │   Render (Docker)              │
└─────────────────────────┘        └────────────────────────────────┘
```

---

## Hizli Baslangic

### Yerel Kurulum

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Tarayicida `http://localhost:5173` adresini acin.

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
| `SUPABASE_URL` | — | Supabase proje URL'si |
| `SUPABASE_SERVICE_KEY` | — | Supabase service_role anahtari (legacy JWT formati `eyJ...`) |
| `OMR_DATA_DIR` | `/tmp/omr_data` | SQLite fallback dizini (Supabase yoksa) |

> **Not:** Supabase Python SDK yeni `sb_secret_...` format anahtarlarla uyumlu degildir. Supabase Dashboard > Settings > API > Service Role Key altindaki `eyJ...` ile baslayan legacy JWT anahtarini kullanin.

---

## Kullanim

### 1. Sinav Olusturma

1. **Ayarlar** sekmesine gidin
2. Soru sayisini secin (5-200 arasi)
3. Sik sayisini belirleyin (A-B-C-D veya A-B-C-D-E)
4. Ders kodunu girin (ornegin MAT101)
5. Kitapcik A/B kullanacaksaniz toggle'i acin
6. Cevap anahtarini isaretleyin (kitapcik aciksa her iki kitapcik icin ayri ayri)
7. **Yazdirilabilir form indir** ile PDF'i indirin ve A4 kagida yazdirin
8. **Devam et** ile sinav oturumunu olusturun

### 2. Sinif Listesi (Istege Bagli)

1. **Sinif** sekmesine gidin
2. Ogrenci eklemek icin uc yontem:
   - **Tek tek ekleme** — Ad, Soyad, No alanlarina yazin
   - **Toplu yapistirma** — Excel'den kopyala-yapistir (Ad, Soyad, No formatinda)
   - **PDF yukleme** — Sinif listesi PDF dosyasi yukleyin, otomatik ayiklanir
3. **Kaydet ve taramaya gec** butonuna basin

### 3. Tarama

1. **Tara** sekmesine gidin
2. Telefon kamerasini acin veya fotograf yukleyin
3. Doldurulan formu cerceve icine hizalayin (4 kose isareti gorunmeli)
4. Yakalama butonuna basin
5. Sonuc aninda gorunur: puan, cevaplar, ogrenci bilgileri
6. Her taranan formun gorseli otomatik olarak Supabase Storage'a yuklenir

### 4. Dogrulama

1. **Dogrula** sekmesinde tum tarama sonuclari listelenir
2. Taranan form goruntusu ile birlikte ad, soyad ve numara duzenlenebilir
3. Kitapcik yanlis algilandiysa A/B butonu ile degistirilir (puan otomatik yeniden hesaplanir)
4. Onaylayinca ogrenci sinif listesiyle eslestirilir ve notu kaydedilir

### 5. Formlar

1. **Formlar** sekmesinde taranan tum optik formlar grid gorunumunde listelenir
2. Forma tiklayarak buyuk goruntu acilir
3. Indirme butonu ile form gorseli kaydedilebilir

### 6. Sonuclar ve Analiz

1. **Sonuclar** sekmesinde:
   - Sinif ortalamasi, en yuksek ve en dusuk puan
   - Puan dagilimi
   - Soru bazli dogru orani analizi
   - Sinif listesi yuklediyseniz her ogrencinin notu
   - Tum taranan kagitlarin detayli sonuclari
2. CSV olarak disa aktarabilirsiniz
3. Tek tek tarama sonuclarini veya tum sinavi silebilirsiniz

### 7. Kayitli Sinava Devam Etme

1. **Ayarlar** sekmesinde **Kayitli Sinavlar** listesi gorunur
2. Ders kodu, soru sayisi ve taranan ogrenci sayisi gosterilir
3. Tiklayarak sinava kaldigi yerden devam edebilirsiniz
4. Tum veriler (cevap anahtari, sinif listesi, tarama sonuclari, form gorselleri) korunur

---

## Optik Form Yapisi

```
┌──────────────────────────────────────────────┐
│  [ArUco 0]                      [ArUco 1]    │
│                                              │
│            SINAV OPTIK FORMU                 │
│            Ders: MAT101                      │
│                                              │
│   AD      [_][_][_][_][_]...[_]   (20 kutu)  │
│   SOYAD   [_][_][_][_][_]...[_]   (20 kutu)  │
│   NO      [_][_][_][_][_][_][_][_][_]        │
│                          KITAPCIK: (A) (B)   │
│                                              │
│   [QR KOD]                                   │
│   (sinav ID, ders kodu, soru sayisi)         │
│                                              │
│         A    B    C    D    E                 │
│    1.  (A)  (B)  (C)  (D)  (E)               │
│    2.  (A)  (B)  (C)  (D)  (E)               │
│    ...          5'li gruplar halinde          │
│                                              │
│  [ArUco 2]                      [ArUco 3]    │
└──────────────────────────────────────────────┘
```

**Form ozellikleri:**

- Sutun basliklari (A B C D E) her sutunun ustunde gorunur
- 5'li gruplar halinde satir ayiricilari
- Alternatif satir arka planlari (kolay okuma icin)
- Kitapcik secici opsiyonel (kapaliysa formda gosterilmez)
- Footer: Made by Sena Kose

---

## OMR Nasil Calisir

1. **ArUco Algilama** — 4 kose isareti OpenCV ArUco modulu ile bulunur. 8 farkli on-isleme stratejisi (CLAHE, blur, golge normalizasyon, adaptif esik, Otsu, keskinlestirme, guclu CLAHE, ham gri) birlestirilerek maksimum algilama saglanir.
2. **Coklu Olcek** — Isaretler bulunamazsa goruntu 0.75x, 1.25x ve 0.5x olceklerde yeniden taranir
3. **Perspektif Duzeltme** — Goruntu duz hale getirilir (aci ve egiklik duzeltmesi)
4. **Adaptif Esikleme** — Farkli isik kosullarinda calisabilmek icin
5. **Balon Analizi** — Her balon bolgesinin doluluk orani hesaplanir
6. **Karar Mantigi** — Doluluk %35'in uzerindeyse isaretli kabul edilir; birden fazla isaretlenmisse en yuksek secilir veya belirsiz olarak isaretlenir
7. **Kitapcik Algilama** — NO satirindaki A/B balonlari okunarak dogru cevap anahtari secilir
8. **OCR** — Karakter kutularindan sablon eslestirme ve kontur analizi ile harf/rakam tanima
9. **QR Okuma** — pyzbar ile formdan sinav bilgileri cikartilir

---

## Teknoloji Yigini

| Bilesen | Teknoloji |
|---------|-----------|
| Frontend | React 19, Vite 8, Tailwind CSS 4 |
| Backend | Python 3.11, FastAPI |
| OMR Motoru | OpenCV 4.10 (ArUco + adaptif esikleme + coklu on-isleme) |
| OCR Motoru | OpenCV sablon eslestirme + kontur analizi |
| QR Kod | qrcode (olusturma), pyzbar (okuma) |
| PDF Olusturma | ReportLab (DejaVuSans — Turkce karakter destegi) |
| PDF Ayiklama | pdfplumber (sinif listesi PDF okuma) |
| Veritabani | Supabase PostgreSQL (kalici depolama) + SQLite (fallback) |
| Gorsel Depolama | Supabase Storage (form gorselleri) |
| Kamera | react-webcam |
| HTTP | axios |
| Ikonlar | lucide-react |
| Dagitim | Render (backend, Docker), Vercel (frontend) |

---

## Proje Yapisi

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI endpoint'leri
│   │   ├── omr_engine.py         OpenCV OMR isleme (marker algilama, balon okuma, kitapcik)
│   │   ├── ocr_engine.py         Karakter tanima motoru
│   │   ├── qr_reader.py          QR kod okuyucu
│   │   ├── form_generator.py     PDF form olusturucu
│   │   ├── storage.py            Supabase + SQLite depolama katmani
│   │   └── models.py             Pydantic semalari
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx               Ana React uygulamasi (tek dosya)
│   │   ├── main.jsx              Giris noktasi
│   │   └── index.css             Tailwind stilleri
│   ├── package.json
│   └── vercel.json
├── sample_forms/                  Ornek optik formlar
└── README.md
```

---

## API Referansi

### Oturum Yonetimi

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Sinav oturumu olustur |
| `GET` | `/api/sessions` | Tum kayitli sinavlari listele |
| `GET` | `/api/sessions/{id}` | Oturum detaylarini getir |
| `DELETE` | `/api/sessions/{id}` | Sinavi ve tum verilerini sil |
| `DELETE` | `/api/sessions/{id}/results/{index}` | Tek bir tarama sonucunu sil |

### Form Olusturma

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | Bos form PDF indir |
| `POST` | `/api/forms/generate` | Ozel form olustur |

### Tarama

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Yuklenen goruntuden tara (dosya yukleme) |
| `POST` | `/api/scan/base64` | Base64 goruntuden tara (kamera yakalama) |

### Sinif Listesi

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sinif listesi yukle (JSON) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sinif listesi yukle (PDF) |
| `GET` | `/api/sessions/{id}/roster` | Sinif listesini getir |

### Dogrulama

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Dogrulama bekleyen taramalari getir |
| `POST` | `/api/sessions/{id}/verify` | OCR sonucunu duzenle, kitapcik degistir ve onayla |

### Sonuclar ve Analiz

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/stats` | Sinav istatistikleri |
| `GET` | `/api/sessions/{id}/export` | Sonuclari CSV olarak indir |

---

## Yapilandirma

### OMR Motoru — `omr_engine.py`

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `fill_threshold` | 0.35 | Balonun isaretli sayilmasi icin minimum doluluk orani |
| `ambiguity_threshold` | 0.15 | En yuksek iki balon arasindaki minimum fark |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sozluk tipi |

### OCR Motoru — `ocr_engine.py`

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `empty_threshold` | 0.03 | Kutunun bos sayilmasi icin esik degeri |
| `REVIEW_THRESHOLD` | 0.6 | Bu guvenin altindaki sonuclar dogrulama gerektirir |

### Form Olusturucu — `form_generator.py`

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `num_questions` | 40 | Soru sayisi (5-200) |
| `options` | A, B, C, D, E | Sik listesi |
| `show_booklet` | true | Kitapcik secicisini goster veya gizle |
| `name_boxes` | 20 | Ad icin karakter kutusu sayisi |
| `surname_boxes` | 20 | Soyad icin karakter kutusu sayisi |
| `student_no_boxes` | 9 | Ogrenci numarasi icin kutu sayisi |

---

## Sorun Giderme

**4 isaret bulunamadi / Perspektif duzeltme basarisiz**
- 4 kose isaretinin tamaminin goruntude gorundugundan emin olun
- Isaretler uzerinde golge olmasin
- Kamerayi yaklasik 30 cm yukseklikten sabit tutun
- Hata mesajinda hangi marker'larin eksik oldugu gosterilir (orn. "Kose isaretcileri eksik: 2 (sol alt)")
- Sistem 8 farkli on-isleme ve 4 farkli olcek dener; yine de basarisizsa kagit duzlugunu kontrol edin

**Kitapcik yanlis algilandi**
- Dogrulama ekraninda A/B butonuyla kitapcigi manuel degistirebilirsiniz
- Degistirince puan dogru cevap anahtariyla yeniden hesaplanir

**Dusuk dogruluk**
- Koyu kalem veya tukenmez ile balonlari tamamen doldurun
- Iyi ve duz aydinlatma saglayin
- Burusuk veya katlanmis kagit kullanmayin

**Kamera calismiyor**
- Tarayicida kamera iznini verin
- HTTPS veya localhost kullanin (kamera guvenli baglam gerektirir)

**Turkce karakterler formda gorunmuyor**
- Backend'de `fonts-dejavu-core` paketinin yuklu oldugunu kontrol edin
- Docker kullaniyorsaniz Dockerfile'da zaten mevcut

**Veriler kayboldu**
- Supabase yapilandirilmissa veriler kalici olarak saklanir
- Supabase yoksa `OMR_DATA_DIR` degiskeninin kalici bir dizine isaret ettiginden emin olun
- Render free tier'da dosya sistemi gecicidir; kalici depolama icin Supabase kullanin

**Supabase baglanti hatasi**
- `SUPABASE_SERVICE_KEY` olarak legacy JWT formatini kullanin (`eyJ...` ile baslamali)
- Yeni `sb_secret_...` formati Python SDK ile uyumlu degildir

---

## Dagitim

### Backend (Render)

1. Render'da yeni bir **Web Service** olusturun
2. Docker runtime secin
3. Root directory: `backend`
4. Ortam degiskenlerini ekleyin:
   - `SUPABASE_URL` = Supabase proje URL'si
   - `SUPABASE_SERVICE_KEY` = Legacy JWT service_role key

### Frontend (Vercel)

1. Vercel'de yeni bir proje olusturun
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Ortam degiskeni: `VITE_API_URL` = Render backend URL'si

### Supabase Kurulumu

1. Supabase'de yeni bir proje olusturun
2. SQL Editor'da `sessions` tablosunu olusturun:
   ```sql
   CREATE TABLE sessions (
     session_id TEXT PRIMARY KEY,
     data TEXT NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```
3. Storage'da `form-images` bucket'i olusturun (public)
4. Settings > API'den legacy JWT service_role key'i alin

---

## Lisans

MIT

---

Ogretmenler icin gelistirilmistir.
