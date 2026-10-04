---
title: "Zero-Cloud Local LAN & Offline Architecture"
date: "2026-10-05"
time: "01:38:30+05:30"
author: "deadsec778 & Antigravity AI"
tags:
  - security
  - local-mode
  - offline-first
  - lan
  - zero-knowledge
  - cryptography
type: "Architecture Deep-Dive"
status: "Active"
version: "1.0.0"
---

# 🔒 Zero-Cloud Local LAN & Offline Architecture

> [!NOTE]
> Related Notes: [[Home]], [[Integrations-Module-Feature-Flags-and-Local-Mode]], [[Database-Migrations-and-GitHub-Reference-Changelog]]

---

## 🎯 1. Design Principles for Local Mode

When `INTEGRATIONS_ENABLED=false` is configured in `.env`, the password manager guarantees:
1. **Zero Outbound Network Requests**: No sockets opened to Google OAuth, Google UserInfo API, or Gmail SMTP servers.
2. **Instant Local User Registration**: Eliminates the external email OTP dependency so administrators and users can sign up immediately on private LAN subnets.
3. **Graceful Degraded UI**: External sign-in buttons (Google SSO) and email recovery inputs automatically hide or display explanatory local badges.
4. **Local Security Preservation**: PBKDF2 (390,000 rounds) + Fernet encryption remain 100% per-user and zero-knowledge.

---

## 🔄 2. Local Mode vs Cloud Mode Workflows

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as Flask Application
    participant DB as MariaDB / MySQL
    participant Mail as Gmail SMTP

    Note over User,Mail: SCENARIO A: Local LAN Mode (INTEGRATIONS_ENABLED=false)
    User->>App: POST /signup (username, email, password)
    App->>DB: Check uniqueness (username, email)
    App->>DB: INSERT INTO users (bcrypt hash, PBKDF2 salt)
    App-->>User: 302 Redirect to / (Success Flash: Local Mode)

    Note over User,Mail: SCENARIO B: Cloud / Hybrid Mode (INTEGRATIONS_ENABLED=true)
    User->>App: POST /signup (username, email, password)
    App->>DB: INSERT INTO email_otps (otp_hash, expires_at)
    App->>Mail: Send 6-digit OTP email
    Mail-->>User: Delivers Verification Code
    User->>App: POST /signup/verify (otp_code)
    App->>DB: Verify OTP hash & mark is_used=1
    App->>DB: INSERT INTO users (bcrypt hash, PBKDF2 salt)
    App-->>User: 302 Redirect to / (Account Verified)
```

---

## 🛡️ 3. Credential Recovery in Air-Gapped Environments

In cloud mode, forgotten passwords are recovered via one-time email OTP tokens. In local LAN mode:
- The `/forgot-password` endpoint displays an alert banner explaining that email delivery is disabled.
- Password resets are handled securely through administrative role permissions (`role = 'admin'`), where admins can reset or modify user accounts in the dashboard.

---

## 🧪 4. Verification

This architecture is validated by automated tests in `pass/api/test_integration_flags.py`:
- `test_local_signup_creates_account_directly`
- `test_google_routes_guard_when_disabled`
- `test_login_page_google_button_hidden_when_disabled`
