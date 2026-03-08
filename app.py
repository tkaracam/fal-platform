from __future__ import annotations

import json
import os
import sqlite3
import hashlib
import hmac
import re
import csv
import base64
import mimetypes
import io
import uuid
import secrets
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
try:
    from PIL import Image
except Exception:
    Image = None
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = Path("/var/data/data.db") if Path("/var/data").exists() else (BASE_DIR / "data.db")
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH))).expanduser()
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fal-platform-secret")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "1").strip() == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=int(os.getenv("SESSION_TTL_SECONDS", "86400")))
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@2026")
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "")
PAYMENT_LINK = os.getenv("PAYMENT_LINK", "")
PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "manual").strip().lower()
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1").strip() == "1"
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "https://instagram.com")
X_URL = os.getenv("X_URL", "https://x.com")
TELEGRAM_URL = os.getenv("TELEGRAM_URL", "https://t.me")
LIVE_SUPPORT_URL = os.getenv("LIVE_SUPPORT_URL", "https://t.me")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_USE_BATCH = os.getenv("OPENAI_USE_BATCH", "0").strip() == "1"
AI_INPUT_COST_PER_1M = float(os.getenv("AI_INPUT_COST_PER_1M", "0"))
AI_OUTPUT_COST_PER_1M = float(os.getenv("AI_OUTPUT_COST_PER_1M", "0"))
EXPECTED_CARD_COUNT = {"katina": 7, "tarot": 10}
LANGUAGES = {"tr", "en", "de", "fr"}
DEFAULT_LANG = "tr"
EUROPE_COUNTRIES = {
    "AL", "AD", "AM", "AT", "AZ", "BA", "BE", "BG", "BY", "CH", "CY", "CZ", "DE", "DK",
    "EE", "ES", "FI", "FO", "FR", "GB", "GE", "GI", "GR", "HR", "HU", "IE", "IS", "IT",
    "LI", "LT", "LU", "LV", "MC", "MD", "ME", "MK", "MT", "NL", "NO", "PL", "PT", "RO",
    "RS", "RU", "SE", "SI", "SK", "SM", "TR", "UA", "VA",
}
TRANSLATIONS = {
    "tr": {
        "brand": "Orakelia",
        "nav_coffee": "Kahve",
        "nav_katina": "Katina",
        "nav_tarot": "Tarot",
        "nav_agb": "AGB",
        "nav_impressum": "Impressum",
        "nav_datenschutz": "Datenschutz",
        "nav_login": "Üye Girişi",
        "nav_register": "Kayıt Ol",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        "lang_de": "Deutsch",
        "lang_fr": "Français",
        "language_field": "Dil",
        "menu_languages": "Diller",
        "home_kicker": "Modern Online Fal Deneyimi",
        "home_title": "Fal Türünü Seç ve İlgili Sekmeye Geç",
        "home_desc": "Aşağıdaki türlerden birini seçerek ilgili sayfaya geçebilirsin.",
        "home_cta_primary": "Hemen Başla",
        "home_cta_secondary": "Fal Türlerini Gör",
        "home_badge_1": "Canlı Destek",
        "live_support": "Canlı Destek",
        "home_badge_2": "Güvenli Ödeme",
        "home_badge_3": "3 Dil Seçeneği",
        "home_welcome_title": "Profesyonel Online Fal Platformu",
        "home_welcome_desc": "Fal türünü seç, falcını belirle ve talebini birkaç adımda güvenle tamamla.",
        "home_welcome_item_1": "Doğrulanmış falcı profilleri",
        "home_welcome_item_2": "Hızlı talep ve ödeme akışı",
        "home_welcome_item_3": "TR / EN / DE çok dilli kullanım",
        "home_welcome_cta": "Fal Türünü Seç",
        "home_slider_welcome": "Orakelia'ya hoş geldiniz",
        "home_slider_subtext": "Kalbine takılan soruları birlikte netleştirelim; sana en uygun falcıyla hemen başlayalım.",
        "choice_coffee": "Kahve Falı",
        "home_coffee_slogan_kicker": "Orakelia'ya hoş geldin – online profesyonel fal danışmanlığı platformun.",
        "home_coffee_slogan": "Orakelia'ya hoş geldiniz. Kahve falında sezgini güçlendir, net bir başlangıç yap.",
        "choice_katina": "Katina Aşk Falı",
        "choice_tarot": "Tarot Falı",
        "home_slide_cta": "Falcılara Git",
        "home_coffee_slide_cta": "Kahve Falına Git",
        "home_slide_text_1": "Kahve Falı ile içsel netlik",
        "home_slide_text_2": "Katina ile aşkın işaretlerini keşfet",
        "home_slide_text_3": "Tarot ile yolunu aydınlat",
        "home_info_1_title": "Orakelia – Ruhsal Yol Rehberin",
        "home_info_1_body": "Bazen hayatta aşk, gelecek veya önemli kararlarla ilgili sorularla karşılaşırız.\n\nBir fal, yeni bakış açıları keşfetmene ve gizli bağlantıları görmene yardımcı olabilir.",
        "home_info_2_title": "Geleneksel Fal Yöntemleri",
        "home_info_2_body": "Yüzyıllardır insanlar işaretleri yorumlamak ve yön bulmak için fal yöntemlerinden yararlanır.\n\nOrakelia'da farklı yöntemleri keşfedebilirsin:\n\nKahve Falı\nTarot Kartları\nKatina Aşk Falı",
        "home_info_3_title": "Cevaplarını Bul",
        "home_info_3_body": "Fal, sana yeni ipuçları verebilir ve durumuna farklı bir açıdan bakmana yardımcı olabilir.\n\nŞimdi kendi kişisel falına başla.",
        "slider_prev": "Önceki slayt",
        "slider_next": "Sonraki slayt",
        "coffee_title": "Kahve Falı Talebi",
        "price_label": "Ücret",
        "full_name": "Ad Soyad",
        "phone": "Telefon",
        "question": "Soru",
        "coffee_photo": "Telve Fotoğrafı",
        "submit_coffee": "Kahve Falını Gönder",
        "katina_title": "Katina Aşk Falı",
        "katina_desc": "7 kart ilişki açılımı: sen, partner, ilişki enerjisi, engel, yakın gelecek, tavsiye, olası sonuç.",
        "katina_question": "Aşk Sorunuz",
        "submit_katina": "Katina Falını Gönder",
        "tarot_title": "Tarot Falı",
        "tarot_desc": "10 kart detaylı açılım (Celtic Cross): durum, engel, temel etki, yakın geçmiş, olası gelişme, yakın gelecek, sen, çevre, umut/korkular, sonuç.",
        "tarot_question": "Tarot Sorunuz",
        "submit_tarot": "Tarot Falını Gönder",
        "login_title": "Üye Girişi",
        "login_kicker": "Hesabına Giriş",
        "login_desc": "Hesabına giriş yaparak fal taleplerini ve yorumlarını yönetebilirsin.",
        "email": "E-Posta",
        "username": "Kullanıcı Adı",
        "password": "Şifre",
        "login_submit": "Giriş Yap",
        "forgot_password": "Şifremi Unuttum",
        "forgot_title": "Şifre Yenile",
        "forgot_desc": "Kullanıcı adı, e-posta ve telefon bilgini girip yeni şifre belirleyebilirsin.",
        "forgot_submit": "Şifreyi Yenile",
        "forgot_bad": "Kullanıcı adı (min 3), e-posta, telefon, yeni şifre (min 4) ve şifre tekrarı zorunludur.",
        "forgot_not_found": "Bilgiler eşleşmedi. Lütfen kullanıcı adı, e-posta ve telefonu kontrol edin.",
        "forgot_ok": "Şifreniz yenilendi. Yeni şifrenizle giriş yapabilirsiniz.",
        "logout_submit": "Çıkış Yap",
        "nav_panel": "Panelim",
        "panel_title": "Kullanıcı Paneli",
        "panel_desc": "Son 20 fal kaydın ve yorumların burada listelenir.",
        "panel_no_data": "Henüz kayıtlı fal geçmişin yok.",
        "panel_reader": "Falcı",
        "panel_type": "Tür",
        "panel_date": "Tarih",
        "panel_question": "Soru",
        "panel_result": "Yorum",
        "panel_status": "Durum",
        "status_pending": "Bekliyor",
        "status_paid": "Ödendi",
        "status_in_progress": "Yorumlanıyor",
        "status_completed": "Tamamlandı",
        "timeline_waiting": "Beklemede",
        "timeline_processing": "Yorumlanıyor",
        "timeline_approved": "Onaylandı",
        "timeline_sent": "Gönderildi",
        "panel_filter_label": "Tür Filtresi",
        "panel_filter_all": "Tümü",
        "panel_detail_toggle": "Detay",
        "panel_detail_question": "Soru Detayı",
        "panel_detail_result": "Yorum Detayı",
        "panel_open_reading": "Fal Detayı",
        "reading_focus_title": "Fal Detayı",
        "reading_focus_desc": "Bu sayfada yalnızca seçtiğin fal yorumu gösterilir.",
        "msg_reading_not_ready": "Bu fal henüz yayınlanmadı.",
        "profile_title": "Hesap Bilgileri",
        "profile_desc": "İsim, e-posta, telefon bilgilerini güncelleyebilir ve şifreni yenileyebilirsin.",
        "profile_new_password": "Yeni Şifre",
        "profile_new_password_confirm": "Yeni Şifre (Tekrar)",
        "register_password_repeat": "Şifre (Tekrar)",
        "profile_save": "Bilgileri Kaydet",
        "register_title": "Kayıt Ol",
        "register_kicker": "Yeni Hesap",
        "register_desc": "Hızlıca hesap oluştur, fal geçmişine ve yorumlarına panelinden eriş.",
        "register_submit": "Kaydı Tamamla",
        "msg_login_ok": "Giriş başarılı.",
        "msg_login_bad": "Kullanıcı adı veya şifre hatalı.",
        "msg_register_ok": "Kayıt tamamlandı. Giriş yapabilirsiniz.",
        "msg_register_bad": "Ad soyad, e-posta, telefon, kullanıcı adı (min 3) zorunludur. Şifre en az 6 karakter olmalı, en az 1 büyük harf ve 1 özel karakter içermeli ve tekrar alanı ile aynı olmalıdır.",
        "msg_register_exists": "Bu kullanıcı adı zaten kullanılıyor.",
        "username_checking": "Kontrol ediliyor...",
        "username_available": "Kullanıcı adı uygun.",
        "username_taken": "Kullanıcı adı zaten var.",
        "username_too_short": "Kullanıcı adı en az 3 karakter olmalı.",
        "msg_auth_required": "Bu sayfa için giriş yapmanız gerekli.",
        "msg_profile_saved": "Hesap bilgileri güncellendi.",
        "msg_profile_bad_name": "Ad soyad alanı zorunludur.",
        "msg_profile_bad_email": "Geçerli bir e-posta giriniz.",
        "msg_profile_bad_phone": "Telefon alanı zorunludur.",
        "msg_profile_bad_password": "Şifre en az 4 karakter olmalı ve tekrar alanı ile aynı olmalı.",
        "msg_csrf_invalid": "Güvenlik doğrulaması başarısız. Lütfen sayfayı yenileyip tekrar deneyin.",
        "msg_too_many_attempts": "Çok fazla hatalı deneme yapıldı. Lütfen {minutes} dakika sonra tekrar deneyin.",
        "agb_title": "AGB ve Yasal Bilgilendirme",
        "agb_desc": "Bu sayfa kullanım koşulları ve görsel lisans bilgilerini içerir.",
        "agb_photo_license": "Falcı fotoğrafları Pexels ücretsiz lisansı ile kullanılmaktadır.",
        "impressum_title": "Impressum",
        "impressum_desc": "Bu sayfa, online fal/orakel danışmanlığı sunan dijital platformlar için gerekli temel yasal bilgilendirmeleri içerir. Aşağıda işletmeci bilgileri, iletişim kanalları, sorumluluk sınırları ve kullanıcıya yönelik hukuki açıklamalar yer alır.",
        "impressum_provider_title": "Hizmet Sağlayıcı",
        "impressum_provider_body": "Orakelia • Online Fal Danışmanlığı Platformu (Dijital Hizmet). Platform; kahve falı, tarot ve katina içeriklerinin dijital ortamda talep edilmesi, yönetilmesi ve sonuçlandırılması için çalışır.",
        "impressum_contact_title": "İletişim",
        "impressum_contact_body": "E-posta: support@orakelia.com • Ortalama yanıt süresi: 24-48 saat • Resmi talepler, teknik bildirimler ve gizlilik başvuruları aynı kanal üzerinden kabul edilir.",
        "impressum_responsible_title": "İçerikten Sorumlu",
        "impressum_responsible_body": "Orakelia Platform Yönetimi. Yayınlanan metinler, kullanıcı iletişimi, sistem yönetimi ve süreç denetimi bu birim tarafından yürütülür.",
        "impressum_content_title": "İçerik Sorumluluğu",
        "impressum_content_body": "Sayfadaki içerikler özenle hazırlanır, düzenli aralıklarla gözden geçirilir ve gerekli durumlarda güncellenir. Buna rağmen tüm bilgilerin her an eksiksiz, kesintisiz, güncel veya hatasız olacağı garanti edilemez. Kullanıcı, içerikleri kendi değerlendirmesiyle kullanmayı kabul eder.",
        "impressum_links_title": "Harici Bağlantılar",
        "impressum_links_body": "Harici sitelere verilen bağlantıların içerikleri ilgili yayıncıların sorumluluğundadır. Bağlantı verildiği anda hukuka aykırı içerik tespit edilmemiştir; ancak bağlantı verilen sayfaların sonraki değişiklikleri sürekli kontrol edilemez. İhlal bildirimi halinde ilgili bağlantılar makul süre içinde kaldırılır.",
        "impressum_dispute_title": "Uyuşmazlık ve Tüketici Bilgilendirmesi",
        "impressum_dispute_body": "İhtilaf durumunda önce support@orakelia.com üzerinden doğrudan çözüm süreci yürütülmesi önerilir. Talebinizde kullanıcı adı, işlem tarihi ve konu özeti paylaşmanız inceleme sürecini hızlandırır. Mahkeme öncesi iletişim adımı, tarafların hızlı uzlaşması için öncelikli kabul edilir.",
        "impressum_disclaimer_title": "Yasal Uyarı",
        "impressum_disclaimer_body": "Bu platformdaki içerikler manevi ve eğlence amaçlıdır; tıbbi, psikolojik, hukuki veya finansal danışmanlık yerine geçmez. Hayati, sağlıkla ilgili, hukuki veya yüksek riskli mali kararlar için yetkili profesyonel danışmanlara başvurulmalıdır.",
        "impressum_copyright_title": "Telif Hakkı",
        "impressum_copyright_body": "Bu sitedeki metinler, tasarımlar ve platforma ait özgün içerikler telif kapsamında korunur. Üçüncü taraf görseller kendi lisans şartlarına tabidir. Yazılı izin olmaksızın kopyalama, çoğaltma, yeniden yayınlama veya ticari kullanım yasaktır.",
        "datenschutz_title": "Datenschutz",
        "datenschutz_desc": "Bu gizlilik politikası, platform kullanımı sırasında hangi kişisel verilerin toplandığını, hangi amaçlarla işlendiğini, ne kadar süre saklandığını ve hangi haklara sahip olduğunuzu açıklar. Metin; hesap yönetimi, fal talepleri, ödeme süreçleri ve güvenlik kayıtları dahil tüm temel işlem adımlarını kapsar.",
        "datenschutz_controller_title": "Veri Sorumlusu",
        "datenschutz_controller_body": "Veri sorumlusu: Orakelia Platform Yönetimi • İletişim: support@orakelia.com. Veri işleme faaliyetleri, hizmetin sağlanması ve yasal yükümlülüklerin yerine getirilmesi amacıyla merkezi olarak yönetilir.",
        "datenschutz_data_title": "İşlenen Veri Türleri",
        "datenschutz_data_body": "Hesap ve talep süreçlerinde ad-soyad, kullanıcı adı, e-posta, telefon, soru metni, seçilen kartlar, yüklenen görseller, ödeme durumu, yorum metni, işlem zaman damgaları, sistem günlükleri, IP ve teknik oturum/cihaz verileri işlenebilir. Destek taleplerinde gönderdiğiniz ek bilgiler de kapsam dahilinde değerlendirilebilir.",
        "datenschutz_purpose_title": "İşleme Amaçları",
        "datenschutz_purpose_body": "Veriler; üyelik oluşturma ve doğrulama, fal talebinin alınması ve işlenmesi, AI destekli yorum üretimi, yönetici onayı, ödeme doğrulaması, müşteri bildirimleri, sahtecilik/güvenlik kontrolleri, hata analizi, performans ölçümü ve hizmet kalitesinin artırılması amaçlarıyla kullanılır.",
        "datenschutz_legal_title": "Hukuki Dayanak",
        "datenschutz_legal_body": "Veri işleme; hizmet sözleşmesinin kurulması/ifası, platform güvenliği ve sürekliliğine ilişkin meşru menfaatler, muhasebe ve yasal yükümlülükler ile gerektiğinde açık rıza dayanaklarına göre yürütülür. İlgili mevzuat kapsamında talep edilen kayıtlar yetkili mercilere sunulabilir.",
        "datenschutz_storage_title": "Saklama Süresi",
        "datenschutz_storage_body": "Veriler yalnızca gerekli süre boyunca saklanır. Hesap verileri kullanıcı talebi ve yasal zorunluluk dengesi gözetilerek tutulur; ödeme ve muhasebe kayıtları ilgili mevzuatın gerektirdiği süre boyunca saklanabilir. Süre sonunda kayıtlar silinir, anonimleştirilir veya erişimi kısıtlanır.",
        "datenschutz_sharing_title": "Üçüncü Taraf Hizmetler",
        "datenschutz_sharing_body": "Ödeme, e-posta iletimi, barındırma, güvenlik ve AI yorumlama süreçlerinde sözleşmeli hizmet sağlayıcılar kullanılabilir. Bu sağlayıcılarla yalnızca ilgili hizmet için zorunlu olan veri paylaşılır ve mümkün olduğunda veri minimizasyonu uygulanır. Tüm üçüncü taraflar sözleşmesel gizlilik yükümlülüğüne tabidir.",
        "datenschutz_cookies_title": "Çerezler ve Oturum",
        "datenschutz_cookies_body": "Platform, oturum güvenliği, giriş durumu, CSRF koruması ve dil tercihi gibi temel işlevler için teknik çerezler kullanır. Bu çerezler hizmetin çalışması için gereklidir. Pazarlama/profilleme amaçlı üçüncü taraf izleme çerezleri kullanılmaz.",
        "datenschutz_security_title": "Veri Güvenliği",
        "datenschutz_security_body": "Uygulamada erişim kontrolü, parola güvenliği, HTTPS aktarım koruması, oturum doğrulaması, CSRF önlemleri, günlükleme ve altyapı seviyesinde teknik/organizasyonel güvenlik tedbirleri uygulanır. Buna rağmen internet üzerindeki hiçbir iletim yöntemi mutlak güvenlik garantisi vermez.",
        "datenschutz_transfer_title": "Uluslararası Veri Aktarımı",
        "datenschutz_transfer_body": "Kullanılan servis sağlayıcıların konumuna bağlı olarak veriler farklı ülkelerde işlenebilir. Sınır ötesi aktarım halinde sözleşmesel koruma hükümleri, erişim sınırlandırması ve mümkün olduğu ölçüde teknik güvenlik önlemleri uygulanır.",
        "datenschutz_rights_title": "Haklarınız",
        "datenschutz_rights_body": "Yürürlükteki mevzuata göre verilerinize erişim, düzeltme, silme, işleme kısıtlama, itiraz ve veri taşınabilirliği haklarına sahipsiniz. Ayrıca verdiğiniz rızayı geleceğe etkili olacak şekilde geri çekebilir, sonuç alamazsanız yetkili denetim otoritesine başvurabilirsiniz.",
        "datenschutz_contact_title": "Gizlilik Başvuruları",
        "datenschutz_contact_body": "Gizlilik talepleriniz için: support@orakelia.com (konu: Datenschutz). Başvurunuzda hesap e-postanızı, talep türünü ve ilgili tarih aralığını belirtmeniz değerlendirme süresini kısaltır.",
        "msg_fill_coffee": "Lütfen tüm kahve falı alanlarını doldurun.",
        "msg_need_photo": "Telve fotoğrafı yüklemeniz gerekiyor.",
        "msg_bad_file": "Sadece png, jpg, jpeg veya webp dosyaları kabul edilir.",
        "msg_too_many_photos": "En fazla {count} foto yükleyebilirsiniz.",
        "msg_coffee_ok": "Kahve falı talebiniz alındı. Ödeme sayfasına yönlendiriliyorsunuz.",
        "msg_bad_type": "Geçersiz fal türü.",
        "msg_fill_card": "Kart falı için tüm alanlar zorunlu.",
        "msg_need_cards": "{count} kart seçimi gerekli.",
        "msg_card_ok": "Kart falınız alındı. Ödeme adımına geçiniz.",
        "msg_bad_payment": "Geçersiz ödeme kaydı.",
        "msg_no_payment": "Ödeme kaydı bulunamadı.",
        "choose_reader_title": "Falcını Seç",
        "choose_reader_desc": "Aşağıdaki falcılardan birini seçtikten sonra talep formu açılır.",
        "coffee_reader_slogan": "Bir yudum. Bir bakış. Sana özel bir mesaj.",
        "katina_reader_slogan": "Aşk konuşsun. Kalbinin sesini dinle.",
        "tarot_reader_slogan": "Kartlar konuşsun. Kaderini gör.",
        "reader_photo_note": "Falcı fotoğrafları Pexels ücretsiz lisansı ile kullanılmaktadır.",
        "reader_photo_link": "Lisans Detayı",
        "selected_reader": "Seçilen Falcı",
        "change_reader": "Falcı Değiştir",
        "msg_choose_reader": "Lütfen önce bir falcı seçin.",
        "reader_live_now": "Şu anda {count} kişi baktırıyor",
        "reader_rating_label": "{rating}/5 ({count} yorum)",
        "rate_title": "Falcını Değerlendir",
        "rate_desc": "Fal sonrası kısa bir değerlendirme bırakabilirsin.",
        "rate_score": "Puan",
        "rate_comment": "Yorum",
        "rate_submit": "Değerlendirmeyi Gönder",
        "rate_done": "Teşekkürler, değerlendirmen kaydedildi.",
        "rate_error": "Geçersiz değerlendirme.",
        "ai_result_title": "Fal Yorumu",
        "ai_result_pending": "Yorum hazırlanıyor.",
        "ai_result_review": "Falınız yorumlanıyor (ortalama 20-30 dk).",
    },
    "en": {
        "brand": "Orakelia",
        "nav_coffee": "Coffee",
        "nav_katina": "Katina",
        "nav_tarot": "Tarot",
        "nav_agb": "AGB",
        "nav_impressum": "Impressum",
        "nav_datenschutz": "Datenschutz",
        "nav_login": "Sign In",
        "nav_register": "Sign Up",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        "lang_de": "Deutsch",
        "lang_fr": "Français",
        "language_field": "Language",
        "menu_languages": "Languages",
        "home_kicker": "Modern Online Reading Experience",
        "home_title": "Choose a Reading Type and Continue",
        "home_desc": "Select one of the reading types below to open its page.",
        "home_cta_primary": "Start Now",
        "home_cta_secondary": "View Reading Types",
        "home_badge_1": "Live Support",
        "live_support": "Live Support",
        "home_badge_2": "Secure Payment",
        "home_badge_3": "3 Languages",
        "home_welcome_title": "Professional Online Fortune Platform",
        "home_welcome_desc": "Choose a reading type, select your reader, and complete your request securely in minutes.",
        "home_welcome_item_1": "Verified reader profiles",
        "home_welcome_item_2": "Fast request and payment flow",
        "home_welcome_item_3": "TR / EN / DE multilingual use",
        "home_welcome_cta": "Choose Reading Type",
        "home_slider_welcome": "Welcome to Orakelia",
        "home_slider_subtext": "Let us turn your questions into clear answers with the reader that best matches your energy.",
        "choice_coffee": "Coffee Reading",
        "home_coffee_slogan_kicker": "Welcome to Orakelia — your platform for professional online fortune guidance.",
        "home_coffee_slogan": "Welcome to Orakelia. Start your coffee reading with clarity and calm energy.",
        "choice_katina": "Katina Love Reading",
        "choice_tarot": "Tarot Reading",
        "home_slide_cta": "Go to Readers",
        "home_coffee_slide_cta": "Go to Coffee Reading",
        "home_slide_text_1": "Find inner clarity with coffee reading",
        "home_slide_text_2": "Discover love signs through Katina",
        "home_slide_text_3": "Illuminate your path with tarot",
        "home_info_1_title": "Orakelia – Your Spiritual Guide",
        "home_info_1_body": "Sometimes in life we face questions about love, the future, or important decisions.\n\nA reading can help you discover new perspectives and reveal hidden connections.",
        "home_info_2_title": "Traditional Oracle Methods",
        "home_info_2_body": "For centuries, people have used oracle methods to interpret signs and find guidance.\n\nAt Orakelia, you can explore different methods:\n\nCoffee Reading\nTarot Cards\nKatina Love Reading",
        "home_info_3_title": "Find Your Answers",
        "home_info_3_body": "A reading can offer you new impulses and help you see your situation from a different perspective.\n\nStart your personal reading now.",
        "slider_prev": "Previous slide",
        "slider_next": "Next slide",
        "coffee_title": "Coffee Reading Request",
        "price_label": "Price",
        "full_name": "Full Name",
        "phone": "Phone",
        "question": "Question",
        "coffee_photo": "Coffee Grounds Photo",
        "submit_coffee": "Submit Coffee Reading",
        "katina_title": "Katina Love Reading",
        "katina_desc": "7-card relationship spread: you, partner, relationship energy, obstacle, near future, advice, outcome.",
        "katina_question": "Your Love Question",
        "submit_katina": "Submit Katina Reading",
        "tarot_title": "Tarot Reading",
        "tarot_desc": "10-card detailed spread (Celtic Cross): situation, challenge, root influence, recent past, potential outcome, near future, self, environment, hopes/fears, final outcome.",
        "tarot_question": "Your Tarot Question",
        "submit_tarot": "Submit Tarot Reading",
        "login_title": "Sign In",
        "login_kicker": "Account Access",
        "login_desc": "Sign in to manage your readings and view your history in one place.",
        "email": "Email",
        "username": "Username",
        "password": "Password",
        "login_submit": "Sign In",
        "forgot_password": "Forgot Password",
        "forgot_title": "Reset Password",
        "forgot_desc": "Enter your username, email and phone, then set a new password.",
        "forgot_submit": "Reset Password",
        "forgot_bad": "Username (min 3), email, phone, new password (min 4), and repeated password are required.",
        "forgot_not_found": "No matching account found. Please check username, email and phone.",
        "forgot_ok": "Your password has been reset. You can sign in with your new password.",
        "logout_submit": "Sign Out",
        "nav_panel": "My Panel",
        "panel_title": "User Panel",
        "panel_desc": "Your latest 20 readings and interpretations are listed here.",
        "panel_no_data": "You have no saved readings yet.",
        "panel_reader": "Reader",
        "panel_type": "Type",
        "panel_date": "Date",
        "panel_question": "Question",
        "panel_result": "Reading",
        "panel_status": "Status",
        "status_pending": "Pending",
        "status_paid": "Paid",
        "status_in_progress": "In Progress",
        "status_completed": "Completed",
        "timeline_waiting": "Waiting",
        "timeline_processing": "In Progress",
        "timeline_approved": "Approved",
        "timeline_sent": "Sent",
        "panel_filter_label": "Type Filter",
        "panel_filter_all": "All",
        "panel_detail_toggle": "Details",
        "panel_detail_question": "Question Details",
        "panel_detail_result": "Reading Details",
        "panel_open_reading": "Open Reading",
        "reading_focus_title": "Reading Detail",
        "reading_focus_desc": "This page shows only the selected reading for easier viewing.",
        "msg_reading_not_ready": "This reading is not published yet.",
        "profile_title": "Account Details",
        "profile_desc": "Update your name, email and phone details, and reset your password.",
        "profile_new_password": "New Password",
        "profile_new_password_confirm": "New Password (Repeat)",
        "register_password_repeat": "Password (Repeat)",
        "profile_save": "Save Details",
        "register_title": "Sign Up",
        "register_kicker": "Create Account",
        "register_desc": "Create your account to access your reading history and personal panel.",
        "register_submit": "Complete Registration",
        "msg_login_ok": "Signed in successfully.",
        "msg_login_bad": "Invalid username or password.",
        "msg_register_ok": "Registration completed. You can sign in now.",
        "msg_register_bad": "Full name, email, phone, and username (min 3) are required. Password must be at least 6 characters, include 1 uppercase letter and 1 special character, and match the repeat field.",
        "msg_register_exists": "This username is already in use.",
        "username_checking": "Checking...",
        "username_available": "Username is available.",
        "username_taken": "This username already exists.",
        "username_too_short": "Username must be at least 3 characters.",
        "msg_auth_required": "You need to sign in for this page.",
        "msg_profile_saved": "Account details updated.",
        "msg_profile_bad_name": "Full name is required.",
        "msg_profile_bad_email": "Please enter a valid email.",
        "msg_profile_bad_phone": "Phone field is required.",
        "msg_profile_bad_password": "Password must be at least 4 characters and match the repeat field.",
        "msg_csrf_invalid": "Security verification failed. Please refresh the page and try again.",
        "msg_too_many_attempts": "Too many failed attempts. Please try again in {minutes} minutes.",
        "agb_title": "AGB and Legal Information",
        "agb_desc": "This page contains terms of use and image license information.",
        "agb_photo_license": "Reader photos are used under the free Pexels license.",
        "impressum_title": "Impressum",
        "impressum_desc": "This page provides the core legal disclosure information required for an online fortune/oracle advisory platform. It includes operator details, contact channels, responsibility scope, and legal notices for users.",
        "impressum_provider_title": "Service Provider",
        "impressum_provider_body": "Orakelia • Online Fortune Guidance Platform (Digital Service). The platform is used to submit, manage, and complete coffee, tarot, and Katina reading requests digitally.",
        "impressum_contact_title": "Contact",
        "impressum_contact_body": "Email: support@orakelia.com • Typical response time: 24-48 hours • Formal requests, technical notifications, and privacy inquiries are handled through this channel.",
        "impressum_responsible_title": "Responsible for Content",
        "impressum_responsible_body": "Orakelia Platform Administration. This unit is responsible for published content, operational management, and user communication processes.",
        "impressum_content_title": "Content Liability",
        "impressum_content_body": "Platform content is prepared with care, reviewed regularly, and updated when necessary. Nevertheless, we cannot guarantee that all information is complete, uninterrupted, up-to-date, or entirely error-free at all times. Users remain responsible for how they use the provided content.",
        "impressum_links_title": "External Links",
        "impressum_links_body": "Content of external websites is the responsibility of their respective operators. At the time of linking, no unlawful content was identifiable; however, continuous monitoring of external pages is not technically reasonable. Upon valid notice of infringement, affected links will be removed within a reasonable period.",
        "impressum_dispute_title": "Dispute Resolution",
        "impressum_dispute_body": "In case of a dispute, we recommend contacting support@orakelia.com first to seek a direct and practical resolution. Please include your username, transaction date, and a short issue summary to speed up review. A direct pre-litigation communication step is preferred.",
        "impressum_disclaimer_title": "Legal Notice",
        "impressum_disclaimer_body": "Content on this platform is spiritual/entertainment-oriented and does not replace medical, psychological, legal, or financial advice. For health, legal, or high-risk financial decisions, users should consult qualified licensed professionals.",
        "impressum_copyright_title": "Copyright",
        "impressum_copyright_body": "Texts, designs, and original platform content on this site are protected by copyright. Third-party visuals remain subject to their own licenses. Unauthorized copying, republication, redistribution, or commercial reuse is prohibited.",
        "datenschutz_title": "Datenschutz",
        "datenschutz_desc": "This privacy policy explains which personal data is collected while using the platform, why it is processed, how long it is stored, and what rights you have. It covers account workflows, reading requests, payment-related records, and operational security logs.",
        "datenschutz_controller_title": "Data Controller",
        "datenschutz_controller_body": "Data controller: Orakelia Platform Administration • Contact: support@orakelia.com. Processing activities are centrally managed to deliver services and comply with legal obligations.",
        "datenschutz_data_title": "Categories of Data Processed",
        "datenschutz_data_body": "During account and reading workflows we may process full name, username, email, phone, question text, selected cards, uploaded images, reading output, payment status, event timestamps, system logs, IP data, and technical session/device metadata. Additional support data you voluntarily provide may also be processed.",
        "datenschutz_purpose_title": "Purposes of Processing",
        "datenschutz_purpose_body": "Data is processed to register and verify accounts, receive and handle reading requests, generate AI-assisted interpretations, run admin approval workflows, verify payments, deliver customer notifications, apply fraud/security checks, analyze incidents, and improve platform quality.",
        "datenschutz_legal_title": "Legal Basis",
        "datenschutz_legal_body": "Processing is based on contract performance, legitimate interests (security and service continuity), accounting/legal compliance obligations, and consent where required. Where lawfully requested, records may be disclosed to competent public authorities.",
        "datenschutz_storage_title": "Retention Period",
        "datenschutz_storage_body": "Data is retained only as long as necessary for service delivery and legal obligations. Account-related data is kept according to user lifecycle and legal requirements; payment/accounting records may be retained for statutory periods. After retention ends, records are deleted, anonymized, or access-restricted.",
        "datenschutz_sharing_title": "Third-Party Service Providers",
        "datenschutz_sharing_body": "We may use contracted providers for payments, email delivery, hosting, operational security, and AI interpretation services. Only data required for each specific purpose is shared, and data-minimization principles are applied where possible. Providers are contractually bound to confidentiality and data protection obligations.",
        "datenschutz_cookies_title": "Cookies and Session Data",
        "datenschutz_cookies_body": "The platform uses essential technical cookies for secure login state, CSRF/session protection, and language preferences. These cookies are necessary for core functionality. No third-party marketing/profiling tracking cookies are used.",
        "datenschutz_security_title": "Data Security",
        "datenschutz_security_body": "We implement access controls, password security measures, HTTPS transport encryption, session safeguards, logging controls, and infrastructure-level technical/organizational protections. Despite these controls, no internet-based transmission method can guarantee absolute security.",
        "datenschutz_transfer_title": "International Data Transfers",
        "datenschutz_transfer_body": "Depending on provider locations, data may be processed outside your country or region. In such cases, contractual safeguards, access restrictions, and technical controls are applied as appropriate to protect transferred data.",
        "datenschutz_rights_title": "Your Rights",
        "datenschutz_rights_body": "Under applicable law, you may request access, correction, deletion, restriction of processing, objection, and data portability where relevant. You may also withdraw consent for future processing and file a complaint with a competent supervisory authority if needed.",
        "datenschutz_contact_title": "Privacy Requests",
        "datenschutz_contact_body": "For privacy requests: support@orakelia.com (subject: Datenschutz). Please include your account email, request type, and relevant date range to speed up processing.",
        "msg_fill_coffee": "Please fill in all coffee reading fields.",
        "msg_need_photo": "You need to upload a coffee grounds photo.",
        "msg_bad_file": "Only png, jpg, jpeg or webp files are allowed.",
        "msg_too_many_photos": "You can upload up to {count} photos.",
        "msg_coffee_ok": "Your coffee reading request has been received. Redirecting to payment page.",
        "msg_bad_type": "Invalid reading type.",
        "msg_fill_card": "All card reading fields are required.",
        "msg_need_cards": "{count} card selections are required.",
        "msg_card_ok": "Your card reading request has been received. Proceed to payment.",
        "msg_bad_payment": "Invalid payment record.",
        "msg_no_payment": "Payment record not found.",
        "choose_reader_title": "Choose Your Reader",
        "choose_reader_desc": "Select one reader below, then the request form will open.",
        "coffee_reader_slogan": "One sip. One glance. A message for you.",
        "katina_reader_slogan": "Let love speak. Listen to your heart.",
        "tarot_reader_slogan": "Let the cards speak. Discover your destiny.",
        "reader_photo_note": "Reader photos are used under the free Pexels license.",
        "reader_photo_link": "License Details",
        "selected_reader": "Selected Reader",
        "change_reader": "Change Reader",
        "msg_choose_reader": "Please choose a reader first.",
        "reader_live_now": "{count} people are currently in session",
        "reader_rating_label": "{rating}/5 ({count} reviews)",
        "rate_title": "Rate Your Reader",
        "rate_desc": "You can leave quick feedback after your reading.",
        "rate_score": "Score",
        "rate_comment": "Comment",
        "rate_submit": "Submit Rating",
        "rate_done": "Thanks, your feedback has been saved.",
        "rate_error": "Invalid rating.",
        "ai_result_title": "Reading Result",
        "ai_result_pending": "Interpretation is being generated.",
        "ai_result_review": "Your reading is being prepared (average 20-30 minutes).",
    },
    "de": {
        "brand": "Orakelia",
        "nav_coffee": "Kaffee",
        "nav_katina": "Katina",
        "nav_tarot": "Tarot",
        "nav_agb": "AGB",
        "nav_impressum": "Impressum",
        "nav_datenschutz": "Datenschutz",
        "nav_login": "Anmelden",
        "nav_register": "Registrieren",
        "lang_tr": "Türkisch",
        "lang_en": "Englisch",
        "lang_de": "Deutsch",
        "lang_fr": "Französisch",
        "language_field": "Sprache",
        "menu_languages": "Sprachen",
        "home_kicker": "Modernes Online-Orakel",
        "home_title": "Wähle eine Art und wechsle zur Seite",
        "home_desc": "Wähle unten eine Kategorie, um zur passenden Seite zu gehen.",
        "home_cta_primary": "Jetzt Starten",
        "home_cta_secondary": "Orakelarten Ansehen",
        "home_badge_1": "Live-Support",
        "live_support": "Live-Chat",
        "home_badge_2": "Sichere Zahlung",
        "home_badge_3": "3 Sprachen",
        "home_welcome_title": "Professionelle Online-Orakelplattform",
        "home_welcome_desc": "Wähle eine Orakelart, bestimme deine Person und sende deine Anfrage sicher in wenigen Schritten.",
        "home_welcome_item_1": "Verifizierte Profile",
        "home_welcome_item_2": "Schneller Anfrage- und Zahlungsablauf",
        "home_welcome_item_3": "Mehrsprachig: TR / EN / DE",
        "home_welcome_cta": "Orakelart Wählen",
        "home_slider_welcome": "Willkommen bei Orakelia",
        "home_slider_subtext": "Lass uns deine Fragen gemeinsam klären und starte jetzt mit der Beraterin, die am besten zu deiner Energie passt.",
        "choice_coffee": "Kaffeesatz-Orakel",
        "home_coffee_slogan_kicker": "Willkommen bei Orakelia – deine Plattform für professionelle Online-Fal-Beratung.",
        "home_coffee_slogan": "Willkommen bei Orakelia. Starte dein Kaffee-Orakel mit Klarheit und ruhiger Energie.",
        "choice_katina": "Katina-Liebesorakel",
        "choice_tarot": "Tarot-Orakel",
        "home_slide_cta": "Zu den Beraterinnen",
        "home_coffee_slide_cta": "Zum Kaffee-Orakel",
        "home_slide_text_1": "Orakelia – Dein spiritueller Wegweiser\n\nManchmal stehen wir im Leben vor Fragen über Liebe, Zukunft oder wichtige Entscheidungen.\n\nEin Orakel kann helfen, neue Perspektiven zu entdecken und verborgene Zusammenhänge sichtbar zu machen.",
        "home_slide_text_2": "Traditionelle Orakelmethoden\n\nSeit Jahrhunderten nutzen Menschen Orakel, um Zeichen zu deuten und Orientierung zu finden.\n\nBei Orakelia kannst du verschiedene Methoden entdecken:\n\nKaffeesatzlesen\nTarotkarten\nKatina Liebesorakel",
        "home_slide_text_3": "Finde deine Antworten\n\nDas Orakel kann dir neue Impulse geben und dir helfen, deine Situation aus einer anderen Perspektive zu betrachten.\n\nStarte jetzt deine persönliche Orakellegung.\n\nOrakel starten",
        "home_info_1_title": "Orakelia – Dein spiritueller Wegweiser",
        "home_info_1_body": "Manchmal stehen wir im Leben vor Fragen über Liebe, Zukunft oder wichtige Entscheidungen.\n\nEin Orakel kann helfen, neue Perspektiven zu entdecken und verborgene Zusammenhänge sichtbar zu machen.",
        "home_info_2_title": "Traditionelle Orakelmethoden",
        "home_info_2_body": "Seit Jahrhunderten nutzen Menschen Orakel, um Zeichen zu deuten und Orientierung zu finden.\n\nBei Orakelia kannst du verschiedene Methoden entdecken:\n\nKaffeesatzlesen\nTarotkarten\nKatina Liebesorakel",
        "home_info_3_title": "Finde deine Antworten",
        "home_info_3_body": "Das Orakel kann dir neue Impulse geben und dir helfen, deine Situation aus einer anderen Perspektive zu betrachten.\n\nStarte jetzt deine persönliche Orakellegung.",
        "slider_prev": "Vorherige Folie",
        "slider_next": "Nächste Folie",
        "coffee_title": "Kaffeesatz-Anfrage",
        "price_label": "Preis",
        "full_name": "Vollständiger Name",
        "phone": "Telefon",
        "question": "Frage",
        "coffee_photo": "Foto vom Kaffeesatz",
        "submit_coffee": "Kaffee-Orakel senden",
        "katina_title": "Katina-Liebesorakel",
        "katina_desc": "7-Karten-Beziehungslegung: Du, Partner, Beziehungsenergie, Hindernis, nahe Zukunft, Rat, Ergebnis.",
        "katina_question": "Deine Liebesfrage",
        "submit_katina": "Katina senden",
        "tarot_title": "Tarot-Orakel",
        "tarot_desc": "Detaillierte 10-Karten-Legung (Keltisches Kreuz): Situation, Hindernis, Grundenergie, jüngste Vergangenheit, mögliche Entwicklung, nahe Zukunft, du selbst, Umfeld, Hoffnungen/Ängste, Ergebnis.",
        "tarot_question": "Deine Tarot-Frage",
        "submit_tarot": "Tarot senden",
        "login_title": "Anmelden",
        "login_kicker": "Kontozugang",
        "login_desc": "Melde dich an, um deine Anfragen und Deutungen zentral zu verwalten.",
        "email": "E-Mail",
        "username": "Benutzername",
        "password": "Passwort",
        "login_submit": "Anmelden",
        "forgot_password": "Passwort vergessen",
        "forgot_title": "Passwort erneuern",
        "forgot_desc": "Gib Benutzername, E-Mail und Telefon ein und lege ein neues Passwort fest.",
        "forgot_submit": "Passwort erneuern",
        "forgot_bad": "Benutzername (min. 3), E-Mail, Telefon, neues Passwort (min. 4) und Passwortwiederholung sind erforderlich.",
        "forgot_not_found": "Keine passenden Kontodaten gefunden. Bitte Benutzername, E-Mail und Telefon prüfen.",
        "forgot_ok": "Dein Passwort wurde erneuert. Du kannst dich jetzt mit dem neuen Passwort anmelden.",
        "logout_submit": "Abmelden",
        "nav_panel": "Mein Bereich",
        "panel_title": "Benutzerbereich",
        "panel_desc": "Deine letzten 20 Orakel und Deutungen werden hier angezeigt.",
        "panel_no_data": "Noch keine gespeicherten Orakel vorhanden.",
        "panel_reader": "Person",
        "panel_type": "Art",
        "panel_date": "Datum",
        "panel_question": "Frage",
        "panel_result": "Deutung",
        "panel_status": "Status",
        "status_pending": "Wartet",
        "status_paid": "Bezahlt",
        "status_in_progress": "In Bearbeitung",
        "status_completed": "Abgeschlossen",
        "timeline_waiting": "Wartet",
        "timeline_processing": "In Bearbeitung",
        "timeline_approved": "Freigegeben",
        "timeline_sent": "Gesendet",
        "panel_filter_label": "Art-Filter",
        "panel_filter_all": "Alle",
        "panel_detail_toggle": "Details",
        "panel_detail_question": "Fragedetails",
        "panel_detail_result": "Deutungsdetails",
        "panel_open_reading": "Orakel Öffnen",
        "reading_focus_title": "Orakel-Detail",
        "reading_focus_desc": "Auf dieser Seite siehst du nur das ausgewählte Orakel für besseres Lesen.",
        "msg_reading_not_ready": "Dieses Orakel ist noch nicht veröffentlicht.",
        "profile_title": "Kontodaten",
        "profile_desc": "Du kannst Name, E-Mail und Telefon aktualisieren und dein Passwort erneuern.",
        "profile_new_password": "Neues Passwort",
        "profile_new_password_confirm": "Neues Passwort (Wiederholen)",
        "register_password_repeat": "Passwort (Wiederholen)",
        "profile_save": "Daten Speichern",
        "register_title": "Registrieren",
        "register_kicker": "Neues Konto",
        "register_desc": "Erstelle dein Konto und greife jederzeit auf deinen Verlauf im Benutzerbereich zu.",
        "register_submit": "Registrierung abschließen",
        "msg_login_ok": "Anmeldung erfolgreich.",
        "msg_login_bad": "Benutzername oder Passwort ist falsch.",
        "msg_register_ok": "Registrierung abgeschlossen. Jetzt anmelden.",
        "msg_register_bad": "Vollständiger Name, E-Mail, Telefon und Benutzername (min. 3) sind erforderlich. Das Passwort muss mindestens 6 Zeichen lang sein, mindestens 1 Großbuchstaben und 1 Sonderzeichen enthalten und mit der Wiederholung übereinstimmen.",
        "msg_register_exists": "Dieser Benutzername ist bereits vergeben.",
        "username_checking": "Wird geprüft...",
        "username_available": "Benutzername ist verfügbar.",
        "username_taken": "Dieser Benutzername existiert bereits.",
        "username_too_short": "Benutzername muss mindestens 3 Zeichen lang sein.",
        "msg_auth_required": "Für diese Seite ist eine Anmeldung erforderlich.",
        "msg_profile_saved": "Kontodaten wurden aktualisiert.",
        "msg_profile_bad_name": "Vollständiger Name ist erforderlich.",
        "msg_profile_bad_email": "Bitte eine gültige E-Mail eingeben.",
        "msg_profile_bad_phone": "Telefonfeld ist erforderlich.",
        "msg_profile_bad_password": "Passwort muss mindestens 4 Zeichen haben und mit der Wiederholung übereinstimmen.",
        "msg_csrf_invalid": "Sicherheitsprüfung fehlgeschlagen. Bitte Seite neu laden und erneut versuchen.",
        "msg_too_many_attempts": "Zu viele fehlgeschlagene Versuche. Bitte in {minutes} Minuten erneut versuchen.",
        "agb_title": "AGB und Rechtliche Hinweise",
        "agb_desc": "Diese Seite enthält Nutzungsbedingungen und Bildlizenz-Informationen.",
        "agb_photo_license": "Die Fotos werden unter der kostenlosen Pexels-Lizenz genutzt.",
        "impressum_title": "Impressum",
        "impressum_desc": "Diese Seite enthält die zentralen rechtlichen Anbieterinformationen für eine digitale Orakel-/Beratungsplattform. Aufgeführt sind Betreiberangaben, Kontaktwege, Verantwortlichkeiten und rechtliche Hinweise für Nutzerinnen und Nutzer.",
        "impressum_provider_title": "Diensteanbieter",
        "impressum_provider_body": "Orakelia • Online-Orakelberatungsplattform (Digitale Dienstleistung). Die Plattform dient der digitalen Annahme, Verwaltung und Abwicklung von Kaffee-, Tarot- und Katina-Anfragen.",
        "impressum_contact_title": "Kontakt",
        "impressum_contact_body": "E-Mail: support@orakelia.com • Übliche Antwortzeit: 24-48 Stunden • Offizielle Anfragen, technische Meldungen und Datenschutzthemen werden über diesen Kanal bearbeitet.",
        "impressum_responsible_title": "Inhaltlich Verantwortlich",
        "impressum_responsible_body": "Orakelia Plattform-Administration. Diese Stelle verantwortet veröffentlichte Inhalte, den technischen Betrieb und die Kommunikation mit Nutzerinnen und Nutzern.",
        "impressum_content_title": "Haftung für Inhalte",
        "impressum_content_body": "Die Inhalte werden mit Sorgfalt erstellt, regelmäßig geprüft und bei Bedarf aktualisiert. Dennoch kann keine Gewähr für Vollständigkeit, ständige Verfügbarkeit, Aktualität oder absolute Fehlerfreiheit übernommen werden. Die Nutzung der Inhalte erfolgt in eigener Verantwortung.",
        "impressum_links_title": "Haftung für Links",
        "impressum_links_body": "Für Inhalte externer Links sind ausschließlich deren Betreiber verantwortlich. Zum Zeitpunkt der Verlinkung waren keine Rechtsverstöße erkennbar; eine permanente inhaltliche Kontrolle externer Seiten ist jedoch nicht zumutbar. Bei bekannt gewordenen Rechtsverletzungen werden betroffene Links zeitnah entfernt.",
        "impressum_dispute_title": "Streitbeilegung",
        "impressum_dispute_body": "Bei Unstimmigkeiten empfehlen wir zunächst die direkte Kontaktaufnahme über support@orakelia.com zur außergerichtlichen Klärung. Bitte übermitteln Sie Benutzername, Vorgangsdatum und eine kurze Sachverhaltsbeschreibung, damit die Prüfung schneller erfolgen kann.",
        "impressum_disclaimer_title": "Rechtlicher Hinweis",
        "impressum_disclaimer_body": "Die Inhalte dieser Plattform dienen spirituellen/unterhaltenden Zwecken und ersetzen keine medizinische, psychologische, rechtliche oder finanzielle Beratung. Für Gesundheitsfragen, Rechtsangelegenheiten oder risikorelevante Finanzentscheidungen sind qualifizierte Fachstellen zu konsultieren.",
        "impressum_copyright_title": "Urheberrecht",
        "impressum_copyright_body": "Texte, Designs und eigene Plattforminhalte dieser Website sind urheberrechtlich geschützt. Inhalte Dritter unterliegen zusätzlich deren jeweiligen Lizenzbedingungen. Unerlaubte Vervielfältigung, Veröffentlichung, Weitergabe oder kommerzielle Nutzung ist untersagt.",
        "datenschutz_title": "Datenschutz",
        "datenschutz_desc": "Diese Datenschutzerklärung erläutert, welche personenbezogenen Daten bei der Nutzung der Plattform erhoben werden, zu welchen Zwecken die Verarbeitung erfolgt, wie lange Daten gespeichert werden und welche Rechte Ihnen zustehen. Erfasst sind insbesondere Kontoabläufe, Orakelanfragen, Zahlungsprozesse und Sicherheitsprotokolle.",
        "datenschutz_controller_title": "Verantwortliche Stelle",
        "datenschutz_controller_body": "Verantwortlich: Orakelia Plattform-Administration • Kontakt: support@orakelia.com. Die Verarbeitungsvorgänge werden zentral gesteuert, um die Leistungserbringung sowie rechtliche Pflichten sicherzustellen.",
        "datenschutz_data_title": "Verarbeitete Datenkategorien",
        "datenschutz_data_body": "Im Konto- und Anfrageprozess können Name, Benutzername, E-Mail, Telefon, Fragetext, ausgewählte Karten, hochgeladene Bilder, Deutungsergebnisse, Zahlungsstatus, Zeitstempel, Systemprotokolle, IP-Informationen sowie technische Sitzungs-/Gerätedaten verarbeitet werden. Freiwillige Angaben aus Supportanfragen können ebenfalls betroffen sein.",
        "datenschutz_purpose_title": "Zwecke der Verarbeitung",
        "datenschutz_purpose_body": "Die Verarbeitung erfolgt zur Kontoerstellung und Verifizierung, Anfrageannahme und Bearbeitung, KI-gestützten Deutungserstellung, administrativen Freigabeprozessen, Zahlungsprüfung, Kundenkommunikation, Missbrauchs- und Sicherheitskontrolle, Fehleranalyse sowie kontinuierlichen Qualitätsverbesserung.",
        "datenschutz_legal_title": "Rechtsgrundlagen",
        "datenschutz_legal_body": "Die Verarbeitung erfolgt auf Grundlage der Vertragserfüllung, berechtigter Interessen (Sicherheit und Betriebsstabilität), gesetzlicher Aufbewahrungs-/Nachweispflichten und – soweit erforderlich – auf Basis einer Einwilligung. Bei gesetzlicher Verpflichtung können Daten an zuständige Behörden übermittelt werden.",
        "datenschutz_storage_title": "Speicherdauer",
        "datenschutz_storage_body": "Daten werden nur so lange gespeichert, wie es für die Leistungserbringung und gesetzliche Pflichten erforderlich ist. Kontobezogene Daten richten sich nach Nutzungsdauer und Rechtslage; abrechnungsrelevante Daten können für gesetzliche Fristen aufbewahrt werden. Danach erfolgt Löschung, Anonymisierung oder Zugriffsbeschränkung.",
        "datenschutz_sharing_title": "Einsatz von Dienstleistern",
        "datenschutz_sharing_body": "Für Zahlung, E-Mail-Versand, Hosting, Betriebssicherheit und KI-gestützte Deutung können vertraglich gebundene Dienstleister eingesetzt werden. Übermittelt werden nur die jeweils erforderlichen Daten; das Prinzip der Datenminimierung wird angewendet. Dienstleister sind vertraglich zu Vertraulichkeit und Datenschutz verpflichtet.",
        "datenschutz_cookies_title": "Cookies und Sitzungsdaten",
        "datenschutz_cookies_body": "Die Plattform nutzt notwendige technische Cookies für Login-/Sitzungsverwaltung, CSRF-Schutz und Spracheinstellungen. Diese Cookies sind für den Betrieb erforderlich. Marketing- oder Profiling-Tracking-Cookies von Drittanbietern werden nicht eingesetzt.",
        "datenschutz_security_title": "Datensicherheit",
        "datenschutz_security_body": "Wir setzen Zugriffskontrollen, Passwortschutz, HTTPS-Transportverschlüsselung, Sitzungsabsicherung, Protokollierung und technische/organisatorische Schutzmaßnahmen auf Infrastruktur-Ebene ein. Trotz angemessener Sicherheitsmaßnahmen kann bei internetbasierter Datenübertragung keine absolute Sicherheit garantiert werden.",
        "datenschutz_transfer_title": "Internationale Datenübermittlung",
        "datenschutz_transfer_body": "Je nach Standort eingesetzter Dienstleister kann eine Verarbeitung außerhalb Ihres Landes oder der EU stattfinden. In solchen Fällen werden geeignete vertragliche Garantien, Zugriffsbeschränkungen und technische Schutzmaßnahmen eingesetzt.",
        "datenschutz_rights_title": "Ihre Rechte",
        "datenschutz_rights_body": "Sie haben je nach Rechtslage insbesondere das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung, Widerspruch und Datenübertragbarkeit. Eine erteilte Einwilligung kann mit Wirkung für die Zukunft widerrufen werden. Zudem besteht ein Beschwerderecht bei einer zuständigen Datenschutzaufsichtsbehörde.",
        "datenschutz_contact_title": "Datenschutzkontakt",
        "datenschutz_contact_body": "Datenschutzanfragen: support@orakelia.com (Betreff: Datenschutz). Bitte geben Sie zur schnelleren Bearbeitung Ihre Konto-E-Mail, die Art Ihres Anliegens und den relevanten Zeitraum an.",
        "msg_fill_coffee": "Bitte alle Felder für das Kaffee-Orakel ausfüllen.",
        "msg_need_photo": "Bitte ein Foto vom Kaffeesatz hochladen.",
        "msg_bad_file": "Nur png-, jpg-, jpeg- oder webp-Dateien sind erlaubt.",
        "msg_too_many_photos": "Du kannst maximal {count} Fotos hochladen.",
        "msg_coffee_ok": "Deine Anfrage wurde empfangen. Weiterleitung zur Zahlung.",
        "msg_bad_type": "Ungültige Orakelart.",
        "msg_fill_card": "Alle Felder für das Karten-Orakel sind erforderlich.",
        "msg_need_cards": "Bitte {count} Karten auswählen.",
        "msg_card_ok": "Deine Kartenanfrage wurde empfangen. Bitte zur Zahlung gehen.",
        "msg_bad_payment": "Ungültiger Zahlungseintrag.",
        "msg_no_payment": "Zahlungseintrag nicht gefunden.",
        "choose_reader_title": "Wähle deine Wahrsagerin",
        "choose_reader_desc": "Bitte zuerst eine Person auswählen, dann erscheint das Formular.",
        "coffee_reader_slogan": "Ein Schluck. Ein Blick. Eine Botschaft für dich.",
        "katina_reader_slogan": "Lass die Liebe sprechen. Lausche deinem Herzen.",
        "tarot_reader_slogan": "Lass die Karten sprechen. Erkenne dein Schicksal.",
        "reader_photo_note": "Die Fotos werden unter der kostenlosen Pexels-Lizenz genutzt.",
        "reader_photo_link": "Lizenzdetails",
        "selected_reader": "Gewählte Person",
        "change_reader": "Person wechseln",
        "msg_choose_reader": "Bitte zuerst eine Person auswählen.",
        "reader_live_now": "Aktuell sind {count} Personen in Sitzung",
        "reader_rating_label": "{rating}/5 ({count} Bewertungen)",
        "rate_title": "Person Bewerten",
        "rate_desc": "Nach dem Orakel kannst du eine kurze Bewertung senden.",
        "rate_score": "Bewertung",
        "rate_comment": "Kommentar",
        "rate_submit": "Bewertung Senden",
        "rate_done": "Danke, deine Bewertung wurde gespeichert.",
        "rate_error": "Ungültige Bewertung.",
        "ai_result_title": "Orakeldeutung",
        "ai_result_pending": "Deutung wird erstellt.",
        "ai_result_review": "Dein Orakel wird bearbeitet (durchschnittlich 20-30 Minuten).",
    },
}

PEXELS_LICENSE_URL = "https://www.pexels.com/license/"


@app.after_request
def apply_security_headers(response):
    # Core hardening headers for browser-side attack surface reduction.
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

    csp = (
        "default-src 'self'; "
        "base-uri 'self'; frame-ancestors 'none'; form-action 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.openai.com; "
        "object-src 'none'; upgrade-insecure-requests"
    )
    response.headers["Content-Security-Policy"] = csp

    if request.is_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
READER_IMAGE_IDS = {
    "coffee": [7179798, 10675984, 10149102, 6014323, 6944681, 8391599, 8770834, 8770819, 8243891, 8243899],
    "katina": [7221692, 15302311, 27498144, 27498188, 19256898, 20769916, 7267117, 8262603, 7658227, 29095570],
    "tarot": [6806709, 33499774, 34491688, 32441935, 34622478, 30254856, 32305602, 35080529, 32728873, 30219425],
}


def pexels_image_url(photo_id: int) -> str:
    return f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&fit=crop&h=900&w=700"


def build_reader_profiles(reading_type: str, names: list[str]) -> list[dict[str, str]]:
    image_ids = READER_IMAGE_IDS[reading_type]
    return [
        {"id": f"{reading_type}_{index + 1}", "name": name, "image": pexels_image_url(image_ids[index])}
        for index, name in enumerate(names)
    ]


READER_PROFILES = {
    "coffee": build_reader_profiles("coffee", ["Maya", "Selin", "Deniz", "Efsun", "Lara", "Aylin", "Mina", "Asya", "Yelda", "Nehir"]),
    "katina": build_reader_profiles("katina", ["Peri", "Naz", "Sera", "Mira", "Rana", "Dora", "İnci", "Nisan", "Melda", "Ekin"]),
    "tarot": build_reader_profiles("tarot", ["Aria", "Selene", "Lina", "Melis", "Elif", "Luna", "Iris", "Elya", "Nova", "Yaren"]),
}

READER_STYLE_PROFILES = {
    "Maya": {"tone": "soft and reassuring", "method": "symbol-first intuitive synthesis", "focus": "emotional balance"},
    "Selin": {"tone": "direct and practical", "method": "pattern spotting and clear conclusions", "focus": "decision clarity"},
    "Deniz": {"tone": "warm and poetic", "method": "narrative symbolism with gentle metaphors", "focus": "inner healing"},
    "Efsun": {"tone": "mystical yet grounded", "method": "archetype and shadow reading", "focus": "deep transformation"},
    "Lara": {"tone": "optimistic and motivating", "method": "future path framing", "focus": "confidence and action"},
    "Aylin": {"tone": "calm and analytical", "method": "cause-effect interpretation", "focus": "stability"},
    "Mina": {"tone": "romantic and delicate", "method": "relationship energy mapping", "focus": "love dynamics"},
    "Asya": {"tone": "bold and straightforward", "method": "truth-first interpretation", "focus": "boundaries"},
    "Yelda": {"tone": "maternal and protective", "method": "supportive guidance reading", "focus": "safety and trust"},
    "Nehir": {"tone": "flowing and reflective", "method": "timeline-based interpretation", "focus": "long-term harmony"},
    "Peri": {"tone": "charming and nuanced", "method": "heart-centered card synthesis", "focus": "romantic timing"},
    "Naz": {"tone": "elegant and concise", "method": "signal filtering and key-point reading", "focus": "clear next step"},
    "Sera": {"tone": "empathetic and intimate", "method": "feeling-layer analysis", "focus": "emotional truth"},
    "Mira": {"tone": "visionary and bright", "method": "opportunity and turning-point scan", "focus": "new beginnings"},
    "Rana": {"tone": "firm and realistic", "method": "risk-opportunity balance", "focus": "smart choices"},
    "Dora": {"tone": "friendly and modern", "method": "plain-language translation of symbols", "focus": "everyday impact"},
    "İnci": {"tone": "gentle and wise", "method": "slow-depth interpretation", "focus": "patience and maturity"},
    "Nisan": {"tone": "fresh and energetic", "method": "momentum-based reading", "focus": "timely action"},
    "Melda": {"tone": "structured and strategic", "method": "position-by-position logic", "focus": "planning"},
    "Ekin": {"tone": "balanced and sincere", "method": "context-first interpretation", "focus": "relationship health"},
    "Aria": {"tone": "confident and elegant", "method": "arc reading (past-present-future)", "focus": "life direction"},
    "Selene": {"tone": "lunar and introspective", "method": "inner motive decoding", "focus": "self-awareness"},
    "Lina": {"tone": "minimal and sharp", "method": "signal amplification", "focus": "what truly matters"},
    "Melis": {"tone": "uplifting and clear", "method": "strength-based reading", "focus": "personal power"},
    "Elif": {"tone": "grounded and trustworthy", "method": "reality-check interpretation", "focus": "stability in love"},
    "Luna": {"tone": "dreamy but concrete", "method": "intuitive symbols to practical steps", "focus": "hope with realism"},
    "Iris": {"tone": "curious and observant", "method": "detail clustering", "focus": "hidden signals"},
    "Elya": {"tone": "compassionate and calm", "method": "healing-centered interpretation", "focus": "closure and relief"},
    "Nova": {"tone": "modern and dynamic", "method": "breakthrough-oriented reading", "focus": "change readiness"},
    "Yaren": {"tone": "honest and heartful", "method": "straight emotional reading", "focus": "authentic connection"},
}


def reader_style_prompt(reader_name: str, lang: str) -> str:
    style = READER_STYLE_PROFILES.get(reader_name, {
        "tone": "warm and natural",
        "method": "balanced intuitive interpretation",
        "focus": "clear guidance",
    })
    tone = style["tone"]
    method = style["method"]
    focus = style["focus"]
    if lang == "en":
        return (
            f"Reader character profile ({reader_name}): "
            f"Tone: {tone}. Method: {method}. Core focus: {focus}. "
            "Keep this character consistent in wording, rhythm, and interpretation style."
        )
    if lang == "de":
        return (
            f"Charakterprofil der Kartenlegerin ({reader_name}): "
            f"Ton: {tone}. Methode: {method}. Fokus: {focus}. "
            "Halte diesen Stil in Wortwahl, Rhythmus und Deutungslogik konsequent ein."
        )
    return (
        f"Falcı karakter profili ({reader_name}): "
        f"Ton: {tone}. Yöntem: {method}. Ana odak: {focus}. "
        "Bu karakteri kelime seçimi, anlatım ritmi ve yorumlama metodunda tutarlı biçimde koru."
    )


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS coffee_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                question TEXT NOT NULL,
                reader_name TEXT NOT NULL DEFAULT '',
                image_path TEXT NOT NULL,
                image_paths TEXT NOT NULL DEFAULT '[]',
                ai_status TEXT NOT NULL DEFAULT 'pending',
                ai_reading TEXT NOT NULL DEFAULT '',
                ai_published INTEGER NOT NULL DEFAULT 0,
                ai_batch_id TEXT NOT NULL DEFAULT '',
                ai_custom_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                paid INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS card_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                reading_type TEXT NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                question TEXT NOT NULL,
                reader_name TEXT NOT NULL DEFAULT '',
                selected_cards TEXT NOT NULL,
                ai_status TEXT NOT NULL DEFAULT 'pending',
                ai_reading TEXT NOT NULL DEFAULT '',
                ai_published INTEGER NOT NULL DEFAULT 0,
                ai_batch_id TEXT NOT NULL DEFAULT '',
                ai_custom_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                paid INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                request_kind TEXT NOT NULL,
                request_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'TL',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_ci
                ON users(lower(username))
                """
            )
        except sqlite3.IntegrityError:
            # Existing legacy rows may already violate case-insensitive uniqueness.
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reader_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_kind TEXT NOT NULL,
                request_id INTEGER NOT NULL,
                reading_type TEXT NOT NULL,
                reader_id TEXT NOT NULL,
                reader_name TEXT NOT NULL,
                full_name TEXT NOT NULL,
                rating REAL NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(request_kind, request_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                ip TEXT NOT NULL,
                attempted_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_scope_ip_time
            ON auth_attempts(scope, ip, attempted_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reading_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_kind TEXT NOT NULL,
                request_id INTEGER NOT NULL,
                reading_type TEXT NOT NULL,
                customer_name TEXT NOT NULL DEFAULT '',
                reader_name TEXT NOT NULL DEFAULT '',
                actor TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                ai_status TEXT NOT NULL DEFAULT '',
                ai_reading TEXT NOT NULL DEFAULT '',
                model_name TEXT NOT NULL DEFAULT '',
                token_input INTEGER NOT NULL DEFAULT 0,
                token_output INTEGER NOT NULL DEFAULT 0,
                token_total INTEGER NOT NULL DEFAULT 0,
                cost_estimate REAL NOT NULL DEFAULT 0,
                quality_flags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reading_audit_request
            ON reading_audit(request_kind, request_id, created_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reading_audit_created
            ON reading_audit(created_at)
            """
        )
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN paid INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN image_paths TEXT NOT NULL DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN paid INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN reader_name TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN reader_name TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE payment_requests ADD COLUMN currency TEXT NOT NULL DEFAULT 'TL'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE payment_requests ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_status TEXT NOT NULL DEFAULT 'pending'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_reading TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_published INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_batch_id TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_custom_id TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_status TEXT NOT NULL DEFAULT 'pending'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_reading TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_published INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_batch_id TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_custom_id TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_published_at TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE coffee_requests ADD COLUMN ai_published_by TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_published_at TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE card_requests ADD COLUMN ai_published_by TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE reading_audit ADD COLUMN model_name TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE reading_audit ADD COLUMN token_input INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE reading_audit ADD COLUMN token_output INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE reading_audit ADD COLUMN token_total INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE reading_audit ADD COLUMN cost_estimate REAL NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE reading_audit ADD COLUMN quality_flags TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required() -> bool:
    return bool(session.get("is_admin"))


def get_admin_actor() -> str:
    actor = str(session.get("admin_username", "")).strip()
    return actor or "admin"


def estimate_tokens_from_text(text: str) -> int:
    body = (text or "").strip()
    if not body:
        return 0
    return max(1, (len(body) + 3) // 4)


def get_model_cost_rates(model_name: str) -> tuple[float, float]:
    if AI_INPUT_COST_PER_1M > 0 and AI_OUTPUT_COST_PER_1M > 0:
        return AI_INPUT_COST_PER_1M, AI_OUTPUT_COST_PER_1M
    defaults: dict[str, tuple[float, float]] = {
        "gpt-4.1-mini": (0.40, 1.60),
        "gpt-4.1": (2.00, 8.00),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
    }
    return defaults.get(model_name, defaults["gpt-4.1-mini"])


def estimate_ai_observability(
    reading_type: str,
    question: str,
    ai_reading: str,
    image_count: int = 0,
    selected_cards_raw: str = "",
    model_name: str = "",
) -> tuple[int, int, int, float, str]:
    q_tokens = estimate_tokens_from_text(question)
    cards_tokens = estimate_tokens_from_text(selected_cards_raw)
    output_tokens = estimate_tokens_from_text(ai_reading)

    if reading_type == "coffee":
        input_tokens = 420 + q_tokens + (image_count * 850)
    else:
        input_tokens = 320 + q_tokens + cards_tokens

    total_tokens = input_tokens + output_tokens
    in_rate, out_rate = get_model_cost_rates(model_name or OPENAI_MODEL)
    cost_estimate = (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate

    flags: list[str] = []
    if len((ai_reading or "").strip()) > 2600:
        flags.append("long")
    if (ai_reading or "").strip():
        issues = validate_reading_quality(ai_reading)
        if issues:
            flags.append("quality_risk")

    return input_tokens, output_tokens, total_tokens, round(cost_estimate, 6), ",".join(flags)


def log_reading_event(
    request_kind: str,
    request_id: int,
    reading_type: str,
    customer_name: str,
    reader_name: str,
    actor: str,
    action: str,
    ai_status: str,
    ai_reading: str,
    model_name: str = "",
    token_input: int = 0,
    token_output: int = 0,
    token_total: int = 0,
    cost_estimate: float = 0.0,
    quality_flags: str = "",
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO reading_audit (
                request_kind, request_id, reading_type, customer_name, reader_name,
                actor, action, ai_status, ai_reading, model_name, token_input, token_output, token_total, cost_estimate, quality_flags, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_kind,
                int(request_id),
                reading_type,
                (customer_name or "").strip(),
                (reader_name or "").strip(),
                (actor or "").strip(),
                action,
                ai_status,
                ai_reading,
                model_name or OPENAI_MODEL,
                max(0, int(token_input or 0)),
                max(0, int(token_output or 0)),
                max(0, int(token_total or 0)),
                float(cost_estimate or 0.0),
                quality_flags or "",
                datetime.utcnow().isoformat(),
            ),
        )


def get_current_user_id() -> int:
    raw = session.get("user_id")
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def user_logged_in() -> bool:
    return get_current_user_id() > 0


def get_current_user_profile() -> dict[str, str]:
    user_id = get_current_user_id()
    if user_id <= 0:
        return {"full_name": "", "phone": "", "email": ""}
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT username, full_name, phone, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        latest_payment = conn.execute(
            """
            SELECT full_name, phone
            FROM payment_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        latest_coffee = conn.execute(
            """
            SELECT full_name, phone
            FROM coffee_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        latest_card = conn.execute(
            """
            SELECT full_name, phone
            FROM card_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return {"full_name": "", "phone": "", "email": ""}
    username = str(row["username"] or "").strip()
    full_name = str(row["full_name"] or "").strip()
    phone = str(row["phone"] or "").strip()
    email = str(row["email"] or "").strip().lower()

    if not full_name:
        for source in (latest_payment, latest_coffee, latest_card):
            if source and str(source["full_name"] or "").strip():
                full_name = str(source["full_name"]).strip()
                break
    if not full_name and username:
        full_name = username

    if not phone:
        for source in (latest_payment, latest_coffee, latest_card):
            if source and str(source["phone"] or "").strip():
                phone = str(source["phone"]).strip()
                break
    if not email and "@" in username:
        email = username.lower()

    return {
        "full_name": full_name,
        "phone": phone,
        "email": email,
    }


def get_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    return request.remote_addr or "unknown"


def record_auth_failure(scope: str, ip: str) -> None:
    now_iso = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO auth_attempts (scope, ip, attempted_at) VALUES (?, ?, ?)",
            (scope, ip, now_iso),
        )


def clear_auth_failures(scope: str, ip: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM auth_attempts WHERE scope = ? AND ip = ?",
            (scope, ip),
        )


def is_auth_rate_limited(scope: str, ip: str, max_attempts: int, window_seconds: int) -> bool:
    cutoff_iso = (datetime.utcnow() - timedelta(seconds=window_seconds)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "DELETE FROM auth_attempts WHERE attempted_at < ?",
            (cutoff_iso,),
        )
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM auth_attempts
            WHERE scope = ? AND ip = ? AND attempted_at >= ?
            """,
            (scope, ip, cutoff_iso),
        ).fetchone()
    count = int(row[0]) if row else 0
    return count >= max_attempts


def clean_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def build_whatsapp_link(phone: str, message: str) -> str:
    digits = clean_phone(phone)
    if not digits:
        return ""
    return f"https://wa.me/{digits}?text={quote(message)}"


def create_payment_record(
    request_kind: str, request_id: int, full_name: str, phone: str, amount: int, currency: str, user_id: int = 0
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO payment_requests (user_id, request_kind, request_id, full_name, phone, amount, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, request_kind, request_id, full_name, phone, amount, currency, "pending", datetime.utcnow().isoformat()),
        )


ALLOWED_ORDER_STATUSES = {"pending", "paid", "in_progress", "completed"}
ORDER_STATUS_NEXT = {
    "pending": "paid",
    "paid": "in_progress",
    "in_progress": "completed",
    "completed": "completed",
}


def normalize_order_status(raw: str) -> str:
    status = raw.strip().lower()
    if status in ALLOWED_ORDER_STATUSES:
        return status
    return "pending"


def build_customer_timeline(order_status: str, ai_status: str, ai_published: int) -> list[dict[str, object]]:
    normalized_status = normalize_order_status(order_status)
    reading_ready = str(ai_status).strip().lower() == "ready"
    published = int(ai_published or 0) == 1

    done_map = {
        "waiting": normalized_status in {"paid", "in_progress", "completed"},
        "processing": normalized_status in {"in_progress", "completed"} or reading_ready,
        "approved": published,
        "sent": normalized_status == "completed" and published,
    }
    order = ["waiting", "processing", "approved", "sent"]
    current = "sent"
    for key in order:
        if not done_map[key]:
            current = key
            break

    return [
        {
            "key": key,
            "label_key": f"timeline_{key}",
            "done": bool(done_map[key]),
            "current": bool(current == key),
        }
        for key in order
    ]


def set_order_status(request_kind: str, request_id: int, new_status: str) -> None:
    normalized = normalize_order_status(new_status)
    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    paid_flag = 1 if normalized in {"paid", "in_progress", "completed"} else 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            UPDATE payment_requests
            SET status = ?
            WHERE request_kind = ? AND request_id = ?
            """,
            (normalized, request_kind, request_id),
        )
        conn.execute(
            f"UPDATE {table_name} SET paid = ? WHERE id = ?",
            (paid_flag, request_id),
        )


def get_current_order_status(request_kind: str, request_id: int) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT status
            FROM payment_requests
            WHERE request_kind = ? AND request_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (request_kind, request_id),
        ).fetchone()
    if row is None:
        return "pending"
    return normalize_order_status(str(row["status"]))


def send_email_message(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if not SMTP_HOST:
        return False, "SMTP_HOST eksik"
    if not SMTP_FROM:
        return False, "SMTP_FROM eksik"
    try:
        message = EmailMessage()
        message["From"] = SMTP_FROM
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            if SMTP_USE_TLS:
                server.starttls()
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
        return True, "ok"
    except Exception as exc:
        app.logger.exception("Email delivery failed")
        return False, str(exc)


def notify_reading_completed(request_kind: str, request_id: int) -> tuple[bool, str]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if request_kind == "coffee":
            row = conn.execute(
                """
                SELECT c.full_name, c.reader_name, u.email
                FROM coffee_requests c
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.id = ?
                """,
                (request_id,),
            ).fetchone()
            reading_label = "Kahve Falı"
        else:
            row = conn.execute(
                """
                SELECT c.full_name, c.reader_name, u.email
                FROM card_requests c
                LEFT JOIN users u ON u.id = c.user_id
                WHERE c.id = ?
                """,
                (request_id,),
            ).fetchone()
            reading_label = "Kart Falı"
    if row is None:
        return False, "Talep kaydı bulunamadı"
    email = str(row["email"] or "").strip()
    if not email or "@" not in email:
        return False, "Müşteri e-postası eksik veya geçersiz"
    full_name = str(row["full_name"] or "Müşteri")
    reader_name = str(row["reader_name"] or "Falcı")
    subject = "Fal Yorumunuz Hazır"
    body = (
        f"Merhaba {full_name},\n\n"
        f"{reading_label} yorumunuz hazırlandı.\n"
        f"Falcınız: {reader_name}\n\n"
        f"Panelinize giriş yaparak yorumunuzu görebilirsiniz:\n"
        f"https://orakelia.com/dashboard?lang=tr\n\n"
        "Sevgiler,\n"
        "Orakelia"
    )
    return send_email_message(email, subject, body)


def parse_json_list(raw: str) -> list[str]:
    try:
        parsed = json.loads(raw or "[]")
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except ValueError:
        pass
    return []


def file_to_data_url(path: Path) -> str:
    # Cost optimization: downscale image before vision inference.
    if Image is not None:
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((768, 768))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=78, optimize=True)
            raw = buf.getvalue()
        mime = "image/jpeg"
    else:
        mime, _ = mimetypes.guess_type(path.name)
        mime = mime or "application/octet-stream"
        raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def extract_response_text(payload: dict[str, object]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    output = payload.get("output")
    if isinstance(output, list):
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "output_text" and isinstance(part.get("text"), str):
                    chunks.append(part["text"].strip())
        joined = "\n".join([c for c in chunks if c])
        if joined:
            return joined
    return ""


def openai_http_json(url: str, method: str = "GET", body: dict[str, object] | None = None, timeout: int = 45) -> dict[str, object]:
    req = Request(
        url,
        data=(json.dumps(body).encode("utf-8") if body is not None else None),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def openai_http_text(url: str, timeout: int = 45) -> str:
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def stripe_currency_code(currency: str) -> str:
    normalized = currency.strip().lower()
    if normalized in {"tl", "try"}:
        return "try"
    if normalized in {"eur", "usd"}:
        return normalized
    return "eur"


def stripe_create_checkout_session(
    amount: int,
    currency: str,
    request_kind: str,
    request_id: int,
    success_url: str,
    cancel_url: str,
) -> str:
    if not STRIPE_SECRET_KEY:
        return ""

    stripe_currency = stripe_currency_code(currency)
    product_name = f"Fal Ödemesi ({request_kind}-{request_id})"
    payload = (
        f"mode=payment"
        f"&success_url={quote(success_url, safe=':/?=&')}"
        f"&cancel_url={quote(cancel_url, safe=':/?=&')}"
        f"&line_items[0][quantity]=1"
        f"&line_items[0][price_data][currency]={quote(stripe_currency)}"
        f"&line_items[0][price_data][unit_amount]={int(amount) * 100}"
        f"&line_items[0][price_data][product_data][name]={quote(product_name)}"
        f"&metadata[request_kind]={quote(request_kind)}"
        f"&metadata[request_id]={int(request_id)}"
    ).encode("utf-8")

    req = Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=payload,
        headers={
            "Authorization": f"Bearer {STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Stripe HTTP {exc.code}: {error_body}") from exc
    return str(data.get("url", ""))


def verify_stripe_signature(raw_body: bytes, signature_header: str) -> bool:
    if not STRIPE_WEBHOOK_SECRET:
        return False
    parts = [p.strip() for p in signature_header.split(",") if p.strip()]
    timestamp = ""
    signatures: list[str] = []
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "t":
            timestamp = value
        elif key == "v1":
            signatures.append(value)
    if not timestamp or not signatures:
        return False
    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(STRIPE_WEBHOOK_SECRET.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


def queue_openai_batch(input_items: list[dict[str, str]]) -> tuple[str, str, str]:
    custom_id = f"fal-{uuid.uuid4().hex[:16]}"
    batch_line = {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": OPENAI_MODEL,
            "input": [{"role": "user", "content": input_items}],
            "temperature": 0.9,
        },
    }
    file_bytes = (json.dumps(batch_line, ensure_ascii=False) + "\n").encode("utf-8")
    boundary = f"----falbatch{uuid.uuid4().hex}"
    body_chunks = [
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="purpose"\r\n\r\n',
        b"batch\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="file"; filename="batch.jsonl"\r\n',
        b"Content-Type: application/jsonl\r\n\r\n",
        file_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    multipart_body = b"".join(body_chunks)
    file_req = Request(
        "https://api.openai.com/v1/files",
        data=multipart_body,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urlopen(file_req, timeout=45) as resp:
            file_payload = json.loads(resp.read().decode("utf-8"))
        file_id = str(file_payload.get("id", ""))
        if not file_id:
            return "error", "", ""
        batch_payload = openai_http_json(
            "https://api.openai.com/v1/batches",
            method="POST",
            body={
                "input_file_id": file_id,
                "endpoint": "/v1/responses",
                "completion_window": "24h",
            },
            timeout=45,
        )
        batch_id = str(batch_payload.get("id", ""))
        if not batch_id:
            return "error", "", ""
        return "batched", batch_id, custom_id
    except Exception:
        return "error", "", ""


def resolve_openai_batch_result(batch_id: str, custom_id: str) -> tuple[str, str]:
    if not batch_id or not custom_id or not OPENAI_API_KEY:
        return "error", ""
    try:
        batch = openai_http_json(f"https://api.openai.com/v1/batches/{batch_id}", timeout=20)
    except Exception:
        return "error", ""
    status = str(batch.get("status", ""))
    if status not in {"completed"}:
        return "batched", ""
    output_file_id = str(batch.get("output_file_id", ""))
    if not output_file_id:
        return "error", ""
    try:
        raw = openai_http_text(f"https://api.openai.com/v1/files/{output_file_id}/content", timeout=30)
    except Exception:
        return "error", ""
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if str(obj.get("custom_id")) != custom_id:
            continue
        response = obj.get("response")
        if isinstance(response, dict):
            body = response.get("body")
            if isinstance(body, dict):
                text = extract_response_text(body)
                if text:
                    return "ready", text
    return "error", ""


def call_openai_reading(input_items: list[dict[str, str]]) -> tuple[str, str, str, str]:
    if not OPENAI_API_KEY:
        return "no_key", "", "", ""
    if OPENAI_USE_BATCH:
        status, batch_id, custom_id = queue_openai_batch(input_items)
        return status, "", batch_id, custom_id
    try:
        payload = openai_http_json(
            "https://api.openai.com/v1/responses",
            method="POST",
            body={
                "model": OPENAI_MODEL,
                "input": [{"role": "user", "content": input_items}],
                "temperature": 0.9,
            },
            timeout=45,
        )
    except Exception:
        return "error", "", "", ""
    text = extract_response_text(payload)
    if not text:
        return "error", "", "", ""
    return "ready", text, "", ""


def build_coffee_prompt(question: str, full_name: str, reader_name: str, lang: str, image_count: int) -> str:
    character = reader_style_prompt(reader_name, lang)
    if lang == "en":
        return (
            "You are an experienced Turkish coffee reading expert. "
            "Write in a warm, natural, human tone; avoid robotic language and avoid generic filler. "
            "Use ONLY the uploaded grounds photos and the user's question. Do not invent symbols that are not visible.\n"
            f"{character}\n"
            "Language rule: Write the full response in English only.\n"
            "Style:\n"
            "- Write as if you are speaking one-to-one with the client in a warm, human tone.\n"
            "- Start with one short overall-energy paragraph.\n"
            "- Then continue with flowing mini-sections (not rigid numbered lists).\n"
            "- Use varied sentence lengths; avoid repetitive template phrases.\n"
            "- Be clear, practical, and emotionally intelligent.\n"
            "- End with exactly 3 short actionable suggestions.\n"
            f"Final line must be exactly this name only: {reader_name}\n"
            f"Client: {full_name}\nQuestion: {question}\nPhoto count: {image_count}"
        )
    if lang == "de":
        return (
            "Du bist eine erfahrene Kaffeesatz-Orakelberaterin. "
            "Schreibe warm, natürlich und menschlich; nicht mechanisch. "
            "Nutze NUR die hochgeladenen Fotos und die Frage. Keine erfundenen Symbole.\n"
            f"{character}\n"
            "Sprachregel: Schreibe die komplette Antwort nur auf Deutsch.\n"
            "Stil:\n"
            "- Schreibe wie in einem persönlichen Gespräch: warm, nahbar und menschlich.\n"
            "- Starte mit einem kurzen Absatz zur Gesamtenergie.\n"
            "- Danach klare, natürliche Abschnitte statt starrer Listen.\n"
            "- Nutze abwechslungsreiche Satzlängen und vermeide Schablonensätze.\n"
            "- Konkrete, alltagsnahe Sprache.\n"
            "- Am Ende genau 3 kurze Empfehlungen.\n"
            f"Letzte Zeile muss exakt nur dieser Name sein: {reader_name}\n"
            f"Kundin: {full_name}\nFrage: {question}\nAnzahl Fotos: {image_count}"
        )
    return (
        "Deneyimli bir kahve falı yorumcususun. "
        "Yorumu sıcak, doğal ve insan gibi yaz; mekanik ve şablon cümlelerden kaçın. "
        "Sadece yüklenen telve fotoğraflarını ve soruyu kullan. Fotoğrafta görünmeyen sembol uydurma.\n"
        f"{character}\n"
        "Dil kuralı: Cevabın tamamını yalnızca Türkçe yaz.\n"
        "Yazım tarzı:\n"
        "- Müşteriyle birebir konuşur gibi samimi ve sıcak bir dil kullan.\n"
        "- Kısa bir 'genel enerji' paragrafıyla başla.\n"
        "- Sonra akıcı ara başlıklarla devam et (katı numaralı liste olmasın).\n"
        "- Cümle uzunluklarını çeşitlendir; tekrarlayan şablon kalıplardan kaçın.\n"
        "- Gerçekçi, net ve duygusal olarak dengeli bir dil kullan.\n"
        "- Sonda tam 3 kısa, uygulanabilir tavsiye ver.\n"
        f"Son satır yalnızca şu isim olsun: {reader_name}\n"
        f"Müşteri: {full_name}\nSoru: {question}\nFotoğraf Sayısı: {image_count}"
    )


def format_cards_for_prompt(selected_cards: str) -> str:
    try:
        parsed = json.loads(selected_cards or "[]")
    except ValueError:
        return selected_cards
    if not isinstance(parsed, list):
        return selected_cards
    lines: list[str] = []
    for idx, item in enumerate(parsed, start=1):
        if isinstance(item, dict):
            position = str(item.get("position", f"Pozisyon {idx}")).strip()
            card = str(item.get("card", f"Kart {idx}")).strip()
            lines.append(f"{idx}. {position}: {card}")
        else:
            lines.append(f"{idx}. {str(item)}")
    return "\n".join(lines) if lines else selected_cards


def build_card_prompt(reading_type: str, question: str, full_name: str, reader_name: str, selected_cards: str, lang: str) -> str:
    is_tarot = reading_type == "tarot"
    layout = "7 kart Katina aşk açılımı" if reading_type == "katina" else "10 kart Tarot açılımı (Kelt Haçı)"
    cards_detail = format_cards_for_prompt(selected_cards)
    character = reader_style_prompt(reader_name, lang)
    if lang == "en":
        depth_rule = (
            "Tarot depth rule: Interpret all 10 positions one by one, then provide a combined synthesis of the full spread.\n"
            if is_tarot
            else ""
        )
        return (
            f"You are a professional {reading_type} reader. Interpret based on the selected spread and user question.\n"
            f"Spread: {layout}\nClient: {full_name}\nQuestion: {question}\nSelected cards/positions:\n{cards_detail}\n"
            f"{character}\n"
            f"{depth_rule}"
            "Important: card values above are internal technical IDs. Never print these IDs in the final text.\n"
            "Language rule: Write the full response in English only.\n"
            "Write naturally and warmly, not mechanically. Avoid generic template wording.\n"
            "Write like a real human conversation with the client: clear, personal, and emotionally aware.\n"
            "Use varied sentence lengths and transitions so it reads natural, not formulaic.\n"
            "Flow:\n"
            "- Short overall theme paragraph\n"
            "- Position-based interpretation in human language\n"
            "- Risk/opportunity notes\n"
            "- Exactly 3 concise recommendations\n"
            f"Final line must be exactly this name only: {reader_name}"
        )
    if lang == "de":
        depth_rule = (
            "Tarot-Tiefe: Deute alle 10 Positionen nacheinander und fasse danach die Gesamtenergie der Legung zusammen.\n"
            if is_tarot
            else ""
        )
        return (
            f"Du bist eine professionelle {reading_type}-Legung Assistenz. Deute basierend auf den gezogenen Karten und der Frage.\n"
            f"Legung: {layout}\nKundin: {full_name}\nFrage: {question}\nGezogene Karten/Positionen:\n{cards_detail}\n"
            f"{character}\n"
            f"{depth_rule}"
            "Wichtig: Die Kartenwerte oben sind interne technische IDs. Diese IDs dürfen im finalen Text nicht erscheinen.\n"
            "Sprachregel: Schreibe die komplette Antwort nur auf Deutsch.\n"
            "Schreibe natürlich, warm und nicht mechanisch.\n"
            "Schreibe wie in einem echten Beratungsgespräch: persönlich, klar und empathisch.\n"
            "Nutze abwechslungsreiche Satzlängen und natürliche Übergänge statt starrer Formeln.\n"
            "Struktur:\n"
            "- Kurzer Absatz zur Gesamtenergie\n"
            "- Deutung nach Positionen in natürlicher Sprache\n"
            "- Risiko/Chance\n"
            "- Genau 3 klare Empfehlungen\n"
            f"Letzte Zeile muss exakt nur dieser Name sein: {reader_name}"
        )
    depth_rule = (
        "Tarot derinlik kuralı: 10 kartın tüm pozisyonlarını tek tek yorumla, ardından açılımın toplam enerjisini birleştirerek özetle.\n"
        if is_tarot
        else ""
    )
    return (
        f"Profesyonel bir {reading_type} fal yorumcususun. Seçilen açılım ve soru üzerinden yorum üret.\n"
        f"Açılım: {layout}\nMüşteri: {full_name}\nSoru: {question}\nSeçilen kart/pozisyonlar:\n{cards_detail}\n"
        f"{character}\n"
        f"{depth_rule}"
        "Önemli: Yukarıdaki kart değerleri sistem içi teknik ID'dir. Nihai yorum metninde bu ID'leri asla yazma.\n"
        "Dil kuralı: Cevabın tamamını yalnızca Türkçe yaz.\n"
        "Dil sıcak, doğal ve insan gibi olsun; mekanik şablon cümlelerden kaçın.\n"
        "Müşteriyle gerçek bir sohbet ediyor gibi yaz: kişisel, anlaşılır ve empatik ol.\n"
        "Cümle ritmini çeşitlendir, doğal geçişler kullan; kalıp metin gibi görünmesin.\n"
        "Akış:\n"
        "- Kısa bir genel enerji paragrafı\n"
        "- Pozisyonlara göre yorum (doğal cümlelerle)\n"
        "- Fırsat/risk notları\n"
        "- Tam 3 kısa ve uygulanabilir öneri\n"
        f"Son satır yalnızca şu isim olsun: {reader_name}"
    )


def generate_coffee_ai_reading(question: str, full_name: str, reader_name: str, image_paths: list[str], lang: str) -> tuple[str, str, str, str]:
    content: list[dict[str, str]] = [{"type": "input_text", "text": build_coffee_prompt(question, full_name, reader_name, lang, len(image_paths))}]
    for rel in image_paths[:3]:
        abs_path = (BASE_DIR / "static" / rel).resolve()
        if abs_path.exists():
            content.append({"type": "input_image", "image_url": file_to_data_url(abs_path)})
    return call_openai_reading(content)


def generate_card_ai_reading(reading_type: str, question: str, full_name: str, reader_name: str, selected_cards: str, lang: str) -> tuple[str, str, str, str]:
    content = [{"type": "input_text", "text": build_card_prompt(reading_type, question, full_name, reader_name, selected_cards, lang)}]
    return call_openai_reading(content)


def stable_hash_int(seed: str) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def estimate_live_count(reader_id: str, now: datetime) -> int:
    day_key = now.strftime("%Y%m%d")
    daily_total = 1 + (stable_hash_int(f"day:{reader_id}:{day_key}") % 8)
    # Each reading is ~30 minutes (2 sessions/hour). We model queue/load by hour.
    hour_curve = [0.45, 0.4, 0.35, 0.35, 0.4, 0.45, 0.55, 0.72, 0.9, 1.0, 1.05, 1.1,
                  1.0, 0.95, 1.0, 1.05, 1.15, 1.28, 1.35, 1.25, 1.1, 0.9, 0.7, 0.55]
    jitter = ((stable_hash_int(f"hour:{reader_id}:{day_key}:{now.hour}") % 100) / 100.0) - 0.5
    estimated_queue = (daily_total * hour_curve[now.hour]) + (daily_total / 4.0) + (jitter * 0.8)
    return max(1, min(8, round(estimated_queue)))


def default_rating_for_reader(reader_id: str) -> float:
    return 3.0 + ((stable_hash_int(f"rating:{reader_id}") % 16) / 10.0)


def get_feedback_map(reading_type: str) -> dict[str, dict[str, float | int]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT reader_id, AVG(rating) AS avg_rating, COUNT(*) AS review_count
            FROM reader_feedback
            WHERE reading_type = ?
            GROUP BY reader_id
            """,
            (reading_type,),
        ).fetchall()
    return {
        row["reader_id"]: {
            "avg_rating": float(row["avg_rating"]) if row["avg_rating"] is not None else 0.0,
            "review_count": int(row["review_count"] or 0),
        }
        for row in rows
    }


def normalize_rating(raw: float) -> float:
    return max(3.0, min(4.5, round(raw * 2) / 2))


def get_readers(reading_type: str) -> list[dict[str, object]]:
    base = READER_PROFILES.get(reading_type, [])
    feedback_map = get_feedback_map(reading_type)
    now = datetime.now()
    readers: list[dict[str, str | float | int]] = []
    for reader in base:
        summary = feedback_map.get(reader["id"])
        review_count = int(summary["review_count"]) if summary else 0
        rating_value = normalize_rating(float(summary["avg_rating"])) if summary and review_count > 0 else normalize_rating(default_rating_for_reader(reader["id"]))
        live_count = estimate_live_count(reader["id"], now)
        readers.append(
            {
                **reader,
                "live_count": live_count,
                "rating_value": rating_value,
                "review_count": review_count,
            }
        )
    return readers


def get_reader_by_id(reading_type: str, reader_id: str) -> dict[str, object] | None:
    for reader in get_readers(reading_type):
        if reader["id"] == reader_id:
            return reader
    return None


def get_reader_id_by_name(reading_type: str, reader_name: str) -> str:
    for reader in READER_PROFILES.get(reading_type, []):
        if reader["name"] == reader_name:
            return reader["id"]
    return ""


def get_country_code() -> str:
    header_keys = [
        "CF-IPCountry",
        "CloudFront-Viewer-Country",
        "X-Country-Code",
        "X-Geo-Country",
        "X-AppEngine-Country",
    ]
    for key in header_keys:
        value = request.headers.get(key, "").strip().upper()
        if len(value) == 2 and value.isalpha():
            return value
    if request.remote_addr in {"127.0.0.1", "::1", "localhost"}:
        return "TR"
    return ""


def get_pricing() -> tuple[int, str]:
    country = get_country_code()
    if country == "TR":
        return 200, "TL"
    if country in EUROPE_COUNTRIES:
        return 20, "EUR"
    return 20, "EUR"


def detect_lang_by_country() -> str:
    country = get_country_code()
    if country == "TR":
        return "tr"
    if country not in EUROPE_COUNTRIES:
        return "en"
    if country in {"DE", "AT", "LI"}:
        return "de"
    if country in {"FR", "BE", "LU", "MC"}:
        return "fr"
    return "en"


def get_lang() -> str:
    requested = request.args.get("lang", "").strip().lower()
    if requested in LANGUAGES:
        session["lang"] = requested
        return requested
    saved = session.get("lang")
    if saved in LANGUAGES:
        return saved
    detected = detect_lang_by_country()
    session["lang"] = detected
    return detected


def t(key: str, **kwargs: object) -> str:
    lang = get_lang()
    raw = (
        TRANSLATIONS.get(lang, {}).get(key)
        or TRANSLATIONS.get("en", {}).get(key)
        or TRANSLATIONS.get(DEFAULT_LANG, {}).get(key)
        or key
    )
    if kwargs:
        return raw.format(**kwargs)
    return raw


def is_strong_registration_password(password: str) -> bool:
    if len(password) < 6:
        return False
    if re.search(r"[A-Z]", password) is None:
        return False
    if re.search(r"[^A-Za-z0-9]", password) is None:
        return False
    return True


def lang_url(target_lang: str) -> str:
    if target_lang not in LANGUAGES:
        target_lang = DEFAULT_LANG
    args = request.args.to_dict(flat=True)
    args["lang"] = target_lang
    if request.endpoint:
        return url_for(request.endpoint, **(request.view_args or {}), **args)
    return f"?lang={target_lang}"


def resolve_image_path(image_path: str) -> str:
    if image_path.startswith(("http://", "https://")):
        return image_path
    return url_for("static", filename=image_path)


def csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return str(token)


@app.before_request
def enforce_csrf_on_post():
    if request.method != "POST":
        return None
    if request.endpoint in {"stripe_webhook"}:
        return None
    token_form = request.form.get("_csrf_token", "")
    token_session = str(session.get("_csrf_token", ""))
    if token_form and token_session and hmac.compare_digest(token_form, token_session):
        return None

    flash(t("msg_csrf_invalid"), "error")
    fallback = request.referrer or url_for("home", lang=get_lang())
    if request.endpoint in {"admin_login", "admin_logout", "mark_paid"}:
        fallback = url_for("admin")
    return redirect(fallback)


@app.context_processor
def inject_i18n():
    return {
        "t": t,
        "lang": get_lang(),
        "lang_url": lang_url,
        "csrf_token": csrf_token,
        "is_logged_in": user_logged_in(),
        "current_username": session.get("username", ""),
        "reader_image_url": resolve_image_path,
        "pexels_license_url": PEXELS_LICENSE_URL,
        "instagram_url": INSTAGRAM_URL,
        "x_url": X_URL,
        "telegram_url": TELEGRAM_URL,
        "live_support_url": LIVE_SUPPORT_URL,
    }


@app.get("/")
def home():
    return render_template(
        "index.html",
        whatsapp_number=WHATSAPP_NUMBER,
    )


@app.get("/coffee")
def coffee_page():
    reader_id = request.args.get("reader", "").strip()
    if reader_id:
        return redirect(url_for("coffee_reader_page", reader_id=reader_id, lang=get_lang()))
    return render_template("coffee.html", readers=get_readers("coffee"))


@app.get("/coffee/reader/<reader_id>")
def coffee_reader_page(reader_id: str):
    if not user_logged_in():
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    amount, currency = get_pricing()
    selected_reader = get_reader_by_id("coffee", reader_id)
    if selected_reader is None:
        flash(t("msg_choose_reader"), "error")
        return redirect(url_for("coffee_page", lang=get_lang()))
    profile = get_current_user_profile()
    return render_template(
        "coffee_reader.html",
        reading_price=amount,
        currency=currency,
        selected_reader=selected_reader,
        prefill_full_name=profile["full_name"],
        prefill_phone=profile["phone"],
        prefill_email=profile["email"],
    )


@app.get("/katina")
def katina_page():
    reader_id = request.args.get("reader", "").strip()
    if reader_id:
        return redirect(url_for("katina_reader_page", reader_id=reader_id, lang=get_lang()))
    return render_template("katina.html", readers=get_readers("katina"))


@app.get("/katina/reader/<reader_id>")
def katina_reader_page(reader_id: str):
    if not user_logged_in():
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    amount, currency = get_pricing()
    selected_reader = get_reader_by_id("katina", reader_id)
    if selected_reader is None:
        flash(t("msg_choose_reader"), "error")
        return redirect(url_for("katina_page", lang=get_lang()))
    profile = get_current_user_profile()
    return render_template(
        "katina_reader.html",
        reading_price=amount,
        currency=currency,
        selected_reader=selected_reader,
        prefill_full_name=profile["full_name"],
        prefill_phone=profile["phone"],
        prefill_email=profile["email"],
    )


@app.get("/tarot")
def tarot_page():
    reader_id = request.args.get("reader", "").strip()
    if reader_id:
        return redirect(url_for("tarot_reader_page", reader_id=reader_id, lang=get_lang()))
    return render_template("tarot.html", readers=get_readers("tarot"))


@app.get("/tarot/reader/<reader_id>")
def tarot_reader_page(reader_id: str):
    if not user_logged_in():
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    amount, currency = get_pricing()
    selected_reader = get_reader_by_id("tarot", reader_id)
    if selected_reader is None:
        flash(t("msg_choose_reader"), "error")
        return redirect(url_for("tarot_page", lang=get_lang()))
    profile = get_current_user_profile()
    return render_template(
        "tarot_reader.html",
        reading_price=amount,
        currency=currency,
        selected_reader=selected_reader,
        prefill_full_name=profile["full_name"],
        prefill_phone=profile["phone"],
        prefill_email=profile["email"],
    )


@app.get("/login")
def login_page():
    return render_template("login.html")


@app.post("/login")
def login_submit():
    ip = get_client_ip()
    if is_auth_rate_limited("user_login", ip, max_attempts=8, window_seconds=15 * 60):
        flash(t("msg_too_many_attempts", minutes=15), "error")
        return redirect(url_for("login_page", lang=get_lang()))

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    if row is None or not check_password_hash(str(row["password_hash"]), password):
        record_auth_failure("user_login", ip)
        flash(t("msg_login_bad"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    clear_auth_failures("user_login", ip)
    session["user_id"] = int(row["id"])
    session["username"] = username
    flash(t("msg_login_ok"), "ok")
    return redirect(url_for("dashboard_page", lang=get_lang()))


@app.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@app.post("/forgot-password")
def forgot_password_submit():
    username = request.form.get("username", "").strip().lower()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    new_password = request.form.get("new_password", "")
    new_password_confirm = request.form.get("new_password_confirm", "")

    if len(username) < 3 or "@" not in email or not phone or len(new_password) < 4 or new_password != new_password_confirm:
        flash(t("forgot_bad"), "error")
        return redirect(url_for("forgot_password_page", lang=get_lang()))

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id FROM users
            WHERE lower(username) = ? AND lower(email) = ? AND phone = ?
            LIMIT 1
            """,
            (username, email, phone),
        ).fetchone()
        if row is None:
            flash(t("forgot_not_found"), "error")
            return redirect(url_for("forgot_password_page", lang=get_lang()))
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), int(row["id"])),
        )

    flash(t("forgot_ok"), "ok")
    return redirect(url_for("login_page", lang=get_lang()))


@app.get("/register")
def register_page():
    prefill = session.pop("register_prefill", None)
    if not isinstance(prefill, dict):
        prefill = {}
    return render_template("register.html", prefill=prefill)


@app.get("/api/username-available")
def username_available_api():
    username = request.args.get("username", "").strip().lower()
    if len(username) < 3:
        return jsonify({"ok": True, "available": False, "reason": "too_short"})
    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE lower(username) = ? LIMIT 1",
            (username,),
        ).fetchone()
    return jsonify({"ok": True, "available": exists is None, "reason": "taken" if exists else ""})


@app.post("/register")
def register_submit():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    session["register_prefill"] = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "phone": phone,
    }
    if (
        len(username) < 3
        or not full_name
        or "@" not in email
        or not phone
        or not is_strong_registration_password(password)
        or password != password_confirm
    ):
        flash(t("msg_register_bad"), "error")
        return redirect(url_for("register_page", lang=get_lang()))
    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute(
            "SELECT 1 FROM users WHERE lower(username) = ? LIMIT 1",
            (username,),
        ).fetchone()
        if existing is not None:
            flash(t("msg_register_exists"), "error")
            return redirect(url_for("register_page", lang=get_lang()))
        try:
            conn.execute(
                """
                INSERT INTO users (username, password_hash, full_name, email, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, generate_password_hash(password), full_name, email, phone, datetime.utcnow().isoformat()),
            )
        except sqlite3.IntegrityError:
            flash(t("msg_register_exists"), "error")
            return redirect(url_for("register_page", lang=get_lang()))
    session.pop("register_prefill", None)
    flash(t("msg_register_ok"), "ok")
    return redirect(url_for("login_page", lang=get_lang()))


@app.post("/logout")
def logout_submit():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("home", lang=get_lang()))


@app.get("/dashboard")
def dashboard_page():
    user_id = get_current_user_id()
    if user_id <= 0:
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    selected_type = request.args.get("type", "all").strip().lower()
    if selected_type not in {"all", "coffee", "katina", "tarot"}:
        selected_type = "all"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        user_row = conn.execute(
            "SELECT username, full_name, email, phone FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if user_row is None:
            session.pop("user_id", None)
            session.pop("username", None)
            flash(t("msg_auth_required"), "error")
            return redirect(url_for("login_page", lang=get_lang()))
        coffee_rows = conn.execute(
            """
            SELECT id, 'coffee' AS reading_type, reader_name, question, ai_status, ai_reading, ai_published, created_at,
                   COALESCE(
                     (SELECT status FROM payment_requests p
                      WHERE p.request_kind = 'coffee' AND p.request_id = coffee_requests.id
                      ORDER BY p.id DESC LIMIT 1),
                     'pending'
                   ) AS order_status
            FROM coffee_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()
        card_rows = conn.execute(
            """
            SELECT id, reading_type, reader_name, question, ai_status, ai_reading, ai_published, created_at,
                   COALESCE(
                     (SELECT status FROM payment_requests p
                      WHERE p.request_kind = 'card' AND p.request_id = card_requests.id
                      ORDER BY p.id DESC LIMIT 1),
                     'pending'
                   ) AS order_status
            FROM card_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()

    merged: list[dict[str, str]] = []
    for row in coffee_rows:
        merged.append(
            {
                "id": str(row["id"]),
                "request_kind": "coffee",
                "type": str(row["reading_type"]),
                "reader_name": str(row["reader_name"]),
                "question": str(row["question"]),
                "result": str(row["ai_reading"]) if (str(row["ai_status"]) == "ready" and int(row["ai_published"] or 0) == 1) else t("ai_result_review"),
                "created_at": str(row["created_at"]),
                "order_status": normalize_order_status(str(row["order_status"])),
                "timeline": build_customer_timeline(
                    str(row["order_status"]),
                    str(row["ai_status"]),
                    int(row["ai_published"] or 0),
                ),
            }
        )
    for row in card_rows:
        merged.append(
            {
                "id": str(row["id"]),
                "request_kind": "card",
                "type": str(row["reading_type"]),
                "reader_name": str(row["reader_name"]),
                "question": str(row["question"]),
                "result": str(row["ai_reading"]) if (str(row["ai_status"]) == "ready" and int(row["ai_published"] or 0) == 1) else t("ai_result_review"),
                "created_at": str(row["created_at"]),
                "order_status": normalize_order_status(str(row["order_status"])),
                "timeline": build_customer_timeline(
                    str(row["order_status"]),
                    str(row["ai_status"]),
                    int(row["ai_published"] or 0),
                ),
            }
        )

    merged.sort(key=lambda x: x["created_at"], reverse=True)
    if selected_type != "all":
        merged = [row for row in merged if row["type"] == selected_type]
    merged = merged[:20]
    return render_template("dashboard.html", rows=merged, user=user_row, selected_type=selected_type)


@app.get("/reading/<request_kind>/<int:request_id>")
def customer_reading_page(request_kind: str, request_id: int):
    if request_kind not in {"coffee", "card"}:
        flash(t("msg_bad_type"), "error")
        return redirect(url_for("dashboard_page", lang=get_lang()))

    user_id = get_current_user_id()
    if user_id <= 0:
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if request_kind == "coffee":
            row = conn.execute(
                """
                SELECT id, 'coffee' AS reading_type, reader_name, question, ai_status, ai_reading, ai_published, created_at,
                       COALESCE(
                         (SELECT status FROM payment_requests p
                          WHERE p.request_kind = 'coffee' AND p.request_id = coffee_requests.id
                          ORDER BY p.id DESC LIMIT 1),
                         'pending'
                       ) AS order_status
                FROM coffee_requests
                WHERE id = ? AND user_id = ?
                LIMIT 1
                """,
                (request_id, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT id, reading_type, reader_name, question, ai_status, ai_reading, ai_published, created_at,
                       COALESCE(
                         (SELECT status FROM payment_requests p
                          WHERE p.request_kind = 'card' AND p.request_id = card_requests.id
                          ORDER BY p.id DESC LIMIT 1),
                         'pending'
                       ) AS order_status
                FROM card_requests
                WHERE id = ? AND user_id = ?
                LIMIT 1
                """,
                (request_id, user_id),
            ).fetchone()

    if row is None:
        flash(t("msg_no_payment"), "error")
        return redirect(url_for("dashboard_page", lang=get_lang()))

    if str(row["ai_status"]) != "ready" or int(row["ai_published"] or 0) != 1 or not str(row["ai_reading"]).strip():
        flash(t("msg_reading_not_ready"), "error")
        return redirect(url_for("dashboard_page", lang=get_lang()))

    return render_template(
        "customer_reading.html",
        row=row,
        request_kind=request_kind,
        timeline=build_customer_timeline(
            str(row["order_status"]),
            str(row["ai_status"]),
            int(row["ai_published"] or 0),
        ),
    )


@app.post("/account/update")
def account_update():
    user_id = get_current_user_id()
    if user_id <= 0:
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    new_password = request.form.get("new_password", "")
    new_password_confirm = request.form.get("new_password_confirm", "")

    if not full_name:
        flash(t("msg_profile_bad_name"), "error")
        return redirect(url_for("dashboard_page", lang=get_lang()))
    if "@" not in email:
        flash(t("msg_profile_bad_email"), "error")
        return redirect(url_for("dashboard_page", lang=get_lang()))
    if not phone:
        flash(t("msg_profile_bad_phone"), "error")
        return redirect(url_for("dashboard_page", lang=get_lang()))
    if new_password:
        if len(new_password) < 4 or new_password != new_password_confirm:
            flash(t("msg_profile_bad_password"), "error")
            return redirect(url_for("dashboard_page", lang=get_lang()))

    with sqlite3.connect(DB_PATH) as conn:
        if new_password:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, email = ?, phone = ?, password_hash = ?
                WHERE id = ?
                """,
                (full_name, email, phone, generate_password_hash(new_password), user_id),
            )
        else:
            conn.execute(
                """
                UPDATE users
                SET full_name = ?, email = ?, phone = ?
                WHERE id = ?
                """,
                (full_name, email, phone, user_id),
            )
    flash(t("msg_profile_saved"), "ok")
    return redirect(url_for("dashboard_page", lang=get_lang()))


@app.get("/agb")
def agb_page():
    return render_template("agb.html")


@app.get("/impressum")
def impressum_page():
    return render_template("impressum.html")


@app.get("/datenschutz")
def datenschutz_page():
    return render_template("datenschutz.html")


@app.post("/submit-coffee")
def submit_coffee():
    if not user_logged_in():
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    question = request.form.get("question", "").strip()
    reader_id = request.form.get("reader_id", "").strip()
    photos = [p for p in request.files.getlist("coffee_photos") if p and p.filename.strip()]
    lang = get_lang()
    user_id = get_current_user_id()
    profile = get_current_user_profile()
    if profile["full_name"]:
        full_name = profile["full_name"]
    if profile["phone"]:
        phone = profile["phone"]
    amount, currency = get_pricing()
    selected_reader = get_reader_by_id("coffee", reader_id)

    if not full_name or not phone or not question:
        flash(t("msg_fill_coffee"), "error")
        if reader_id:
            return redirect(url_for("coffee_reader_page", lang=get_lang(), reader_id=reader_id))
        return redirect(url_for("coffee_page", lang=get_lang()))

    if selected_reader is None:
        flash(t("msg_choose_reader"), "error")
        return redirect(url_for("coffee_page", lang=get_lang()))

    if not photos:
        flash(t("msg_need_photo"), "error")
        return redirect(url_for("coffee_reader_page", lang=get_lang(), reader_id=reader_id))

    if len(photos) > 6:
        flash(t("msg_too_many_photos", count=6), "error")
        return redirect(url_for("coffee_reader_page", lang=get_lang(), reader_id=reader_id))

    saved_paths: list[str] = []
    for photo in photos:
        if not allowed_file(photo.filename):
            flash(t("msg_bad_file"), "error")
            return redirect(url_for("coffee_reader_page", lang=get_lang(), reader_id=reader_id))
        safe_name = secure_filename(photo.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = f"{timestamp}_{safe_name}"
        save_path = UPLOAD_DIR / filename
        photo.save(save_path)
        saved_paths.append(f"uploads/{filename}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO coffee_requests (user_id, full_name, phone, question, reader_name, image_path, image_paths, ai_status, ai_reading, ai_published, ai_batch_id, ai_custom_id, created_at, paid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0)
            """,
            (
                user_id,
                full_name,
                phone,
                question,
                selected_reader["name"],
                saved_paths[0],
                json.dumps(saved_paths, ensure_ascii=False),
                "pending",
                "",
                "",
                "",
                datetime.utcnow().isoformat(),
            ),
        )
        request_id = cursor.lastrowid

    ai_status, ai_reading, ai_batch_id, ai_custom_id = generate_coffee_ai_reading(
        question,
        full_name,
        selected_reader["name"],
        saved_paths,
        lang,
    )
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE coffee_requests SET ai_status = ?, ai_reading = ?, ai_published = 0, ai_batch_id = ?, ai_custom_id = ? WHERE id = ?",
            (ai_status, ai_reading, ai_batch_id, ai_custom_id, int(request_id)),
        )
    token_input, token_output, token_total, cost_estimate, quality_flags = estimate_ai_observability(
        reading_type="coffee",
        question=question,
        ai_reading=ai_reading,
        image_count=len(saved_paths),
        model_name=OPENAI_MODEL,
    )
    log_reading_event(
        request_kind="coffee",
        request_id=int(request_id),
        reading_type="coffee",
        customer_name=full_name,
        reader_name=selected_reader["name"],
        actor="system-ai",
        action="generated",
        ai_status=ai_status,
        ai_reading=ai_reading,
        model_name=OPENAI_MODEL,
        token_input=(token_input if ai_status in {"ready", "batched"} else 0),
        token_output=(token_output if ai_status == "ready" else 0),
        token_total=(token_total if ai_status in {"ready", "batched"} else 0),
        cost_estimate=(cost_estimate if ai_status in {"ready", "batched"} else 0.0),
        quality_flags=quality_flags,
    )

    create_payment_record("coffee", int(request_id), full_name, phone, amount, currency, user_id=user_id)

    flash(t("msg_coffee_ok"), "ok")
    return redirect(
        url_for("payment_page", request_kind="coffee", request_id=request_id, lang=get_lang())
    )


@app.post("/submit-cards")
def submit_cards():
    if not user_logged_in():
        flash(t("msg_auth_required"), "error")
        return redirect(url_for("login_page", lang=get_lang()))
    reading_type = request.form.get("reading_type", "").strip()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    question = request.form.get("question", "").strip()
    selected_cards = request.form.get("selected_cards", "").strip()
    reader_id = request.form.get("reader_id", "").strip()
    lang = get_lang()
    user_id = get_current_user_id()
    profile = get_current_user_profile()
    if profile["full_name"]:
        full_name = profile["full_name"]
    if profile["phone"]:
        phone = profile["phone"]
    amount, currency = get_pricing()

    if reading_type not in {"katina", "tarot"}:
        flash(t("msg_bad_type"), "error")
        return redirect(url_for("katina_page", lang=get_lang()))

    selected_reader = get_reader_by_id(reading_type, reader_id)
    if selected_reader is None:
        flash(t("msg_choose_reader"), "error")
        return redirect(url_for("katina_page" if reading_type == "katina" else "tarot_page", lang=get_lang()))

    if not full_name or not phone or not question or not selected_cards:
        flash(t("msg_fill_card"), "error")
        if reading_type == "katina":
            return redirect(url_for("katina_reader_page", lang=get_lang(), reader_id=reader_id))
        return redirect(url_for("tarot_reader_page", lang=get_lang(), reader_id=reader_id))

    expected_count = EXPECTED_CARD_COUNT.get(reading_type)
    try:
        parsed = json.loads(selected_cards)
        if not isinstance(parsed, list) or len(parsed) != expected_count:
            raise ValueError
    except ValueError:
        flash(t("msg_need_cards", count=expected_count), "error")
        if reading_type == "katina":
            return redirect(url_for("katina_reader_page", lang=get_lang(), reader_id=reader_id))
        return redirect(url_for("tarot_reader_page", lang=get_lang(), reader_id=reader_id))

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO card_requests (user_id, reading_type, full_name, phone, question, reader_name, selected_cards, ai_status, ai_reading, ai_published, ai_batch_id, ai_custom_id, created_at, paid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0)
            """,
            (
                user_id,
                reading_type,
                full_name,
                phone,
                question,
                selected_reader["name"],
                selected_cards,
                "pending",
                "",
                "",
                "",
                datetime.utcnow().isoformat(),
            ),
        )
        request_id = cursor.lastrowid

    ai_status, ai_reading, ai_batch_id, ai_custom_id = generate_card_ai_reading(
        reading_type,
        question,
        full_name,
        selected_reader["name"],
        selected_cards,
        lang,
    )
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE card_requests SET ai_status = ?, ai_reading = ?, ai_published = 0, ai_batch_id = ?, ai_custom_id = ? WHERE id = ?",
            (ai_status, ai_reading, ai_batch_id, ai_custom_id, int(request_id)),
        )
    token_input, token_output, token_total, cost_estimate, quality_flags = estimate_ai_observability(
        reading_type=reading_type,
        question=question,
        ai_reading=ai_reading,
        selected_cards_raw=selected_cards,
        model_name=OPENAI_MODEL,
    )
    log_reading_event(
        request_kind="card",
        request_id=int(request_id),
        reading_type=reading_type,
        customer_name=full_name,
        reader_name=selected_reader["name"],
        actor="system-ai",
        action="generated",
        ai_status=ai_status,
        ai_reading=ai_reading,
        model_name=OPENAI_MODEL,
        token_input=(token_input if ai_status in {"ready", "batched"} else 0),
        token_output=(token_output if ai_status == "ready" else 0),
        token_total=(token_total if ai_status in {"ready", "batched"} else 0),
        cost_estimate=(cost_estimate if ai_status in {"ready", "batched"} else 0.0),
        quality_flags=quality_flags,
    )

    create_payment_record("card", int(request_id), full_name, phone, amount, currency, user_id=user_id)

    flash(t("msg_card_ok"), "ok")
    return redirect(url_for("payment_page", request_kind="card", request_id=request_id, lang=get_lang()))


@app.get("/payment/<request_kind>/<int:request_id>")
def payment_page(request_kind: str, request_id: int):
    if request_kind not in {"coffee", "card"}:
        flash(t("msg_bad_payment"), "error")
        return redirect(url_for("home", lang=get_lang()))

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM payment_requests
            WHERE request_kind = ? AND request_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (request_kind, request_id),
        ).fetchone()

        feedback_row = conn.execute(
            """
            SELECT rating, comment
            FROM reader_feedback
            WHERE request_kind = ? AND request_id = ?
            """,
            (request_kind, request_id),
        ).fetchone()

        if request_kind == "coffee":
            req = conn.execute(
                "SELECT reader_name, ai_status, ai_reading, ai_published, ai_batch_id, ai_custom_id FROM coffee_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
            reading_type = "coffee"
        else:
            req = conn.execute(
                "SELECT reading_type, reader_name, ai_status, ai_reading, ai_published, ai_batch_id, ai_custom_id FROM card_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
            reading_type = str(req["reading_type"]) if req else "tarot"

    if row is None or req is None:
        flash(t("msg_no_payment"), "error")
        return redirect(url_for("home", lang=get_lang()))

    ai_status = str(req["ai_status"])
    ai_reading = str(req["ai_reading"])
    ai_published = int(req["ai_published"] or 0)
    ai_batch_id = str(req["ai_batch_id"])
    ai_custom_id = str(req["ai_custom_id"])
    payment_state = request.args.get("payment", "").strip().lower()
    if payment_state not in {"success", "cancel"}:
        payment_state = ""

    if ai_status == "batched" and ai_batch_id and ai_custom_id:
        new_status, new_reading = resolve_openai_batch_result(ai_batch_id, ai_custom_id)
        if new_status != ai_status or (new_status == "ready" and new_reading and new_reading != ai_reading):
            table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    f"UPDATE {table_name} SET ai_status = ?, ai_reading = ? WHERE id = ?",
                    (new_status, new_reading, request_id),
                )
            ai_status = new_status
            ai_reading = new_reading

    reader_name = str(req["reader_name"])
    reader_id = get_reader_id_by_name(reading_type, reader_name)
    stripe_enabled = PAYMENT_PROVIDER == "stripe" and bool(STRIPE_SECRET_KEY)
    can_view_reading = bool(ai_status == "ready" and ai_reading and ai_published == 1)
    return render_template(
        "payment.html",
        row=row,
        payment_link=PAYMENT_LINK,
        payment_provider=PAYMENT_PROVIDER,
        stripe_enabled=stripe_enabled,
        payment_state=payment_state,
        reading_type=reading_type,
        reader_name=reader_name,
        reader_id=reader_id,
        feedback_row=feedback_row,
        ai_status=ai_status,
        ai_reading=ai_reading,
        ai_published=ai_published,
        can_view_reading=can_view_reading,
    )


@app.post("/payment/checkout/<request_kind>/<int:request_id>")
def start_checkout(request_kind: str, request_id: int):
    if request_kind not in {"coffee", "card"}:
        flash(t("msg_bad_payment"), "error")
        return redirect(url_for("home", lang=get_lang()))
    if PAYMENT_PROVIDER != "stripe" or not STRIPE_SECRET_KEY:
        flash("Ödeme sağlayıcısı yapılandırılmamış.", "error")
        return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))
    if not STRIPE_SECRET_KEY.startswith("sk_"):
        flash("Stripe gizli anahtarı hatalı. Yönetici ayarları kontrol etmeli.", "error")
        return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, amount, currency, status
            FROM payment_requests
            WHERE request_kind = ? AND request_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (request_kind, request_id),
        ).fetchone()
    if row is None:
        flash(t("msg_no_payment"), "error")
        return redirect(url_for("home", lang=get_lang()))
    if str(row["status"]) == "paid":
        flash("Bu ödeme zaten tamamlandı.", "ok")
        return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))

    base_url = request.url_root.rstrip("/")
    payment_url = url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang(), _external=False)
    success_url = f"{base_url}{payment_url}?payment=success"
    cancel_url = f"{base_url}{payment_url}?payment=cancel"
    stripe_error_message = ""
    try:
        checkout_url = stripe_create_checkout_session(
            amount=int(row["amount"]),
            currency=str(row["currency"]),
            request_kind=request_kind,
            request_id=request_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )
    except Exception as exc:
        app.logger.exception(
            "Stripe checkout session failed: kind=%s request_id=%s amount=%s currency=%s",
            request_kind,
            request_id,
            int(row["amount"]),
            str(row["currency"]),
        )
        stripe_error_message = str(exc)[:220]
        checkout_url = ""
    if not checkout_url:
        if stripe_error_message:
            flash(f"Stripe hata: {stripe_error_message}", "error")
        else:
            flash("Stripe yanıtı geçersiz (checkout URL alınamadı).", "error")
        flash("Ödeme oturumu başlatılamadı. Lütfen daha sonra tekrar deneyin.", "error")
        return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))
    return render_template(
        "checkout_redirect.html",
        checkout_url=checkout_url,
    )


@app.post("/webhook/stripe")
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        return {"ok": False}, 400
    raw_body = request.get_data(cache=False, as_text=False)
    signature = request.headers.get("Stripe-Signature", "")
    if not verify_stripe_signature(raw_body, signature):
        return {"ok": False}, 400

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except ValueError:
        return {"ok": False}, 400

    event_type = str(event.get("type", ""))
    data_obj = event.get("data", {}).get("object", {})
    if not isinstance(data_obj, dict):
        return {"ok": True}

    if event_type == "checkout.session.completed":
        metadata = data_obj.get("metadata", {})
        if isinstance(metadata, dict):
            request_kind = str(metadata.get("request_kind", ""))
            request_id_raw = str(metadata.get("request_id", "0"))
            try:
                request_id = int(request_id_raw)
            except ValueError:
                request_id = 0
            if request_kind in {"coffee", "card"} and request_id > 0:
                table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        """
                        UPDATE payment_requests
                        SET status = 'paid'
                        WHERE request_kind = ? AND request_id = ?
                        """,
                        (request_kind, request_id),
                    )
                    conn.execute(
                        f"UPDATE {table_name} SET paid = 1 WHERE id = ?",
                        (request_id,),
                    )
    return {"ok": True}


@app.post("/rate-reader")
def rate_reader():
    request_kind = request.form.get("request_kind", "").strip()
    request_id_raw = request.form.get("request_id", "").strip()
    rating_raw = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    if request_kind not in {"coffee", "card"} or not request_id_raw:
        flash(t("rate_error"), "error")
        return redirect(url_for("home", lang=get_lang()))

    try:
        request_id = int(request_id_raw)
        rating = float(rating_raw)
    except ValueError:
        flash(t("rate_error"), "error")
        return redirect(url_for("home", lang=get_lang()))

    if rating < 3.0 or rating > 4.5:
        flash(t("rate_error"), "error")
        return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        payment = conn.execute(
            """
            SELECT full_name FROM payment_requests
            WHERE request_kind = ? AND request_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (request_kind, request_id),
        ).fetchone()

        if payment is None:
            flash(t("rate_error"), "error")
            return redirect(url_for("home", lang=get_lang()))

        if request_kind == "coffee":
            req = conn.execute("SELECT reader_name FROM coffee_requests WHERE id = ?", (request_id,)).fetchone()
            reading_type = "coffee"
        else:
            req = conn.execute("SELECT reading_type, reader_name FROM card_requests WHERE id = ?", (request_id,)).fetchone()
            reading_type = str(req["reading_type"]) if req else "tarot"

        if req is None:
            flash(t("rate_error"), "error")
            return redirect(url_for("home", lang=get_lang()))

        reader_name = str(req["reader_name"])
        reader_id = get_reader_id_by_name(reading_type, reader_name)
        if not reader_id:
            flash(t("rate_error"), "error")
            return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))

        conn.execute(
            """
            INSERT INTO reader_feedback
            (request_kind, request_id, reading_type, reader_id, reader_name, full_name, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_kind, request_id)
            DO UPDATE SET rating = excluded.rating, comment = excluded.comment, created_at = excluded.created_at
            """,
            (
                request_kind,
                request_id,
                reading_type,
                reader_id,
                reader_name,
                str(payment["full_name"]),
                rating,
                comment,
                datetime.utcnow().isoformat(),
            ),
        )

    flash(t("rate_done"), "ok")
    return redirect(url_for("payment_page", request_kind=request_kind, request_id=request_id, lang=get_lang()))


@app.post("/admin/login")
def admin_login():
    ip = get_client_ip()
    if is_auth_rate_limited("admin_login", ip, max_attempts=5, window_seconds=30 * 60):
        flash(t("msg_too_many_attempts", minutes=30), "error")
        return redirect(url_for("admin"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if is_auth_rate_limited("admin_login_user", username or "-", max_attempts=8, window_seconds=30 * 60):
        flash("Bu admin hesabı için çok fazla deneme var. 30 dakika sonra tekrar deneyin.", "error")
        return redirect(url_for("admin"))
    if is_auth_rate_limited("admin_login_combo", f"{ip}|{username}", max_attempts=6, window_seconds=30 * 60):
        flash("Bu kullanıcı/IP kombinasyonu geçici olarak kilitlendi. 30 dakika sonra tekrar deneyin.", "error")
        return redirect(url_for("admin"))

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        clear_auth_failures("admin_login", ip)
        clear_auth_failures("admin_login_user", username or "-")
        clear_auth_failures("admin_login_combo", f"{ip}|{username}")
        session["is_admin"] = True
        session["admin_username"] = username
        return redirect(url_for("admin"))
    record_auth_failure("admin_login", ip)
    record_auth_failure("admin_login_user", username or "-")
    record_auth_failure("admin_login_combo", f"{ip}|{username}")
    flash("Admin kullanıcı adı veya şifresi hatalı.", "error")
    return redirect(url_for("admin"))


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin"))


@app.post("/admin/mark-paid/<request_kind>/<int:request_id>")
def mark_paid(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))

    set_order_status(request_kind, request_id, "paid")
    flash("Ödeme durumu güncellendi.", "ok")
    return redirect(url_for("admin"))


@app.post("/admin/set-status/<request_kind>/<int:request_id>/<new_status>")
def admin_set_status(request_kind: str, request_id: int, new_status: str):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))
    target_status = normalize_order_status(new_status)
    current_status = get_current_order_status(request_kind, request_id)
    set_order_status(request_kind, request_id, target_status)
    if target_status == "completed":
        delivered, reason = notify_reading_completed(request_kind, request_id)
        if delivered:
            flash("Durum tamamlandı ve müşteriye e-posta bildirimi gönderildi.", "ok")
        else:
            flash(f"Durum tamamlandı. E-posta bildirimi gönderilemedi: {reason}", "error")
    else:
        flash(f"Durum güncellendi: {target_status}", "ok")
    return redirect(url_for("admin"))


@app.post("/admin/resend-completed-email/<request_kind>/<int:request_id>")
def admin_resend_completed_email(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))
    delivered, reason = notify_reading_completed(request_kind, request_id)
    if delivered:
        flash("Müşteriye e-posta tekrar gönderildi.", "ok")
    else:
        flash(f"E-posta tekrar gönderilemedi: {reason}", "error")
    return redirect(url_for("admin"))


def parse_bulk_selected_items(raw_items: list[str]) -> list[tuple[str, int]]:
    selected: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for raw in raw_items:
        item = str(raw or "").strip().lower()
        if ":" not in item:
            continue
        request_kind, raw_id = item.split(":", 1)
        if request_kind not in {"coffee", "card"}:
            continue
        try:
            request_id = int(raw_id)
        except ValueError:
            continue
        key = (request_kind, request_id)
        if key in seen:
            continue
        seen.add(key)
        selected.append(key)
    return selected


def delete_request_with_related(request_kind: str, request_id: int) -> tuple[bool, str]:
    if request_kind not in {"coffee", "card"}:
        return False, "Geçersiz talep türü."
    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    label = "Kahve" if request_kind == "coffee" else "Kart"

    with sqlite3.connect(DB_PATH) as conn:
        exists = conn.execute(f"SELECT id FROM {table_name} WHERE id = ?", (request_id,)).fetchone()
        if not exists:
            return False, f"{label} falı kaydı bulunamadı."

        deleted_payments = conn.execute(
            "DELETE FROM payment_requests WHERE request_kind = ? AND request_id = ?",
            (request_kind, request_id),
        ).rowcount
        deleted_feedback = conn.execute(
            "DELETE FROM reader_feedback WHERE request_kind = ? AND request_id = ?",
            (request_kind, request_id),
        ).rowcount
        try:
            deleted_audit = conn.execute(
                "DELETE FROM reading_audit WHERE request_kind = ? AND request_id = ?",
                (request_kind, request_id),
            ).rowcount
        except sqlite3.OperationalError:
            deleted_audit = 0
        deleted_request = conn.execute(
            f"DELETE FROM {table_name} WHERE id = ?",
            (request_id,),
        ).rowcount

    return (
        True,
        f"{label} falı kaydı silindi. Talep: {deleted_request}, Ödeme: {deleted_payments}, Değerlendirme: {deleted_feedback}, Log: {deleted_audit}",
    )


def approve_reading_request(request_kind: str, request_id: int) -> tuple[bool, str]:
    if request_kind not in {"coffee", "card"}:
        return False, "Geçersiz talep türü."
    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if request_kind == "coffee":
            row = conn.execute(
                """
                SELECT id, full_name, reader_name, question, ai_status, ai_reading
                FROM coffee_requests
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
            reading_type = "coffee"
            selected_cards = ""
        else:
            row = conn.execute(
                """
                SELECT id, full_name, reader_name, question, reading_type, selected_cards, ai_status, ai_reading
                FROM card_requests
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
            reading_type = str((row["reading_type"] if row else "tarot") or "tarot")
            selected_cards = str((row["selected_cards"] if row else "") or "")

    if row is None:
        return False, "Talep bulunamadı."

    reading_text = str(row["ai_reading"] or "").strip()
    if str(row["ai_status"] or "") != "ready" or not reading_text:
        return False, "Yorum hazır değil. Önce yorum üretilmeli."

    quality_issues = validate_reading_quality(reading_text)
    if quality_issues:
        return False, "Yorum kalite kontrolünden geçmedi: " + " | ".join(quality_issues)

    current_status = get_current_order_status(request_kind, request_id)
    if current_status in {"pending", "paid"}:
        set_order_status(request_kind, request_id, "in_progress")

    token_input, token_output, token_total, _, quality_flags = estimate_ai_observability(
        reading_type=reading_type,
        question=str(row["question"] or ""),
        ai_reading=reading_text,
        selected_cards_raw=selected_cards,
        model_name=OPENAI_MODEL,
    )
    log_reading_event(
        request_kind=request_kind,
        request_id=request_id,
        reading_type=reading_type,
        customer_name=str(row["full_name"] or ""),
        reader_name=str(row["reader_name"] or ""),
        actor=get_admin_actor(),
        action="approved",
        ai_status="ready",
        ai_reading="Toplu onay verildi.",
        model_name=OPENAI_MODEL,
        token_input=token_input,
        token_output=token_output,
        token_total=token_total,
        cost_estimate=0.0,
        quality_flags=quality_flags,
    )
    return True, "Yorum onaylandı."


def publish_reading_to_customer(request_kind: str, request_id: int) -> tuple[str, str]:
    if request_kind not in {"coffee", "card"}:
        return "error", "Geçersiz işlem."
    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        select_type_sql = "'coffee' AS reading_type" if request_kind == "coffee" else "reading_type"
        row = conn.execute(
            f"SELECT ai_status, ai_reading, ai_published, full_name, reader_name, {select_type_sql} FROM {table_name} WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            return "error", "Talep bulunamadı."
        if int(row["ai_published"] or 0) == 1:
            return "skipped", "Bu yorum zaten müşteriye gönderilmiş."

        reading_text = str(row["ai_reading"] or "").strip()
        if str(row["ai_status"]) != "ready" or not reading_text:
            return "error", "Yorum hazır değil. Önce yorum üretilmeli."
        quality_issues = validate_reading_quality(reading_text)
        if quality_issues:
            return "error", "Yorum kalite kontrolünden geçmedi: " + " | ".join(quality_issues)

        published_at = datetime.utcnow().isoformat()
        published_by = get_admin_actor()
        conn.execute(
            f"UPDATE {table_name} SET ai_published = 1, ai_published_at = ?, ai_published_by = ? WHERE id = ?",
            (published_at, published_by, request_id),
        )

    reading_type = "coffee" if request_kind == "coffee" else str(row["reading_type"] or "tarot")
    log_reading_event(
        request_kind=request_kind,
        request_id=request_id,
        reading_type=reading_type,
        customer_name=str(row["full_name"] or ""),
        reader_name=str(row["reader_name"] or ""),
        actor=published_by,
        action="published",
        ai_status="ready",
        ai_reading=reading_text,
        model_name=OPENAI_MODEL,
        token_input=estimate_tokens_from_text(reading_text),
        token_output=estimate_tokens_from_text(reading_text),
        token_total=estimate_tokens_from_text(reading_text) * 2,
        cost_estimate=0.0,
        quality_flags=("quality_risk" if validate_reading_quality(reading_text) else ""),
    )
    mail_ok, mail_reason = notify_reading_completed(request_kind, request_id)
    log_reading_event(
        request_kind=request_kind,
        request_id=request_id,
        reading_type=reading_type,
        customer_name=str(row["full_name"] or ""),
        reader_name=str(row["reader_name"] or ""),
        actor=published_by,
        action=("mail_sent" if mail_ok else "mail_failed"),
        ai_status=("sent" if mail_ok else "failed"),
        ai_reading=("Yayın sonrası bildirim e-postası gönderildi." if mail_ok else f"Mail gönderilemedi: {mail_reason}"),
        model_name=OPENAI_MODEL,
        token_input=0,
        token_output=0,
        token_total=0,
        cost_estimate=0.0,
        quality_flags="",
    )
    if mail_ok:
        return "success", "Yorum müşteriye yayınlandı ve bilgilendirme e-postası gönderildi."
    return "warning", f"Yorum müşteriye yayınlandı. E-posta gönderilemedi: {mail_reason}"


@app.post("/admin/delete-request/coffee/<int:request_id>")
def admin_delete_coffee_request(request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    ok, message = delete_request_with_related("coffee", request_id)
    flash(message, "ok" if ok else "error")
    return redirect(request.referrer or url_for("admin"))


@app.post("/admin/delete-request/card/<int:request_id>")
def admin_delete_card_request(request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    ok, message = delete_request_with_related("card", request_id)
    flash(message, "ok" if ok else "error")
    return redirect(request.referrer or url_for("admin"))


@app.post("/admin/delete-audit/<int:audit_id>")
def admin_delete_audit(audit_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))

    try:
        with sqlite3.connect(DB_PATH) as conn:
            deleted = conn.execute("DELETE FROM reading_audit WHERE id = ?", (audit_id,)).rowcount
    except sqlite3.OperationalError:
        flash("Yorum geçmişi tablosu bulunamadı.", "error")
        return redirect(request.referrer or url_for("admin"))

    if deleted:
        flash("Yorum geçmişi kaydı silindi.", "ok")
    else:
        flash("Yorum geçmişi kaydı bulunamadı.", "error")
    return redirect(request.referrer or url_for("admin"))


def regenerate_ai_for_request(request_kind: str, request_id: int, lang: str) -> tuple[bool, str]:
    reading_type = "coffee"
    customer_name = ""
    reader_name = ""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if request_kind == "coffee":
            row = conn.execute(
                """
                SELECT question, full_name, reader_name, image_path, image_paths
                FROM coffee_requests
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT reading_type, question, full_name, reader_name, selected_cards
                FROM card_requests
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
    if row is None:
        return False, "Talep bulunamadı"
    if request_kind == "coffee":
        reading_type = "coffee"
    else:
        reading_type = str(row["reading_type"] or "tarot")
    customer_name = str(row["full_name"] or "")
    reader_name = str(row["reader_name"] or "")

    if request_kind == "coffee":
        image_paths = parse_json_list(str(row["image_paths"] or "[]"))
        if not image_paths and str(row["image_path"] or "").strip():
            image_paths = [str(row["image_path"]).strip()]
        ai_status, ai_reading, ai_batch_id, ai_custom_id = generate_coffee_ai_reading(
            str(row["question"] or ""),
            str(row["full_name"] or ""),
            str(row["reader_name"] or "Falcı"),
            image_paths,
            lang,
        )
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                UPDATE coffee_requests
                SET ai_status = ?, ai_reading = ?, ai_published = 0, ai_batch_id = ?, ai_custom_id = ?
                WHERE id = ?
                """,
                (ai_status, ai_reading, ai_batch_id, ai_custom_id, request_id),
            )
        token_input, token_output, token_total, cost_estimate, quality_flags = estimate_ai_observability(
            reading_type="coffee",
            question=str(row["question"] or ""),
            ai_reading=ai_reading,
            image_count=len(image_paths),
            model_name=OPENAI_MODEL,
        )
    else:
        ai_status, ai_reading, ai_batch_id, ai_custom_id = generate_card_ai_reading(
            str(row["reading_type"] or "tarot"),
            str(row["question"] or ""),
            str(row["full_name"] or ""),
            str(row["reader_name"] or "Falcı"),
            str(row["selected_cards"] or "[]"),
            lang,
        )
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                UPDATE card_requests
                SET ai_status = ?, ai_reading = ?, ai_published = 0, ai_batch_id = ?, ai_custom_id = ?
                WHERE id = ?
                """,
                (ai_status, ai_reading, ai_batch_id, ai_custom_id, request_id),
            )
        token_input, token_output, token_total, cost_estimate, quality_flags = estimate_ai_observability(
            reading_type=reading_type,
            question=str(row["question"] or ""),
            ai_reading=ai_reading,
            selected_cards_raw=str(row["selected_cards"] or ""),
            model_name=OPENAI_MODEL,
        )
    log_reading_event(
        request_kind=request_kind,
        request_id=request_id,
        reading_type=reading_type,
        customer_name=customer_name,
        reader_name=reader_name,
        actor=get_admin_actor(),
        action="regenerated",
        ai_status=ai_status,
        ai_reading=ai_reading,
        model_name=OPENAI_MODEL,
        token_input=(token_input if ai_status in {"ready", "batched"} else 0),
        token_output=(token_output if ai_status == "ready" else 0),
        token_total=(token_total if ai_status in {"ready", "batched"} else 0),
        cost_estimate=(cost_estimate if ai_status in {"ready", "batched"} else 0.0),
        quality_flags=quality_flags,
    )

    if ai_status == "ready":
        return True, "Yorum yeniden üretildi. Müşteriye göndermek için yayınlayın."
    if ai_status == "batched":
        return True, "Yorum kuyruğa alındı (batch). Hazır olunca yayınlayabilirsiniz."
    if ai_status == "no_key":
        return False, "OpenAI anahtarı eksik (OPENAI_API_KEY)."
    return False, f"Yorum üretilemedi: {ai_status}"


def validate_reading_quality(text: str) -> list[str]:
    issues: list[str] = []
    body = (text or "").strip()
    if len(body) < 320:
        issues.append("Yorum çok kısa görünüyor (en az 320 karakter önerilir).")

    lowered = body.lower()
    if "yapay zeka" in lowered or "as an ai" in lowered or "ki als ki" in lowered:
        issues.append("Yorumda yapay zeka ifadesi geçiyor.")

    if re.search(r"\b(?:tarot|katina)-kart-\d+\b", lowered):
        issues.append("Yorumda teknik kart ID görünüyor (ör: tarot-kart-58).")

    signature_markers = ("Falcı:", "Reader:", "Kaffeesatzleserin:", "Kartenlegerin:")
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    last_line = lines[-1] if lines else ""
    plain_name_signature = bool(last_line and 1 <= len(last_line.split()) <= 3 and len(last_line) <= 32)
    if (not any(marker in body for marker in signature_markers)) and (not plain_name_signature):
        issues.append("Yorum sonunda falcı imzası eksik.")

    return issues


def compute_quality_score(text: str) -> tuple[int, str]:
    body = (text or "").strip()
    if not body:
        return 0, "weak"
    score = 70
    length = len(body)
    if length < 450:
        score -= 15
    elif length > 2600:
        score -= 10
    else:
        score += 8
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    if len(paragraphs) >= 4:
        score += 6
    recommendation_hits = len(re.findall(r"\b(öneri|tavsiye|adım|suggestion|recommendation|empfehlung)\b", body.lower()))
    if recommendation_hits >= 2:
        score += 6
    issues = validate_reading_quality(body)
    score -= min(30, len(issues) * 12)
    score = max(0, min(100, score))
    if score >= 85:
        return score, "excellent"
    if score >= 70:
        return score, "good"
    if score >= 55:
        return score, "fair"
    return score, "weak"


@app.post("/admin/publish-reading/<request_kind>/<int:request_id>")
def admin_publish_reading(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))
    confirm_publish = request.form.get("confirm_publish")
    if confirm_publish is not None and str(confirm_publish).strip() != "1":
        flash("Müşteriye gönderim iptal edildi.", "error")
        return redirect(url_for("admin_edit_reading", request_kind=request_kind, request_id=request_id))

    status, message = publish_reading_to_customer(request_kind, request_id)
    flash(message, "ok" if status in {"success", "skipped"} else "error")
    return redirect(url_for("admin"))


@app.post("/admin/bulk-action")
def admin_bulk_action():
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))

    action = request.form.get("bulk_action", "").strip().lower()
    if action not in {"regenerate", "approve", "publish", "delete"}:
        flash("Geçersiz toplu işlem.", "error")
        return redirect(request.referrer or url_for("admin"))

    selected = parse_bulk_selected_items(request.form.getlist("selected"))
    if not selected:
        flash("Toplu işlem için en az bir fal seçmelisiniz.", "error")
        return redirect(request.referrer or url_for("admin"))
    if len(selected) > 200:
        flash("Aynı anda en fazla 200 kayıt işlenebilir.", "error")
        return redirect(request.referrer or url_for("admin"))

    stats = {"success": 0, "warning": 0, "skipped": 0, "error": 0}
    errors: list[str] = []
    lang = get_lang()

    for request_kind, request_id in selected:
        status = "error"
        message = "Bilinmeyen hata"
        if action == "regenerate":
            ok, message = regenerate_ai_for_request(request_kind, request_id, lang)
            status = "success" if ok else "error"
        elif action == "approve":
            ok, message = approve_reading_request(request_kind, request_id)
            status = "success" if ok else "error"
        elif action == "publish":
            status, message = publish_reading_to_customer(request_kind, request_id)
        elif action == "delete":
            ok, message = delete_request_with_related(request_kind, request_id)
            status = "success" if ok else "error"

        stats[status] = stats.get(status, 0) + 1
        if status == "error":
            errors.append(f"{request_kind}-{request_id}: {message}")

    action_label = {
        "regenerate": "yorumla",
        "approve": "onayla",
        "publish": "gönder",
        "delete": "sil",
    }[action]
    flash(
        f"Toplu işlem ({action_label}) tamamlandı. Başarılı: {stats['success']}, Uyarı: {stats['warning']}, Atlandı: {stats['skipped']}, Hata: {stats['error']}.",
        "ok" if stats["error"] == 0 else "error",
    )
    if errors:
        flash("Hata detayları: " + " | ".join(errors[:5]), "error")
    return redirect(request.referrer or url_for("admin"))


@app.post("/admin/regenerate-reading/<request_kind>/<int:request_id>")
def admin_regenerate_reading(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))
    ok, message = regenerate_ai_for_request(request_kind, request_id, get_lang())
    flash(message, "ok" if ok else "error")
    return redirect(url_for("admin"))


@app.post("/admin/save-reading/<request_kind>/<int:request_id>")
def admin_save_reading(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))

    edited = request.form.get("ai_reading", "").strip()
    if not edited:
        flash("Yorum metni boş olamaz.", "error")
        return redirect(url_for("admin"))

    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    customer_name = ""
    reader_name = ""
    reading_type = "coffee" if request_kind == "coffee" else "tarot"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            f"SELECT id, full_name, reader_name, question, {'\"\" AS selected_cards' if request_kind == 'coffee' else 'selected_cards'}, {'\"coffee\" AS reading_type' if request_kind == 'coffee' else 'reading_type'} FROM {table_name} WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            flash("Talep bulunamadı.", "error")
            return redirect(url_for("admin"))
        customer_name = str(row["full_name"] or "")
        reader_name = str(row["reader_name"] or "")
        reading_type = str(row["reading_type"] or reading_type)
        conn.execute(
            f"""
            UPDATE {table_name}
            SET ai_status = 'ready',
                ai_reading = ?,
                ai_published = 0,
                ai_batch_id = '',
                ai_custom_id = ''
            WHERE id = ?
            """,
            (edited, request_id),
        )
    token_input, token_output, token_total, _, quality_flags = estimate_ai_observability(
        reading_type=reading_type,
        question=str(row["question"] or ""),
        ai_reading=edited,
        selected_cards_raw=str(row["selected_cards"] or ""),
        model_name=OPENAI_MODEL,
    )
    log_reading_event(
        request_kind=request_kind,
        request_id=request_id,
        reading_type=reading_type,
        customer_name=customer_name,
        reader_name=reader_name,
        actor=get_admin_actor(),
        action="edited",
        ai_status="ready",
        ai_reading=edited,
        model_name=OPENAI_MODEL,
        token_input=token_input,
        token_output=token_output,
        token_total=token_total,
        cost_estimate=0.0,
        quality_flags=quality_flags,
    )
    flash("Yorum kaydedildi. Müşteriye göndermek için 'Müşteriye Gönder' butonunu kullan.", "ok")
    if request.form.get("next", "").strip() == "edit":
        return redirect(url_for("admin_edit_reading", request_kind=request_kind, request_id=request_id))
    return redirect(url_for("admin"))


@app.get("/admin/edit-reading/<request_kind>/<int:request_id>")
def admin_edit_reading(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))

    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if request_kind == "coffee":
            row = conn.execute(
                f"""
                SELECT id, full_name, phone, question, reader_name, ai_status, ai_reading, ai_published, ai_published_at, ai_published_by, created_at
                FROM {table_name}
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
        else:
            row = conn.execute(
                f"""
                SELECT id, full_name, phone, question, reader_name, reading_type, ai_status, ai_reading, ai_published, ai_published_at, ai_published_by, created_at
                FROM {table_name}
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()

    if row is None:
        flash("Talep bulunamadı.", "error")
        return redirect(url_for("admin"))

    return render_template("admin_edit_reading.html", request_kind=request_kind, row=row)


def parse_admin_filters() -> dict[str, str]:
    raw_type = request.args.get("type", "all").strip().lower()
    raw_status = request.args.get("status", "all").strip().lower()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    q = request.args.get("q", "").strip()
    audit_action = request.args.get("audit_action", "all").strip().lower()
    audit_actor = request.args.get("audit_actor", "").strip()
    audit_request = request.args.get("audit_request", "").strip().lower()
    return {
        "type": raw_type if raw_type in {"all", "coffee", "katina", "tarot"} else "all",
        "status": raw_status if raw_status in {"all", "pending", "paid", "in_progress", "completed"} else "all",
        "date_from": date_from,
        "date_to": date_to,
        "q": q,
        "audit_action": audit_action if audit_action in {"all", "generated", "regenerated", "approved", "edited", "published", "mail_sent", "mail_failed"} else "all",
        "audit_actor": audit_actor,
        "audit_request": audit_request,
    }


def build_date_range(date_from: str, date_to: str) -> tuple[str, str]:
    start = ""
    end = ""
    if date_from:
        start = f"{date_from}T00:00:00"
    if date_to:
        try:
            end_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            end = end_dt.strftime("%Y-%m-%dT00:00:00")
        except ValueError:
            end = ""
    return start, end


def fetch_filtered_admin_data(filters: dict[str, str]) -> tuple[list[sqlite3.Row], list[sqlite3.Row], list[sqlite3.Row]]:
    date_start, date_end = build_date_range(filters["date_from"], filters["date_to"])
    query = filters["q"]
    type_filter = filters["type"]
    status_filter = filters["status"]

    coffee_sql = (
        "SELECT coffee_requests.*, "
        "COALESCE((SELECT status FROM payment_requests p "
        "WHERE p.request_kind = 'coffee' AND p.request_id = coffee_requests.id "
        "ORDER BY p.id DESC LIMIT 1), 'pending') AS order_status "
        "FROM coffee_requests WHERE 1=1"
    )
    coffee_params: list[object] = []
    if type_filter in {"katina", "tarot"}:
        coffee_sql += " AND 0"
    if status_filter != "all":
        coffee_sql += (
            " AND EXISTS (SELECT 1 FROM payment_requests p "
            "WHERE p.request_kind = 'coffee' AND p.request_id = coffee_requests.id AND p.status = ?)"
        )
        coffee_params.append(status_filter)
    if date_start:
        coffee_sql += " AND created_at >= ?"
        coffee_params.append(date_start)
    if date_end:
        coffee_sql += " AND created_at < ?"
        coffee_params.append(date_end)
    if query:
        like = f"%{query}%"
        coffee_sql += " AND (full_name LIKE ? OR phone LIKE ? OR question LIKE ? OR reader_name LIKE ?)"
        coffee_params.extend([like, like, like, like])
    coffee_sql += " ORDER BY id DESC LIMIT 300"

    card_sql = (
        "SELECT card_requests.*, "
        "COALESCE((SELECT status FROM payment_requests p "
        "WHERE p.request_kind = 'card' AND p.request_id = card_requests.id "
        "ORDER BY p.id DESC LIMIT 1), 'pending') AS order_status "
        "FROM card_requests WHERE 1=1"
    )
    card_params: list[object] = []
    if type_filter in {"katina", "tarot"}:
        card_sql += " AND reading_type = ?"
        card_params.append(type_filter)
    elif type_filter == "coffee":
        card_sql += " AND 0"
    if status_filter != "all":
        card_sql += (
            " AND EXISTS (SELECT 1 FROM payment_requests p "
            "WHERE p.request_kind = 'card' AND p.request_id = card_requests.id AND p.status = ?)"
        )
        card_params.append(status_filter)
    if date_start:
        card_sql += " AND created_at >= ?"
        card_params.append(date_start)
    if date_end:
        card_sql += " AND created_at < ?"
        card_params.append(date_end)
    if query:
        like = f"%{query}%"
        card_sql += " AND (full_name LIKE ? OR phone LIKE ? OR question LIKE ? OR reader_name LIKE ?)"
        card_params.extend([like, like, like, like])
    card_sql += " ORDER BY id DESC LIMIT 300"

    payment_sql = "SELECT * FROM payment_requests WHERE 1=1"
    payment_params: list[object] = []
    if type_filter == "coffee":
        payment_sql += " AND request_kind = 'coffee'"
    elif type_filter in {"katina", "tarot"}:
        payment_sql += " AND request_kind = 'card' AND request_id IN (SELECT id FROM card_requests WHERE reading_type = ?)"
        payment_params.append(type_filter)
    if status_filter in {"pending", "paid", "in_progress", "completed"}:
        payment_sql += " AND status = ?"
        payment_params.append(status_filter)
    if date_start:
        payment_sql += " AND created_at >= ?"
        payment_params.append(date_start)
    if date_end:
        payment_sql += " AND created_at < ?"
        payment_params.append(date_end)
    if query:
        like = f"%{query}%"
        payment_sql += " AND (full_name LIKE ? OR phone LIKE ? OR request_kind LIKE ?)"
        payment_params.extend([like, like, like])
    payment_sql += " ORDER BY id DESC LIMIT 500"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        coffee_rows = conn.execute(coffee_sql, tuple(coffee_params)).fetchall()
        card_rows = conn.execute(card_sql, tuple(card_params)).fetchall()
        payment_rows = conn.execute(payment_sql, tuple(payment_params)).fetchall()
    return coffee_rows, card_rows, payment_rows


def fetch_reading_audit_rows(filters: dict[str, str]) -> list[sqlite3.Row]:
    date_start, date_end = build_date_range(filters["date_from"], filters["date_to"])
    query = filters["q"]
    type_filter = filters["type"]
    audit_action = filters.get("audit_action", "all")
    audit_actor = filters.get("audit_actor", "").strip()
    audit_request = filters.get("audit_request", "").strip().lower()
    sql = "SELECT * FROM reading_audit WHERE 1=1"
    params: list[object] = []
    if type_filter in {"coffee", "katina", "tarot"}:
        sql += " AND reading_type = ?"
        params.append(type_filter)
    if audit_action in {"generated", "regenerated", "approved", "edited", "published", "mail_sent", "mail_failed"}:
        sql += " AND action = ?"
        params.append(audit_action)
    if audit_actor:
        sql += " AND actor LIKE ?"
        params.append(f"%{audit_actor}%")
    if audit_request:
        request_id = None
        request_kind = None
        if "-" in audit_request:
            head, tail = audit_request.split("-", 1)
            if head in {"coffee", "card"}:
                request_kind = head
                try:
                    request_id = int(tail)
                except ValueError:
                    request_id = None
        else:
            try:
                request_id = int(audit_request)
            except ValueError:
                request_id = None
        if request_id is not None:
            sql += " AND request_id = ?"
            params.append(request_id)
            if request_kind:
                sql += " AND request_kind = ?"
                params.append(request_kind)
    if date_start:
        sql += " AND created_at >= ?"
        params.append(date_start)
    if date_end:
        sql += " AND created_at < ?"
        params.append(date_end)
    if query:
        like = f"%{query}%"
        sql += " AND (customer_name LIKE ? OR reader_name LIKE ? OR actor LIKE ? OR ai_reading LIKE ?)"
        params.extend([like, like, like, like])
    sql += " ORDER BY id DESC LIMIT 500"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, tuple(params)).fetchall()


def fetch_admin_summary() -> dict[str, int]:
    today_start = datetime.utcnow().strftime("%Y-%m-%dT00:00:00")
    cutoff_30m = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        users_total = int(conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"])
        users_today = int(
            conn.execute("SELECT COUNT(*) AS c FROM users WHERE created_at >= ?", (today_start,)).fetchone()["c"]
        )
        coffee_total = int(conn.execute("SELECT COUNT(*) AS c FROM coffee_requests").fetchone()["c"])
        card_total = int(conn.execute("SELECT COUNT(*) AS c FROM card_requests").fetchone()["c"])
        requests_today = int(
            conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM coffee_requests WHERE created_at >= ?) +
                  (SELECT COUNT(*) FROM card_requests WHERE created_at >= ?) AS c
                """,
                (today_start, today_start),
            ).fetchone()["c"]
        )
        payment_status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS c
            FROM payment_requests
            GROUP BY status
            """
        ).fetchall()
        ops_row = conn.execute(
            """
            SELECT
              COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0) AS pending_total,
              COALESCE(SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END), 0) AS in_progress_total,
              COALESCE(SUM(CASE WHEN status = 'in_progress' AND created_at <= ? THEN 1 ELSE 0 END), 0) AS overdue_30_total,
              COALESCE(SUM(CASE WHEN status = 'completed' AND created_at >= ? THEN 1 ELSE 0 END), 0) AS completed_today_total
            FROM payment_requests
            """,
            (cutoff_30m, today_start),
        ).fetchone()
        oldest_wait_row = conn.execute(
            """
            SELECT created_at
            FROM payment_requests
            WHERE status IN ('pending', 'in_progress')
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        ai_row = conn.execute(
            """
            SELECT
                COUNT(*) AS c,
                COALESCE(SUM(cost_estimate), 0) AS cost_sum,
                COALESCE(SUM(token_total), 0) AS token_sum
            FROM reading_audit
            WHERE created_at >= ?
              AND action IN ('generated', 'regenerated')
            """,
            (today_start,),
        ).fetchone()
    status_counts = {str(row["status"]): int(row["c"]) for row in payment_status_rows}
    ai_count = int(ai_row["c"] or 0)
    ai_cost = float(ai_row["cost_sum"] or 0.0)
    ai_tokens = int(ai_row["token_sum"] or 0)
    oldest_wait_minutes = 0
    if oldest_wait_row and oldest_wait_row["created_at"]:
        try:
            oldest_dt = datetime.fromisoformat(str(oldest_wait_row["created_at"]))
            oldest_wait_minutes = max(0, int((datetime.utcnow() - oldest_dt).total_seconds() // 60))
        except ValueError:
            oldest_wait_minutes = 0
    return {
        "users_total": users_total,
        "users_today": users_today,
        "requests_total": coffee_total + card_total,
        "requests_today": requests_today,
        "coffee_total": coffee_total,
        "card_total": card_total,
        "pending_count": status_counts.get("pending", 0),
        "paid_count": status_counts.get("paid", 0),
        "in_progress_count": status_counts.get("in_progress", 0),
        "completed_count": status_counts.get("completed", 0),
        "ai_runs_today": ai_count,
        "ai_tokens_today": ai_tokens,
        "ai_cost_today": ai_cost,
        "ai_cost_avg": (ai_cost / ai_count) if ai_count else 0.0,
        "ops_pending_total": int(ops_row["pending_total"] or 0),
        "ops_in_progress_total": int(ops_row["in_progress_total"] or 0),
        "ops_overdue_30_total": int(ops_row["overdue_30_total"] or 0),
        "ops_completed_today_total": int(ops_row["completed_today_total"] or 0),
        "ops_oldest_wait_minutes": oldest_wait_minutes,
    }


@app.get("/admin/export.csv")
def admin_export_csv():
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    filters = parse_admin_filters()
    _, _, payment_rows = fetch_filtered_admin_data(filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["payment_id", "request_kind", "request_id", "full_name", "phone", "amount", "currency", "status", "created_at"])
    for row in payment_rows:
        writer.writerow(
            [
                row["id"],
                row["request_kind"],
                row["request_id"],
                row["full_name"],
                row["phone"],
                row["amount"],
                row["currency"],
                row["status"],
                row["created_at"],
            ]
        )
    csv_data = output.getvalue()
    filename = f"admin-payments-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(csv_data, mimetype="text/csv; charset=utf-8", headers=headers)


@app.get("/admin/audit-export.csv")
def admin_audit_export_csv():
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    filters = parse_admin_filters()
    audit_rows = fetch_reading_audit_rows(filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "audit_id",
            "request_kind",
            "request_id",
            "reading_type",
            "customer_name",
            "reader_name",
            "actor",
            "action",
            "ai_status",
            "model_name",
            "token_input",
            "token_output",
            "token_total",
            "cost_estimate",
            "quality_flags",
            "created_at",
            "ai_reading",
        ]
    )
    for row in audit_rows:
        writer.writerow(
            [
                row["id"],
                row["request_kind"],
                row["request_id"],
                row["reading_type"],
                row["customer_name"],
                row["reader_name"],
                row["actor"],
                row["action"],
                row["ai_status"],
                row["model_name"],
                row["token_input"],
                row["token_output"],
                row["token_total"],
                row["cost_estimate"],
                row["quality_flags"],
                row["created_at"],
                row["ai_reading"],
            ]
        )
    csv_data = output.getvalue()
    filename = f"admin-reading-audit-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(csv_data, mimetype="text/csv; charset=utf-8", headers=headers)


@app.get("/admin")
def admin():
    if not admin_required():
        return render_template("admin_login.html")

    filters = parse_admin_filters()
    coffee_rows, card_rows, payment_rows = fetch_filtered_admin_data(filters)
    reading_audit_rows = fetch_reading_audit_rows(filters)
    summary = fetch_admin_summary()

    coffee_was = [
        {
            "id": row["id"],
            "full_name": row["full_name"],
            "phone": row["phone"],
            "question": row["question"],
            "reader_name": row["reader_name"],
            "created_at": row["created_at"],
            "image_path": row["image_path"],
            "image_paths": parse_json_list(row["image_paths"]),
            "ai_status": row["ai_status"],
            "ai_reading": row["ai_reading"],
            "ai_published": int(row["ai_published"] or 0),
            "quality_flags": (
                (("long" if len(str(row["ai_reading"] or "").strip()) > 2600 else "") +
                 (",quality_risk" if validate_reading_quality(str(row["ai_reading"] or "").strip()) else ""))
                .strip(",")
            ) if str(row["ai_status"]) == "ready" else "",
            "quality_score": compute_quality_score(str(row["ai_reading"] or "").strip())[0] if str(row["ai_status"]) == "ready" else 0,
            "quality_label": compute_quality_score(str(row["ai_reading"] or "").strip())[1] if str(row["ai_status"]) == "ready" else "",
            "paid": row["paid"],
            "order_status": normalize_order_status(str(row["order_status"])),
            "next_status": ORDER_STATUS_NEXT[normalize_order_status(str(row["order_status"]))],
            "wa_link": build_whatsapp_link(
                row["phone"], f"Merhaba {row['full_name']}, kahve falı talebiniz hazırlanıyor."
            ),
        }
        for row in coffee_rows
    ]
    card_was = [
        {
            "id": row["id"],
            "reading_type": row["reading_type"],
            "full_name": row["full_name"],
            "phone": row["phone"],
            "question": row["question"],
            "reader_name": row["reader_name"],
            "selected_cards": row["selected_cards"],
            "ai_status": row["ai_status"],
            "ai_reading": row["ai_reading"],
            "ai_published": int(row["ai_published"] or 0),
            "quality_flags": (
                (("long" if len(str(row["ai_reading"] or "").strip()) > 2600 else "") +
                 (",quality_risk" if validate_reading_quality(str(row["ai_reading"] or "").strip()) else ""))
                .strip(",")
            ) if str(row["ai_status"]) == "ready" else "",
            "quality_score": compute_quality_score(str(row["ai_reading"] or "").strip())[0] if str(row["ai_status"]) == "ready" else 0,
            "quality_label": compute_quality_score(str(row["ai_reading"] or "").strip())[1] if str(row["ai_status"]) == "ready" else "",
            "created_at": row["created_at"],
            "paid": row["paid"],
            "order_status": normalize_order_status(str(row["order_status"])),
            "next_status": ORDER_STATUS_NEXT[normalize_order_status(str(row["order_status"]))],
            "wa_link": build_whatsapp_link(
                row["phone"],
                f"Merhaba {row['full_name']}, {row['reading_type']} falı talebiniz alındı.",
            ),
        }
        for row in card_rows
    ]
    audit_was = [
        {
            "id": row["id"],
            "request_kind": row["request_kind"],
            "request_id": row["request_id"],
            "reading_type": row["reading_type"],
            "customer_name": row["customer_name"],
            "reader_name": row["reader_name"],
            "actor": row["actor"],
            "action": row["action"],
            "ai_status": row["ai_status"],
            "created_at": row["created_at"],
            "model_name": row["model_name"],
            "token_total": int(row["token_total"] or 0),
            "cost_estimate": float(row["cost_estimate"] or 0.0),
            "quality_flags": row["quality_flags"],
            "quality_score": compute_quality_score(str(row["ai_reading"] or "").strip())[0] if row["ai_reading"] else 0,
            "quality_label": compute_quality_score(str(row["ai_reading"] or "").strip())[1] if row["ai_reading"] else "",
            "ai_excerpt": (str(row["ai_reading"] or "").strip()[:220] + ("..." if len(str(row["ai_reading"] or "").strip()) > 220 else "")),
        }
        for row in reading_audit_rows
    ]

    return render_template(
        "admin.html",
        coffee_rows=coffee_was,
        card_rows=card_was,
        payment_rows=payment_rows,
        reading_audit_rows=audit_was,
        filters=filters,
        summary=summary,
    )


UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
init_db()


if __name__ == "__main__":
    app.run(debug=True)
