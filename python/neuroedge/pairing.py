"""
Pairing a brain with the box over the network (Profile A, Q-83): `neuroedge pair`.

One directory holds what `mcp serve --http` and the brain need:

    ca.pem                 CA signing both certificates (box: --client-ca; brain: its CA)
    hop.pem, hop.key       the box's server certificate
    nao.pem, nao.key       the brain's client certificate (mTLS)
    jwks.json              public key of the token signature (box: --jwks)
    issuer.key             private token-signing key: stays with the box, never on a VPS
    nao.token              the brain's access token, bound to nao.pem (cnf.x5t#S256)
    revoked.txt            thumbprints of brain certificates no longer accepted (box: --revoked)
    hop.json               issuer and audience, reused by `renew` and `rotate`

    pair init    the whole set
    pair renew   a new token for the same certificate (DP-A-04): the box keeps running
    pair rotate  a new brain certificate and token; the old certificate is revoked (DP-A-11)

A token lives at most `MAX_TOKEN_DAYS` (DP-A-04, docs/spec/deployment_profiles.md); asking for
more is refused here, and the box refuses such a token too (`mcp_http`, `lifetime_too_long`).
Needs `cryptography` and `PyJWT`, present with `neuroedge[mcp]`.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import ipaddress
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import NeuroEdgeError

ISSUER = "https://neuroedge.local/issuer"
SCOPE = "neuroedge:call"
SUBJECT = "neuroclaw"
MAX_TOKEN_DAYS = 7
CERT_DAYS = 365
REVOKED = "revoked.txt"
WHERE = "neuroedge pair"


def _x509() -> Any:
    try:
        import jwt  # noqa: F401
        from cryptography import x509
    except ImportError as exc:
        raise NeuroEdgeError(
            where=WHERE,
            why="pairing needs `cryptography` and `PyJWT`",
            how="pip install 'neuroedge[mcp]'",
        ) from exc
    return x509


def _name(common_name: str) -> Any:
    x509 = _x509()
    from cryptography.x509.oid import NameOID

    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _san(host: str) -> Any:
    x509 = _x509()
    try:
        return x509.IPAddress(ipaddress.ip_address(host))
    except ValueError:
        return x509.DNSName(host)


def _certificate(subject, key, ca_key, *, days, ca=False, usage=None, hosts=(), issuer=None):
    x509 = _x509()
    from cryptography.hazmat.primitives import hashes

    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(_name(subject))
        .issuer_name(_name(issuer or "neuroedge pairing CA"))
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


def _write_cert(path: Path, cert: Any) -> None:
    from cryptography.hazmat.primitives import serialization

    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def _write_key(path: Path, key: Any) -> None:
    from cryptography.hazmat.primitives import serialization

    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def thumbprint(cert_pem: bytes) -> str:
    """`x5t#S256` of a PEM certificate: what a token binds and `revoked.txt` lists."""
    x509 = _x509()
    from cryptography.hazmat.primitives import serialization

    der = x509.load_pem_x509_certificate(cert_pem).public_bytes(serialization.Encoding.DER)
    return base64.urlsafe_b64encode(hashlib.sha256(der).digest()).rstrip(b"=").decode("ascii")


def _days(days: int) -> int:
    if not 1 <= days <= MAX_TOKEN_DAYS:
        raise NeuroEdgeError(
            where=f"{WHERE} (--token-days {days})",
            why=f"a brain token lives 1 to {MAX_TOKEN_DAYS} days (DP-A-04): a leaked one must expire",
            how=f"ask for {MAX_TOKEN_DAYS} days or fewer, and renew with `neuroedge pair renew`",
        )
    return days


def mint(out: Path, days: int = MAX_TOKEN_DAYS) -> str:
    """A token for the brain, bound to `nao.pem`, signed with `issuer.key`, `days` long."""
    import jwt
    from cryptography.hazmat.primitives import serialization

    days = _days(days)
    settings = json.loads((out / "hop.json").read_text())
    key = serialization.load_pem_private_key((out / "issuer.key").read_bytes(), password=None)
    now = int(time.time())
    claims = {
        "iss": settings["issuer"],
        "aud": settings["audience"],
        "sub": settings.get("subject", SUBJECT),
        "iat": now,
        "exp": now + days * 86400,
        "scope": SCOPE,
        "cnf": {"x5t#S256": thumbprint((out / "nao.pem").read_bytes())},
    }
    token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": "pair"})
    (out / "nao.token").write_text(token + "\n")
    (out / "nao.token").chmod(0o600)
    return token


def _brain_certificate(out: Path, days: int) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID

    x509 = _x509()
    ca_key = serialization.load_pem_private_key((out / "ca.key").read_bytes(), password=None)
    ca = x509.load_pem_x509_certificate((out / "ca.pem").read_bytes())
    issuer = ca.subject.rfc4514_string().removeprefix("CN=")
    key = ec.generate_private_key(ec.SECP256R1())
    settings = json.loads((out / "hop.json").read_text())
    cert = _certificate(
        settings.get("subject", SUBJECT),
        key,
        ca_key,
        days=days,
        usage=ExtendedKeyUsageOID.CLIENT_AUTH,
        issuer=issuer,
    )
    _write_cert(out / "nao.pem", cert)
    _write_key(out / "nao.key", key)


def create(
    out: Path,
    audience: str,
    issuer: str = ISSUER,
    *,
    cert_days: int = CERT_DAYS,
    token_days: int = MAX_TOKEN_DAYS,
    hosts: list[str] | tuple[str, ...] = (),
    subject: str = SUBJECT,
) -> None:
    """Every file of the pairing directory (see the module docstring)."""
    import jwt
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID

    _days(token_days)
    parts = urlsplit(audience)
    if parts.scheme != "https" or not parts.hostname:
        raise NeuroEdgeError(
            where=f"{WHERE} (--audience)",
            why=f"the audience must be https://host[:port]/mcp, not {audience!r}",
            how="pass exactly the URL the brain calls",
        )
    out.mkdir(parents=True, exist_ok=True)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    _write_cert(
        out / "ca.pem",
        _certificate("neuroedge pairing CA", ca_key, ca_key, days=cert_days, ca=True),
    )
    _write_key(out / "ca.key", ca_key)  # rotation signs new brain certificates with it
    names = list(dict.fromkeys([parts.hostname, *hosts, "localhost", "127.0.0.1"]))
    key = ec.generate_private_key(ec.SECP256R1())
    _write_cert(
        out / "hop.pem",
        _certificate(
            parts.hostname,
            key,
            ca_key,
            days=cert_days,
            usage=ExtendedKeyUsageOID.SERVER_AUTH,
            hosts=names,
        ),
    )
    _write_key(out / "hop.key", key)
    (out / "hop.json").write_text(
        json.dumps({"issuer": issuer, "audience": audience, "subject": subject})
    )
    _brain_certificate(out, cert_days)
    signing = ec.generate_private_key(ec.SECP256R1())
    _write_key(out / "issuer.key", signing)
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(signing.public_key()))
    (out / "jwks.json").write_text(json.dumps({"keys": [{**jwk, "kid": "pair", "use": "sig"}]}))
    revoked = out / REVOKED
    if not revoked.exists():
        revoked.write_text("# brain certificate thumbprints the box refuses (DP-A-11)\n")
    mint(out, token_days)


def renew(out: Path, days: int = MAX_TOKEN_DAYS) -> str:
    """DP-A-04: a new token for the same certificate; the running box accepts it as is."""
    return mint(out, days)


def rotate(out: Path, *, cert_days: int = CERT_DAYS, token_days: int = MAX_TOKEN_DAYS) -> str:
    """
    DP-A-11: a new brain certificate and a token bound to it; the old certificate's thumbprint
    goes into `revoked.txt`, which a running box reads again on its next connection.
    """
    _days(token_days)
    old = thumbprint((out / "nao.pem").read_bytes())
    _brain_certificate(out, cert_days)
    with (out / REVOKED).open("a", encoding="ascii") as handle:
        handle.write(old + "\n")
    return mint(out, token_days)
