# 📒 Opus Pro: Project Ledger

This is the central log of all development actions, feature updates, and usage guides.

---

## 🗓️ May 16, 2026

### ✅ Completed Actions
1.  **Stripe Integration**: Fully wired the frontend to the backend Stripe Checkout flow.
2.  **Monetization Logic**: Implemented a 15-minute free limit and mandatory watermarks for free users.
3.  **Pro Tier**: Enabled automatic watermark removal and quota increase upon successful Stripe payment.
4.  **Google OAuth**: Added UI and logic for "Continue with Google" login.
5.  **Branching Strategy**: Established `main` (production) and `dev` (development) git branches.
6.  **Professional Tooling**: Added smoke tests, a dev helper script (`dev.ps1`), and updated `.env.example`.
7.  **Bug Fixes**: Resolved a critical syntax error in `script.js` that disabled all buttons.

### 🛠️ Current System Status
*   **Backend**: Running in Docker (FastAPI + Celery + Redis).
*   **Database**: SQLite (`opus_pro.db`) tracking users and jobs.
*   **Payments**: Connected to Stripe Test Mode.
*   **Auth**: Connected to Supabase.

---

## 📖 How to Use Everything

### 🚀 Running the Project
Use the new helper script:
```powershell
.\scripts\dev.ps1 run
```

### 💳 Testing Payments
1.  Open the app and log in.
2.  Click the **FREE** tier badge.
3.  Click **Start 7-Day Free Trial**.
4.  Use test card `4242 4242 4242 4242` on the Stripe page.
5.  **Important**: Keep `stripe listen` running in a separate terminal to confirm the payment.

### 🔍 Running Health Checks
Before merging or deploying, run the smoke test:
```powershell
.\scripts\dev.ps1 test
```

### 📜 Viewing Logs
To see real-time backend activity and errors:
```powershell
.\scripts\dev.ps1 logs
```

---

## 📝 Pending Items
- [ ] Enable Google OAuth in Supabase Dashboard (User Action).
- [ ] Add real Price IDs for Production.
- [ ] Implement face-tracking sensitivity settings.
