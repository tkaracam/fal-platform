# Orakelia Runbook

Bu dokuman canli sistemde acil durumlarda hizli hareket etmek icin hazirlandi.

## 1) Site Acilmiyor

1. Render panelinde `fal-platform` servisinin `Events` ve `Logs` bolumlerini kontrol et.
2. Son deploy durumu `Live` degilse `Redeploy` baslat.
3. Domain/DNS degisikligi yapildiysa Cloudflare DNS kayitlarini tekrar dogrula.

## 2) Admin Girisi Calismiyor

1. Render -> Service -> `Environment` bolumune gir.
2. `ADMIN_USERNAME` ve `ADMIN_PASSWORD` degerlerini kontrol et.
3. Gerekirse yeni deger gir, `Save Changes` yap.
4. Deploy tamamlandiktan sonra `https://orakelia.com/admin` tekrar dene.

## 3) HTTPS / Sertifika Sorunu

1. Cloudflare -> `SSL/TLS` modu `Full (strict)` olmali.
2. Cloudflare -> `Edge Certificates`:
   - `Always Use HTTPS` = On
   - `Automatic HTTPS Rewrites` = On
3. Render -> `Custom Domains`:
   - Domain `Verified`
   - Certificate `Issued`

## 4) Formlar Hata Veriyor

1. Tarayicida hard refresh yap.
2. Render loglarda 4xx/5xx ve CSRF hatalarini kontrol et.
3. Yeni degisiklikten sonra olduysa son commiti incele.

## 5) Hizli Rollback

1. Son stabil commit hash'ini bul:
   - `git log --oneline`
2. Problemli commit'i geri al:
   - `git revert <commit_hash>`
3. Push et:
   - `git push`
4. Render auto-deploy ile onceki stabil duruma doner.

## 6) Guvenlik Ihlali Suphesi

1. Hemen su degerleri degistir:
   - `ADMIN_PASSWORD`
   - `SECRET_KEY`
   - `OPENAI_API_KEY` (gerekirse)
2. Tum eski GitHub token/PAT anahtarlarini iptal et.
3. Render loglarini ve admin erisimlerini kontrol et.

## 7) Operasyonel Haftalik Kontrol

1. `https://orakelia.com` aciliyor mu?
2. Login/Register/Admin ekranlari calisiyor mu?
3. Render son deploy `Live` mi?
4. Cloudflare SSL/TLS ayarlari degismis mi?
5. Kritik hata logu var mi?

## 8) Stripe Odeme Kurulumu

1. Render -> Service -> `Environment`:
   - `PAYMENT_PROVIDER=stripe`
   - `STRIPE_SECRET_KEY=...`
   - `STRIPE_WEBHOOK_SECRET=...`
2. Stripe Dashboard -> Webhooks:
   - Endpoint URL: `https://orakelia.com/webhook/stripe`
   - Event: `checkout.session.completed`
3. Deploy bittikten sonra test:
   - Odeme sayfasinda `Odeme Yap` butonu gorunmeli.
   - Test odeme sonrasi admin panelde kayit `paid` olmali.

## 9) Test ve Live Anahtar Ayrimi

1. Test ortami:
   - `STRIPE_SECRET_KEY=sk_test_...`
   - `STRIPE_WEBHOOK_SECRET=whsec_...` (test endpoint secret)
2. Canli ortami:
   - `STRIPE_SECRET_KEY=sk_live_...`
   - `STRIPE_WEBHOOK_SECRET=whsec_...` (live endpoint secret)
3. Hata onleme:
   - `SECRET_KEY` ile `STRIPE_SECRET_KEY` karistirilmamalidir.
   - `pk_...` veya `rk_...` degeri `STRIPE_SECRET_KEY` alanina yazilmaz.

## 10) Go-Live Kontrol Listesi

1. Stripe hesabi live activation tamamlandi mi?
2. Render env'de `sk_live` ve live `whsec` girildi mi?
3. Stripe live webhook endpoint'i `https://orakelia.com/webhook/stripe` mi?
4. Event `checkout.session.completed` secili mi?
5. Webhook teslimatinda HTTP 200 aliniyor mu?
6. Canli kartla dusuk tutarli 1 test odeme yapildi mi?
7. Admin panelde odeme kaydi `paid` oldu mu?
8. Basarisiz odeme denemesinde sistem guvenli sekilde geri donuyor mu?

## 11) Veritabani Yedekleme ve Geri Yukleme (Kalici Plan)

Bu proje icin yedekleme scriptleri:

- `scripts/db_backup.py` -> sikistirilmis `.sqlite3.gz` yedek alir
- `scripts/db_restore.py` -> yedekten geri yukleme yapar

### 11.1 Manuel yedek alma

```bash
cd /Users/Tolga/Documents/GitHub/fal-platform
python3 scripts/db_backup.py --retain-days 14 --keep-min 14
```

Varsayilanlar:

- DB: `DATABASE_PATH` yoksa `/var/data/data.db` (varsa), degilse local `data.db`
- Yedek klasoru: `/var/data/backups` (render), localde `./backups`

### 11.2 Otomatik gunluk yedek (Render Cron Job)

Render Dashboard -> `New` -> `Cron Job`

- Command:
  - `python3 scripts/db_backup.py --retain-days 14 --keep-min 14`
- Schedule:
  - gunde 1 kez (onerilen: gece saatleri)
- Environment:
  - `DATABASE_PATH=/var/data/data.db`
  - (opsiyonel) `BACKUP_DIR=/var/data/backups`

Bu sekilde her gun yedek alinir, 14 gunden eski yedekler otomatik temizlenir
(en az son 14 yedek korunur).

### 11.3 Yedekten geri yukleme

Son yedege don:

```bash
cd /Users/Tolga/Documents/GitHub/fal-platform
python3 scripts/db_restore.py --yes
```

Belirli bir yedekten don:

```bash
cd /Users/Tolga/Documents/GitHub/fal-platform
python3 scripts/db_restore.py --backup-file /var/data/backups/data-YYYYMMDD-HHMMSS.sqlite3.gz --yes
```

Notlar:

- Geri yuklemeden once mevcut DB'nin bir kopyasi otomatik alinir:
  - `/var/data/backups/pre-restore-YYYYMMDD-HHMMSS.sqlite3`
- Geri yuklenen DB icin `PRAGMA integrity_check` yapilir; bozuk yedek kabul edilmez.

### 11.4 Hizli dogrulama

```bash
ls -lah /var/data/backups | tail -n 20
```

Yedek dosyalari icin beklenen uzantilar:

- `.sqlite3.gz`
- `.sqlite3.gz.sha256`
- `.sqlite3.gz.json`
