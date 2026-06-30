"""SSH 代理 — ProxyJump / SOCKS5 / HTTP socket 工厂"""
import socket

import paramiko


def make_socks5_socket(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 30,
) -> socket.socket:
    """通过 SOCKS5 代理建立到目标的 TCP socket"""
    import socks  # PySocks

    s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
    s.set_proxy(socks.SOCKS5, proxy_host, proxy_port,
                username=username, password=password)
    s.settimeout(timeout)
    s.connect((target_host, target_port))
    return s


def make_http_connect_socket(
    proxy_host: str,
    proxy_port: int,
    target_host: str,
    target_port: int,
    username: str | None = None,
    password: str | None = None,
    timeout: int = 30,
) -> socket.socket:
    """通过 HTTP CONNECT 隧道建立到目标的 socket"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((proxy_host, proxy_port))
    auth = ""
    if username:
        import base64
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        auth = f"Proxy-Authorization: Basic {token}\r\n"
    req = (
        f"CONNECT {target_host}:{target_port} HTTP/1.1\r\n"
        f"Host: {target_host}:{target_port}\r\n"
        f"{auth}\r\n"
    )
    s.sendall(req.encode())
    resp = s.recv(4096).decode("utf-8", "replace")
    if "200" not in resp.split("\r\n")[0]:
        s.close()
        raise ConnectionError(f"HTTP 代理 CONNECT 失败: {resp.splitlines()[0]}")
    return s


def make_proxyjump_channel(
    jump_client: paramiko.SSHClient,
    target_host: str,
    target_port: int,
    timeout: int = 30,
):
    """通过已连接的跳板机建立到目标的 channel"""
    transport = jump_client.get_transport()
    if transport is None:
        raise RuntimeError("跳板机 transport 未激活")
    return transport.open_channel(
        "direct-tcpip",
        (target_host, target_port),
        ("127.0.0.1", 0),
        timeout=timeout,
    )
