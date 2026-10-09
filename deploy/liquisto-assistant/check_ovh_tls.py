"""Check server-verified TLS only, without mailbox login or message access."""

import imaplib
import json
import smtplib
import ssl

results = {"imap_tls": False, "smtp_starttls": False, "authentication_tested": False,
           "messages_read": False, "messages_sent": False}
context = ssl.create_default_context()
try:
    with imaplib.IMAP4_SSL("ssl0.ovh.net", 993, ssl_context=context, timeout=15) as inbox:
        results["imap_tls"] = bool(inbox.sock.version())
    with smtplib.SMTP("ssl0.ovh.net", 587, timeout=15) as smtp:
        smtp.ehlo()
        if smtp.has_extn("starttls"):
            smtp.starttls(context=context)
            smtp.ehlo()
            results["smtp_starttls"] = bool(smtp.sock.version())
except Exception:
    results["failed_check"] = "ovh-tls-handshake"
print(json.dumps(results, sort_keys=True))
raise SystemExit(0 if results["imap_tls"] and results["smtp_starttls"] else 1)
