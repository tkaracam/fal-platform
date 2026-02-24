# Fal Platformu

## Ozellikler
- Kahve fali: telve fotografi yukleme + soru + musteri iletisim bilgisi
- Katina ask ve tarot: kapali kartlardan 3 secim, otomatik shuffle
- Odeme adimi: talep kaydi sonrasi odeme sayfasina yonlendirme
- Admin paneli: sifreli giris, talepleri gorme, odeme durumu isaretleme, WhatsApp hizli mesaj

## Kurulum
```bash
cd /Users/Tolga/Documents/GitHub/fal-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ortam Degiskenleri (istege bagli)
```bash
export SECRET_KEY="guclu-bir-secret"
export ADMIN_PASSWORD="guclu-admin-sifresi"
export WHATSAPP_NUMBER="905xxxxxxxxx"
export PAYMENT_LINK="https://odeme-sayfan.com/checkout"
export COFFEE_PRICE="250"
export CARD_PRICE="200"
```

## Calistirma
```bash
python3 app.py
```

- Ana sayfa: `http://127.0.0.1:5000`
- Admin: `http://127.0.0.1:5000/admin`

Not: `PAYMENT_LINK` bos birakilirsa odeme sayfasinda uyari gorunur.
