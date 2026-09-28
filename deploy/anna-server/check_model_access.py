"""Print only the HTTP status for Anna's configured OpenAI model access."""

import os
import urllib.error
import urllib.request


request = urllib.request.Request(
    "https://api.openai.com/v1/models/gpt-realtime-1.5",
    headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
)
try:
    print(urllib.request.urlopen(request, timeout=15).status)
except urllib.error.HTTPError as error:
    print(error.code)
