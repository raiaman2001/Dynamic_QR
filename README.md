# Dynamic QR Pro 🚀

Welcome to **Dynamic QR Pro**, an enterprise-level, highly customizable Dynamic QR Code Generator and Management System built with Python (Flask) and SQLite.

## What is a Dynamic QR Code?
Unlike static QR codes that cannot be changed once printed, **Dynamic QR Codes** allow you to update the destination link or content behind the QR code at any time without reprinting the physical code.

## Key Features ✨

### 1. Smart & Advanced Routing
- **Device-Based Routing**: Redirect Apple users to the App Store and Android users to the Play Store.
- **Time-Based Routing**: Send users to a "Daytime URL" during the day and a "Nighttime URL" at night.
- **A/B Testing**: Provide multiple URLs, and the system will randomly distribute traffic among them to test which link performs better.
- **Geo-Fencing**: Block specific countries from accessing your QR codes.

### 2. Deep Analytics 📊
Track exactly how your QR codes are performing. The built-in dashboard shows:
- Total scan counts.
- Real-time visitor locations (Country/City).
- Device types, Operating Systems (iOS, Android, Windows), and Browsers.
- IP Addresses and timestamps.

### 3. Security & Limits 🔒
- **Password Protection**: Ask users for a password before they can access the QR content.
- **Scan Limits**: Make the QR code expire automatically after a certain number of scans.
- **Time Expiry**: Set a specific date and time for the QR code to expire.
- **One-Time Use**: A QR code that destroys itself after the very first scan.

### 4. Secure Authentication System
- Full Login/Registration system.
- **Forgot Password**: Features real SMTP Email integration to securely send 6-digit password reset codes to the user's email address.

## How to Run the Project Locally 💻

1. **Clone the repository:**
   ```bash
   git clone https://github.com/raiaman2001/Dynamic_QR.git
   cd Dynamic_QR
   ```

2. **Install requirements:**
   Make sure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Environment Variables (Email Settings):**
   Create a `.env` file in the root folder to configure SMTP for password resets and scan alerts:
   ```env
   SMTP_EMAIL=your_gmail_address@gmail.com
   SMTP_PASSWORD=your_16_character_app_password
   ```

4. **Run the server:**
   ```bash
   python Qr.py
   ```
   Open your browser and go to `http://localhost:5000`.

## Folder Structure 📂
- `Qr.py`: The main Flask backend server.
- `templates/ui.html`: The beautiful, responsive frontend UI.
- `static/style.css` & `static/script.js`: Clean separated styling and frontend logic.
- `qrcodes/`: Directory where generated QR code image files are stored.
- `uploads/`: Directory for user-uploaded files (like PDFs or logos).
- `qr_pro.db`: The SQLite database (automatically created on first run).

---
*Built with ❤️ for powerful QR management.*
