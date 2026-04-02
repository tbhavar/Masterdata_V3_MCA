# MCA V3 Masterdata Solution - Setup Guide

This guide will walk you through the steps to configure the **Masterdata_V3_MCA** project for both local development and automated cloud execution.

---

## 1. GitHub Personal Access Token (PAT)

The frontend uses a GitHub PAT to trigger the automation workflow on your behalf.

### Steps to Create:
1.  Go to [GitHub Settings > Tokens (Classic)](https://github.com/settings/tokens).
2.  Click **Generate new token (classic)**.
3.  Note as: `MCA Masterdata Dispatch`.
4.  Select the **`repo`** scope (Full control of private repositories).
5.  Click **Generate token** and **copy it immediately**.

### Local Configuration:
Rename `config.example.js` to `config.js` and paste your token inside:
```javascript
const CONFIG = {
    GITHUB_PAT: "your_token_here"
};
```

---

## 2. GitHub Repository Secrets (Cloud)

For the automation script (`mca_orchestrator.py`) to run on GitHub Actions, you must set the following secrets in your repository:

### Steps to Set:
1.  Open your repository on GitHub.
2.  Go to **Settings > Secrets and variables > Actions**.
3.  Click **New repository secret** for each of these:

| Secret Name | Description |
| :--- | :--- |
| **`MCA_USER`** | Your MCA V3 portal login username. |
| **`MCA_PASS`** | Your MCA V3 portal login password. |
| **`GMAIL_USER`** | Your Gmail address (e.g., `you@gmail.com`). |
| **`GMAIL_APP_PASSWORD`** | A 16-character App Password from Google Account Security. |

> [!TIP]
> **To get a GMAIL_APP_PASSWORD**:
> 1. Go to your [Google Account > Security](https://myaccount.google.com/security).
> 2. Enable **2-Step Verification**.
> 3. Search for "App Passwords" and create one labeled `MCA Scraper`.

---

## 3. Playwright Local Installation

If you intend to run the scraper script (`mca_orchestrator.py`) directly on your machine:

1.  Install the required Python packages:
    ```bash
    pip install playwright ddddocr requests
    ```
2.  Install the Playwright browser binaries:
    ```bash
    playwright install chromium
    ```

---

## 4. Troubleshooting

- **Captcha Failures**: The `ddddocr` engine is generally accurate but may fail. The script includes retry logic, but ensure the `captcha-img` selector in MCA V3 hasn't changed.
- **Login Issues**: Ensure your MCA V3 account is not locked and that you have completed the one-time registration on the new portal.
- **Email Not Sent**: Check your `GMAIL_APP_PASSWORD` and ensure "Less secure app access" is NOT needed (App Passwords are the modern way).

---

## 5. Security Warning

> [!CAUTION]
> Never commit your `config.js` or any file containing raw passwords to a public repository. Always use **Repository Secrets** for production and `.gitignore` for local secrets.
