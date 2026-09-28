"""Read the last inbound caller number from the FRITZ!Box call log via TR-064.

Uses only httpx (already a telephony dependency). No extra packages required.
The FRITZ!Box does not forward the original caller ID in SIP headers for
internal registrations, but it does record it in the call log immediately.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx


_SOAP_BODY = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
  <s:Body>
    <u:GetCallList xmlns:u="urn:dslforum-org:service:X_AVM-DE_OnTel:1"/>
  </s:Body>
</s:Envelope>"""

_SOAP_ACTION = "urn:dslforum-org:service:X_AVM-DE_OnTel:1#GetCallList"
_TR064_URL = "http://{host}:49000/upnp/control/x_contact"


async def get_last_inbound_caller(
    host: str,
    username: str,
    password: str,
    *,
    max_age_seconds: int = 30,
) -> str:
    """Return the last inbound caller number recorded in the FRITZ!Box call log.

    Returns an empty string when the number is withheld, unavailable, or the
    call log cannot be read. Never raises; failures are silent by design so a
    missing caller number never blocks a call.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            soap = await client.post(
                _TR064_URL.format(host=host),
                content=_SOAP_BODY.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": _SOAP_ACTION,
                },
                auth=(username, password),
            )
        if soap.status_code != 200:
            return ""
        url_match = re.search(r"<NewCallListURL>(.*?)</NewCallListURL>", soap.text)
        if not url_match:
            return ""
        async with httpx.AsyncClient(timeout=5.0) as client:
            log = await client.get(url_match.group(1), auth=(username, password))
        if log.status_code != 200:
            return ""
        return _extract_last_inbound(log.text, max_age_seconds)
    except Exception:
        return ""


def _extract_last_inbound(xml_text: str, max_age_seconds: int) -> str:
    """Parse the call log XML and return the most recent inbound caller number."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return ""
    now = datetime.now(timezone.utc)
    for call in root.iter("Call"):
        # Type 1 = inbound, Type 2 = missed — both have the caller number.
        call_type = call.findtext("Type", "")
        if call_type not in ("1", "2"):
            continue
        date_text = call.findtext("Date", "")
        try:
            # FRITZ!Box format: "25.07.26 14:32" (local time, no TZ)
            call_time = datetime.strptime(date_text, "%d.%m.%y %H:%M")
            age = abs((now.replace(tzinfo=None) - call_time).total_seconds())
            if age > max_age_seconds:
                continue
        except ValueError:
            continue
        number = call.findtext("Caller", "").strip()
        # Withheld or unavailable numbers are empty or contain only non-digits.
        digits = re.sub(r"\D", "", number)
        if len(digits) >= 6:
            return number
    return ""
