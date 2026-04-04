<div align="center">

<br>

<img src="https://img.shields.io/badge/%E2%80%8E-OMR%20Scanner-black?style=for-the-badge&labelColor=0f172a&color=1e293b" alt="OMR Scanner" height="40">

<br><br>

**Optik Form Okuyucu ve El Yazisi Tanima Sistemi**

<sub>Sinav kagitlarini telefon kamerasiyla tarayan, optik isleme ile cevaplari okuyan,<br>el yazisi tanima ile ogrenci bilgilerini cikaran ve otomatik notlandiran bulut tabanli platform.</sub>

<br>

<a href="https://react.dev"><img src="https://img.shields.io/badge/React_19-0f172a?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"></a>
<a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0f172a?style=for-the-badge&logo=fastapi&logoColor=009688" alt="FastAPI"></a>
<a href="https://opencv.org"><img src="https://img.shields.io/badge/OpenCV_4.10-0f172a?style=for-the-badge&logo=opencv&logoColor=5C3EE8" alt="OpenCV"></a>
<a href="https://supabase.com"><img src="https://img.shields.io/badge/Supabase-0f172a?style=for-the-badge&logo=supabase&logoColor=3FCF8E" alt="Supabase"></a>

<br><br>

<a href="https://omr-scanner-nhfmmgemm-sena-koses-projects.vercel.app">Canli Demo</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;<a href="#api-referansi">API Dokumantasyonu</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;<a href="#hizli-baslangic">Kurulum</a>

<br>

---

</div>

<br>

## Genel Bakis

OMR Scanner, ogretmenlerin sinav surecini uctan uca dijitallestiren bir web uygulamasidir. Yazdirilabilir optik form olusturma, telefon kamerasiyla tarama, otomatik notlandirma, sinif listesi eslestirme ve detayli istatistik analizi tek bir platformda sunar. Her ogretmen kendi hesabiyla giris yapar ve yalnizca kendi sinavlarini gorur.

<br>

## Ozellikler

<table>
<tr>
<td width="50%" valign="top">

### Form Olusturma
- A4 PDF formatinda yazdirilabilir sinav formu
- ArUco hizalama isaretleri, QR kod, karakter kutulari
- 5 ile 200 arasi esnek soru sayisi
- 4 sik (A-D) veya 5 sik (A-E) secenegi
- Opsiyonel Kitapcik A/B destegi
- Ders kodu entegrasyonu (baslik + QR)

</td>
<td width="50%" valign="top">

### Tarama ve Tanima
- Telefon kamerasi ile canli tarama veya foto yukleme
- ArUco tabanliperspektif duzeltme (8 on-isleme stratejisi)
- Adaptif esikleme ile balon algilama
- El yazisi OCR (ad, soyad, ogrenci no)
- QR kod ile sinav meta verisi okuma
- Kitapcik A/B otomatik algilama

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Kullanici ve Sinif Yonetimi
- Ogretmen girisi (Supabase Auth, e-posta/sifre)
- JWT tabanli guvenli oturum (RS256/HS256, JWKS)
- Her ogretmen yalnizca kendi verilerini gorur
- Sinif listesi: manuel, toplu yapistirma veya PDF
- Otomatik ogrenci eslestirme (numara/isim)
- Manuel dogrulama ve duzeltme ekrani

</td>
<td width="50%" valign="top">

### Notlandirma ve Analiz
- Cevap anahtarina gore anlik puanlama
- Kitapcik degisikliginde otomatik yeniden puanlama
- Sinif ortalamasi, en yuksek/dusuk puan
- Puan dagilimi ve soru bazli dogru orani
- CSV disa aktarma
- Taranan form gorsellerinin kalici depolanmasi

</td>
</tr>
</table>

<br>

## Mimari

```
                         +---------------------------------+
                         |           Supabase              |
                         |   Auth  |  PostgreSQL  |  Storage  |
                         +---------------------------------+
                                   ^            ^
                                   |            |
     +--------------------+   REST |            |   +------------------------------+
     |                    |   API  |            |   |                              |
     |   React 19 + Vite  |--------+            +---|   FastAPI Backend             |
     |   Tailwind CSS 4   |                         |                              |
     |                    |                         |   OMR Engine    (OpenCV)      |
     |   > Ayarlar        |                         |   OCR Engine    (Tesseract)   |
     |   > Sinif Listesi  |                         |   Form Uretici  (ReportLab)  |
     |   > Tarama         |                         |   QR Okuyucu    (pyzbar)     |
     |   > Dogrulama      |                         |   Auth          (JWT/JWKS)   |
     |   > Sonuclar       |                         |                              |
     |   > Formlar        |                         +------------------------------+
     |                    |                                       |
     +--------------------+                                 Docker / Render
           Vercel
```

<br>

## Hizli Baslangic

### Yerel Kurulum

<table>
<tr>
<td>

**Backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

</td>
<td>

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Tarayicida `http://localhost:5173` adresini acin.

</td>
</tr>
</table>

> Supabase ortam degiskenleri tanimlanmamissa auth atlanir ve tek kullanici modunda calisir.

### Docker

```bash
cd backend
docker build -t omr-backend .
docker run -p 8000:8000 omr-backend
```

<br>

## Ortam Degiskenleri

<table>
<tr>
<th colspan="3" align="left">Backend (Render)</th>
</tr>
<tr>
<td><code>SUPABASE_URL</code></td>
<td>Supabase proje URL'si</td>
<td><code>https://xxx.supabase.co</code></td>
</tr>
<tr>
<td><code>SUPABASE_SERVICE_KEY</code></td>
<td>Supabase service_role anahtari</td>
<td><code>eyJ...</code> formati</td>
</tr>
<tr>
<td><code>SUPABASE_JWT_SECRET</code></td>
<td>JWT token dogrulama anahtari</td>
<td>Settings > API > JWT Secret</td>
</tr>
<tr>
<td><code>OMR_DATA_DIR</code></td>
<td>SQLite fallback dizini</td>
<td>Varsayilan: <code>/tmp/omr_data</code></td>
</tr>
</table>

<table>
<tr>
<th colspan="3" align="left">Frontend (Vercel)</th>
</tr>
<tr>
<td><code>VITE_API_URL</code></td>
<td>Backend API adresi</td>
<td><code>https://xxx.onrender.com</code></td>
</tr>
<tr>
<td><code>VITE_SUPABASE_URL</code></td>
<td>Supabase proje URL'si</td>
<td><code>https://xxx.supabase.co</code></td>
</tr>
<tr>
<td><code>VITE_SUPABASE_ANON_KEY</code></td>
<td>Supabase anon (public) anahtari</td>
<td><code>eyJ...</code> formati</td>
</tr>
</table>

<br>

## Kullanim Kilavuzu

### 1 &mdash; Kayit ve Giris

Uygulamayi actiginda giris ekrani karsilar. Ilk kullanimda **Kayit Ol** ile e-posta ve sifre belirle, sonraki girislerde **Giris Yap** ile devam et. Her ogretmen yalnizca kendi sinavlarini gorur.

### 2 &mdash; Sinav Olusturma

**Ayarlar** sekmesinden soru sayisini (5-200), sik sayisini (4 veya 5), ders kodunu ve kitapcik tercihini ayarla. Cevap anahtarini isaretleyip **Yazdirilabilir form indir** ile PDF'i al. **Devam et** ile sinav oturumunu baslat.

### 3 &mdash; Sinif Listesi

**Sinif** sekmesinden ogrenci ekle: tek tek giris, Excel'den toplu yapistirma veya PDF yukleme. Bu adim istege bagli — sinif listesi olmadan da tarama yapilabilir.

### 4 &mdash; Tarama

**Tara** sekmesinde telefon kamerasini ac veya fotograf yukle. Doldurulan formu cerceve icine hizala (4 kose isareti gorunmeli) ve yakalama butonuna bas. Sonuc aninda gorunur: puan, cevaplar ve ogrenci bilgileri.

### 5 &mdash; Dogrulama

**Dogrula** sekmesinde tum taramalar listelenir. Taranan form goruntusu esliginde ad, soyad, numara ve kitapcik duzenlenebilir. Onaylanan taramalar sinif listesiyle eslestirilir.

### 6 &mdash; Sonuclar ve Analiz

**Sonuclar** sekmesinde sinif ortalamasi, puan dagilimi ve soru bazli analiz goruntulenir. Tum sonuclari CSV olarak indirebilirsin. **Formlar** sekmesinde taranan optik formlari goruntuleyip indirebilirsin.

<br>

## Optik Form Yapisi

```
+--------------------------------------------------+
|  [ArUco 0]                          [ArUco 1]    |
|                                                  |
|              SINAV OPTIK FORMU                   |
|              Ders: MAT101                        |
|                                                  |
|   AD      [_][_][_][_][_][_]...[_]    (20 kutu)  |
|   SOYAD   [_][_][_][_][_][_]...[_]    (20 kutu)  |
|   NO      [_][_][_][_][_][_][_][_][_]            |
|                            KITAPCIK:  (A)  (B)   |
|                                                  |
|   [QR KOD]                                       |
|                                                  |
|          A    B    C    D    E                    |
|     1.  (A)  (B)  (C)  (D)  (E)                  |
|     2.  (A)  (B)  (C)  (D)  (E)                  |
|     ...           5'li gruplar halinde            |
|                                                  |
|  [ArUco 2]                          [ArUco 3]    |
+--------------------------------------------------+
```

<br>

## OMR Isleme Hatti

| Adim | Islem | Aciklama |
|:----:|-------|----------|
| 1 | ArUco Algilama | 4 kose isareti, 8 on-isleme stratejisi, coklu olcek (0.5x-1.25x) |
| 2 | Perspektif Duzeltme | Aci ve egiklik duzeltmesi, 1200x1700 px normalize cikti |
| 3 | Golge Normalizasyonu | Gaussian blur ile yerel aydinlatma tahmini, esit kontrastli cikti |
| 4 | CLAHE | Adaptif histogram esitleme ile balon kontrastini artirma |
| 5 | Balon Analizi | Her balonun ortalama yogunluk degeri, en karanlik = isaretli |
| 6 | Karar Mantigi | Yogunluk farki esikleri: isaretli / bos / birden fazla isaretli |
| 7 | Kitapcik Algilama | A/B balon yogunluk karsilastirmasi |
| 8 | OCR | Sablon eslestirme + kontur analizi ile karakter tanima |
| 9 | QR Okuma | pyzbar ile sinav ID, ders kodu, soru sayisi |

<br>

## Teknoloji Yigini

| Katman | Teknolojiler |
|--------|-------------|
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, lucide-react, react-webcam, axios |
| **Backend** | Python 3.11, FastAPI, uvicorn |
| **Kimlik Dogrulama** | Supabase Auth, PyJWT (RS256/HS256), JWKS otomatik anahtar yonetimi |
| **Goruntu Isleme** | OpenCV 4.10, ArUco, CLAHE, adaptif esikleme, golge normalizasyonu |
| **Karakter Tanima** | OpenCV sablon eslestirme, kontur analizi |
| **QR Kod** | qrcode (olusturma), pyzbar (okuma) |
| **PDF** | ReportLab (DejaVuSans Turkce font destegi), pdfplumber |
| **Veritabani** | Supabase PostgreSQL, SQLite fallback |
| **Dosya Depolama** | Supabase Storage (form gorselleri) |
| **Dagitim** | Render (Docker), Vercel |

<br>

## Proje Yapisi

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI endpoint'leri ve is mantigi
│   │   ├── auth.py                 JWT/JWKS kimlik dogrulama
│   │   ├── omr_engine.py           OpenCV tabanli OMR motoru
│   │   ├── ocr_engine.py           El yazisi karakter tanima
│   │   ├── qr_reader.py            QR kod okuyucu
│   │   ├── form_generator.py       PDF form olusturucu
│   │   ├── storage.py              Supabase + SQLite veri katmani
│   │   └── models.py               Pydantic veri semalari
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 Ana React uygulamasi (~2000 satir)
│   │   ├── main.jsx                Giris noktasi
│   │   └── index.css               Tailwind yapilandirmasi
│   ├── package.json
│   └── vercel.json
└── README.md
```

<br>

## API Referansi

> Tum `/api/sessions/*` ve `/api/scan/*` endpoint'leri `Authorization: Bearer <token>` header'i gerektirir.
> Form olusturma endpoint'leri herkese aciktir.

<details>
<summary><b>Oturum Yonetimi</b></summary>
<br>

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Yeni sinav oturumu olustur |
| `GET` | `/api/sessions` | Kullanicinin sinavlarini listele |
| `GET` | `/api/sessions/{id}` | Oturum detaylarini getir |
| `DELETE` | `/api/sessions/{id}` | Sinavi tamamen sil |
| `DELETE` | `/api/sessions/{id}/results/{idx}` | Tek tarama sonucunu sil |

</details>

<details>
<summary><b>Form Olusturma</b></summary>
<br>

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | n soruluk bos form PDF indir |
| `POST` | `/api/forms/generate` | Ozel parametrelerle form olustur |

</details>

<details>
<summary><b>Tarama</b></summary>
<br>

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Dosya yukleyerek tara |
| `POST` | `/api/scan/base64` | Base64 goruntuden tara (kamera) |

</details>

<details>
<summary><b>Sinif Listesi</b></summary>
<br>

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sinif listesi yukle (JSON) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sinif listesi yukle (PDF) |
| `GET` | `/api/sessions/{id}/roster` | Sinif listesini getir |

</details>

<details>
<summary><b>Dogrulama ve Sonuclar</b></summary>
<br>

| Metod | Endpoint | Aciklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Dogrulama bekleyenleri getir |
| `POST` | `/api/sessions/{id}/verify` | Sonucu duzenle ve onayla |
| `GET` | `/api/sessions/{id}/stats` | Sinav istatistikleri |
| `GET` | `/api/sessions/{id}/export` | CSV disa aktarma |

</details>

<br>

## Yapilandirma Parametreleri

<details>
<summary><b>OMR Motoru</b></summary>
<br>

| Parametre | Varsayilan | Aciklama |
|-----------|:---------:|----------|
| `fill_threshold` | 0.35 | Balon doluluk esigi |
| `ambiguity_threshold` | 0.15 | Belirsiz isaretleme esigi |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sozluk tipi |
| Shadow normalization | Gaussian 101x101 | Yerel aydinlatma tahmini |
| CLAHE | clipLimit=3.0 | Adaptif kontrast |

</details>

<details>
<summary><b>OCR Motoru</b></summary>
<br>

| Parametre | Varsayilan | Aciklama |
|-----------|:---------:|----------|
| `empty_threshold` | 0.03 | Bos kutu algilama esigi |
| `REVIEW_THRESHOLD` | 0.6 | Dogrulama gerektiren guven esigi |

</details>

<details>
<summary><b>Form Olusturucu</b></summary>
<br>

| Parametre | Varsayilan | Aciklama |
|-----------|:---------:|----------|
| `num_questions` | 40 | Soru sayisi (5-200) |
| `options` | A, B, C, D, E | Sik listesi |
| `show_booklet` | true | Kitapcik secicisi gorunsun mu |
| `name_boxes` | 20 | Ad karakter kutusu sayisi |
| `surname_boxes` | 20 | Soyad karakter kutusu sayisi |
| `student_no_boxes` | 9 | Numara kutusu sayisi |

</details>

<br>

## Sorun Giderme

| Sorun | Cozum |
|-------|-------|
| Kose isaretleri bulunamadi | 4 ArUco isaretinin tamami cercevede olmali, golge ve kirisiklik olmamali |
| Kitapcik yanlis algilandi | Dogrulama ekraninda A/B butonuyla degistir, puan otomatik guncellenir |
| Dusuk okuma dogrulugu | Koyu kursun kalem kullanin, kagit duz ve iyi aydinlatilmis olmali |
| Kamera acilmiyor | Tarayici kamera izni verin, HTTPS gereklidir |
| Turkce karakter bozuk | Docker'da `fonts-dejavu-core` paketini kontrol edin |
| Veriler kayboldu | Supabase yapilandirin; Render free tier gecici dosya sistemi kullanir |
| 401 Unauthorized | Backend ortam degiskenlerini kontrol edin: `SUPABASE_URL`, `SUPABASE_JWT_SECRET` |

<br>

## Dagitim

<table>
<tr>
<td width="33%" valign="top">

### Backend — Render

1. Yeni **Web Service** olustur
2. Runtime: **Docker**
3. Root directory: `backend`
4. Ortam degiskenleri:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `SUPABASE_JWT_SECRET`

</td>
<td width="33%" valign="top">

### Frontend — Vercel

1. Yeni proje olustur
2. Root: `frontend`
3. Build: `npm run build`
4. Output: `dist`
5. Ortam degiskenleri:
   - `VITE_API_URL`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`

</td>
<td width="34%" valign="top">

### Supabase

1. Yeni proje olustur
2. SQL Editor'da calistir:
```sql
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id),
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_sessions_user
  ON sessions(user_id);
```
3. Storage: `form-images` bucket (public)
4. Auth: Email provider aktif

</td>
</tr>
</table>

<br>

## Lisans

MIT

<br>

---

<div align="center">

<sub>Crafted with care for teachers by **Sena Kose**</sub>

</div>
