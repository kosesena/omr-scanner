<div align="center">

# OMR Scanner

**Optik Form Okuyucu ve El Yazisi Tanima Sistemi**

Sinav kagitlarini telefon kamerasiyla tarayan, optik formu okuyan, el yazisi karakter kutularindan ogrenci bilgilerini cikaran ve sinif listesiyle eslestirerek otomatik notlandiran web tabanli sistem.

[![React](https://img.shields.io/badge/React_19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV_4.10-5C3EE8?style=flat&logo=opencv&logoColor=white)](https://opencv.org)
[![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat&logo=supabase&logoColor=white)](https://supabase.com)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=flat&logo=vercel&logoColor=white)](https://vercel.com)
[![Render](https://img.shields.io/badge/Render-46E3B7?style=flat&logo=render&logoColor=white)](https://render.com)

[Canli Demo](https://omr-scanner-ng7f273w1-sena-koses-projects.vercel.app) · [API Dokumantasyonu](#api-referansi)

</div>

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

### Kullanici Yonetimi
- **Ogretmen Girisi** — E-posta ve sifre ile giris/kayit (Supabase Auth)
- **Veri Izolasyonu** — Her ogretmen sadece kendi sinavlarini gorur ve yonetir
- **Guvenli Oturum** — JWT tabanli kimlik dogrulama (RS256/HS256), JWKS ile otomatik anahtar yonetimi

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
                    +---------------------------+
                    |        Supabase           |
                    |  Auth / PostgreSQL / Strg  |
                    +---------------------------+
                              ^       ^
                              |       |
  +-------------------+       |       |       +----------------------------+
  |                   |       |       |       |                            |
  |  React + Vite     | REST  |       +-------+  FastAPI Backend           |
  |  Frontend         +-------+               |                            |
  |                   |                        |  OMR Engine (OpenCV)       |
  |  Ayarlar          |                        |  OCR Engine (Tesseract)    |
  |  Sinif Listesi    |                        |  Form Generator (PDF)      |
  |  Tarama           |                        |  QR Reader (pyzbar)        |
  |  Dogrulama        |                        |  Auth (JWT/JWKS)           |
  |  Sonuclar         |                        |                            |
  |  Formlar          |                        +----------------------------+
  |                   |                                    |
  +-------------------+                              Docker / Render
        Vercel
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

> Yerel gelistirmede Supabase env var'lari yoksa auth atlanir ve tek kullanici modunda calisir.

### Docker

```bash
cd backend
docker build -t omr-backend .
docker run -p 8000:8000 omr-backend
```

---

## Ortam Degiskenleri

### Backend (Render)

| Degisken | Aciklama |
|----------|----------|
| `SUPABASE_URL` | Supabase proje URL'si |
| `SUPABASE_SERVICE_KEY` | Supabase service_role anahtari (legacy JWT formati `eyJ...`) |
| `SUPABASE_JWT_SECRET` | Supabase JWT Secret (token dogrulama icin) |
| `OMR_DATA_DIR` | SQLite fallback dizini (varsayilan: `/tmp/omr_data`) |

### Frontend (Vercel)

| Degisken | Aciklama |
|----------|----------|
| `VITE_API_URL` | Backend API adresi |
| `VITE_SUPABASE_URL` | Supabase proje URL'si |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon (public) anahtari |

---

## Kullanim

### 1. Kayit ve Giris

1. Uygulamayi acin, giris ekrani karsilar
2. Ilk kullanimda **Kayit Ol** ile e-posta ve sifre belirleyin
3. Sonraki girislerde **Giris Yap** ile devam edin
4. Her ogretmen sadece kendi sinavlarini gorur

### 2. Sinav Olusturma

1. **Ayarlar** sekmesine gidin
2. Soru sayisini secin (5-200 arasi)
3. Sik sayisini belirleyin (A-B-C-D veya A-B-C-D-E)
4. Ders kodunu girin (ornegin MAT101)
5. Kitapcik A/B kullanacaksaniz toggle'i acin
6. Cevap anahtarini isaretleyin (kitapcik aciksa her iki kitapcik icin ayri ayri)
7. **Yazdirilabilir form indir** ile PDF'i indirin ve A4 kagida yazdirin
8. **Devam et** ile sinav oturumunu olusturun

### 3. Sinif Listesi (Istege Bagli)

1. **Sinif** sekmesine gidin
2. Ogrenci eklemek icin uc yontem:
   - **Tek tek ekleme** — Ad, Soyad, No alanlarina yazin
   - **Toplu yapistirma** — Excel'den kopyala-yapistir (Ad, Soyad, No formatinda)
   - **PDF yukleme** — Sinif listesi PDF dosyasi yukleyin, otomatik ayiklanir
3. **Kaydet ve taramaya gec** butonuna basin

### 4. Tarama

1. **Tara** sekmesine gidin
2. Telefon kamerasini acin veya fotograf yukleyin
3. Doldurulan formu cerceve icine hizalayin (4 kose isareti gorunmeli)
4. Yakalama butonuna basin
5. Sonuc aninda gorunur: puan, cevaplar, ogrenci bilgileri
6. Her taranan formun gorseli otomatik olarak Supabase Storage'a yuklenir

### 5. Dogrulama

1. **Dogrula** sekmesinde tum tarama sonuclari listelenir
2. Taranan form goruntusu ile birlikte ad, soyad ve numara duzenlenebilir
3. Kitapcik yanlis algilandiysa A/B butonu ile degistirilir (puan otomatik yeniden hesaplanir)
4. Onaylayinca ogrenci sinif listesiyle eslestirilir ve notu kaydedilir

### 6. Formlar

1. **Formlar** sekmesinde taranan tum optik formlar grid gorunumunde listelenir
2. Forma tiklayarak buyuk goruntu acilir
3. Indirme butonu ile form gorseli kaydedilebilir

### 7. Sonuclar ve Analiz

1. **Sonuclar** sekmesinde sinif ortalamasi, en yuksek/dusuk puan, puan dagilimi ve soru bazli analiz goruntulenir
2. Sinif listesi yuklediyseniz her ogrencinin notu listelenir
3. CSV olarak disa aktarabilirsiniz
4. Tek tek tarama sonuclarini veya tum sinavi silebilirsiniz

### 8. Kayitli Sinava Devam Etme

1. **Ayarlar** sekmesinde **Kayitli Sinavlar** listesi gorunur
2. Ders kodu, soru sayisi ve taranan ogrenci sayisi gosterilir
3. Tiklayarak sinava kaldigi yerden devam edebilirsiniz

---

## Optik Form Yapisi

```
+----------------------------------------------+
|  [ArUco 0]                      [ArUco 1]    |
|                                              |
|            SINAV OPTIK FORMU                 |
|            Ders: MAT101                      |
|                                              |
|   AD      [_][_][_][_][_]...[_]   (20 kutu)  |
|   SOYAD   [_][_][_][_][_]...[_]   (20 kutu)  |
|   NO      [_][_][_][_][_][_][_][_][_]        |
|                          KITAPCIK: (A) (B)   |
|                                              |
|   [QR KOD]                                   |
|                                              |
|         A    B    C    D    E                 |
|    1.  (A)  (B)  (C)  (D)  (E)               |
|    2.  (A)  (B)  (C)  (D)  (E)               |
|    ...          5'li gruplar halinde          |
|                                              |
|  [ArUco 2]                      [ArUco 3]    |
+----------------------------------------------+
```

- Sutun basliklari her sutunun ustunde gorunur
- 5'li gruplar halinde satir ayiricilari
- Alternatif satir arka planlari
- Kitapcik secici opsiyonel
- Footer: Made by Sena Kose

---

## OMR Pipeline

| Adim | Islem | Detay |
|------|-------|-------|
| 1 | ArUco Algilama | 4 kose isareti, 8 on-isleme stratejisi, coklu olcek |
| 2 | Perspektif Duzeltme | Aci ve egiklik duzeltmesi |
| 3 | Adaptif Esikleme | Farkli isik kosullarina uyum |
| 4 | Balon Analizi | Her balon bolgesinin doluluk orani |
| 5 | Karar Mantigi | %35 esik, belirsiz isaretleme tespiti |
| 6 | Kitapcik Algilama | A/B balon okuma |
| 7 | OCR | Sablon eslestirme + kontur analizi |
| 8 | QR Okuma | pyzbar ile sinav meta verisi |

---

## Teknoloji Yigini

| Katman | Teknoloji |
|--------|-----------|
| Frontend | React 19, Vite 8, Tailwind CSS 4, lucide-react |
| Backend | Python 3.11, FastAPI, uvicorn |
| Kimlik Dogrulama | Supabase Auth, JWT (RS256/HS256), JWKS |
| Goruntu Isleme | OpenCV 4.10, ArUco, adaptif esikleme |
| Karakter Tanima | OpenCV sablon eslestirme, kontur analizi |
| QR Kod | qrcode (olusturma), pyzbar (okuma) |
| PDF | ReportLab (DejaVuSans), pdfplumber |
| Veritabani | Supabase PostgreSQL + SQLite fallback |
| Depolama | Supabase Storage (form gorselleri) |
| Kamera | react-webcam |
| HTTP | axios |
| Dagitim | Render (Docker), Vercel |

---

## Proje Yapisi

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI endpoint'leri
│   │   ├── auth.py               JWT/JWKS kimlik dogrulama
│   │   ├── omr_engine.py         OpenCV OMR isleme
│   │   ├── ocr_engine.py         Karakter tanima motoru
│   │   ├── qr_reader.py          QR kod okuyucu
│   │   ├── form_generator.py     PDF form olusturucu
│   │   ├── storage.py            Supabase + SQLite depolama
│   │   └── models.py             Pydantic semalari
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx               Ana React uygulamasi
│   │   ├── main.jsx              Giris noktasi
│   │   └── index.css             Tailwind stilleri
│   ├── package.json
│   └── vercel.json
└── README.md
```

---

## API Referansi

> Tum `/api/sessions/*` ve `/api/scan/*` endpoint'leri `Authorization: Bearer <token>` header'i gerektirir. Form olusturma endpoint'leri herkese aciktir.

### Oturum Yonetimi

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Sinav oturumu olustur |
| `GET` | `/api/sessions` | Kullanicinin sinavlarini listele |
| `GET` | `/api/sessions/{id}` | Oturum detaylari |
| `DELETE` | `/api/sessions/{id}` | Sinavi sil |
| `DELETE` | `/api/sessions/{id}/results/{idx}` | Tek tarama sonucunu sil |

### Form Olusturma

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | Bos form PDF indir |
| `POST` | `/api/forms/generate` | Ozel form olustur |

### Tarama

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Dosya yukleyerek tara |
| `POST` | `/api/scan/base64` | Base64 goruntuden tara |

### Sinif Listesi

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sinif listesi yukle (JSON) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sinif listesi yukle (PDF) |
| `GET` | `/api/sessions/{id}/roster` | Sinif listesini getir |

### Dogrulama

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Dogrulama bekleyenleri getir |
| `POST` | `/api/sessions/{id}/verify` | Sonucu duzenle ve onayla |

### Sonuclar

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/stats` | Sinav istatistikleri |
| `GET` | `/api/sessions/{id}/export` | CSV disa aktarma |

---

## Yapilandirma

### OMR Motoru

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `fill_threshold` | 0.35 | Balon doluluk esigi |
| `ambiguity_threshold` | 0.15 | Belirsizlik esigi |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sozluk tipi |

### OCR Motoru

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `empty_threshold` | 0.03 | Bos kutu esigi |
| `REVIEW_THRESHOLD` | 0.6 | Dogrulama gerektiren guven esigi |

### Form Olusturucu

| Parametre | Varsayilan | Aciklama |
|-----------|-----------|----------|
| `num_questions` | 40 | Soru sayisi (5-200) |
| `options` | A, B, C, D, E | Sik listesi |
| `show_booklet` | true | Kitapcik secicisi |
| `name_boxes` | 20 | Ad kutu sayisi |
| `surname_boxes` | 20 | Soyad kutu sayisi |
| `student_no_boxes` | 9 | Numara kutu sayisi |

---

## Sorun Giderme

| Sorun | Cozum |
|-------|-------|
| 4 isaret bulunamadi | 4 kose isaretinin tamami goruntuye girmeli, golge olmamali |
| Kitapcik yanlis algilandi | Dogrulama ekraninda A/B butonu ile degistirin |
| Dusuk dogruluk | Koyu kalem kullanin, iyi aydinlatma saglayin |
| Kamera calismiyor | Tarayicida kamera izni verin, HTTPS kullanin |
| Turkce karakter sorunu | `fonts-dejavu-core` paketini kontrol edin |
| Veriler kayboldu | Supabase kullanin, Render free tier gecici dosya sistemi kullanir |
| Supabase baglanti hatasi | Legacy JWT key kullanin (`eyJ...` formati) |

---

## Dagitim

### Backend — Render

1. Yeni **Web Service** olusturun (Docker runtime)
2. Root directory: `backend`
3. Ortam degiskenleri: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`

### Frontend — Vercel

1. Yeni proje olusturun, root: `frontend`
2. Build: `npm run build`, output: `dist`
3. Ortam degiskenleri: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

### Supabase

1. Yeni proje olusturun
2. SQL Editor'da calistirin:
   ```sql
   CREATE TABLE sessions (
     session_id TEXT PRIMARY KEY,
     user_id UUID REFERENCES auth.users(id),
     data TEXT NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   CREATE INDEX idx_sessions_user_id ON sessions(user_id);
   ```
3. Storage'da `form-images` bucket'i olusturun (public)
4. Authentication > Providers > Email yapilandirilir

---

## Lisans

MIT

---

<div align="center">

Crafted with care for teachers by **Sena Kose**

</div>
