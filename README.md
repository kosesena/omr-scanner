<div align="center">

<br>

<img src="https://img.shields.io/badge/%E2%80%8E-OMR%20Scanner-black?style=for-the-badge&labelColor=0f172a&color=1e293b" alt="OMR Scanner" height="40">

<br><br>

**Optik Form Okuyucu ve El Yazısı Tanıma Sistemi**

<sub>Sınav kağıtlarını telefon kamerasıyla tarayan, optik işleme ile cevapları okuyan,<br>el yazısı tanıma ile öğrenci bilgilerini çıkaran ve otomatik notlandıran bulut tabanlı platform.</sub>

<br>

<a href="https://react.dev"><img src="https://img.shields.io/badge/React_19-0f172a?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"></a>
<a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0f172a?style=for-the-badge&logo=fastapi&logoColor=009688" alt="FastAPI"></a>
<a href="https://opencv.org"><img src="https://img.shields.io/badge/OpenCV_4.10-0f172a?style=for-the-badge&logo=opencv&logoColor=5C3EE8" alt="OpenCV"></a>
<a href="https://supabase.com"><img src="https://img.shields.io/badge/Supabase-0f172a?style=for-the-badge&logo=supabase&logoColor=3FCF8E" alt="Supabase"></a>

<br><br>

<a href="https://omr-scanner-nhfmmgemm-sena-koses-projects.vercel.app">Canlı Demo</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;<a href="#api-referansı">API Dokümantasyonu</a>&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;<a href="#hızlı-başlangıç">Kurulum</a>

<br>

---

</div>

<br>

## Genel Bakış

OMR Scanner, öğretmenlerin sınav sürecini uçtan uca dijitalleştiren bir web uygulamasıdır. Yazdırılabilir optik form oluşturma, telefon kamerasıyla tarama, otomatik notlandırma, sınıf listesi eşleştirme ve detaylı istatistik analizi tek bir platformda sunar. Her öğretmen kendi hesabıyla giriş yapar ve yalnızca kendi sınavlarını görür.

<br>

## Özellikler

<table>
<tr>
<td width="50%" valign="top">

### Form Oluşturma
- A4 PDF formatında yazdırılabilir sınav formu
- ArUco hizalama işaretleri, QR kod, karakter kutuları
- 20 veya 40 soru sayısı seçeneği
- 4 şık (A-D) veya 5 şık (A-E) seçeneği
- Opsiyonel Kitapçık A/B desteği
- Ders kodu entegrasyonu (başlık + QR)

</td>
<td width="50%" valign="top">

### Tarama ve Tanıma
- Telefon kamerası ile canlı tarama veya fotoğraf yükleme
- ArUco tabanlı perspektif düzeltme (8 ön-işleme stratejisi)
- Adaptif eşikleme ile balon algılama
- El yazısı OCR (ad, soyad, öğrenci no)
- QR kod ile sınav meta verisi okuma
- Kitapçık A/B otomatik algılama

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Kullanıcı ve Sınıf Yönetimi
- Öğretmen girişi (Supabase Auth, e-posta/şifre)
- JWT tabanlı güvenli oturum (RS256/HS256, JWKS)
- Her öğretmen yalnızca kendi verilerini görür
- Sınıf listesi: manuel, toplu yapıştırma veya PDF
- Otomatik öğrenci eşleştirme (numara/isim)
- Manuel doğrulama ve düzeltme ekranı

</td>
<td width="50%" valign="top">

### Notlandırma ve Analiz
- Cevap anahtarına göre anlık puanlama
- Kitapçık değişikliğinde otomatik yeniden puanlama
- Sınıf ortalaması, en yüksek/düşük puan
- Puan dağılımı ve soru bazlı doğru oranı
- CSV dışa aktarma
- Taranan form görsellerinin kalıcı depolanması

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
     |   > Sınıf Listesi  |                         |   Form Üretici  (ReportLab)  |
     |   > Tarama         |                         |   QR Okuyucu    (pyzbar)     |
     |   > Doğrulama      |                         |   Auth          (JWT/JWKS)   |
     |   > Sonuçlar       |                         |                              |
     |   > Formlar        |                         +------------------------------+
     |                    |                                       |
     +--------------------+                                 Docker / Render
           Vercel
```

<br>

## Hızlı Başlangıç

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

Tarayıcıda `http://localhost:5173` adresini açın.

</td>
</tr>
</table>

> Supabase ortam değişkenleri tanımlanmamışsa auth atlanır ve tek kullanıcı modunda çalışır.

### Docker

```bash
cd backend
docker build -t omr-backend .
docker run -p 8000:8000 omr-backend
```

<br>

## Ortam Değişkenleri

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
<td>Supabase service_role anahtarı</td>
<td><code>eyJ...</code> formatı</td>
</tr>
<tr>
<td><code>SUPABASE_JWT_SECRET</code></td>
<td>JWT token doğrulama anahtarı</td>
<td>Settings > API > JWT Secret</td>
</tr>
<tr>
<td><code>OMR_DATA_DIR</code></td>
<td>SQLite fallback dizini</td>
<td>Varsayılan: <code>/tmp/omr_data</code></td>
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
<td>Supabase anon (public) anahtarı</td>
<td><code>eyJ...</code> formatı</td>
</tr>
</table>

<br>

## Kullanım Kılavuzu

### 1 &mdash; Kayıt ve Giriş

Uygulamayı açtığında giriş ekranı karşılar. İlk kullanımda **Kayıt Ol** ile e-posta ve şifre belirle, sonraki girişlerde **Giriş Yap** ile devam et. Her öğretmen yalnızca kendi sınavlarını görür.

### 2 &mdash; Sınav Oluşturma

**Ayarlar** sekmesinden soru sayısını (20 veya 40), şık sayısını (4 veya 5), ders kodunu ve kitapçık tercihini ayarla. Cevap anahtarını işaretleyip **Yazdırılabilir form indir** ile PDF'i al. **Devam et** ile sınav oturumunu başlat.

### 3 &mdash; Sınıf Listesi

**Sınıf** sekmesinden öğrenci ekle: tek tek giriş, Excel'den toplu yapıştırma veya PDF yükleme. Bu adım isteğe bağlı — sınıf listesi olmadan da tarama yapılabilir.

### 4 &mdash; Tarama

**Tara** sekmesinde telefon kamerasını aç veya fotoğraf yükle. Doldurulan formu çerçeve içine hizala (4 köşe işareti görünmeli) ve yakalama butonuna bas. Sonuç anında görünür: öğrenci numarası ve notu.

### 5 &mdash; Doğrulama

**Doğrula** sekmesinde tüm taramalar listelenir. Taranan form görüntüsü eşliğinde ad, soyad, numara ve kitapçık manuel olarak düzeltilip kaydedilir. Sonuçlar genellikle bu adımda doğrulanarak kesinleştirilir.

### 6 &mdash; Sonuçlar ve Analiz

**Sonuçlar** sekmesinde sınıf ortalaması, puan dağılımı ve soru bazlı analiz görüntülenir. Tüm sonuçları CSV olarak indirebilirsin. **Formlar** sekmesinde taranan optik formları görüntüleyip indirebilirsin.

<br>

## Optik Form Yapısı

```
+--------------------------------------------------+
|  [ArUco 0]                          [ArUco 1]    |
|                                                  |
|              SINAV OPTİK FORMU                   |
|              Ders: MAT101                        |
|                                                  |
|   AD      [_][_][_][_][_][_]...[_]    (20 kutu)  |
|   SOYAD   [_][_][_][_][_][_]...[_]    (20 kutu)  |
|   NO      [_][_][_][_][_][_][_][_][_]            |
|                            KİTAPÇIK:  (A)  (B)   |
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

## OMR İşleme Hattı

| Adım | İşlem | Açıklama |
|:----:|-------|----------|
| 1 | ArUco Algılama | 4 köşe işareti, 8 ön-işleme stratejisi, çoklu ölçek (0.5x-1.25x) |
| 2 | Perspektif Düzeltme | Açı ve eğiklik düzeltmesi, 1200x1700 px normalize çıktı |
| 3 | Gölge Normalizasyonu | Gaussian blur ile yerel aydınlatma tahmini, eşit kontrastlı çıktı |
| 4 | CLAHE | Adaptif histogram eşitleme ile balon kontrastını artırma |
| 5 | Balon Analizi | Her balonun ortalama yoğunluk değeri, en karanlık = işaretli |
| 6 | Karar Mantığı | Yoğunluk farkı eşikleri: işaretli / boş / birden fazla işaretli |
| 7 | Kitapçık Algılama | A/B balon yoğunluk karşılaştırması |
| 8 | OCR | Şablon eşleştirme + kontür analizi ile karakter tanıma |
| 9 | QR Okuma | pyzbar ile sınav ID, ders kodu, soru sayısı |

<br>

## Teknoloji Yığını

| Katman | Teknolojiler |
|--------|-------------|
| **Frontend** | React 19, Vite 8, Tailwind CSS 4, lucide-react, react-webcam, axios |
| **Backend** | Python 3.11, FastAPI, uvicorn |
| **Kimlik Doğrulama** | Supabase Auth, PyJWT (RS256/HS256), JWKS otomatik anahtar yönetimi |
| **Görüntü İşleme** | OpenCV 4.10, ArUco, CLAHE, adaptif eşikleme, gölge normalizasyonu |
| **Karakter Tanıma** | OpenCV şablon eşleştirme, kontür analizi |
| **QR Kod** | qrcode (oluşturma), pyzbar (okuma) |
| **PDF** | ReportLab (DejaVuSans Türkçe font desteği), pdfplumber |
| **Veritabanı** | Supabase PostgreSQL, SQLite fallback |
| **Dosya Depolama** | Supabase Storage (form görselleri) |
| **Dağıtım** | Render (Docker), Vercel |

<br>

## Proje Yapısı

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI endpoint'leri ve iş mantığı
│   │   ├── auth.py                 JWT/JWKS kimlik doğrulama
│   │   ├── omr_engine.py           OpenCV tabanlı OMR motoru
│   │   ├── ocr_engine.py           El yazısı karakter tanıma
│   │   ├── qr_reader.py            QR kod okuyucu
│   │   ├── form_generator.py       PDF form oluşturucu
│   │   ├── storage.py              Supabase + SQLite veri katmanı
│   │   └── models.py               Pydantic veri şemaları
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 Ana React uygulaması (~2000 satır)
│   │   ├── main.jsx                Giriş noktası
│   │   └── index.css               Tailwind yapılandırması
│   ├── package.json
│   └── vercel.json
└── README.md
```

<br>

## API Referansı

> Tüm `/api/sessions/*` ve `/api/scan/*` endpoint'leri `Authorization: Bearer <token>` header'ı gerektirir.
> Form oluşturma endpoint'leri herkese açıktır.

<details>
<summary><b>Oturum Yönetimi</b></summary>
<br>

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Yeni sınav oturumu oluştur |
| `GET` | `/api/sessions` | Kullanıcının sınavlarını listele |
| `GET` | `/api/sessions/{id}` | Oturum detaylarını getir |
| `DELETE` | `/api/sessions/{id}` | Sınavı tamamen sil |
| `DELETE` | `/api/sessions/{id}/results/{idx}` | Tek tarama sonucunu sil |

</details>

<details>
<summary><b>Form Oluşturma</b></summary>
<br>

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | n soruluk boş form PDF indir |
| `POST` | `/api/forms/generate` | Özel parametrelerle form oluştur |

</details>

<details>
<summary><b>Tarama</b></summary>
<br>

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Dosya yükleyerek tara |
| `POST` | `/api/scan/base64` | Base64 görüntüden tara (kamera) |

</details>

<details>
<summary><b>Sınıf Listesi</b></summary>
<br>

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sınıf listesi yükle (JSON) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sınıf listesi yükle (PDF) |
| `GET` | `/api/sessions/{id}/roster` | Sınıf listesini getir |

</details>

<details>
<summary><b>Doğrulama ve Sonuçlar</b></summary>
<br>

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Doğrulama bekleyenleri getir |
| `POST` | `/api/sessions/{id}/verify` | Sonucu düzenle ve onayla |
| `GET` | `/api/sessions/{id}/stats` | Sınav istatistikleri |
| `GET` | `/api/sessions/{id}/export` | CSV dışa aktarma |

</details>

<br>

## Yapılandırma Parametreleri

<details>
<summary><b>OMR Motoru</b></summary>
<br>

| Parametre | Varsayılan | Açıklama |
|-----------|:---------:|----------|
| `fill_threshold` | 0.35 | Balon doluluk eşiği |
| `ambiguity_threshold` | 0.15 | Belirsiz işaretleme eşiği |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sözlük tipi |
| Shadow normalization | Gaussian 101x101 | Yerel aydınlatma tahmini |
| CLAHE | clipLimit=3.0 | Adaptif kontrast |

</details>

<details>
<summary><b>OCR Motoru</b></summary>
<br>

| Parametre | Varsayılan | Açıklama |
|-----------|:---------:|----------|
| `empty_threshold` | 0.03 | Boş kutu algılama eşiği |
| `REVIEW_THRESHOLD` | 0.6 | Doğrulama gerektiren güven eşiği |

</details>

<details>
<summary><b>Form Oluşturucu</b></summary>
<br>

| Parametre | Varsayılan | Açıklama |
|-----------|:---------:|----------|
| `num_questions` | 40 | Soru sayısı (20 veya 40) |
| `options` | A, B, C, D, E | Şık listesi |
| `show_booklet` | true | Kitapçık seçicisi görünsün mü |
| `name_boxes` | 20 | Ad karakter kutusu sayısı |
| `surname_boxes` | 20 | Soyad karakter kutusu sayısı |
| `student_no_boxes` | 9 | Numara kutusu sayısı |

</details>

<br>

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| Köşe işaretleri bulunamadı | 4 ArUco işaretinin tamamı çerçevede olmalı, gölge ve kırışıklık olmamalı |
| Kitapçık yanlış algılandı | Doğrulama ekranında A/B butonuyla değiştir, puan otomatik güncellenir |
| Düşük okuma doğruluğu | Koyu kurşun kalem kullanın, kağıt düz ve iyi aydınlatılmış olmalı |
| Kamera açılmıyor | Tarayıcı kamera izni verin, HTTPS gereklidir |
| Türkçe karakter bozuk | Docker'da `fonts-dejavu-core` paketini kontrol edin |
| Veriler kayboldu | Supabase yapılandırın; Render free tier geçici dosya sistemi kullanır |
| 401 Unauthorized | Backend ortam değişkenlerini kontrol edin: `SUPABASE_URL`, `SUPABASE_JWT_SECRET` |

<br>

## Platform ve Dağıtım Mimarisi

Proje üç ayrı bulut platformu üzerinde çalışır. Her biri farklı bir sorumluluğu üstlenir:

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────────┐
│     Vercel       │     │       Render         │     │      Supabase        │
│                  │     │                      │     │                      │
│  React 19 SPA   │────▶│  FastAPI (Docker)     │────▶│  Auth (JWT/JWKS)     │
│  Vite 8 build   │ API │  Python 3.11          │     │  PostgreSQL DB       │
│  Tailwind CSS 4 │     │  OpenCV + Tesseract   │     │  Storage (görseller) │
│                  │     │  Port: 8000           │     │                      │
└─────────────────┘     └─────────────────────┘     └──────────────────────┘
```

### Frontend — Vercel

React 19 + Vite 8 ile oluşturulan tek sayfa uygulama (SPA) Vercel üzerinde barındırılır.

| Özellik | Detay |
|---------|-------|
| **Framework** | Vite 8 (React 19) |
| **Build komutu** | `npm run build` |
| **Çıktı dizini** | `dist` |
| **Root dizin** | `frontend` |
| **Routing** | `vercel.json` ile tüm rotalar `index.html`'e yönlendirilir (SPA fallback) |

**Ortam değişkenleri:**

| Değişken | Açıklama |
|----------|----------|
| `VITE_API_URL` | Render üzerindeki backend API adresi (`https://xxx.onrender.com`) |
| `VITE_SUPABASE_URL` | Supabase proje URL'si (`https://xxx.supabase.co`) |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon (public) anahtarı — istemci tarafı auth için |

Frontend, kullanıcı arayüzünü sunar ve tüm API isteklerini Render'daki backend'e yönlendirir. Supabase ile doğrudan yalnızca kimlik doğrulama (giriş/kayıt) için iletişim kurar.

### Backend — Render (Docker)

FastAPI tabanlı Python backend'i Docker konteyneri olarak Render üzerinde çalışır.

| Özellik | Detay |
|---------|-------|
| **Base image** | Python 3.11 Slim |
| **Framework** | FastAPI + Uvicorn |
| **Port** | 8000 |
| **Plan** | Free tier |
| **Dockerfile** | `backend/Dockerfile` |
| **Yapılandırma** | `render.yaml` |

**Docker konteynerinde yüklü sistem paketleri:**

| Paket | Kullanım |
|-------|----------|
| `libzbar0` | QR kod okuma (pyzbar) |
| `fonts-dejavu-core` | Türkçe karakterli PDF oluşturma (ReportLab) |
| `tesseract-ocr`, `tesseract-ocr-tur` | OCR — Türkçe el yazısı tanıma |
| `libglib2.0-0` | OpenCV bağımlılığı |

**Ortam değişkenleri:**

| Değişken | Açıklama |
|----------|----------|
| `SUPABASE_URL` | Supabase proje URL'si |
| `SUPABASE_SERVICE_KEY` | Supabase service_role anahtarı (tam yetki) |
| `SUPABASE_JWT_SECRET` | JWT token doğrulama anahtarı (HS256 fallback) |
| `OMR_DATA_DIR` | SQLite fallback dizini (varsayılan: `/tmp/omr_data`) |

**Backend'in yaptığı işler:**
- Yüklenen form görüntülerini OpenCV ile işler (perspektif düzeltme, balon okuma)
- Tesseract + şablon eşleştirme ile el yazısı tanır (ad, soyad, numara)
- pyzbar ile QR koddan sınav meta verisini okur
- ReportLab ile yazdırılabilir optik form PDF'i oluşturur
- Sınav oturumlarını Supabase veritabanına kaydeder
- Taranan form görsellerini Supabase Storage'a yükler
- JWT token doğrulaması ile kullanıcı bazlı erişim kontrolü sağlar

> **Not:** Supabase ortam değişkenleri tanımlanmamışsa backend otomatik olarak SQLite'a düşer ve tek kullanıcı modunda çalışır (geliştirme ortamı için).

### Supabase — Veritabanı, Auth ve Depolama

Supabase üç temel hizmet sunar:

#### 1. Kimlik Doğrulama (Auth)

| Özellik | Detay |
|---------|-------|
| **Yöntem** | E-posta / şifre |
| **Token formatı** | JWT (RS256 — JWKS ile doğrulama, HS256 fallback) |
| **JWKS endpoint** | `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` |
| **Kullanıcı izolasyonu** | Her öğretmen yalnızca kendi `user_id`'sine ait oturumları görebilir |

Kullanıcı giriş yaptığında Supabase bir JWT token verir. Bu token her API isteğinde `Authorization: Bearer <token>` header'ı ile backend'e gönderilir. Backend, token'ı doğrulayarak `user_id`'yi çıkarır ve tüm veritabanı sorgularını bu ID ile filtreler.

#### 2. Veritabanı (PostgreSQL)

Tek bir `sessions` tablosu tüm sınav verilerini tutar:

```sql
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,      -- benzersiz oturum kimliği
  user_id    UUID REFERENCES auth.users(id),  -- öğretmenin Supabase user ID'si
  data       JSONB NOT NULL,        -- tüm sınav verisi (aşağıya bakın)
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
```

**`data` JSONB sütununda saklanan veriler:**

| Alan | Açıklama |
|------|----------|
| `answer_key` | Cevap anahtarı (soru → doğru şık) |
| `answer_key_b` | Kitapçık B cevap anahtarı (opsiyonel) |
| `use_booklet` | A/B kitapçık modu aktif mi |
| `num_questions` | Soru sayısı |
| `num_options` | Şık sayısı (4 veya 5) |
| `exam_id` | QR koddan okunan sınav kimliği |
| `course_code` | Ders kodu |
| `results[]` | Tarama sonuçları dizisi (her tarama: öğrenci bilgisi, cevaplar, puan, form görseli URL'si) |
| `roster[]` | Sınıf listesi (ad, soyad, numara, eşleşen puan) |
| `pending_review[]` | Doğrulama bekleyen tarama indeksleri |

#### 3. Dosya Depolama (Storage)

| Özellik | Detay |
|---------|-------|
| **Bucket adı** | `form-images` |
| **Erişim** | Public |
| **Dosya formatı** | JPEG |
| **Yol yapısı** | `{session_id}/{result_index}.jpg` |
| **Public URL** | `{SUPABASE_URL}/storage/v1/object/public/form-images/{session_id}/{0}.jpg` |

Taranan her optik form görseli base64'ten JPEG'e dönüştürülerek bu bucket'a yüklenir. Oturum silindiğinde ilgili tüm görseller de otomatik olarak temizlenir.

<br>

### Dağıtım Adımları

<table>
<tr>
<td width="33%" valign="top">

#### Backend — Render

1. Yeni **Web Service** oluştur
2. Runtime: **Docker**
3. Root directory: `backend`
4. Ortam değişkenleri:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `SUPABASE_JWT_SECRET`

</td>
<td width="33%" valign="top">

#### Frontend — Vercel

1. Yeni proje oluştur
2. Root: `frontend`
3. Build: `npm run build`
4. Output: `dist`
5. Ortam değişkenleri:
   - `VITE_API_URL`
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`

</td>
<td width="34%" valign="top">

#### Supabase

1. Yeni proje oluştur
2. SQL Editor'da yukarıdaki `CREATE TABLE` sorgusunu çalıştır
3. Storage: `form-images` bucket oluştur (public)
4. Auth: Email provider'ı aktif et

</td>
</tr>
</table>

### Veri Akışı

```
1. Öğretmen giriş yapar → Supabase Auth → JWT token alınır
2. Sınav oluşturulur    → POST /api/sessions/create → Supabase PostgreSQL'e kaydedilir
3. Form taranır         → POST /api/scan/base64 → OpenCV + OCR işler → sonuç Supabase'e yazılır
4. Görsel yüklenir      → Form görseli → Supabase Storage (form-images bucket)
5. Sınıf listesi eklenir → POST /api/sessions/{id}/roster → session data'ya eklenir
6. Sonuçlar incelenir   → GET /api/sessions/{id}/stats → istatistikler hesaplanır
7. CSV dışa aktarılır   → GET /api/sessions/{id}/export → indirilebilir dosya
```

<br>

## Lisans

MIT

<br>

---

<div align="center">

<sub>Crafted with care for teachers by **Sena Köse**</sub>

</div>
