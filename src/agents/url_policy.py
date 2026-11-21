from __future__ import annotations

import asyncio
import http.client
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit


class UnsafeURL(ValueError):
    pass


@dataclass(frozen=True)
class PublicTarget:
    url: str
    hostname: str
    port: int
    ip_address: str
    request_target: str
    tls: bool


def _public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global


def _resolve(hostname: str, port: int) -> list[str]:
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise UnsafeURL("The destination host could not be resolved.") from exc
    addresses = sorted({record[4][0].split("%")[0] for record in records})
    if not addresses or any(not _public_ip(address) for address in addresses):
        raise UnsafeURL("The destination resolves to a non-public network address.")
    return addresses


async def validate_public_http_url(url: str) -> PublicTarget:
    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURL("The destination URL is malformed.") from exc
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").rstrip(".").lower()
    if scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
        raise UnsafeURL("Only public HTTP and HTTPS URLs without credentials can be fetched.")
    if port is None:
        port = 443 if scheme == "https" else 80
    if port != (443 if scheme == "https" else 80):
        raise UnsafeURL("Only the standard HTTP and HTTPS ports can be fetched.")
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".localhost", ".local", ".internal")):
        raise UnsafeURL("Local and metadata destinations cannot be fetched.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        addresses = await asyncio.to_thread(_resolve, host, port)
    else:
        addresses = [host]
        if not _public_ip(host):
            raise UnsafeURL("The destination resolves to a non-public network address.")
    path = parsed.path or "/"
    request_target = path + (f"?{parsed.query}" if parsed.query else "")
    normalized = urlunsplit((scheme, parsed.netloc, path, parsed.query, ""))
    return PublicTarget(normalized, host, port, addresses[0], request_target, scheme == "https")


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, target: PublicTarget, timeout: float):
        super().__init__(target.hostname, target.port, timeout=timeout)
        self.target = target

    def _new_conn(self):
        return socket.create_connection((self.target.ip_address, self.target.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, target: PublicTarget, timeout: float):
        super().__init__(target.hostname, target.port, timeout=timeout)
        self.target = target

    def _new_conn(self):
        return socket.create_connection((self.target.ip_address, self.target.port), self.timeout)


def _request(target: PublicTarget, timeout: float, max_bytes: int) -> tuple[int, dict[str, str], bytes]:
    connection = (
        _PinnedHTTPSConnection(target, timeout)
        if target.tls
        else _PinnedHTTPConnection(target, timeout)
    )
    try:
        connection.request(
            "GET",
            target.request_target,
            headers={
                "Host": target.hostname if target.port in {80, 443} else f"{target.hostname}:{target.port}",
                "User-Agent": "HandoffResearch/1.0 (+https://github.com/)",
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise UnsafeURL("The page exceeded the configured response-size limit.")
        return response.status, {key.lower(): value for key, value in response.getheaders()}, payload
    finally:
        connection.close()


async def fetch_public_page(
    url: str, *, timeout: float = 12, max_bytes: int = 1_000_000, max_redirects: int = 3
) -> tuple[str, str, bytes]:
    current = url
    for redirect_count in range(max_redirects + 1):
        target = await validate_public_http_url(current)
        status, headers, payload = await asyncio.to_thread(_request, target, timeout, max_bytes)
        if status in {301, 302, 303, 307, 308}:
            location = headers.get("location")
            if not location or redirect_count == max_redirects:
                raise UnsafeURL("The page redirected too many times.")
            current = urljoin(target.url, location)
            continue
        if status < 200 or status >= 300:
            raise UnsafeURL(f"The page returned HTTP {status}.")
        content_type = headers.get("content-type", "").lower()
        if not any(kind in content_type for kind in ("text/html", "application/xhtml+xml", "text/plain")):
            raise UnsafeURL("The destination did not return a readable text page.")
        return target.url, content_type, payload
    raise UnsafeURL("The page could not be fetched safely.")
