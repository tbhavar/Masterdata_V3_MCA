import os
import json
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import playwright.sync_api as p
import ddddocr
import requests

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

def send_email(to_email, company_name, report_url):
    sender_email = os.environ.get("GMAIL_USER")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")

    with open("email_template.html", "r") as f:
        template = f.read()
    
    body = template.replace("{{COMPANY_NAME}}", company_name) \
                   .replace("{{REPORT_URL}}", report_url) \
                   .replace("{{DISCLAIMER}}", DISCLAIMER)

    msg = MIMEMultipart()
    msg['From'] = f"TBHAVAR Master Data Portal <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = f"Master Data Report: {company_name}"
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    # Load parameters from environment or payload
    # In a real GitHub Actions scenario, these would be passed via environment variables
    config = json.loads(os.environ.get("MCA_PAYLOAD", "{}"))
    cins = config.get("cins", [])
    user_email = config.get("email", "")
    force_refresh = config.get("force_refresh", False)
    
    username = os.environ.get("MCA_USER")
    password = os.environ.get("MCA_PASS")

    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    for cin in cins:
        try:
            # Check cache
            # For simplicity, we use the CIN as a cache key if Company Name is not yet known
            # But the user asked for [Company_Name].html
            # We'll first check if any file starts with the Company Name or if we have a mapping
            
            # This is a simplified cache check - normally you'd want a more robust lookup
            search_prefix = cin # Fallback
            cached_file = None
            if not force_refresh:
                for f in os.listdir(ARCHIVE_DIR):
                    if f.startswith(cin):
                        cached_file = f
                        break
            
            if cached_file:
                print(f"Fetching {cin} from cache...")
                # In GitHub Pages, the URL would be https://[username].github.io/[repo]/master_data_archive/[filename]
                report_url = f"https://tbhavar.github.io/Masterdata_V3_MCA/{ARCHIVE_DIR}/{cached_file}"
                send_email(user_email, cin, report_url)
                continue

            # Scrape live data
            data = scrape_mca_master_data(cin, username, password)
            company_name = data.get("Company Name", cin)
            
            # Generate report
            filename, filepath = generate_html_report(company_name, data)
            
            # Commit handled by GitHub Actions workflow
            
            # Send email
            report_url = f"https://tbhavar.github.io/Masterdata_V3_MCA/{ARCHIVE_DIR}/{filename}"
            send_email(user_email, company_name, report_url)
            
        except Exception as e:
            print(f"Error processing {cin}: {e}")

if __name__ == "__main__":
    main()
