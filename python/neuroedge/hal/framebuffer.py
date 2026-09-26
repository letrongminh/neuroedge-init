"""
`display` on target `linux`: where a checked frame goes (TSK-S5-09, FR-TGT-02).

The frame itself — its format, its size against the board's declared resolution,
its digest and the `display_frame` event — is the same code as `sim`
(`hal.sim.make_frame`), so a session shows and records the same frames on either
target. Only the last step differs, and it is chosen, never guessed:

* ``memory`` — the frame is kept in memory and nowhere else: CI, a headless box;
* ``/dev/fbN`` — the Linux framebuffer of a Pi's HDMI or DSI panel. Pixels are
  packed into the device's own layout (bits per pixel and colour offsets read
  from the kernel) and written row by row at the top-left corner. The device is
  opened per frame and closed at once, so nothing is held between frames.

A text frame has no pixels, and this module renders no fonts: the framebuffer
refuses one rather than drawing nothing.
"""

from __future__ import annotations

import struct
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..errors import BoardCapabilityError
from .sim import Frame

FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602


class DisplayBackend(Protocol):
    name: str

    def show(self, frame: Frame, where: str) -> None: ...


class MemoryDisplay:
    """No panel: the frame lives in `LinuxHAL.frames`, as on `sim`."""

    name = "memory"

    def show(self, frame: Frame, where: str) -> None:
        return None


@dataclass(frozen=True)
class FbGeometry:
    xres: int
    yres: int
    xoffset: int
    yoffset: int
    bits_per_pixel: int
    line_length: int
    red: tuple[int, int]  # (offset, length) in bits
    green: tuple[int, int]
    blue: tuple[int, int]


def kernel_geometry(fd: int) -> FbGeometry:
    """The device's layout, from the FBIOGET_VSCREENINFO / FBIOGET_FSCREENINFO ioctls."""
    import fcntl

    var = fcntl.ioctl(fd, FBIOGET_VSCREENINFO, bytes(160))
    xres, yres, _xv, _yv, xoff, yoff, bpp, _gray, *bits = struct.unpack_from("=8I12I", var)
    fix_format = "@16sLIIIIHHHI"
    fix = fcntl.ioctl(fd, FBIOGET_FSCREENINFO, bytes(struct.calcsize(fix_format) + 32))
    line_length = struct.unpack_from(fix_format, fix)[-1]
    red, green, blue = (bits[0], bits[1]), (bits[3], bits[4]), (bits[6], bits[7])
    return FbGeometry(xres, yres, xoff, yoff, bpp, line_length, red, green, blue)


def pack_pixels(frame: Frame, geometry: FbGeometry) -> bytes:
    """The frame's pixels in the framebuffer's layout, host byte order."""
    red, green, blue = geometry.red, geometry.green, geometry.blue
    little = sys.byteorder == "little"
    if geometry.bits_per_pixel not in (16, 24, 32):
        raise ValueError(f"{geometry.bits_per_pixel} bits per pixel")
    # Fast paths for the two layouts a Pi uses; `pack_general` is what they must equal.
    if (
        geometry.bits_per_pixel == 16
        and frame.format == "rgb565"
        and (red, green, blue) == ((11, 5), (5, 6), (0, 5))
    ):
        if not little:
            return frame.data  # frames are big-endian RGB565 (sim.Frame.rgb888)
        out = bytearray(len(frame.data))
        out[0::2], out[1::2] = frame.data[1::2], frame.data[0::2]
        return bytes(out)
    rgb = frame.rgb888()
    if geometry.bits_per_pixel == 32 and little and (red, green, blue) == ((16, 8), (8, 8), (0, 8)):
        out = bytearray(len(rgb) // 3 * 4)  # XRGB8888: B, G, R, 0 in memory
        out[0::4], out[1::4], out[2::4] = rgb[2::3], rgb[1::3], rgb[0::3]
        return bytes(out)
    return pack_general(rgb, geometry)


def pack_general(rgb: bytes, geometry: FbGeometry) -> bytes:
    """RGB888 pixels packed by the colour offsets and lengths the kernel reports."""
    size = geometry.bits_per_pixel // 8
    fields = (geometry.red, geometry.green, geometry.blue)
    out = bytearray()
    for i in range(0, len(rgb), 3):
        value = 0
        for channel, (offset, length) in zip(rgb[i : i + 3], fields, strict=True):
            value |= (channel >> (8 - length)) << offset
        out += value.to_bytes(size, sys.byteorder)
    return bytes(out)


class FramebufferDisplay:
    """Frames written to a Linux framebuffer device (`/dev/fb0` on a Pi)."""

    name = "framebuffer"

    def __init__(
        self, device: str | Path, geometry: Callable[[int], FbGeometry] | None = None
    ) -> None:
        self.device = str(device)
        self._geometry = geometry or kernel_geometry

    def _error(self, where: str, why: str, how: str) -> BoardCapabilityError:
        return BoardCapabilityError(where=f"{where} ({self.device})", why=why, how=how)

    def show(self, frame: Frame, where: str) -> None:
        if frame.format == "text":
            raise self._error(
                where,
                "a text frame has no pixels, and the framebuffer backend renders no fonts",
                "draw pixels (display.show(pixels, format='rgb565')), or use display='memory'",
            )
        try:
            with open(self.device, "r+b", buffering=0) as fb:
                geometry = self._geometry(fb.fileno())
                self._write(fb, frame, geometry, where)
        except OSError as exc:
            raise self._error(
                where,
                f"cannot write the framebuffer: {exc.strerror or exc}",
                "check the panel is enabled and the user may write the device (group `video`)",
            ) from exc

    def _write(self, fb: Any, frame: Frame, geometry: FbGeometry, where: str) -> None:
        if frame.width > geometry.xres or frame.height > geometry.yres:
            raise self._error(
                where,
                f"frame {frame.width}x{frame.height} exceeds the framebuffer's "
                f"{geometry.xres}x{geometry.yres}",
                "set the panel mode to the board's declared resolution, or draw smaller",
            )
        try:
            pixels = pack_pixels(frame, geometry)
        except ValueError as exc:
            raise self._error(
                where,
                f"the framebuffer's layout ({exc}) is not one frames can be packed into",
                "set the panel to 16, 24 or 32 bits per pixel",
            ) from None
        row = frame.width * geometry.bits_per_pixel // 8
        start = (
            geometry.yoffset * geometry.line_length
            + geometry.xoffset * geometry.bits_per_pixel // 8
        )
        for y in range(frame.height):
            fb.seek(start + y * geometry.line_length)
            written = fb.write(pixels[y * row : (y + 1) * row])
            if written != row:
                raise self._error(
                    where,
                    f"row {y} was cut short ({written} of {row} bytes)",
                    "check line_length and the mode the panel reports",
                )


def display_backend(choice: Any, where: str) -> DisplayBackend | None:
    """`memory`, a `/dev/fb*` path, a backend object, or None (no backend chosen)."""
    if choice is None or not isinstance(choice, str):
        return choice
    if choice == "memory":
        return MemoryDisplay()
    if choice.startswith("/dev/fb"):
        if not Path(choice).exists():
            raise BoardCapabilityError(
                where=where,
                why=f"no framebuffer at {choice}",
                how="enable the panel (dtoverlay, `ls /dev/fb*`), or choose display='memory'",
            )
        return FramebufferDisplay(choice)
    raise BoardCapabilityError(
        where=where,
        why=f"{choice!r} is not a display backend",
        how="choose 'memory' or a framebuffer device such as /dev/fb0",
    )
