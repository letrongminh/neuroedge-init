"""
Web Simulator Backend (L0 sim).
Serves Wokwi Elements UI and WebSocket audio streaming.
"""

__all__ = ["start_simulator"]


def start_simulator(port: int = 8080):
    print(f"Starting NeuroEdge web simulator at http://localhost:{port}")
