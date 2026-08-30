import threading
from flask import Flask, redirect, render_template, render_template_string, send_from_directory, Response, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image
import secrets
import string
import os
import json
import shutil
import socket
import datetime
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32) # Using a random secret for session security
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
QR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrcodes")

for folder in [UPLOAD_FOLDER, QR_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

DB_PATH = "qr_pro.db"

# -----------------------------
# Database
# -----------------------------
def create_database():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            content_type TEXT NOT NULL,
            content_data TEXT NOT NULL,
            password TEXT,
            expiry_datetime TEXT,
            is_one_time BOOLEAN DEFAULT 0,
            scan_limit INTEGER,
            current_scans INTEGER DEFAULT 0,
            device_redirects TEXT,
            geo_restrictions TEXT,
            ab_testing_urls TEXT,
            time_routing TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            base_domain TEXT,
            webhook_email TEXT,
            default_geo TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qr_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            browser TEXT,
            os TEXT,
            platform TEXT,
            country TEXT,
            city TEXT,
            FOREIGN KEY(qr_id) REFERENCES qr_codes(qr_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            email TEXT NOT NULL,
            token TEXT NOT NULL,
            expiry_datetime TEXT NOT NULL
        )
    """)
    try:
        conn.execute("ALTER TABLE qr_codes ADD COLUMN time_routing TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        conn.execute("ALTER TABLE qr_codes ADD COLUMN user_id INTEGER")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        conn.execute("ALTER TABLE users RENAME COLUMN username TO email")
    except sqlite3.OperationalError:
        pass # Column already renamed or doesn't exist
    conn.commit()
    conn.close()

def generate_qr_id():
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(8))

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_qr(content_type, content_data, config=None, logo_path=None, qr_color="#000000", bg_color="#ffffff", user_id=None):
    if config is None: config = {}
    qr_id = generate_qr_id()
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO qr_codes (qr_id, user_id, content_type, content_data, password, expiry_datetime, is_one_time, scan_limit, device_redirects, geo_restrictions, ab_testing_urls, time_routing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qr_id, user_id, content_type, content_data,
            config.get('password', ''),
            config.get('expiry_datetime', ''),
            config.get('is_one_time', False),
            config.get('scan_limit', None),
            config.get('device_redirects', ''),
            config.get('geo_restrictions', ''),
            config.get('ab_testing_urls', ''),
            config.get('time_routing', '')
        )
    )
    conn.commit()
    conn.close()

    base_url = None
    if user_id:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT base_domain FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row and row['base_domain']:
            base_url = row['base_domain'].rstrip('/')

    if not base_url:
        local_ip = get_local_ip()
        base_url = config.get('base_url', f"http://{local_ip}:5000")
        if not base_url: base_url = f"http://{local_ip}:5000"
    
    redirect_url = f"{base_url}/qr/{qr_id}"
    
    # Generate Styled QR
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(redirect_url)
    qr.make(fit=True)
    
    color_mask = SolidFillColorMask(front_color=hex_to_rgb(qr_color), back_color=hex_to_rgb(bg_color))
    
    if logo_path and os.path.exists(logo_path):
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer(), color_mask=color_mask, embeded_image_path=logo_path)
    else:
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer(), color_mask=color_mask)
        
    filename = f"{qr_id}.png"
    filepath = os.path.join(QR_FOLDER, filename)
    img.save(filepath)
    return qr_id, filename

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

# -----------------------------
# Frontend Routes
# -----------------------------
@app.route("/")
def serve_ui():
    response = app.make_response(render_template('ui.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route("/qrcodes/<path:filename>")
def serve_qr_image(filename):
    return send_from_directory(QR_FOLDER, filename)

@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# -----------------------------
# Auth API
# -----------------------------
@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.json
    email = data.get('email', '').strip()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    
    if user:
        # Generate 6 digit token
        import random
        token = str(random.randint(100000, 999999))
        expiry = (datetime.datetime.now() + datetime.timedelta(minutes=15)).isoformat()
        
        # Clear old tokens
        cursor.execute("DELETE FROM password_resets WHERE email=?", (email,))
        cursor.execute("INSERT INTO password_resets (email, token, expiry_datetime) VALUES (?, ?, ?)", (email, token, expiry))
        conn.commit()
        
        # Send Email via SMTP
        smtp_email = os.environ.get('SMTP_EMAIL')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        
        if smtp_email and smtp_password and "your_email@gmail.com" not in smtp_email:
            try:
                msg = MIMEText(f"Your password reset code is: {token}\nThis code will expire in 15 minutes.")
                msg['Subject'] = 'QR Pro - Password Reset Code'
                msg['From'] = smtp_email
                msg['To'] = email

                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(smtp_email, smtp_password)
                server.send_message(msg)
                server.quit()
                print(f"[SUCCESS] Email sent to {email}")
            except Exception as e:
                print(f"[ERROR] Failed to send email: {e}")
                print(f"[FALLBACK CODE] {token}")
        else:
            # Simulating email sending by printing to console
            print("\n" + "="*50)
            print(f"📧 EMAIL SIMULATION (SMTP Not Configured) 📧")
            print(f"To: {email}")
            print(f"Subject: Password Reset Code")
            print(f"Your password reset code is: {token}")
            print("="*50 + "\n")
        
    conn.close()
    
    # Always return success to prevent email enumeration
    return jsonify({"success": True, "message": "If the email is registered, a reset code was sent."})

@app.route("/api/reset-password", methods=["POST"])
def api_reset_password():
    data = request.json
    email = data.get('email', '').strip()
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    
    if not all([email, token, new_password]):
        return jsonify({"error": "Missing fields"}), 400
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT email, token, expiry_datetime FROM password_resets WHERE email=? AND token=?", (email, token))
    reset_record = cursor.fetchone()
    
    if not reset_record:
        conn.close()
        return jsonify({"error": "Invalid or expired reset code."}), 400
        
    expiry = datetime.datetime.fromisoformat(reset_record[2])
    if datetime.datetime.now() > expiry:
        cursor.execute("DELETE FROM password_resets WHERE email=?", (email,))
        conn.commit()
        conn.close()
        return jsonify({"error": "Reset code expired."}), 400
        
    # Valid token, update password
    hashed = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash=? WHERE email=?", (hashed, email))
    cursor.execute("DELETE FROM password_resets WHERE email=?", (email,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Password reset successfully. You can now login."})

@app.route("/api/register", methods=["POST"])
def api_register():
    try:
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email=?", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Email already exists"}), 400
            
        hashed = generate_password_hash(password)
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed))
        user_id = cursor.lastrowid
        
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 1:
            cursor.execute("UPDATE qr_codes SET user_id=? WHERE user_id IS NULL", (user_id,))
            
        conn.commit()
        conn.close()
        
        session['user_id'] = user_id
        session['email'] = email
        
        return jsonify({"success": True, "message": "Account created successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid email or password"}), 401
            
        session['user_id'] = user['id']
        session['email'] = user['email']
        
        return jsonify({"success": True, "message": "Logged in successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route("/api/session", methods=["GET"])
def api_session():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "email": session.get('email')})
    return jsonify({"logged_in": False})

# -----------------------------
# Settings API
# -----------------------------
@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == "GET":
        cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify({
                "base_domain": row['base_domain'] or '',
                "webhook_email": row['webhook_email'] or '',
                "default_geo": row['default_geo'] or ''
            })
        return jsonify({"base_domain": "", "webhook_email": "", "default_geo": ""})
        
    elif request.method == "POST":
        data = request.json or {}
        base_domain = data.get('base_domain', '').strip()
        webhook_email = data.get('webhook_email', '').strip()
        default_geo = data.get('default_geo', '').strip()
        
        cursor.execute("SELECT user_id FROM user_settings WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE user_settings SET base_domain=?, webhook_email=?, default_geo=? WHERE user_id=?",
                (base_domain, webhook_email, default_geo, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO user_settings (user_id, base_domain, webhook_email, default_geo) VALUES (?, ?, ?, ?)",
                (user_id, base_domain, webhook_email, default_geo)
            )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Settings saved successfully"})

# -----------------------------
# REST API
# -----------------------------
@app.route("/api/generate", methods=["POST"])
def api_generate():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        content_type = request.form.get('type', 'url')
        content_data = request.form.get('content_data', '')
        
        if content_type == 'pdf':
            if 'pdf_file' in request.files:
                file = request.files['pdf_file']
                if file.filename:
                    pdf_filename = secrets.token_hex(4) + "_" + file.filename
                    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
                    file.save(pdf_path)
                    content_data = f"/uploads/{pdf_filename}"
        
        if not content_data:
            return jsonify({"error": "Content data or PDF file is required"}), 400
            
        config = {
            'password': request.form.get('password', ''),
            'expiry_datetime': request.form.get('expiry_datetime', ''),
            'is_one_time': request.form.get('is_one_time') == 'true',
            'scan_limit': int(request.form.get('scan_limit')) if request.form.get('scan_limit') else None,
            'base_url': request.form.get('base_url', '')
        }
        
        ios = request.form.get('ios_url', '').strip()
        android = request.form.get('android_url', '').strip()
        if ios or android:
            config['device_redirects'] = json.dumps({'ios': ios, 'android': android})
            
        ab_urls = request.form.get('ab_urls', '').strip()
        if ab_urls:
            urls = [u.strip() for u in ab_urls.split(',') if u.strip()]
            config['ab_testing_urls'] = json.dumps(urls)
            
        geo = request.form.get('geo_restrictions', '').strip()
        if geo:
            config['geo_restrictions'] = geo.upper()
            
        time_day = request.form.get('time_day', '').strip()
        time_night = request.form.get('time_night', '').strip()
        if time_day or time_night:
            config['time_routing'] = json.dumps({'day': time_day, 'night': time_night})
            
        # Handle Logo Upload
        logo_path = None
        if 'logo' in request.files:
            file = request.files['logo']
            if file.filename:
                logo_path = os.path.join(UPLOAD_FOLDER, secrets.token_hex(4) + "_" + file.filename)
                file.save(logo_path)
                
        # Colors
        qr_color = request.form.get('qr_color', '#000000')
        bg_color = request.form.get('bg_color', '#ffffff')
        
        qr_id, filename = create_qr(content_type, content_data, config, logo_path, qr_color, bg_color, user_id=session.get('user_id'))
        
        return jsonify({
            "success": True,
            "qr_id": qr_id,
            "image_url": f"/qrcodes/{filename}",
            "message": "QR Code generated successfully!"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/list", methods=["GET"])
def api_list():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM qr_codes WHERE user_id=? ORDER BY id DESC", (session.get('user_id'),))
        rows = cursor.fetchall()
        
        qrs = []
        for r in rows:
            qrs.append({
                "qr_id": r["qr_id"],
                "content_type": r["content_type"],
                "content_data": r["content_data"],
                "current_scans": r["current_scans"],
                "password": r["password"],
                "expiry_datetime": r["expiry_datetime"],
                "is_one_time": r["is_one_time"],
                "scan_limit": r["scan_limit"],
                "device_redirects": r["device_redirects"],
                "geo_restrictions": r["geo_restrictions"],
                "ab_testing_urls": r["ab_testing_urls"],
                "time_routing": r["time_routing"]
            })
        conn.close()
        return jsonify({"success": True, "qrs": qrs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete/<qr_id>", methods=["DELETE"])
def api_delete(qr_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM qr_codes WHERE qr_id = ? AND user_id = ?", (qr_id, session.get('user_id')))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "QR Code deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/delete_bulk", methods=["POST"])
def api_delete_bulk():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()
        qr_ids = data.get('qr_ids', [])
        
        if not qr_ids:
            return jsonify({"error": "No QR IDs provided"}), 400
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?'] * len(qr_ids))
        query = f"DELETE FROM qr_codes WHERE qr_id IN ({placeholders}) AND user_id = ?"
        cursor.execute(query, qr_ids + [session.get('user_id')])
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"{len(qr_ids)} QR Codes deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/update/<qr_id>", methods=["POST"])
def api_update(qr_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        content_type = request.form.get('type', 'url')
        content_data = request.form.get('content_data', '')
        
        if content_type == 'pdf':
            if 'pdf_file' in request.files:
                file = request.files['pdf_file']
                if file.filename:
                    pdf_filename = secrets.token_hex(4) + "_" + file.filename
                    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
                    file.save(pdf_path)
                    content_data = f"/uploads/{pdf_filename}"
            else:
                # Retain old content_data if no new PDF is uploaded
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT content_data FROM qr_codes WHERE qr_id = ? AND user_id = ?", (qr_id, session.get('user_id')))
                row = cursor.fetchone()
                conn.close()
                if row:
                    content_data = row[0]
        
        if not content_data:
            return jsonify({"error": "Content data or PDF file is required"}), 400
            
        password = request.form.get('password', '')
        expiry = request.form.get('expiry_datetime', '')
        is_one_time = request.form.get('is_one_time') == 'true'
        scan_limit = int(request.form.get('scan_limit')) if request.form.get('scan_limit') else None
        
        ios = request.form.get('ios_url', '').strip()
        android = request.form.get('android_url', '').strip()
        device_redirects = json.dumps({'ios': ios, 'android': android}) if (ios or android) else ''
        
        ab_urls = request.form.get('ab_urls', '').strip()
        ab_testing_urls = json.dumps([u.strip() for u in ab_urls.split(',') if u.strip()]) if ab_urls else ''
        
        geo = request.form.get('geo_restrictions', '').strip().upper()
        
        time_day = request.form.get('time_day', '').strip()
        time_night = request.form.get('time_night', '').strip()
        time_routing = json.dumps({'day': time_day, 'night': time_night}) if (time_day or time_night) else ''
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE qr_codes 
            SET content_type=?, content_data=?, password=?, expiry_datetime=?, is_one_time=?, scan_limit=?, device_redirects=?, ab_testing_urls=?, geo_restrictions=?, time_routing=?
            WHERE qr_id=? AND user_id=?
        ''', (content_type, content_data, password, expiry, is_one_time, scan_limit, device_redirects, ab_testing_urls, geo, time_routing, qr_id, session.get('user_id')))
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "message": "QR Code updated successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# Deep Analytics Helpers
# -----------------------------
def parse_user_agent(ua_string):
    ua = ua_string.lower()
    
    # Browser
    if 'edg' in ua: browser = 'Edge'
    elif 'chrome' in ua and 'opr' not in ua: browser = 'Chrome'
    elif 'safari' in ua and 'chrome' not in ua: browser = 'Safari'
    elif 'firefox' in ua: browser = 'Firefox'
    elif 'opr' in ua or 'opera' in ua: browser = 'Opera'
    else: browser = 'Other'
    
    # OS
    if 'win' in ua: os_name = 'Windows'
    elif 'mac' in ua: os_name = 'macOS'
    elif 'android' in ua: os_name = 'Android'
    elif 'iphone' or 'ipad' in ua: os_name = 'iOS'
    elif 'linux' in ua: os_name = 'Linux'
    else: os_name = 'Other'
    
    # Platform (Device type estimation)
    if 'mobi' in ua or 'android' in ua or 'iphone' in ua: platform = 'Mobile'
    elif 'ipad' in ua or 'tablet' in ua: platform = 'Tablet'
    else: platform = 'Desktop'
    
    return browser, os_name, platform

# -----------------------------
# Dynamic Redirect Router
# -----------------------------
@app.route("/qr/<qr_id>")
def redirect_qr(qr_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM qr_codes WHERE qr_id = ?", (qr_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return "QR Code not found", 404

    # Fetch User Settings
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (row['user_id'],))
    settings = cursor.fetchone()
    
    webhook_email = settings['webhook_email'] if settings and settings['webhook_email'] else None
    default_geo = settings['default_geo'] if settings and settings['default_geo'] else None

    # 1. Update Scans & Limits
    ua = request.headers.get('User-Agent', '').lower()
    is_bot = any(b in ua for b in ['bot', 'spider', 'crawl', 'facebook', 'whatsapp', 'telegram', 'twitter', 'discord', 'linkedin', 'skype', 'vkshare', 'slack'])
    is_prefetch = request.headers.get('Purpose') == 'prefetch' or request.headers.get('X-Purpose') == 'preview' or is_bot
    current_scans = row['current_scans']
    
    if not is_prefetch:
        current_scans += 1
        
    if row['is_one_time'] and current_scans > 1:
        conn.close()
        return "This QR code has already been used.", 403
    if row['scan_limit'] and current_scans > row['scan_limit']:
        conn.close()
        return "Scan limit reached for this QR code.", 403
        
    if not is_prefetch:
        cursor.execute("UPDATE qr_codes SET current_scans = ? WHERE qr_id = ?", (current_scans, qr_id))
        
        # Log deep analytics
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip: ip = ip.split(',')[0].strip()
        browser, os_name, platform = parse_user_agent(ua)
        country = 'Unknown'
        city = 'Unknown'
        
        # Geolocation for non-private IPs
        is_private = not ip or ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.')
        if not is_private:
            try:
                import urllib.request
                req = urllib.request.Request(f'http://ip-api.com/json/{ip}?fields=status,country,city', headers={'User-Agent': 'Mozilla/5.0'})
                geo_info = json.loads(urllib.request.urlopen(req, timeout=1).read())
                if geo_info.get('status') == 'success':
                    country = geo_info.get('country', 'Unknown')
                    city = geo_info.get('city', 'Unknown')
            except Exception:
                pass # Silently fail for analytics to not block redirect
                
        cursor.execute("""
            INSERT INTO qr_scans (qr_id, ip_address, user_agent, browser, os, platform, country, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (qr_id, ip, request.headers.get('User-Agent', ''), browser, os_name, platform, country, city))
        
        conn.commit()
        if webhook_email:
            def send_scan_alert(to_email, q_id, scan_ip, scan_country, scan_city, scan_browser, scan_os, scan_device):
                smtp_email = os.environ.get('SMTP_EMAIL')
                smtp_password = os.environ.get('SMTP_PASSWORD')
                if smtp_email and smtp_password and "your_email@gmail.com" not in smtp_email:
                    try:
                        body = f"Hello,\n\nYour QR Code ({q_id}) was just scanned!\n\nScan Details:\nIP: {scan_ip}\nLocation: {scan_city}, {scan_country}\nDevice: {scan_os} ({scan_device}) - {scan_browser}\nTime: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        msg = MIMEText(body)
                        msg['Subject'] = f'QR Scan Alert: {q_id}'
                        msg['From'] = smtp_email
                        msg['To'] = to_email

                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(smtp_email, smtp_password)
                        server.send_message(msg)
                        server.quit()
                    except Exception as e:
                        print(f"[ERROR] Webhook Email Failed: {e}")
                else:
                    print(f"[WEBHOOK SIMULATION] Scan alert for {q_id} to {to_email}")
            
            # Run in a background thread to prevent slowing down the QR redirect
            threading.Thread(target=send_scan_alert, args=(webhook_email, qr_id, ip, country, city, browser, os_name, platform)).start()
    conn.close()
    
    # 2. Expiry Check
    if row['expiry_datetime']:
        expiry = datetime.datetime.fromisoformat(row['expiry_datetime'])
        if datetime.datetime.now() > expiry:
            return "This QR code has expired.", 410

    # 3. Password Protection
    if row['password']:
        pwd = request.args.get('pwd')
        if pwd != row['password']:
            return f'''
            <html>
            <head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
            <body style="font-family: Arial; padding: 20px; text-align: center; background: #f0f2f5;">
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 400px; margin: 50px auto; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                    <h2 style="color: #333;">🔒 Secure QR Code</h2>
                    <form>
                        <input type="password" name="pwd" placeholder="Enter Password" style="width: 100%; padding: 10px; margin: 15px 0; border: 1px solid #ddd; border-radius: 6px;">
                        <button type="submit" style="background: #1a73e8; color: white; border: none; padding: 12px 20px; width: 100%; border-radius: 6px; cursor: pointer; font-size: 16px;">Unlock</button>
                    </form>
                </div>
            </body>
            </html>
            '''

    # 4. Content Routing
    content_data = row['content_data']
    current_type = row['content_type']
    
    # 4a. Geo-Fencing
    combined_geo = []
    if row['geo_restrictions']:
        combined_geo.extend([x.strip().upper() for x in row['geo_restrictions'].split(',') if x.strip()])
    if default_geo:
        combined_geo.extend([x.strip().upper() for x in default_geo.split(',') if x.strip()])
        
    if combined_geo:
        allowed_locations = combined_geo
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip: ip = ip.split(',')[0].strip()
        
        # Bypass geo-fencing for local/private network IPs during testing
        is_private = not ip or ip == '127.0.0.1' or ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.')
        
        if not is_private:
            try:
                import urllib.request
                req = urllib.request.Request(f'http://ip-api.com/json/{ip}?fields=status,country,countryCode,city', headers={'User-Agent': 'Mozilla/5.0'})
                geo_info = json.loads(urllib.request.urlopen(req, timeout=3).read())
                
                # Only block if API successfully identified a public location
                if geo_info.get('status') == 'success':
                    locs = [geo_info.get('country', '').upper(), geo_info.get('countryCode', '').upper(), geo_info.get('city', '').upper()]
                    if not any(loc in allowed_locations for loc in locs if loc):
                        return "Access Denied: This QR Code is not available in your region.", 403
            except:
                pass # If API fails, allow fallback
            
    # 4b. Time-Based Routing
    if row['time_routing']:
        tr = json.loads(row['time_routing'])
        hour = datetime.datetime.now().hour
        if 6 <= hour < 18 and tr.get('day'):
            content_data = tr['day']
            current_type = 'url'
        elif (hour >= 18 or hour < 6) and tr.get('night'):
            content_data = tr['night']
            current_type = 'url'
    
    # A/B Testing
    if row['ab_testing_urls']:
        urls = json.loads(row['ab_testing_urls'])
        if urls:
            import random
            choice = random.choice([content_data] + urls)
            if choice != content_data:
                content_data = choice
                current_type = 'url'

    # Device Redirect
    if row['device_redirects']:
        dev = json.loads(row['device_redirects'])
        ua = request.headers.get('User-Agent', '').lower()
        if ('iphone' in ua or 'ipad' in ua) and dev.get('ios'):
            content_data = dev.get('ios')
            current_type = 'url'
        elif 'android' in ua and dev.get('android'):
            content_data = dev.get('android')
            current_type = 'url'

    if current_type == 'url':
        if not content_data.startswith("http"): content_data = "http://" + content_data
        return redirect(content_data)
        
    elif current_type == 'text':
        html = f'<div style="font-family: Arial; font-size:20px; padding: 20px;">{content_data}</div>'
        return render_template_string(html)
        
    elif current_type == 'pdf':
        return redirect(content_data)
        
    elif current_type == 'vcard':
        try:
            vd = json.loads(content_data)
        except:
            vd = {}
        
        vcard = ["BEGIN:VCARD", "VERSION:3.0"]
        
        # Name
        # Setting N as empty to avoid redundant "Last Name" displays above "Full Name" on some phones
        vcard.append("N:;;;;")
        vcard.append(f"FN:{vd.get('fn', '')} {vd.get('ln', '')}".strip())
        
        if vd.get('photo'): vcard.append(f"PHOTO;VALUE=uri:{vd.get('photo')}")
        
        # Professional
        if vd.get('company') or vd.get('dept'): vcard.append(f"ORG:{vd.get('company', '')};{vd.get('dept', '')}")
        if vd.get('title'): vcard.append(f"TITLE:{vd.get('title')}")
        if vd.get('role'): vcard.append(f"ROLE:{vd.get('role')}")
        
        # Contact
        if vd.get('work'): vcard.append(f"TEL;TYPE=WORK,VOICE:{vd.get('work')}")
        if vd.get('mobile'): vcard.append(f"TEL;TYPE=CELL,VOICE:{vd.get('mobile')}")
        if vd.get('email'): vcard.append(f"EMAIL;TYPE=PREF,INTERNET:{vd.get('email')}")
        
        # Online
        if vd.get('website'): vcard.append(f"URL:{vd.get('website')}")
        if vd.get('linkedin'): vcard.append(f"X-SOCIALPROFILE;type=linkedin:{vd.get('linkedin')}")
        if vd.get('github'): vcard.append(f"X-SOCIALPROFILE;type=github:{vd.get('github')}")
        if vd.get('whatsapp'): vcard.append(f"X-SOCIALPROFILE;type=whatsapp:{vd.get('whatsapp')}")
        
        # Address
        if any([vd.get('street'), vd.get('city'), vd.get('state'), vd.get('zip'), vd.get('country')]):
            adr = f";;{vd.get('street', '')};{vd.get('city', '')};{vd.get('state', '')};{vd.get('zip', '')};{vd.get('country', '')}"
            vcard.append(f"ADR;TYPE=WORK:{adr}")
            
        # Additional
        if vd.get('bday'): vcard.append(f"BDAY:{vd.get('bday')}")
        if vd.get('notes'): vcard.append(f"NOTE:{vd.get('notes')}")
        
        # Advanced
        for key in ['uid', 'rev', 'kind', 'geo', 'tz', 'lang', 'source', 'related']:
            if vd.get(key):
                vcard.append(f"{key.upper()}:{vd.get(key)}")
                
        vcard.append("END:VCARD")
        vcard_str = "\\n".join(vcard)
        
        response = app.make_response(vcard_str)
        response.headers['Content-Type'] = 'text/vcard; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename="contact_{qr_id}.vcf"'
        return response

# -----------------------------
# Main
# -----------------------------
        return f"Unhandled content type: {current_type}", 400

@app.route("/api/analytics/<qr_id>", methods=["GET"])
def get_analytics(qr_id):
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check ownership
    cursor.execute("SELECT id FROM qr_codes WHERE qr_id=? AND user_id=?", (qr_id, session['user_id']))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "QR code not found or unauthorized"}), 404
        
    # Get total scans
    cursor.execute("SELECT current_scans FROM qr_codes WHERE qr_id=?", (qr_id,))
    total_scans = cursor.fetchone()['current_scans']
    
    # Get browser breakdown
    cursor.execute("SELECT browser, COUNT(*) as count FROM qr_scans WHERE qr_id=? GROUP BY browser", (qr_id,))
    browsers = {row['browser']: row['count'] for row in cursor.fetchall()}
    
    # Get OS breakdown
    cursor.execute("SELECT os, COUNT(*) as count FROM qr_scans WHERE qr_id=? GROUP BY os", (qr_id,))
    oses = {row['os']: row['count'] for row in cursor.fetchall()}
    
    # Get Platform breakdown
    cursor.execute("SELECT platform, COUNT(*) as count FROM qr_scans WHERE qr_id=? GROUP BY platform", (qr_id,))
    platforms = {row['platform']: row['count'] for row in cursor.fetchall()}
    
    # Get Location breakdown (Top 5 countries)
    cursor.execute("SELECT country, COUNT(*) as count FROM qr_scans WHERE qr_id=? AND country != 'Unknown' GROUP BY country ORDER BY count DESC LIMIT 5", (qr_id,))
    locations = {row['country']: row['count'] for row in cursor.fetchall()}
    
    # Get recent scans (last 10)
    cursor.execute("SELECT timestamp, browser, os, platform, country, city FROM qr_scans WHERE qr_id=? ORDER BY timestamp DESC LIMIT 10", (qr_id,))
    recent = [dict(r) for r in cursor.fetchall()]
    
    # Get scans over time (last 7 days grouped by date)
    cursor.execute("SELECT date(timestamp) as scan_date, COUNT(*) as count FROM qr_scans WHERE qr_id=? GROUP BY date(timestamp) ORDER BY scan_date DESC LIMIT 7", (qr_id,))
    scans_over_time = {row['scan_date']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        "success": True,
        "total_scans": total_scans,
        "browsers": browsers,
        "oses": oses,
        "platforms": platforms,
        "locations": locations,
        "recent_scans": recent,
        "scans_over_time": scans_over_time
    })

if __name__ == "__main__":
    create_database()
    print("*"*50)
    print(f"WEB UI AVAILABLE AT: http://{get_local_ip()}:5000")
    print(f"WEB UI AVAILABLE AT: http://127.0.0.1:5000")
    print("*"*50)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)