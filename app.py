from __future__ import annotations

import json
import os
import sqlite3
import hashlib
import hmac
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

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
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
EXPECTED_CARD_COUNT = {"katina": 7, "tarot": 3}
LANGUAGES = {"tr", "en", "de"}
DEFAULT_LANG = "tr"
EUROPE_COUNTRIES = {
    "AL", "AD", "AM", "AT", "AZ", "BA", "BE", "BG", "BY", "CH", "CY", "CZ", "DE", "DK",
    "EE", "ES", "FI", "FO", "FR", "GB", "GE", "GI", "GR", "HR", "HU", "IE", "IS", "IT",
    "LI", "LT", "LU", "LV", "MC", "MD", "ME", "MK", "MT", "NL", "NO", "PL", "PT", "RO",
    "RS", "RU", "SE", "SI", "SK", "SM", "TR", "UA", "VA",
}
TRANSLATIONS = {
    "tr": {
        "brand": "Ateş Fal Evi",
        "nav_coffee": "Kahve",
        "nav_katina": "Katina",
        "nav_tarot": "Tarot",
        "nav_agb": "AGB",
        "nav_login": "Üye Girişi",
        "nav_register": "Kayıt Ol",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        "lang_de": "Deutsch",
        "home_kicker": "Modern Online Fal Deneyimi",
        "home_title": "Fal Türünü Seç ve İlgili Sekmeye Geç",
        "home_desc": "Aşağıdaki türlerden birini seçerek ilgili sayfaya geçebilirsin.",
        "home_cta_primary": "Hemen Başla",
        "home_cta_secondary": "Fal Türlerini Gör",
        "home_badge_1": "Canlı Destek",
        "home_badge_2": "Güvenli Ödeme",
        "home_badge_3": "3 Dil Seçeneği",
        "home_welcome_title": "Profesyonel Online Fal Platformu",
        "home_welcome_desc": "Fal türünü seç, falcını belirle ve talebini birkaç adımda güvenle tamamla.",
        "home_welcome_item_1": "Doğrulanmış falcı profilleri",
        "home_welcome_item_2": "Hızlı talep ve ödeme akışı",
        "home_welcome_item_3": "TR / EN / DE çok dilli kullanım",
        "home_welcome_cta": "Fal Türünü Seç",
        "choice_coffee": "Kahve Falı",
        "choice_katina": "Katina Aşk Falı",
        "choice_tarot": "Tarot Falı",
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
        "tarot_desc": "3 kart açılımı: geçmiş, şimdi, gelecek.",
        "tarot_question": "Tarot Sorunuz",
        "submit_tarot": "Tarot Falını Gönder",
        "login_title": "Üye Girişi",
        "login_kicker": "Hesabına Giriş",
        "login_desc": "Hesabına giriş yaparak fal taleplerini ve yorumlarını yönetebilirsin.",
        "email": "E-Posta",
        "username": "Kullanıcı Adı",
        "password": "Şifre",
        "login_submit": "Giriş Yap",
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
        "panel_filter_label": "Tür Filtresi",
        "panel_filter_all": "Tümü",
        "panel_detail_toggle": "Detay",
        "panel_detail_question": "Soru Detayı",
        "panel_detail_result": "Yorum Detayı",
        "profile_title": "Hesap Bilgileri",
        "profile_desc": "İsim, e-posta, telefon bilgilerini güncelleyebilir ve şifreni yenileyebilirsin.",
        "profile_new_password": "Yeni Şifre",
        "profile_new_password_confirm": "Yeni Şifre (Tekrar)",
        "profile_save": "Bilgileri Kaydet",
        "register_title": "Kayıt Ol",
        "register_kicker": "Yeni Hesap",
        "register_desc": "Hızlıca hesap oluştur, fal geçmişine ve yorumlarına panelinden eriş.",
        "register_submit": "Kaydı Tamamla",
        "msg_login_ok": "Giriş başarılı.",
        "msg_login_bad": "Kullanıcı adı veya şifre hatalı.",
        "msg_register_ok": "Kayıt tamamlandı. Giriş yapabilirsiniz.",
        "msg_register_bad": "Ad soyad, e-posta, telefon, kullanıcı adı (min 3) ve şifre (min 4) zorunludur.",
        "msg_register_exists": "Bu kullanıcı adı zaten kullanılıyor.",
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
        "brand": "Fire Fortune House",
        "nav_coffee": "Coffee",
        "nav_katina": "Katina",
        "nav_tarot": "Tarot",
        "nav_agb": "AGB",
        "nav_login": "Sign In",
        "nav_register": "Sign Up",
        "lang_tr": "Türkçe",
        "lang_en": "English",
        "lang_de": "Deutsch",
        "home_kicker": "Modern Online Reading Experience",
        "home_title": "Choose a Reading Type and Continue",
        "home_desc": "Select one of the reading types below to open its page.",
        "home_cta_primary": "Start Now",
        "home_cta_secondary": "View Reading Types",
        "home_badge_1": "Live Support",
        "home_badge_2": "Secure Payment",
        "home_badge_3": "3 Languages",
        "home_welcome_title": "Professional Online Fortune Platform",
        "home_welcome_desc": "Choose a reading type, select your reader, and complete your request securely in minutes.",
        "home_welcome_item_1": "Verified reader profiles",
        "home_welcome_item_2": "Fast request and payment flow",
        "home_welcome_item_3": "TR / EN / DE multilingual use",
        "home_welcome_cta": "Choose Reading Type",
        "choice_coffee": "Coffee Reading",
        "choice_katina": "Katina Love Reading",
        "choice_tarot": "Tarot Reading",
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
        "tarot_desc": "3-card spread: past, present, future.",
        "tarot_question": "Your Tarot Question",
        "submit_tarot": "Submit Tarot Reading",
        "login_title": "Sign In",
        "login_kicker": "Account Access",
        "login_desc": "Sign in to manage your readings and view your history in one place.",
        "email": "Email",
        "username": "Username",
        "password": "Password",
        "login_submit": "Sign In",
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
        "panel_filter_label": "Type Filter",
        "panel_filter_all": "All",
        "panel_detail_toggle": "Details",
        "panel_detail_question": "Question Details",
        "panel_detail_result": "Reading Details",
        "profile_title": "Account Details",
        "profile_desc": "Update your name, email and phone details, and reset your password.",
        "profile_new_password": "New Password",
        "profile_new_password_confirm": "New Password (Repeat)",
        "profile_save": "Save Details",
        "register_title": "Sign Up",
        "register_kicker": "Create Account",
        "register_desc": "Create your account to access your reading history and personal panel.",
        "register_submit": "Complete Registration",
        "msg_login_ok": "Signed in successfully.",
        "msg_login_bad": "Invalid username or password.",
        "msg_register_ok": "Registration completed. You can sign in now.",
        "msg_register_bad": "Full name, email, phone, username (min 3), and password (min 4) are required.",
        "msg_register_exists": "This username is already in use.",
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
        "brand": "Feuer Orakelhaus",
        "nav_coffee": "Kaffee",
        "nav_katina": "Katina",
        "nav_tarot": "Tarot",
        "nav_agb": "AGB",
        "nav_login": "Anmelden",
        "nav_register": "Registrieren",
        "lang_tr": "Türkisch",
        "lang_en": "Englisch",
        "lang_de": "Deutsch",
        "home_kicker": "Modernes Online-Orakel",
        "home_title": "Wähle eine Art und wechsle zur Seite",
        "home_desc": "Wähle unten eine Kategorie, um zur passenden Seite zu gehen.",
        "home_cta_primary": "Jetzt Starten",
        "home_cta_secondary": "Orakelarten Ansehen",
        "home_badge_1": "Live-Support",
        "home_badge_2": "Sichere Zahlung",
        "home_badge_3": "3 Sprachen",
        "home_welcome_title": "Professionelle Online-Orakelplattform",
        "home_welcome_desc": "Wähle eine Orakelart, bestimme deine Person und sende deine Anfrage sicher in wenigen Schritten.",
        "home_welcome_item_1": "Verifizierte Profile",
        "home_welcome_item_2": "Schneller Anfrage- und Zahlungsablauf",
        "home_welcome_item_3": "Mehrsprachig: TR / EN / DE",
        "home_welcome_cta": "Orakelart Wählen",
        "choice_coffee": "Kaffeesatz-Orakel",
        "choice_katina": "Katina-Liebesorakel",
        "choice_tarot": "Tarot-Orakel",
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
        "tarot_desc": "3-Karten-Legung: Vergangenheit, Gegenwart, Zukunft.",
        "tarot_question": "Deine Tarot-Frage",
        "submit_tarot": "Tarot senden",
        "login_title": "Anmelden",
        "login_kicker": "Kontozugang",
        "login_desc": "Melde dich an, um deine Anfragen und Deutungen zentral zu verwalten.",
        "email": "E-Mail",
        "username": "Benutzername",
        "password": "Passwort",
        "login_submit": "Anmelden",
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
        "panel_filter_label": "Art-Filter",
        "panel_filter_all": "Alle",
        "panel_detail_toggle": "Details",
        "panel_detail_question": "Fragedetails",
        "panel_detail_result": "Deutungsdetails",
        "profile_title": "Kontodaten",
        "profile_desc": "Du kannst Name, E-Mail und Telefon aktualisieren und dein Passwort erneuern.",
        "profile_new_password": "Neues Passwort",
        "profile_new_password_confirm": "Neues Passwort (Wiederholen)",
        "profile_save": "Daten Speichern",
        "register_title": "Registrieren",
        "register_kicker": "Neues Konto",
        "register_desc": "Erstelle dein Konto und greife jederzeit auf deinen Verlauf im Benutzerbereich zu.",
        "register_submit": "Registrierung abschließen",
        "msg_login_ok": "Anmeldung erfolgreich.",
        "msg_login_bad": "Benutzername oder Passwort ist falsch.",
        "msg_register_ok": "Registrierung abgeschlossen. Jetzt anmelden.",
        "msg_register_bad": "Vollständiger Name, E-Mail, Telefon, Benutzername (min. 3) und Passwort (min. 4) sind erforderlich.",
        "msg_register_exists": "Dieser Benutzername ist bereits vergeben.",
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
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def admin_required() -> bool:
    return bool(session.get("is_admin"))


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
        "Ateş Fal Evi"
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
            "temperature": 0.8,
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
                "temperature": 0.8,
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
    if lang == "en":
        return (
            "You are an experienced Turkish coffee reading expert. "
            "Write in a warm, natural, human tone; avoid robotic language and avoid generic filler. "
            "Use ONLY the uploaded grounds photos and the user's question. Do not invent symbols that are not visible.\n"
            "Language rule: Write the full response in English only.\n"
            "Style:\n"
            "- Start with one short overall-energy paragraph.\n"
            "- Then continue with flowing mini-sections (not rigid numbered lists).\n"
            "- Be clear, practical, and emotionally intelligent.\n"
            "- End with exactly 3 short actionable suggestions.\n"
            f"Final line must be exactly: Reader: {reader_name}\n"
            f"Client: {full_name}\nQuestion: {question}\nPhoto count: {image_count}"
        )
    if lang == "de":
        return (
            "Du bist eine erfahrene Kaffeesatz-Orakelberaterin. "
            "Schreibe warm, natürlich und menschlich; nicht mechanisch. "
            "Nutze NUR die hochgeladenen Fotos und die Frage. Keine erfundenen Symbole.\n"
            "Sprachregel: Schreibe die komplette Antwort nur auf Deutsch.\n"
            "Stil:\n"
            "- Starte mit einem kurzen Absatz zur Gesamtenergie.\n"
            "- Danach klare, natürliche Abschnitte statt starrer Listen.\n"
            "- Konkrete, alltagsnahe Sprache.\n"
            "- Am Ende genau 3 kurze Empfehlungen.\n"
            f"Letzte Zeile muss exakt sein: Falcı: {reader_name}\n"
            f"Kundin: {full_name}\nFrage: {question}\nAnzahl Fotos: {image_count}"
        )
    return (
        "Deneyimli bir kahve falı yorumcususun. "
        "Yorumu sıcak, doğal ve insan gibi yaz; mekanik ve şablon cümlelerden kaçın. "
        "Sadece yüklenen telve fotoğraflarını ve soruyu kullan. Fotoğrafta görünmeyen sembol uydurma.\n"
        "Dil kuralı: Cevabın tamamını yalnızca Türkçe yaz.\n"
        "Yazım tarzı:\n"
        "- Kısa bir 'genel enerji' paragrafıyla başla.\n"
        "- Sonra akıcı ara başlıklarla devam et (katı numaralı liste olmasın).\n"
        "- Gerçekçi, net ve duygusal olarak dengeli bir dil kullan.\n"
        "- Sonda tam 3 kısa, uygulanabilir tavsiye ver.\n"
        f"Son satır şu formatta olsun: Falcı: {reader_name}\n"
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
    layout = "7 kart Katina aşk açılımı" if reading_type == "katina" else "3 kart Tarot açılımı"
    cards_detail = format_cards_for_prompt(selected_cards)
    if lang == "en":
        return (
            f"You are a professional {reading_type} reader. Interpret based on the selected spread and user question.\n"
            f"Spread: {layout}\nClient: {full_name}\nQuestion: {question}\nSelected cards/positions:\n{cards_detail}\n"
            "Important: card values above are internal technical IDs. Never print these IDs in the final text.\n"
            "Language rule: Write the full response in English only.\n"
            "Write naturally and warmly, not mechanically. Avoid generic template wording.\n"
            "Flow:\n"
            "- Short overall theme paragraph\n"
            "- Position-based interpretation in human language\n"
            "- Risk/opportunity notes\n"
            "- Exactly 3 concise recommendations\n"
            f"Final line must be exactly: Reader: {reader_name}"
        )
    if lang == "de":
        return (
            f"Du bist eine professionelle {reading_type}-Legung Assistenz. Deute basierend auf den gezogenen Karten und der Frage.\n"
            f"Legung: {layout}\nKundin: {full_name}\nFrage: {question}\nGezogene Karten/Positionen:\n{cards_detail}\n"
            "Wichtig: Die Kartenwerte oben sind interne technische IDs. Diese IDs dürfen im finalen Text nicht erscheinen.\n"
            "Sprachregel: Schreibe die komplette Antwort nur auf Deutsch.\n"
            "Schreibe natürlich, warm und nicht mechanisch.\n"
            "Struktur:\n"
            "- Kurzer Absatz zur Gesamtenergie\n"
            "- Deutung nach Positionen in natürlicher Sprache\n"
            "- Risiko/Chance\n"
            "- Genau 3 klare Empfehlungen\n"
            f"Letzte Zeile muss exakt sein: Falcı: {reader_name}"
        )
    return (
        f"Profesyonel bir {reading_type} fal yorumcususun. Seçilen açılım ve soru üzerinden yorum üret.\n"
        f"Açılım: {layout}\nMüşteri: {full_name}\nSoru: {question}\nSeçilen kart/pozisyonlar:\n{cards_detail}\n"
        "Önemli: Yukarıdaki kart değerleri sistem içi teknik ID'dir. Nihai yorum metninde bu ID'leri asla yazma.\n"
        "Dil kuralı: Cevabın tamamını yalnızca Türkçe yaz.\n"
        "Dil sıcak, doğal ve insan gibi olsun; mekanik şablon cümlelerden kaçın.\n"
        "Akış:\n"
        "- Kısa bir genel enerji paragrafı\n"
        "- Pozisyonlara göre yorum (doğal cümlelerle)\n"
        "- Fırsat/risk notları\n"
        "- Tam 3 kısa ve uygulanabilir öneri\n"
        f"Son satır şu formatta olsun: Falcı: {reader_name}"
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


def get_lang() -> str:
    requested = request.args.get("lang")
    if requested in LANGUAGES:
        session["lang"] = requested
        return requested
    saved = session.get("lang")
    if saved in LANGUAGES:
        return saved
    return DEFAULT_LANG


def t(key: str, **kwargs: object) -> str:
    lang = get_lang()
    raw = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG]).get(key, key)
    if kwargs:
        return raw.format(**kwargs)
    return raw


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

    username = request.form.get("username", "").strip()
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


@app.get("/register")
def register_page():
    return render_template("register.html")


@app.post("/register")
def register_submit():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    if len(username) < 3 or len(password) < 4 or not full_name or "@" not in email or not phone:
        flash(t("msg_register_bad"), "error")
        return redirect(url_for("register_page", lang=get_lang()))
    with sqlite3.connect(DB_PATH) as conn:
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
                "type": str(row["reading_type"]),
                "reader_name": str(row["reader_name"]),
                "question": str(row["question"]),
                "result": str(row["ai_reading"]) if (str(row["ai_status"]) == "ready" and int(row["ai_published"] or 0) == 1) else t("ai_result_review"),
                "created_at": str(row["created_at"]),
                "order_status": normalize_order_status(str(row["order_status"])),
            }
        )
    for row in card_rows:
        merged.append(
            {
                "id": str(row["id"]),
                "type": str(row["reading_type"]),
                "reader_name": str(row["reader_name"]),
                "question": str(row["question"]),
                "result": str(row["ai_reading"]) if (str(row["ai_status"]) == "ready" and int(row["ai_published"] or 0) == 1) else t("ai_result_review"),
                "created_at": str(row["created_at"]),
                "order_status": normalize_order_status(str(row["order_status"])),
            }
        )

    merged.sort(key=lambda x: x["created_at"], reverse=True)
    if selected_type != "all":
        merged = [row for row in merged if row["type"] == selected_type]
    merged = merged[:20]
    return render_template("dashboard.html", rows=merged, user=user_row, selected_type=selected_type)


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
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        clear_auth_failures("admin_login", ip)
        session["is_admin"] = True
        return redirect(url_for("admin"))
    record_auth_failure("admin_login", ip)
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


def regenerate_ai_for_request(request_kind: str, request_id: int, lang: str) -> tuple[bool, str]:
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

    if ai_status == "ready":
        return True, "Yorum yeniden üretildi. Müşteriye göndermek için yayınlayın."
    if ai_status == "batched":
        return True, "Yorum kuyruğa alındı (batch). Hazır olunca yayınlayabilirsiniz."
    if ai_status == "no_key":
        return False, "OpenAI anahtarı eksik (OPENAI_API_KEY)."
    return False, f"Yorum üretilemedi: {ai_status}"


@app.post("/admin/publish-reading/<request_kind>/<int:request_id>")
def admin_publish_reading(request_kind: str, request_id: int):
    if not admin_required():
        flash("Bu alan için admin girişi gerekli.", "error")
        return redirect(url_for("admin"))
    if request_kind not in {"coffee", "card"}:
        flash("Geçersiz işlem.", "error")
        return redirect(url_for("admin"))

    table_name = "coffee_requests" if request_kind == "coffee" else "card_requests"
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            f"SELECT ai_status, ai_reading FROM {table_name} WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            flash("Talep bulunamadı.", "error")
            return redirect(url_for("admin"))
        if str(row["ai_status"]) != "ready" or not str(row["ai_reading"] or "").strip():
            flash("Yorum hazır değil. Önce yorum üretilmeli.", "error")
            return redirect(url_for("admin"))
        conn.execute(
            f"UPDATE {table_name} SET ai_published = 1 WHERE id = ?",
            (request_id,),
        )
    flash("Yorum müşteriye yayınlandı.", "ok")
    return redirect(url_for("admin"))


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
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            f"SELECT id FROM {table_name} WHERE id = ?",
            (request_id,),
        ).fetchone()
        if row is None:
            flash("Talep bulunamadı.", "error")
            return redirect(url_for("admin"))
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
                SELECT id, full_name, phone, question, reader_name, ai_status, ai_reading, ai_published, created_at
                FROM {table_name}
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
        else:
            row = conn.execute(
                f"""
                SELECT id, full_name, phone, question, reader_name, reading_type, ai_status, ai_reading, ai_published, created_at
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
    return {
        "type": raw_type if raw_type in {"all", "coffee", "katina", "tarot"} else "all",
        "status": raw_status if raw_status in {"all", "pending", "paid", "in_progress", "completed"} else "all",
        "date_from": date_from,
        "date_to": date_to,
        "q": q,
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


def fetch_admin_summary() -> dict[str, int]:
    today_start = datetime.utcnow().strftime("%Y-%m-%dT00:00:00")
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
    status_counts = {str(row["status"]): int(row["c"]) for row in payment_status_rows}
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


@app.get("/admin")
def admin():
    if not admin_required():
        return render_template("admin_login.html")

    filters = parse_admin_filters()
    coffee_rows, card_rows, payment_rows = fetch_filtered_admin_data(filters)
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

    return render_template(
        "admin.html",
        coffee_rows=coffee_was,
        card_rows=card_was,
        payment_rows=payment_rows,
        filters=filters,
        summary=summary,
    )


UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
init_db()


if __name__ == "__main__":
    app.run(debug=True)
