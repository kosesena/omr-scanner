# OMR Scanner

**Optik Form Okuyucu ve El Yazısı Tanıma Sistemi**

Sınav kağıtlarını telefon kamerasıyla tarayan, optik formu okuyan, el yazısı karakter kutularından öğrenci bilgilerini çıkaran ve sınıf listesiyle eşleştirerek otomatik notlandıran web tabanlı sistem.

`React` · `FastAPI` · `OpenCV` · `OCR` · `SQLite`

---

## Özellikler

### Form Oluşturma

- **Optik Form Oluşturucu** — A4 PDF formatında yazdırılabilir sınav formu. ArUco hizalama işaretleri, QR kod, karakter kutuları ve balon cevap alanları içerir.
- **Esnek Soru Sayısı** — 20 ve 40 soruluk form desteği
- **Şık Seçeneği** — A-B-C-D (4 şık) veya A-B-C-D-E (5 şık)
- **Kitapçık A/B Desteği** — Opsiyonel kitapçık seçici; kapalıysa formda gösterilmez
- **Ders Kodu** — Formun başlığında ve QR kodunda ders kodu bilgisi

### Tarama ve Tanıma

- **Kamera ile Tarama** — Telefon kamerasını kullanarak optik form okuma veya fotoğraf yükleme
- **OMR Motoru** — OpenCV tabanlı balon algılama, ArUco köşe işaretleri ile perspektif düzeltme ve adaptif eşikleme
- **OCR Motoru** — Karakter kutularından el yazısı tanıma (ad, soyad, öğrenci no)
- **QR Kod Okuma** — Formdan sınav bilgilerini (sınav ID, ders kodu, soru sayısı) otomatik okuma
- **Kitapçık Algılama** — Taranan formda A/B kitapçık balonunu otomatik tespit ederek doğru cevap anahtarıyla notlandırma
- **Form Görseli Kaydetme** — Her taranan öğrencinin optik form görseli kaydedilir ve sonradan incelenebilir

### Sınıf Yönetimi

- **Sınıf Listesi** — Manuel giriş, toplu yapıştırma veya PDF yükleme ile öğrenci listesi oluşturma
- **Otomatik Eşleştirme** — Taranan kağıtları öğrenci numarası veya isim ile sınıf listesine eşleştirme
- **Manuel Doğrulama** — Düşük güvenli OCR sonuçlarını öğretmenin düzenleyebildiği doğrulama ekranı

### Notlandırma ve Analiz

- **Otomatik Notlandırma** — Cevap anahtarına göre anlık puanlama
- **İstatistikler** — Sınıf ortalaması, en yüksek ve en düşük puan, puan dağılımı, soru bazlı doğru oranı analizi
- **CSV Dışa Aktarma** — Tüm sonuçları (öğrenci bilgileri, puanlar, cevaplar) CSV dosyası olarak indirme

### Veri Yönetimi

- **Kalıcı Depolama** — Sınav oturumları, cevap anahtarları, sınıf listeleri, tarama sonuçları ve form görselleri SQLite veritabanında saklanır. Sunucu yeniden başlatılsa bile veriler korunur.
- **Kayıtlı Sınavlara Devam** — Daha önce oluşturulan sınavlar ders koduyla listelenir, tek tıkla kaldığı yerden devam edilir
- **Çoklu Sınav Desteği** — Aynı anda birden fazla sınav oturumu oluşturulabilir ve yönetilebilir

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
│                         │        │   └────────────────────────┘   │
│   Vercel                │        │   ┌────────────────────────┐   │
│                         │        │   │  OCR Engine            │   │
└─────────────────────────┘        │   │  Karakter tanıma       │   │
                                   │   │  Şablon eşleştirme     │   │
                                   │   └────────────────────────┘   │
                                   │   ┌────────────────────────┐   │
                                   │   │  Form Generator        │   │
                                   │   │  ReportLab + QR Code   │   │
                                   │   └────────────────────────┘   │
                                   │   ┌────────────────────────┐   │
                                   │   │  QR Reader (pyzbar)    │   │
                                   │   └────────────────────────┘   │
                                   │   ┌────────────────────────┐   │
                                   │   │  SQLite Storage        │   │
                                   │   │  Oturumlar · Sonuçlar  │   │
                                   │   │  Form görselleri       │   │
                                   │   └────────────────────────┘   │
                                   │                                │
                                   │   Render (Docker)              │
                                   └────────────────────────────────┘
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

### Docker

```bash
cd backend
docker build -t omr-backend .
docker run -p 8000:8000 omr-backend
```

### Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `VITE_API_URL` | `""` (aynı origin) | Frontend için backend API adresi |
| `OMR_DATA_DIR` | `/tmp/omr_data` | SQLite veritabanı dizini |

---

## Kullanım

### 1. Sınav Oluşturma

1. **Ayarlar** sekmesine gidin
2. Soru sayısını seçin (20 veya 40)
3. Şık sayısını belirleyin (A-B-C-D veya A-B-C-D-E)
4. Ders kodunu girin (örneğin MAT101)
5. Kitapçık A/B kullanacaksanız toggle'ı açın
6. Cevap anahtarını işaretleyin (kitapçık açıksa her iki kitapçık için ayrı ayrı)
7. **Yazdırılabilir form indir** ile PDF'i indirin ve A4 kağıda yazdırın
8. **Devam et** ile sınav oturumunu oluşturun

### 2. Sınıf Listesi (İsteğe Bağlı)

1. **Sınıf Listesi** sekmesine gidin
2. Öğrenci eklemek için üç yöntem:
   - **Tek tek ekleme** — Ad, Soyad, No alanlarına yazın
   - **Toplu yapıştırma** — Excel'den kopyala-yapıştır (Ad, Soyad, No formatında)
   - **PDF yükleme** — Sınıf listesi PDF dosyası yükleyin, otomatik ayıklanır
3. **Kaydet ve taramaya geç** butonuna basın

### 3. Tarama

1. **Tara** sekmesine gidin
2. Telefon kamerasını açın veya fotoğraf yükleyin
3. Doldurulan formu çerçeve içine hizalayın (4 köşe işareti görünmeli)
4. Yakalama butonuna basın
5. Sonuç anında görünür: puan, cevaplar, öğrenci bilgileri
6. Her taranan formun görseli otomatik kaydedilir

### 4. Doğrulama

1. **Doğrula** sekmesinde düşük güvenli OCR sonuçları listelenir
2. Taranan form görüntüsünü inceleyip ad, soyad ve numara düzeltebilirsiniz
3. Onaylayınca öğrenci sınıf listesiyle yeniden eşleştirilir

### 5. Sonuçlar ve Analiz

1. **Sonuçlar** sekmesinde:
   - Sınıf ortalaması, en yüksek ve en düşük puan
   - Puan dağılımı
   - Soru bazlı doğru oranı analizi
   - Sınıf listesi yüklediyseniz her öğrencinin notu
   - Tüm taranan kağıtların detaylı sonuçları
2. CSV olarak dışa aktarabilirsiniz (öğrenci bilgileri ve puanlar)

### 6. Kayıtlı Sınava Devam Etme

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

1. **ArUco Algılama** — 4 köşe işareti OpenCV ArUco modülü ile bulunur
2. **Perspektif Düzeltme** — Görüntü düz hale getirilir (açı ve eğiklik düzeltmesi)
3. **Adaptif Eşikleme** — Farklı ışık koşullarında çalışabilmek için
4. **Balon Analizi** — Her balon bölgesinin doluluk oranı hesaplanır
5. **Karar Mantığı** — Doluluk %35'in üzerindeyse işaretli kabul edilir; birden fazla işaretlenmişse en yüksek seçilir veya belirsiz olarak işaretlenir
6. **Kitapçık Algılama** — NO satırındaki A/B balonları okunarak doğru cevap anahtarı seçilir
7. **OCR** — Karakter kutularından şablon eşleştirme ve kontür analizi ile harf/rakam tanıma
8. **QR Okuma** — pyzbar ile formdan sınav bilgileri çıkartılır

---

## Teknoloji Yığını

| Bileşen | Teknoloji |
|---------|-----------|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python 3.11, FastAPI |
| OMR Motoru | OpenCV 4.10 (ArUco + adaptif eşikleme) |
| OCR Motoru | OpenCV şablon eşleştirme + kontür analizi |
| QR Kod | qrcode (oluşturma), pyzbar (okuma) |
| PDF Oluşturma | ReportLab (DejaVuSans — Türkçe karakter desteği) |
| PDF Ayıklama | pdfplumber (sınıf listesi PDF okuma) |
| Veritabanı | SQLite (kalıcı oturum ve sonuç depolama) |
| Kamera | react-webcam |
| Dağıtım | Render (backend, Docker), Vercel (frontend) |

---

## Proje Yapısı

```
omr-scanner/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI endpoint'leri
│   │   ├── omr_engine.py         OpenCV OMR işleme
│   │   ├── ocr_engine.py         Karakter tanıma motoru
│   │   ├── qr_reader.py          QR kod okuyucu
│   │   ├── form_generator.py     PDF form oluşturucu
│   │   ├── storage.py            SQLite kalıcı depolama
│   │   └── models.py             Pydantic şemaları
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx               Ana React uygulaması
│   │   ├── main.jsx              Giriş noktası
│   │   └── index.css             Tailwind stilleri
│   ├── package.json
│   └── vercel.json
├── sample_forms/                  Örnek optik formlar (20 ve 40 soruluk)
└── README.md
```

---

## API Referansı

### Oturum Yönetimi

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/sessions/create` | Sınav oturumu oluştur (cevap anahtarı, ders kodu, kitapçık ayarı) |
| `GET` | `/api/sessions` | Tüm kayıtlı sınavları listele |
| `GET` | `/api/sessions/{id}` | Oturum detaylarını getir (cevap anahtarı, sonuçlar, sınıf listesi dahil) |

### Form Oluşturma

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/forms/download/{n}` | Boş form PDF indir (şık sayısı ve kitapçık parametreleri) |
| `POST` | `/api/forms/generate` | Özel form oluştur (başlık, ders kodu, kutu sayıları vb.) |

### Tarama

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/scan` | Yüklenen görüntüden tara (dosya yükleme) |
| `POST` | `/api/scan/base64` | Base64 görüntüden tara (kamera yakalama) |

### Sınıf Listesi

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `POST` | `/api/sessions/{id}/roster` | Sınıf listesi yükle (JSON formatında) |
| `POST` | `/api/sessions/{id}/roster/pdf` | Sınıf listesi yükle (PDF'den otomatik ayıklama) |
| `GET` | `/api/sessions/{id}/roster` | Sınıf listesini getir (notlar dahil) |

### Doğrulama

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/review` | Doğrulama bekleyen taramaları getir |
| `POST` | `/api/sessions/{id}/verify` | OCR sonucunu düzenle ve onayla |

### Sonuçlar ve Analiz

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| `GET` | `/api/sessions/{id}/stats` | Sınav istatistikleri (ortalama, dağılım, soru analizi) |
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
| `num_questions` | 40 | Soru sayısı (20 veya 40) |
| `options` | A, B, C, D, E | Şık listesi |
| `show_booklet` | true | Kitapçık seçicisini göster veya gizle |
| `name_boxes` | 20 | Ad için karakter kutusu sayısı |
| `surname_boxes` | 20 | Soyad için karakter kutusu sayısı |
| `student_no_boxes` | 9 | Öğrenci numarası için kutu sayısı |

---

## Sorun Giderme

**4 işaret bulunamadı**
- 4 köşe işaretinin tamamının görüntüye girdiğinden emin olun
- İşaretler üzerinde gölge olmasın
- Kamerayı yaklaşık 30 cm yükseklikten sabit tutun

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
- `OMR_DATA_DIR` ortam değişkeninin kalıcı bir dizine işaret ettiğinden emin olun
- Docker kullanıyorsanız volume mount yapın: `-v /host/path:/tmp/omr_data`

---

## Lisans

MIT

---

Öğretmenler için geliştirilmiştir.
