"""
Keys for the light-and-door chat demo: one CA, the box certificate, the brain certificate, the token signing key and the token.

    python demo/i2f-chat-den-cua/tao-khoa.py --out ~/neuroedge-demo-khoa \
        --audience https://hop-nha.tailnet.ts.net:8443/mcp
    python demo/i2f-chat-den-cua/tao-khoa.py --out ~/neuroedge-demo-khoa --renew-token

The same as `neuroedge pair init` / `neuroedge pair renew` (`neuroedge.pairing`), with the demo's
issuer: the token lives at most 7 days (DP-A-04), certificates `--days` days. The real thing issues
certificates and tokens through the relay (TSK-I2f-09). Needs `neuroedge[mcp]`.

Written to the `--out` directory (`neuroedge.pairing` describes each file): ca.pem, ca.key, hop.pem,
hop.key, nao.pem, nao.key, jwks.json, issuer.key, nao.token, revoked.txt, hop.json. Only ca.pem,
nao.pem, nao.key and nao.token ever go to the VPS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from neuroedge import pairing

ISSUER = "https://neuroedge.demo/issuer"
SUBJECT = "nao-chat-den-cua"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audience", help="https://<box name>:8443/mcp, exactly the URL the brain calls")
    parser.add_argument("--issuer", default=ISSUER)
    parser.add_argument("--host", action="append", default=[], help="another name or IP of the box")
    parser.add_argument("--days", type=int, default=30, help="lifetime of the certificates")
    parser.add_argument("--token-days", type=int, default=pairing.MAX_TOKEN_DAYS)
    parser.add_argument("--renew-token", action="store_true", help="only reissue nao.token")
    args = parser.parse_args(argv)
    if args.renew_token:
        pairing.renew(args.out, args.token_days)
    else:
        if not args.audience:
            parser.error("--audience is required (except with --renew-token)")
        pairing.create(
            args.out,
            args.audience,
            args.issuer,
            cert_days=args.days,
            token_days=args.token_days,
            hosts=args.host,
            subject=SUBJECT,
        )
    settings = json.loads((args.out / "hop.json").read_text())
    print(f"keys in {args.out}; the token lives {args.token_days} days")
    print(f"  box:  --issuer {settings['issuer']} --audience {settings['audience']}")


if __name__ == "__main__":
    main()
