"""Prefer IPv4 for outbound connections.

On networks where IPv6 is advertised but not routable, Python tries the IPv6 address first and waits for the
whole connect timeout before falling back to IPv4 (a 3 s API limit becomes useless). Sorting IPv4 first avoids it;
IPv6 remains as a fallback.
"""
import socket

_orig = socket.getaddrinfo


def _ipv4_first(*args, **kwargs):
    res = _orig(*args, **kwargs)
    return sorted(res, key=lambda r: r[0] != socket.AF_INET)


def install():
    if socket.getaddrinfo is _orig:
        socket.getaddrinfo = _ipv4_first
