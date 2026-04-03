# OMR Scanner

**Optik Form Okuyucu ve El Yazısı Tanıma Sistemi**

Sınav kağıtlarını telefon kamerasıyla tarayan, optik formu okuyan, el yazısı karakter kutularından öğrenci bilgilerini çıkaran ve sınıf listesiyle eşleştirerek otomatik notlandıran web tabanlı sistem.

`React` · `FastAPI` · `OpenCV` · `Supabase` · `OCR`

---

## Özellikler

### Form Oluşturma

- **Optik Form Oluşturucu** — A4 PDF formatında yazdırılabilir sınav formu. ArUco hizalama işaretleri, QR kod, karakter kutuları ve balon cevap alanları içerir.
- **Esnek Soru Sayısı** — 5 ile 200 arası soru desteği
- **Şık Seçeneği** — A-B-C-D (4 şık) veya A-B-C-D-E (5 şık)
- **Kitapçık A/B Desteği** — Opsiyonel kitapçık seçici; kapalıysa formda gösterilmez
- **Ders Kodu** — Formun başlığında ve QR kodunda ders kodu bilgisi

### Tarama ve Tanıma

- **Kamera ile Tarama** — Telefon kamerasını kullanarak optik form okuma veya fotoğraf yükleme
- **OMR Motoru** — OpenCV tabanlı balon algılama, ArUco köşe işaretleri ile perspektif düzeltme ve adaptif eşikleme
- **Gelişmiş Marker Algılama** — 8 farklı ön-işleme stratejisi (CLAHE, blur, gölge normalizasyon, adaptif eşik, Otsu, keskinleştirme) ve çoklu ölçek (0.5x, 0.75x, 1.0x, 1.25x) ile yüksek başarı oranı
- **OCR Motoru** — Karakter kutularından el yazısı tanıma (ad, soyad, öğrenci no)
- **QR Kod Okuma** — Formdan sınav bilgilerini (sınav ID, ders kodu, soru sayısı) otomatik okuma
- **Kitapçık Algılama** — Taranan formda A/B kitapçık balonunu otomatik tespit ederek doğru cevap anahtarıyla notlandırma
- **Manuel Kitapçık Düzeltme** — Doğrulama ekranında kitapçık A/B manuel değiştirilebilir, otomatik yeniden notlandırma yapılır
- **Form Görseli Kaydetme** — Her taranan öğrencinin optik form görseli Supabase Storage'da kalıcı olarak saklanır

### Kullanıcı Yönetimi

- **Öğretmen Girişi** — E-posta ve şifre ile giriş/kayıt (Supabase Auth)
- **Veri İzolasyonu** — Her öğretmen sadece kendi sınavlarını görür ve yönetir
- **Güvenli Oturum** — JWT tabanlı kimlik doğrulama, otomatik token yenileme

### Sınıf Yönetimi

- **Sınıf Listesi** — Manuel giriş, toplu yapıştırma veya PDF yükleme ile öğrenci listesi oluşturma
- **Otomatik Eşleştirme** — Taranan kağıtları öğrenci numarası veya isim ile sınıf listesine eşleştirme
- **Manuel Doğrulama** — Tüm taramalar öğretmen onayından geçer; ad, soyad, numara ve kitapçık düzenlenebilir

### Notlandırma ve Analiz

- **Otomatik Notlandırma** — Cevap anahtarına göre anlık puanlama
- **İstatistikler** — Sınıf ortalaması, en yüksek ve en düşük puan, puan dağılımı, soru bazlı doğru oranı analizi
- **CSV Dışa Aktarma** — Tüm sonuçları (öğrenci bilgileri, puanlar, cevaplar) CSV dosyası olarak indirme

### Veri Yönetimi

- **Supabase Entegrasyonu** — Sınav oturumları PostgreSQL'de, form görselleri Supabase Storage'da kalıcı olarak saklanır. Sunucu yeniden başlatılsa veya deploy edilse bile veriler korunur.
- **SQLite Fallback** — Supabase yapılandırılmamışsa yerel SQLite veritabanı kullanılır (geliştirme modu)
- **Kayıtlı Sınavlara Devam** — Daha önce oluşturulan sınavlar ders koduyla listelenir, tek tıkla kaldığı yerden devam edilir
- **Çoklu Sınav Desteği** — Aynı anda birden fazla sınav oturumu oluşturulabilir ve yönetilebilir
- **Sınav ve Sonuç Silme** — Sınavlar tamamen silinebilir veya tek tek tarama sonuçları kaldırılabilir

### Formlar Galerisi

- **Formlar Sayfası** — Taranan tüm optik formların grid görünümünde listelenmesi
- **Büyük Görüntüleme** — Forma tıklayarak tam boyut modal görüntüsü
- **Form İndirme** — Her form görseli ayrı ayrı indirilebilir

### Mobil Uyumlu Tasarım

- **Responsive Arayüz** — Masaüstünde geniş tablo, mobilde kart tabanlı görünüm
- **Mobil Sınıf Listesi** — Küçük ekranlarda özel kart layout'u ile öğrenci listesi
- **Responsive İstatistikler** — Mobilde kompakt stat kartları

---

## Mimari

```
┌─────────────────────────┐        ┌────────────────────────────────┐
│                         │        │                                │
│   React + Vite          │        │   FastAPI Backend              │
│   Frontend              │        │                                │
│                         │        │   ┌────────────────────────┐   │
│   · Ayarlar             │        │   │  OMR Engine            │   │
│   · Sınıf Listesi       │  REST  │   │  OpenCV · ArUco        │   │
│   · Tarama              │◄──────►│   │  Perspektif düzeltme   │   │
│   · Doğrulama           │        │   │  Balon okuma           │   │
│   · Sonuçlar            │        │   │  Kitapçık algılama     │   │
│   · Formlar             │        │   └────────────────────────┘   │
│                         │        │   ┌────────────────────────┐   │
│   Vercel                │        │   │  OCR Engine            │   │
│                         │        │   │  Karakter tanıma       │   │
└─────────────────────────┘        │   │  Şablon eşleştirme    │   │
                                   │   └────────────────────────┘   │
┌─────────────────────────┐        │   ┌────────────────────────┐   │
│                         │        │   │  Form Generator        │   │
│   Supabase              │        │   │  ReportLab + QR Code   │   │
│                         │        │   └────────────────────────┘   │
│   · Auth (kullanıcılar) │        │   ┌────────────────────────┐   │
│   · PostgreSQL          │◄───────│   │  QR Reader (pyzbar)    │   │
│     (oturumlar)         │        │   └────────────────────────┘   │
│   · Storage             │        │                                │
│     (form görselleri)   │        │   Render (Docker)              │
│                         │        │                                │
└─────────────────────────┘        └────────────────────────────────┘
```

---

## Hızlı Başlangıç

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

Tarayıcıda `http://localhost:5173` adresini açın.

> **Not:** Yerel geliştirmede Supabase env var'ları yoksa auth atlanır ve tek kullanıcı modunda çalışır.

### Docker

```bash
cd backend
docker build -t omr-backend .
docker run -p 8000:8000 omr-backend
```

### Ortam Değişkenleri

**Backend (Render)**

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `SUPABASE_URL` | — | Supabase proje URL'si |
| `SUPABASE_SERVICE_KEY` | — | Supabase service_role anahtarı (legacy JWT formatı `eyJ...`) |
| `SUPABASE_JWT_SECRET` | — | Supabase JWT Secret (token doğrulama için) |
| `OMR_DATA_DIR` | `/tmp/omr_data` | SQLite fallback dizini (Supabase yoksa) |

**Frontend (Vercel)**

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `VITE_API_URL` | `""` (aynı origin) | Backend API adresi |
| `VITE_SUPABASE_URL` | — | Supabase proje URL'si |
| `VITE_SUPABASE_ANON_KEY` | — | Supabase anon (public) anahtarı |

> **Not:** Supabase Python SDK yeni `sb_secret_...` format anahtarlarla uyumlu değildir. Supabase Dashboard > Settings > API > Service Role Key altındaki `eyJ...` ile başlayan legacy JWT anahtarını kullanın.

---

## Kullanım

### 1. Kayıt ve Giriş

1. Uygulamayı açın, karşınıza giriş ekranı gelecek
2. İlk kullanımda **Kayıt Ol** ile e-posta ve şifre belirleyin
3. Sonraki girişlerde **Giriş Yap** ile devam edin
4. Her öğretmen sadece kendi sınavlarını görür

### 2. Sınav Oluşturma

1. **Ayarlar** sekmesine gidin
2. Soru sayısını seçin (5-200 arası)
3. Şık sayısını belirleyin (A-B-C-D veya A-B-C-D-E)
4. Ders kodunu girin (örneğin MAT101)
5. Kitapçık A/B kullanacaksanız toggle'ı açın
6. Cevap anahtarını işaretleyin (kitapçık açıksa her iki kitapçık için ayrı ayrı)
7. **Yazdırılabilir form indir** ile PDF'i indirin ve A4 kağıda yazdırın
8. **Devam et** ile sınav oturumunu oluşturun

### 3. Sınıf Listesi (İsteğe Bağlı)

1. **Sınıf** sekmesine gidin
2. Öğrenci eklemek için üç yöntem:
   - **Tek tek ekleme** — Ad, Soyad, No alanlarına yazın
   - **Toplu yapıştırma** — Excel'den kopyala-yapıştır (Ad, Soyad, No formatında)
   - **PDF yükleme** — Sınıf listesi PDF dosyası yükleyin, otomatik ayıklanır
3. **Kaydet ve taramaya geç** butonuna basın

### 4. Tarama

1. **Tara** sekmesine gidin
2. Telefon kamerasını açın veya fotoğraf yükleyin
3. Doldurulan formu çerçeve içine hizalayın (4 köşe işareti görünmeli)
4. Yakalama butonuna basın
5. Sonuç anında görünür: puan, cevaplar, öğrenci bilgileri
6. Her taranan formun görseli otomatik olarak Supabase Storage'a yüklenir

### 5. Doğrulama

1. **Doğrula** sekmesinde tüm tarama sonuçları listelenir
2. Taranan form görüntüsü ile birlikte ad, soyad ve numara düzenlenebilir
3. Kitapçık yanlış algılandıysa A/B butonu ile değiştirilir (puan otomatik yeniden hesaplanır)
4. Onaylayınca öğrenci sınıf listesiyle eşleştirilir ve notu kaydedilir

### 6. Formlar

1. **Formlar** sekmesinde taranan tüm optik formlar grid görünümünde listelenir
2. Forma tıklayarak büyük görüntü açılır
3. İndirme butonu ile form görseli kaydedilebilir

### 7. Sonuçlar ve Analiz

1. **Sonuçlar** sekmesinde:
   - Sınıf ortalaması, en yüksek ve en düşük puan
   - Puan dağılımı
   - Soru bazlı doğru oranı analizi
   - Sınıf listesi yüklediyseniz her öğrencinin notu
   - Tüm taranan kağıtların detaylı sonuçları
2. CSV olarak dışa aktarabilirsiniz
3. Tek tek tarama sonuçlarını veya tüm sınavı silebilirsiniz

### 8. Kayıtlı Sınava Devam Etme

1. **Ayarlar** sekmesinde **Kayıtlı Sınavlar** listesi görünür
2. Ders kodu, soru sayısı ve taranan öğrenci sayısı gösterilir
3. Tıklayarak sınava kaldığı yerden devam edebilirsiniz
4. Tüm veriler (cevap anahtarı, sınıf listesi, tarama sonuçları, form görselleri) korunur

---

## Optik Form Yapısı

```
┌──────────────────────────────────────────────┐
│  [ArUco 0]                      [ArUco 1]    │
│                                              │
│            SINAV OPTİK FORMU                 │
│            Ders: MAT101                      │
│                                              │
│   AD      [_][_][_][_][_]...[_]   (20 kutu)  │
│   SOYAD   [_][_][_][_][_]...[_]   (20 kutu)  │
│   NO      [_][_][_][_][_][_][_][_][_]        │
│                          KİTAPÇIK: (A) (B)   │
│                                              │
│   [QR KOD]                                   │
│   (sınav ID, ders kodu, soru sayısı)         │
│                                              │
│         A    B    C    D    E                 │
│    1.  (A)  (B)  (C)  (D)  (E)               │
│    2.  (A)  (B)  (C)  (D)  (E)               │
│    ...          5'li gruplar halinde          │
│                                              │
│  [ArUco 2]                      [ArUco 3]    │
└──────────────────────────────────────────────┘
```

**Form özellikleri:**

- Sütun başlıkları (A B C D E) her sütunun üstünde görünür
- 5'li gruplar halinde satır ayırıcıları
- Alternatif satır arka planları (kolay okuma için)
- Kitapçık seçici opsiyonel (kapalıysa formda gösterilmez)
- Footer: Made by Sena Köse

---

## OMR Nasıl Çalışır

1. **ArUco Algılama** — 4 köşe işareti OpenCV ArUco modülü ile bulunur. 8 farklı ön-işleme stratejisi (CLAHE, blur, gölge normalizasyon, adaptif eşik, Otsu, keskinleştirme, güçlü CLAHE, ham gri) birleştirilerek maksimum algılama sağlanır.
2. **Çoklu Ölçek** — İşaretler bulunamazsa görüntü 0.75x, 1.25x ve 0.5x ölçeklerde yeniden taranır
3. **Perspektif Düzeltme** — Görüntü düz hale getirilir (açı ve eğiklik düzeltmesi)
4. **Adaptif Eşikleme** — Farklı ışık koşullarında çalışabilmek için
5. **Balon Analizi** — Her balon bölgesinin doluluk oranı hesaplanır
6. **Karar Mantığı** — Doluluk %35'in üzerindeyse işaretli kabul edilir; birden fazla işaretlenmişse en yüksek seçilir veya belirsiz olarak işaretlenir
7. **Kitapçık Algılama** — NO satırındaki A/B balonları okunarak doğru cevap anahtarı seçilir
8. **OCR** — Karakter kutularından şablon eşleştirme ve kontür analizi ile harf/rakam tanıma
9. **QR Okuma** — pyzbar ile formdan sınav bilgileri çıkartılır

---

## Teknoloji Yığını

| Bileşen | Teknoloji |
|---------|-----------|
| Frontend | React 19, Vite 8, Tailwind CSS 4 |
| Backend | Python 3.11, FastAPI |
| Kimlik Doğrulama | Supabase Auth (JWT) |
| OMR Motoru | OpenCV 4.10 (ArUco + adaptif eşikleme + çoklu ön-işleme) |
| OCR Motoru | OpenCV şablon eşleştirme + kontür analizi |
| QR Kod | qrcode (oluşturma), pyzbar (okuma) |
| PDF Oluşturma | ReportLab (DejaVuSans — Türkçe karakter desteği) |
| PDF Ayıklama | pdfplumber (sınıf listesi PDF okuma) |
| Veritabanı | Supabase PostgreSQL (kalıcı depolama) + SQLite (fallback) |
| Görsel Depolama | Supabase Storage (form görselleri) |
| Kamera | react-webcam |
| HTTP | axios |
| İkonlar | lucide-react |
| Dağıtım | Render (backend, Docker), Vercel (frontend) |

---

## Proje Yapısı

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI endpoint'leri
│   │   ├── auth.py               JWT kimlik doğrulama
│   │   ├── omr_engine.py         OpenCV OMR işleme (marker algılama, balon okuma, kitapçık)
│   │   ├── ocr_engine.py         Karakter tanıma motoru
│   │   ├── qr_reader.py          QR kod okuyucu
│   │   ├── form_generator.py     PDF form oluşturucu
│   │   ├── storage.py            Supabase + SQLite depolama katmanı
│   │   └── models.py             Pydantic şemaları
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx               Ana React uygulaması (tek dosya)
│   │   ├── main.jsx              Giriş noktası
│   │   └── index.css             Tailwind stilleri
│   ├── package.json
│   └── vercel.json
├── sample_forms/                  Örnek optik formlar
└── README.md
```

---

## API Referansı

> Tüm `/api/sessions/*`, `/api/scan/*` endpoint'leri `Authorization: Bearer <token>` header'ı gerektirir. Form oluşturma endpoint'leri herkese açıktır.

### Oturum Yönetimi

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Sınav oturumu oluştur |
| `GET` | `/api/sessions` | Kullanıcının kayıtlı sınavlarını listele |
| `GET` | `/api/sessions/{id}` | Oturum detaylarını getir |
| `DELETE` | `/api/sessions/{id}` | Sınavı ve tüm verilerini sil |
| `DELETE` | `/api/sessions/{id}/results/{index}` | Tek bir tarama sonucunu sil |

### Form Oluşturma (Auth gerektirmez)

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | Boş form PDF indir |
| `POST` | `/api/forms/generate` | Özel form oluştur |

### Tarama

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Yüklenen görüntüden tara (dosya yükleme) |
| `POST` | `/api/scan/base64` | Base64 görüntüden tara (kamera yakalama) |

### Sınıf Listesi

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sınıf listesi yükle (JSON) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sınıf listesi yükle (PDF) |
| `GET` | `/api/sessions/{id}/roster` | Sınıf listesini getir |

### Doğrulama

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Doğrulama bekleyen taramaları getir |
| `POST` | `/api/sessions/{id}/verify` | OCR sonucunu düzenle, kitapçık değiştir ve onayla |

### Sonuçlar ve Analiz

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/stats` | Sınav istatistikleri |
| `GET` | `/api/sessions/{id}/export` | Sonuçları CSV olarak indir |

---

## Yapılandırma

### OMR Motoru — `omr_engine.py`

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `fill_threshold` | 0.35 | Balonun işaretli sayılması için minimum doluluk oranı |
| `ambiguity_threshold` | 0.15 | En yüksek iki balon arasındaki minimum fark |
| `ARUCO_DICT_TYPE` | `DICT_4X4_50` | ArUco sözlük tipi |

### OCR Motoru — `ocr_engine.py`

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `empty_threshold` | 0.03 | Kutunun boş sayılması için eşik değeri |
| `REVIEW_THRESHOLD` | 0.6 | Bu güvenin altındaki sonuçlar doğrulama gerektirir |

### Form Oluşturucu — `form_generator.py`

| Parametre | Varsayılan | Açıklama |
|-----------|-----------|----------|
| `num_questions` | 40 | Soru sayısı (5-200) |
| `options` | A, B, C, D, E | Şık listesi |
| `show_booklet` | true | Kitapçık seçicisini göster veya gizle |
| `name_boxes` | 20 | Ad için karakter kutusu sayısı |
| `surname_boxes` | 20 | Soyad için karakter kutusu sayısı |
| `student_no_boxes` | 9 | Öğrenci numarası için kutu sayısı |

---

## Sorun Giderme

**4 işaret bulunamadı / Perspektif düzeltme başarısız**
- 4 köşe işaretinin tamamının görüntüde göründüğünden emin olun
- İşaretler üzerinde gölge olmasın
- Kamerayı yaklaşık 30 cm yükseklikten sabit tutun
- Hata mesajında hangi marker'ların eksik olduğu gösterilir (örn. "Köşe işaretçileri eksik: 2 (sol alt)")
- Sistem 8 farklı ön-işleme ve 4 farklı ölçek dener; yine de başarısızsa kağıt düzlüğünü kontrol edin

**Kitapçık yanlış algılandı**
- Doğrulama ekranında A/B butonuyla kitapçığı manuel değiştirebilirsiniz
- Değiştirince puan doğru cevap anahtarıyla yeniden hesaplanır

**Düşük doğruluk**
- Koyu kalem veya tükenmez ile balonları tamamen doldurun
- İyi ve düz aydınlatma sağlayın
- Buruşuk veya katlanmış kağıt kullanmayın

**Kamera çalışmıyor**
- Tarayıcıda kamera iznini verin
- HTTPS veya localhost kullanın (kamera güvenli bağlam gerektirir)

**Türkçe karakterler formda görünmüyor**
- Backend'de `fonts-dejavu-core` paketinin yüklü olduğunu kontrol edin
- Docker kullanıyorsanız Dockerfile'da zaten mevcut

**Veriler kayboldu**
- Supabase yapılandırılmışsa veriler kalıcı olarak saklanır
- Supabase yoksa `OMR_DATA_DIR` değişkeninin kalıcı bir dizine işaret ettiğinden emin olun
- Render free tier'da dosya sistemi geçicidir; kalıcı depolama için Supabase kullanın

**Supabase bağlantı hatası**
- `SUPABASE_SERVICE_KEY` olarak legacy JWT formatını kullanın (`eyJ...` ile başlamalı)
- Yeni `sb_secret_...` formatı Python SDK ile uyumlu değildir

---

## Dağıtım

### Backend (Render)

1. Render'da yeni bir **Web Service** oluşturun
2. Docker runtime seçin
3. Root directory: `backend`
4. Ortam değişkenlerini ekleyin:
   - `SUPABASE_URL` = Supabase proje URL'si
   - `SUPABASE_SERVICE_KEY` = Legacy JWT service_role key
   - `SUPABASE_JWT_SECRET` = JWT Secret (Settings > JWT Keys > Legacy JWT Secret)

### Frontend (Vercel)

1. Vercel'de yeni bir proje oluşturun
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Ortam değişkenleri:
   - `VITE_API_URL` = Render backend URL'si
   - `VITE_SUPABASE_URL` = Supabase proje URL'si
   - `VITE_SUPABASE_ANON_KEY` = Supabase anon (public) key

### Supabase Kurulumu

1. Supabase'de yeni bir proje oluşturun
2. SQL Editor'da tabloyu oluşturun:
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
3. Storage'da `form-images` bucket'ı oluşturun (public)
4. Settings > API'den legacy JWT service_role key'i alın
5. Settings > JWT Keys > Legacy JWT Secret'ı alın

---

## Lisans

MIT

---

Öğretmenler için geliştirilmiştir.
