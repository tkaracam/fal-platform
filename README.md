# Orakelia Fal Platformu

## Özellikler

- Kahve falı: üç fincan/telve görseline kadar yükleme ve OpenAI görsel yorumlama
- Katina aşk falı: 65 kartlık desteden 7 pozisyonlu açılım
- Tarot falı: 78 kartlık desteden 10 pozisyonlu açılım
- Her fal türü için 10 ayrı falcı; toplam 30 farklı karakter, uzmanlık ve anlatım tarzı
- Gerçek kart adları ve pozisyonlarıyla sunucu taraflı, doğrulanmış yorum akışı
- Türkçe, İngilizce ve Almanca yorum üretimi
- Ödeme onayından sonra 20–30 dakikalık planlı teslim ve kullanıcı panelinde son 10 fal geçmişi
- Ödeme adımı, müşteri paneli ve yönetici kalite kontrolü
- API anahtarını yalnızca sunucuda tutan güvenli OpenAI Responses API entegrasyonu
- Yorumları varsayılan olarak OpenAI tarafında saklamayan `store: false` ayarı

## Kurulum

```bash
cd /Users/Tolga/Documents/GitHub/fal-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ortam Değişkenleri

```bash
export SECRET_KEY="guclu-bir-secret"
export ADMIN_PASSWORD="guclu-admin-sifresi"
export WHATSAPP_NUMBER="905xxxxxxxxx"
export PAYMENT_LINK="https://odeme-sayfan.com/checkout"
export COFFEE_PRICE="250"
export CARD_PRICE="200"
export OPENAI_API_KEY="sunucu-tarafindaki-api-anahtari"
export OPENAI_MODEL="gpt-5.6-luna"
export OPENAI_MAX_OUTPUT_TOKENS="1800"
export OPENAI_MAX_RETRIES="2"
export OPENAI_USE_BATCH="0"
export DELIVERY_MIN_MINUTES="20"
export DELIVERY_MAX_MINUTES="30"
```

`OPENAI_API_KEY` tarayıcıya veya mobil istemciye kesinlikle eklenmemelidir. Anahtar yalnızca uygulamanın çalıştığı sunucunun gizli ortam değişkenlerinde tutulur.

`OPENAI_USE_BATCH=1` yorumları OpenAI Batch API üzerinden sıraya alır. Daha hızlı kullanıcı deneyimi için varsayılan doğrudan Responses API akışı kullanılır.

## Çalıştırma

```bash
python3 app.py
```

- Ana sayfa: `http://127.0.0.1:5000`
- Admin: `http://127.0.0.1:5000/admin`

## Telefona Yükleme (PWA)

Orakelia, RouteSnap'teki hızlı kurulum mantığıyla telefona yüklenebilir:

- iPhone/iPad: siteyi Safari'de aç → **Paylaş** → **Ana Ekrana Ekle**.
- Android: `/install` sayfasındaki **Uygulamayı Yükle** düğmesini kullan veya Chrome menüsünden **Uygulamayı yükle** seçeneğini seç.

Kurulum için site canlı ortamda HTTPS üzerinden yayınlanmalıdır. Üyelik, giriş ve fal geçmişi sunucuda tutulur; PWA önbelleği kişisel sayfaları veya yüklenen fotoğrafları saklamaz.

Not: `PAYMENT_LINK` boş bırakılırsa ödeme sayfasında uyarı görünür. OpenAI anahtarı yoksa talep kaybolmaz; yorum durumu `no_key` olarak kaydedilir ve dış ağa istek gönderilmez.

Fal yorumları eğlence ve kişisel farkındalık amaçlıdır; tıbbi, hukuki veya finansal tavsiye yerine geçmez.

## Planlı Teslim

Ödeme onaylandığında her talep için 20–30 dakika arasında bir teslim zamanı oluşturulur. Uygulama gelen isteklerde zamanı dolan yorumları otomatik yayınlar. Trafikten bağımsız ve dakik teslim için aşağıdaki komutun barındırma servisinde dakikada bir çalıştırılması önerilir:

```bash
python3 scripts/release_due_readings.py
```

## Test

```bash
DATABASE_PATH=/private/tmp/orakelia-test.db \
SESSION_COOKIE_SECURE=0 \
python3 -m unittest discover -s tests -v
```

## Veritabanı Yedekleme

Manuel yedek:

```bash
python3 scripts/db_backup.py --retain-days 14 --keep-min 14
```

Geri yükleme (son yedek):

```bash
python3 scripts/db_restore.py --yes
```

Detaylı operasyon adımları için: `RUNBOOK.md` → “11) Veritabanı Yedekleme ve Geri Yükleme”.
