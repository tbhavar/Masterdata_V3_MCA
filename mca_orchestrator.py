import os
import json
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import playwright.sync_api as p
from playwright_stealth import stealth_sync
import ddddocr
import requests
from email.mime.base import MIMEBase
from email import encoders

# Constants
ARCHIVE_DIR = "master_data_archive"
DISCLAIMER = "These master data details are for information purposes only and not to be relied upon for any legal or financial purpose. Any reliance leading to any losses is the sole responsibility of the decision-maker."
BRANDING = "Generated via tbhavar.in - Office of Tanmay Bhavar, CA."

def solve_captcha(page, selector):
    ocr = ddddocr.DdddOcr(show_ad=False)
    captcha_img = page.query_selector(selector)
    if captcha_img:
        captcha_img.screenshot(path="captcha.png")
        with open("captcha.png", 'rb') as f:
            img_bytes = f.read()
        res = ocr.classification(img_bytes)
        return res
    return ""

def scrape_mca_master_data(cin, username, password):
    with p.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        # Login
        print(f"Logging into MCA V3 for {cin}...")
        page.goto("https://www.mca.gov.in/content/mca/global/en/login.html")
        page.fill("#username", username)
        page.fill("#password", password)
        
        # Solving initial login captcha
        captcha_code = solve_captcha(page, "#captcha-img")
        page.fill("#captcha", captcha_code)
        page.click("#login-btn")
        
        # Check if login success (Wait for navigation or specific element)
        page.wait_for_timeout(3000)
        
        # Navigate to Master Data
        print("Navigating to Company Master Data...")
        page.goto("https://www.mca.gov.in/content/mca/global/en/mca/master-data/v3-company-master-data.html")
        
        # Fill CIN
        page.fill("#companyID", cin)
        
        # Solve Master Data Page Captcha
        captcha_code = solve_captcha(page, "#captcha-img")
        page.fill("#captcha", captcha_code)
        page.click("#search-btn")
        
        # Wait for results
        page.wait_for_selector(".master-data-table", timeout=10000)
        
        # Extract Table Data
        rows = page.query_selector_all(".master-data-table tr")
        data = {}
        for row in rows:
            cols = row.query_selector_all("td")
            if len(cols) == 2:
                key = cols[0].inner_text().strip()
                val = cols[1].inner_text().strip()
                data[key] = val
        
        browser.close()
        return data

def generate_html_report(company_name, data):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    filename = f"{company_name.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M')}.html"
    filepath = os.path.join(ARCHIVE_DIR, filename)
    
    table_rows = "".join([f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in data.items()])
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', sans-serif; padding: 40px; color: #333; }}
            .report-card {{ border: 1px solid #eee; border-radius: 8px; padding: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            h1 {{ color: #1a1a1a; margin-bottom: 20px; font-size: 24px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            td {{ padding: 12px; border-bottom: 1px solid #f0f0f0; }}
            .header {{ display: flex; justify-content: space-between; margin-bottom: 30px; border-bottom: 2px solid #d4af37; padding-bottom: 15px; }}
            .branding {{ color: #d4af37; font-weight: bold; }}
            .timestamp {{ font-size: 0.9rem; color: #666; }}
            .footer {{ margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px; font-size: 0.85rem; color: #888; }}
        </style>
    </head>
    <body>
        <div class="report-card">
            <div class="header">
                <div class="branding">TBHAVAR.IN</div>
                <div class="timestamp">Generated on: {now}</div>
            </div>
            <h1>Company Master Data: {company_name}</h1>
            <table>
                {table_rows}
            </table>
            <div class="footer">
                <p>{BRANDING}</p>
                <p><strong>Disclaimer:</strong> {DISCLAIMER}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(filepath, "w") as f:
        f.write(html_content)
    
    return filename, filepath

def send_email(to_email, company_name, report_url, message_type="success", error_message="", attachment_path=None):
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")

    template_file = "email_template.html" if message_type == "success" else "error_template.html"
    with open(template_file, "r") as f:
        template = f.read()
    
    if message_type == "success":
        body = template.replace("{{COMPANY_NAME}}", company_name) \
                       .replace("{{REPORT_URL}}", report_url) \
                       .replace("{{DISCLAIMER}}", DISCLAIMER)
        subject = f"Master Data Report: {company_name}"
    else:
        body = template.replace("{{COMPANY_NAME}}", company_name) \
                       .replace("{{ERROR_MESSAGE}}", error_message) \
                       .replace("{{DISCLAIMER}}", DISCLAIMER)
        subject = f"ALERT: Master Data Automation Issue - {company_name}"

    msg = MIMEMultipart()
    msg['From'] = f"TBHAVAR Master Data Portal <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(attachment_path)}",
            )
            msg.attach(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email} (Type: {message_type})")
    except Exception as e:
        print(f"Failed to send email: {e}")

def scrape_mca_master_data(cin, username, password):
    ERROR_DIR = "error_logs"
    AUTH_FILE = "auth_state.json"
    if not os.path.exists(ERROR_DIR):
        os.makedirs(ERROR_DIR)

    with p.sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        
        # Load session if it exists, otherwise create a new context
        if os.path.exists(AUTH_FILE):
            print("Using existing session (auth_state.json)...")
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800},
                storage_state=AUTH_FILE
            )
        else:
            print("No session found. Will attempt a fresh login...")
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
        
        page = context.new_page()
        stealth_sync(page) # Apply stealth to mask automation

        try:
            # First, check if we're already logged in by trying to visit Master Data
            print("Attempting to access Company Master Data...")
            page.goto("https://www.mca.gov.in/content/mca/global/en/mca/master-data/v3-company-master-data.html", wait_until="networkidle", timeout=60000)
            
            # Maintenance Check
            if "Maintenance" in page.content() or "undergoing scheduled maintenance" in page.content():
                raise Exception("MCA Portal is currently under maintenance. Please try again later.")

            # Check if redirected to login
            if "fologin.html" in page.url or "login.html" in page.url:
                print("Session expired or missing. Navigating to Login...")
                page.goto("https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html", wait_until="networkidle", timeout=60000)
                
                # Wait for login form
                print("Waiting for login form...")
                page.wait_for_selector("#username", timeout=30000)
                page.fill("#username", username)
                page.fill("#password", password)
                
                # Solving initial login captcha
                captcha_code = solve_captcha(page, "#captcha-img")
                page.fill("#captcha", captcha_code)
                page.click("#login-btn")
                
                # Check for login success
                page.wait_for_timeout(5000)
                
                # Save session for next time
                context.storage_state(path=AUTH_FILE)
                print("New session saved to auth_state.json")
                
                # Re-navigate to Master Data
                page.goto("https://www.mca.gov.in/content/mca/global/en/mca/master-data/v3-company-master-data.html", wait_until="networkidle", timeout=60000)

            # Fill CIN
            page.wait_for_selector("#companyID")
            page.fill("#companyID", cin)
            
            # Solve Master Data Page Captcha
            captcha_code = solve_captcha(page, "#captcha-img")
            page.fill("#captcha", captcha_code)
            page.click("#search-btn")
            
            # Wait for results
            page.wait_for_selector(".master-data-table", timeout=20000)
            
            # Extract Table Data
            rows = page.query_selector_all(".master-data-table tr")
            if not rows:
                raise Exception("No master data table found. Search may have failed or timed out.")

            data = {}
            for row in rows:
                cols = row.query_selector_all("td")
                if len(cols) == 2:
                    key = cols[0].inner_text().strip()
                    val = cols[1].inner_text().strip()
                    data[key] = val
            
            browser.close()
            return data, None
            
        except Exception as e:
            error_msg = str(e)
            print(f"Scraping failed: {error_msg}")
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(ERROR_DIR, f"error_{cin}_{timestamp}.png")
            try:
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"Error screenshot saved to {screenshot_path}")
            except:
                print("Failed to capture error screenshot.")
                screenshot_path = None
            browser.close()
            return None, (error_msg, screenshot_path)

def main():
    # Load parameters from environment or payload
    payload_str = os.environ.get("MCA_PAYLOAD", "{}")
    try:
        config = json.loads(payload_str)
    except json.JSONDecodeError:
        config = {}

    cins = config.get("cins", [])
    user_email = config.get("email", "")
    force_refresh = config.get("force_refresh", False)
    
    username = os.environ.get("MCA_USER")
    password = os.environ.get("MCA_PASS")

    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    for cin in cins:
        try:
            cached_file = None
            if not force_refresh:
                for f in os.listdir(ARCHIVE_DIR):
                    if f.startswith(cin):
                        cached_file = f
                        break
            
            if cached_file:
                print(f"Fetching {cin} from cache...")
                report_url = f"https://tbhavar.github.io/Masterdata_V3_MCA/{ARCHIVE_DIR}/{cached_file}"
                send_email(user_email, cin, report_url)
                continue

            # Scrape live data
            data, error_info = scrape_mca_master_data(cin, username, password)
            
            if error_info:
                error_msg, screenshot_path = error_info
                send_email(user_email, cin, None, message_type="error", error_message=error_msg, attachment_path=screenshot_path)
                continue

            company_name = data.get("Company Name", cin)
            filename, filepath = generate_html_report(company_name, data)
            
            # Email success report
            report_url = f"https://tbhavar.github.io/Masterdata_V3_MCA/{ARCHIVE_DIR}/{filename}"
            send_email(user_email, company_name, report_url)
            
        except Exception as e:
            print(f"Critical error processing {cin}: {e}")

if __name__ == "__main__":
    main()
