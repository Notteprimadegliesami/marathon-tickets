"""
TCS Amsterdam Marathon 2026 - Ticket Resale Monitor
Runs once per invocation. GitHub Actions calls it every 5 minutes.
Credentials are read from environment variables (set as GitHub Secrets).
"""

import asyncio
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.async_api import async_playwright

# ── Configuration (via environment variables / GitHub Secrets) ────────────────

EMAIL_SENDER    = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD  = os.environ["EMAIL_PASSWORD"]
EMAIL_RECIPIENT = os.environ["EMAIL_RECIPIENT"]
URL             = "https://atleta.cc/e/nhIVWn50Rcez/resale"
NO_TICKET_TEXT  = "there are currently no tickets for sale"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(available_count: int, page_text: str):
    subject = f"TICKETS AVAILABLE - TCS Amsterdam Marathon 2026 ({available_count} found)"
    body = (
        f"Good news! Tickets are now available on the resale platform.\n\n"
        f"Available: {available_count}\n\n"
        f"Buy here: {URL}\n\n"
        f"--- Page snapshot ---\n{page_text[:1500]}"
    )
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
    log.info("Email sent to %s", EMAIL_RECIPIENT)

# ── Page check ────────────────────────────────────────────────────────────────

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(3_000)
        text = await page.inner_text("body")
        await browser.close()

    lower = text.lower()
    no_tickets = NO_TICKET_TEXT in lower

    # Extract the "Available" count (appears just before the word "Available")
    # Page format: "  0\nAvailable\n323\nSold"
    available_count = 0
    for line in text.splitlines():
        line = line.strip()
        if line == "Available":
            break
        if line.isdigit():
            available_count = int(line)

    tickets_available = available_count > 0 or not no_tickets

    if tickets_available:
        log.info("TICKETS FOUND! Count=%d — sending email.", available_count)
        send_email(available_count, text)
    else:
        log.info("No tickets yet (Available=0).")

if __name__ == "__main__":
    asyncio.run(main())
