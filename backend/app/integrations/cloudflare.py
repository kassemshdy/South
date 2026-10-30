"""The one thing Janobona asks of Cloudflare: a DNS record per store.

``<sub>.janobona.com`` CNAME ``shops.myshopify.com``, **DNS only**. Shopify
issues the certificate for a connected domain itself and cannot while
Cloudflare's proxy sits in front, so ``proxied`` is always false.
"""

from __future__ import annotations

import httpx

API = "https://api.cloudflare.com/client/v4"
SHOPIFY_TARGET = "shops.myshopify.com"


class CloudflareError(Exception):
    pass


class CloudflareDns:
    def __init__(self, http: httpx.Client, token: str, zone_id: str) -> None:
        self._http = http
        self._headers = {"Authorization": f"Bearer {token}"}
        self._records = f"{API}/zones/{zone_id}/dns_records"

    def create_cname(self, name: str, target: str = SHOPIFY_TARGET) -> str:
        response = self._http.post(
            self._records,
            headers=self._headers,
            json={"type": "CNAME", "name": name, "content": target, "proxied": False, "ttl": 1},
        )
        body = response.json()
        if response.status_code >= 400 or not body.get("success"):
            messages = "; ".join(str(e.get("message")) for e in body.get("errors") or [])
            raise CloudflareError(messages or f"Cloudflare answered {response.status_code}")
        return str(body["result"]["id"])

    def delete(self, record_id: str) -> None:
        response = self._http.delete(f"{self._records}/{record_id}", headers=self._headers)
        # Already gone is as good as deleted.
        if response.status_code >= 400 and response.status_code != 404:
            raise CloudflareError(f"Cloudflare answered {response.status_code}")
