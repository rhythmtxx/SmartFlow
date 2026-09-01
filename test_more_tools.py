"""更多工具（web_search / http_get / http_post / code_exec）测试。

运行： D:\mytools\miniforge3\envs\smartflow\python.exe test_more_tools.py
"""
import asyncio
import socket
import httpx
from unittest.mock import patch

from core.tools import _check_ssrf, ToolRegistry, WebSearchTool, HttpGetTool


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


# ---- web_search ----

def test_web_search_no_key():
    tool = WebSearchTool(api_key="")
    result = asyncio.run(tool.execute(query="今天天气"))
    assert "未配置" in result and "Tavily" in result, result


def test_web_search_formats_results():
    tool = WebSearchTool(api_key="test-key")

    async def _run():
        async def fake_fetch(query, max_results):
            return [{"title": "AI 新闻", "url": "https://example.com/a", "content": "摘要内容" * 30}]
        tool._fetch = fake_fetch
        return await tool.execute(query="AI 新闻", max_results=1)

    result = asyncio.run(_run())
    assert "AI 新闻" in result and "https://example.com/a" in result
    assert len(result) <= 2000


def test_web_search_registered_with_config():
    reg = ToolRegistry(tool_config={"web_search": {"api_key": "k"}})
    assert "web_search" in reg.tools


# ---- http_get ----

def test_http_get_ssrf_blocked():
    tool = HttpGetTool()
    result = asyncio.run(tool.execute(url="http://127.0.0.1/"))
    assert "SSRF" in result, result


def test_http_get_success_and_404():
    async def _run():
        tool = HttpGetTool()
        with patch.object(httpx, "AsyncClient", return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda req: httpx.Response(200, text="hello world" * 5000)))):
            ok = await tool.execute(url="https://api.github.com/")
        assert "200" in ok and "hello world" in ok and "截断" in ok, ok[:200]
        with patch.object(httpx, "AsyncClient", return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda req: httpx.Response(404, text="nope")))):
            nf = await tool.execute(url="https://api.github.com/")
        assert "404" in nf, nf
    asyncio.run(_run())


def test_http_get_redirect_to_internal_blocked():
    async def _run():
        tool = HttpGetTool()
        with patch.object(httpx, "AsyncClient", return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(lambda req: httpx.Response(
                    302, headers={"location": "http://127.0.0.1/"})))):
            result = await tool.execute(url="https://api.github.com/")
        assert "重定向目标被拦截" in result and "SSRF" in result, result
    asyncio.run(_run())


def test_http_get_timeout():
    async def _run():
        tool = HttpGetTool()

        def raise_timeout(req):
            raise httpx.ReadTimeout("t")

        with patch.object(httpx, "AsyncClient", return_value=httpx.AsyncClient(
                transport=httpx.MockTransport(raise_timeout))):
            result = await tool.execute(url="https://api.github.com/")
        assert "超时" in result or "失败" in result, result
    asyncio.run(_run())


def main():
    test_ssrf_blocked()
    print("✓ SSRF 拦截用例通过")
    test_ssrf_allowed()
    print("✓ SSRF 放行用例通过")
    test_web_search_no_key()
    print("✓ web_search 无 Key 提示通过")
    test_web_search_formats_results()
    print("✓ web_search 格式化输出通过")
    test_web_search_registered_with_config()
    print("✓ web_search 配置注册通过")
    test_http_get_ssrf_blocked()
    print("✓ http_get SSRF 拦截通过")
    test_http_get_success_and_404()
    print("✓ http_get 200/404 与截断通过")
    test_http_get_redirect_to_internal_blocked()
    print("✓ http_get 重定向 SSRF 拦截通过")
    test_http_get_timeout()
    print("✓ http_get 超时错误处理通过")
    print("更多工具测试: 全部通过")


if __name__ == "__main__":
    main()
