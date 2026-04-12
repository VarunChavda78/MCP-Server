import os
import sys
# Add parent dir to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SMTP_USER, SMTP_PASS, SMTP_SERVER, SMTP_PORT, APPROVER_EMAIL, BASE_URL
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email():
    print(f"Testing SMTP with {SMTP_SERVER}:{SMTP_PORT}")
    print(f"User: {SMTP_USER}")
    print(f"To: {APPROVER_EMAIL}")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🧪 SMTP Test: MCP DevOps Approval"
    msg["From"] = SMTP_USER
    msg["To"] = APPROVER_EMAIL

    html = f"""
    <html>
    <body>
        <h2>🧪 SMTP Test Successful</h2>
        <p>If you see this, your MCP Server can send approval emails.</p>
        <p>Base URL: {BASE_URL}</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, APPROVER_EMAIL, msg.as_string())
        print("✅ Success: Email sent!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_email()
