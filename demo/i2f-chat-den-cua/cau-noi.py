"""
Cầu nối mTLS cạnh bộ não: PicoClaw nói HTTP với 127.0.0.1, cầu nối mở TLS 1.3 tới hộp tại nhà
và trình chứng chỉ của bộ não.

    python3 demo/i2f-chat-den-cua/cau-noi.py --target hop-nha.tailnet.ts.net:8443 \
        --ca khoa/ca.pem --cert khoa/nao.pem --key khoa/nao.key

Client MCP HTTP của PicoClaw chỉ thêm header (`pkg/mcp/manager.go`, `headerTransport` trên
`http.DefaultTransport`), không trình được chứng chỉ client, mà `mcp serve --http` đòi mTLS. Cầu
nối giữ nguyên luật của hộp thay vì nới nó. Chỉ thư viện chuẩn, chạy được trên VPS có python3.

Nó chỉ nghe trên loopback: phía HTTP chưa mã hoá và mang token, nên không bao giờ ra mạng.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import ipaddress
import ssl
import sys
from collections.abc import Callable


def tls_context(ca: str, cert: str, key: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.load_verify_locations(cafile=ca)
    context.load_cert_chain(cert, key)
    return context


def _split(address: str) -> tuple[str, int]:
    host, _, port = address.rpartition(":")
    return host.strip("[]"), int(port)


def _loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


async def _pump(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, ssl.SSLError):
        pass
    finally:
        if writer.can_write_eof():
            try:
                writer.write_eof()
            except (OSError, RuntimeError):
                writer.close()
        else:
            writer.close()


async def serve(
    listen: str,
    target: str,
    context: ssl.SSLContext,
    server_name: str | None = None,
    on_ready: Callable[[int], None] | None = None,
    log: Callable[[str], None] = lambda line: print(line, file=sys.stderr, flush=True),
) -> None:
    listen_host, listen_port = _split(listen)
    if not _loopback(listen_host):
        raise SystemExit(f"--listen {listen}: the plain side carries the token; loopback only")
    target_host, target_port = _split(target)

    async def handle(client_reader, client_writer) -> None:
        try:
            box_reader, box_writer = await asyncio.open_connection(
                target_host,
                target_port,
                ssl=context,
                server_hostname=server_name or target_host,
            )
        except (OSError, ssl.SSLError) as error:
            log(f"cầu nối: không tới được hộp {target}: {error}")
            client_writer.close()
            return
        await asyncio.gather(
            _pump(client_reader, box_writer),
            _pump(box_reader, client_writer),
        )
        box_writer.close()
        client_writer.close()

    server = await asyncio.start_server(handle, listen_host, listen_port)
    port = server.sockets[0].getsockname()[1]
    log(f"cầu nối: http://{listen_host}:{port} → https://{target} (mTLS)")
    if on_ready is not None:
        on_ready(port)
    async with server:
        await server.serve_forever()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    parser.add_argument("--listen", default="127.0.0.1:8444")
    parser.add_argument("--target", required=True, help="host:port của hộp (mcp serve --http)")
    parser.add_argument("--ca", required=True)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--server-name", help="tên trong chứng chỉ hộp, nếu khác host của --target")
    args = parser.parse_args(argv)
    context = tls_context(args.ca, args.cert, args.key)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve(args.listen, args.target, context, args.server_name))


if __name__ == "__main__":
    main()
