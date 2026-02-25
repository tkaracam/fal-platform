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
