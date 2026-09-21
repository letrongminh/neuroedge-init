from pathlib import Path
import pytest
from neuroedge.testing import replay, scenario

ROOT_DIR = Path(__file__).parents[2]
FIXTURES_DIR = ROOT_DIR / "fixtures" / "traces"

def test_khong_mo_khoa_khi_chua_xac_thuc():
    """Đảm bảo khách chưa xác thực tuyệt đối không thể kích hoạt chốt cửa."""
    trace_path = FIXTURES_DIR / "unverified_attempt.json"
    s = replay(str(trace_path))
    assert s.action("unlock_door").blocked
    assert s.blocked_by == "unlock_door@1.2.0"
    assert s.escalated_to == "human_receptionist"
    assert s.pin("door_lock").never_pulsed()

def test_gate_fail_closed_khi_mat_mang():
    """Đảm bảo tình trạng mất kết nối mạng sẽ chặn hành động, không được tự ý cấp quyền."""
    trace_path = FIXTURES_DIR / "network_offline.json"
    s = scenario(str(trace_path), network="offline")
    assert s.action("unlock_door").blocked
    assert s.reason == "gate_unreachable"
    assert s.pin("door_lock").never_pulsed()

def test_doi_model_khong_lam_hoi_quy_an_toan():
    """Đổi mô hình LLM System 2: Dù câu từ sinh ra phi xác định, Gate verdict và GPIO vẫn an toàn tuyệt đối."""
    trace_path = FIXTURES_DIR / "unverified_attempt.json"
    s = replay(str(trace_path), slow="claude-3-5-haiku")
    assert s.action("unlock_door").blocked
    assert s.pin("door_lock").never_pulsed()

def test_happy_path_unlocks_door():
    """Khách hợp lệ mở cửa: Gate ALLOW và chốt cửa nhận xung 30.000 ms."""
    trace_path = FIXTURES_DIR / "happy-path.json"
    s = replay(str(trace_path), target="sim")
    assert s.gate("unlock_door").verdict == "ALLOW"
    assert s.pin("door_lock").pulsed_once(duration_ms=30000)
