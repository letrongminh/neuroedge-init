"""
Keys for the light-and-door chat demo: one CA, the box certificate, the brain certificate, the token signing key and the token.

    python demo/i2f-chat-den-cua/tao-khoa.py --out ~/neuroedge-demo-khoa \
        --audience https://hop-nha.tailnet.ts.net:8443/mcp
    python demo/i2f-chat-den-cua/tao-khoa.py --out ~/neuroedge-demo-khoa --renew-token

Demo only: the CA and issuer are files on this machine, the token lives `--days` days. The real thing issues
certificates and tokens through the relay (TSK-I2f-09). Needs `cryptography` and `PyJWT`, both present when
`neuroedge[mcp]` is installed.

Written to the `--out` directory:
    ca.pem                         CA signing both certificates (box: --client-ca; bridge: --ca)
    hop.pem, hop.key               the box's server certificate (SAN: name in --audience, localhost)
    nao.pem, nao.key               the brain's client certificate (the bridge presents it)
    jwks.json                      public key for the token signature (box: --jwks)
    issuer.key                     private token-signing key — keep it at home, never upload it to the VPS
    nao.token                      token bound to nao.pem (cnf.x5t#S256), sent by PicoClaw in a header
    hop.json                       issuer and audience, reused by --renew-token
"""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import ipaddress
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ISSUER = "https://neuroedge.demo/issuer"
SCOPE = "neuroedge:call"
SUBJECT = "nao-chat-den-cua"


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _san(host: str) -> x509.GeneralName:
    try:
        return x509.IPAddress(ipaddress.ip_address(host))
    except ValueError:
        return x509.DNSName(host)


def _certificate(subject, key, ca_key, *, days, ca=False, usage=None, hosts=()):
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_name(subject))
        .issuer_name(_name("neuroedge demo CA"))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if usage is not None:
        builder = builder.add_extension(x509.ExtendedKeyUsage([usage]), critical=False)
    if hosts:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([_san(h) for h in hosts]), critical=False
        )
    return builder.sign(ca_key, hashes.SHA256())


def _write_cert(path: Path, cert: x509.Certificate) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _write_key(path: Path, key) -> None:
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def thumbprint(cert_pem: bytes) -> str:
    der = x509.load_pem_x509_certificate(cert_pem).public_bytes(serialization.Encoding.DER)
    return base64.urlsafe_b64encode(hashlib.sha256(der).digest()).rstrip(b"=").decode("ascii")


def mint(out: Path, days: int) -> str:
    """A token for the brain, bound to `nao.pem`, signed with `issuer.key`."""
    settings = json.loads((out / "hop.json").read_text())
    key = serialization.load_pem_private_key((out / "issuer.key").read_bytes(), password=None)
    now = int(time.time())
    claims = {
        "iss": settings["issuer"],
        "aud": settings["audience"],
        "sub": SUBJECT,
        "iat": now,
        "exp": now + days * 86400,
        "scope": SCOPE,
        "cnf": {"x5t#S256": thumbprint((out / "nao.pem").read_bytes())},
    }
    token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": "demo"})
    (out / "nao.token").write_text(token + "\n")
    (out / "nao.token").chmod(0o600)
    return token


def create(out: Path, audience: str, issuer: str, days: int, extra_hosts: list[str]) -> None:
    parts = urlsplit(audience)
    if parts.scheme != "https" or not parts.hostname:
        raise SystemExit(f"--audience must be https://host[:port]/mcp, not {audience!r}")
    out.mkdir(parents=True, exist_ok=True)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    _write_cert(
        out / "ca.pem", _certificate("neuroedge demo CA", ca_key, ca_key, days=days, ca=True)
    )
    hosts = list(dict.fromkeys([parts.hostname, *extra_hosts, "localhost", "127.0.0.1"]))
    for name, usage, san in (
        ("hop", ExtendedKeyUsageOID.SERVER_AUTH, hosts),
        ("nao", ExtendedKeyUsageOID.CLIENT_AUTH, ()),
    ):
        key = ec.generate_private_key(ec.SECP256R1())
        subject = parts.hostname if name == "hop" else SUBJECT
        _write_cert(
            out / f"{name}.pem",
            _certificate(subject, key, ca_key, days=days, usage=usage, hosts=san),
        )
        _write_key(out / f"{name}.key", key)
    signing = ec.generate_private_key(ec.SECP256R1())
    _write_key(out / "issuer.key", signing)
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(signing.public_key()))
    (out / "jwks.json").write_text(json.dumps({"keys": [{**jwk, "kid": "demo", "use": "sig"}]}))
    (out / "hop.json").write_text(json.dumps({"issuer": issuer, "audience": audience}))
    mint(out, days)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audience", help="https://<box name>:8443/mcp, exactly the URL the brain calls")
    parser.add_argument("--issuer", default=ISSUER)
    parser.add_argument("--host", action="append", default=[], help="another name or IP of the box")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--renew-token", action="store_true", help="only reissue nao.token")
    args = parser.parse_args(argv)
    if args.renew_token:
        mint(args.out, args.days)
    else:
        if not args.audience:
            parser.error("--audience is required (except with --renew-token)")
        create(args.out, args.audience, args.issuer, args.days, args.host)
    settings = json.loads((args.out / "hop.json").read_text())
    print(f"keys in {args.out}; token lives {args.days} days")
    print(f"  box:  --issuer {settings['issuer']} --audience {settings['audience']}")


if __name__ == "__main__":
    main()
