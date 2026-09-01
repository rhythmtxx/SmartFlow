"""更多工具（web_search / http_get / http_post / code_exec）测试。

运行： D:\mytools\miniforge3\envs\smartflow\python.exe test_more_tools.py
"""
import asyncio
import socket
from unittest.mock import patch

from core.tools import _check_ssrf


def fake_getaddrinfo(host, port):
    table = {
        "localhost": [("AF_INET", 0, 0, "", ("127.0.0.1", 0))],
        "api.github.com": [("AF_INET", 0, 0, "", ("140.82.112.6", 0))],
        "evil.com": [("AF_INET", 0, 0, "", ("10.0.0.5", 0))],
    }
    if host not in table:
        raise socket.gaierror("mock 解析失败")
    return table[host]


BLOCKED = [
    "http://127.0.0.1:8000/", "http://localhost/", "http://[::1]/",
    "http://10.0.0.1/", "http://172.16.0.1/", "http://192.168.1.1/",
    "http://169.254.169.254/", "file:///etc/passwd", "ftp://example.com/x",
]


def test_ssrf_blocked():
    with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
        for url in BLOCKED:
            reason = _check_ssrf(url)
            assert reason is not None, f"应拦截: {url}"


def test_ssrf_allowed():
    with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
        assert _check_ssrf("http://api.github.com/") is None
        assert _check_ssrf("https://api.github.com/") is None


def main():
    test_ssrf_blocked()
    print("✓ SSRF 拦截用例通过")
    test_ssrf_allowed()
    print("✓ SSRF 放行用例通过")
    print("SSRF 防护测试: 全部通过")


if __name__ == "__main__":
    main()
