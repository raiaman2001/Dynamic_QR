<div align="center">

<img src="https://api.iconify.design/lucide/qr-code.svg?color=%236366f1" width="64" alt="Dynamic QR Pro logo" />

# Dynamic QR Pro

**A customizable Dynamic QR Code generator and management system with smart routing, deep analytics, and built-in security.**

<br />

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-success)

</div>

---

## <img src="https://api.iconify.design/lucide/info.svg?color=%236366f1" width="24" align="top" /> Overview

Dynamic QR Pro is a Flask-based web application for creating and managing **Dynamic QR Codes**.

Unlike static QR codes, which cannot be changed once printed, a dynamic QR code encodes a short redirect link. The destination behind that link can be updated at any time, so the printed code never needs to be reprinted.

---

## <img src="https://api.iconify.design/lucide/layers.svg?color=%236366f1" width="24" align="top" /> Key Features

### <img src="https://api.iconify.design/lucide/route.svg?color=%236366f1" width="20" align="top" /> Smart and Advanced Routing

| Feature | Description |
|---|---|
| **Device-Based Routing** | Redirect iOS users to the App Store and Android users to the Play Store. |
| **Time-Based Routing** | Serve a daytime URL during the day and a nighttime URL at night. |
| **A/B Testing** | Provide multiple URLs and traffic is distributed randomly among them to compare performance. |
| **Geo-Fencing** | Block access to your QR codes from specific countries. |

### <img src="https://api.iconify.design/lucide/activity.svg?color=%236366f1" width="20" align="top" /> Deep Analytics

A built-in dashboard tracks how every QR code performs:

- Total scan count
- Visitor location (country and city)
- Device type, operating system (iOS, Android, Windows) and browser
- IP address and timestamp of each scan

### <img src="https://api.iconify.design/lucide/shield-check.svg?color=%236366f1" width="20" align="top" /> Security and Limits

| Feature | Description |
|---|---|
| **Password Protection** | Require a password before the QR content is accessible. |
| **Scan Limits** | Automatically expire a QR code after a set number of scans. |
| **Time Expiry** | Expire a QR code at a specific date and time. |
| **One-Time Use** | The QR code deactivates itself after the first scan. |

### <img src="https://api.iconify.design/lucide/key-round.svg?color=%236366f1" width="20" align="top" /> Authentication System

- Complete login and registration flow
- Forgot-password support with SMTP email integration, delivering a 6-digit reset code to the user's email

---

## <img src="https://api.iconify.design/lucide/cpu.svg?color=%236366f1" width="24" align="top" /> Tech Stack

<p>
  <img src="https://skillicons.dev/icons?i=python,flask,sqlite,html,css,js,git,github" alt="Tech stack" />
</p>

---

## <img src="https://api.iconify.design/lucide/terminal.svg?color=%236366f1" width="24" align="top" /> Getting Started

### Prerequisites

- Python 3.9 or higher
- pip
- A Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) (required for password-reset emails)

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/raiaman2001/Dynamic_QR.git
cd Dynamic_QR
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Configure environment variables**

Create a `.env` file in the project root to enable SMTP for password resets and scan alerts:

```env
SMTP_EMAIL=your_gmail_address@gmail.com
SMTP_PASSWORD=your_16_character_app_password
```

> **Note:** Never commit your `.env` file. Add it to `.gitignore` so your credentials stay private.

**4. Run the server**

```bash
python Qr.py
```

Open your browser and visit **http://localhost:5000**.

---

## <img src="https://api.iconify.design/lucide/folder-tree.svg?color=%236366f1" width="24" align="top" /> Project Structure

```text
Dynamic_QR/
├── Qr.py               # Main Flask backend server
├── templates/
│   └── ui.html         # Responsive frontend UI
├── static/
│   ├── style.css       # Styling
│   └── script.js       # Frontend logic
├── qrcodes/            # Generated QR code images
├── uploads/            # User-uploaded files (PDFs, logos)
├── qr_pro.db           # SQLite database (auto-created on first run)
├── requirements.txt
└── .env                # SMTP credentials (not committed)
```

---

## <img src="https://api.iconify.design/lucide/user.svg?color=%236366f1" width="24" align="top" /> Author

**Aman Rai**

[![GitHub](https://img.shields.io/badge/GitHub-raiaman2001-181717?logo=github&logoColor=white)](https://github.com/raiaman2001)
