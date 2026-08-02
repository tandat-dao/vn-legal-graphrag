"""Unit test cho `scripts/preflight.py`.

Lý do có tệp này: các nhánh "DB kết nối được" của preflight **chỉ chạy ở máy B**.
Ở máy A mọi thứ đều hỏng nên chúng không bao giờ được thực thi — một lỗi chính tả
kiểu `info.config.params.vectors.size` sẽ chỉ lộ ra đúng lúc bạn cùng nhóm chạy
trước buổi bảo vệ. Test dựng Neo4j/Qdrant giả để đi qua đúng những nhánh đó.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("preflight", GOC / "scripts" / "preflight.py")
preflight = importlib.util.module_from_spec(_spec)
sys.modules["preflight"] = preflight
_spec.loader.exec_module(preflight)


# ---------------------------------------------------------------------------
# Neo4j giả
# ---------------------------------------------------------------------------

class _Session:
    def __init__(self, dem, canh):
        self.dem, self.canh = dem, canh

    def run(self, cypher, **_):
        if "count(n)" in cypher:
            nhan = cypher.split(":")[1].split(")")[0]
            return _Ket({"c": self.dem.get(nhan, 0)})
        return _Ket(canh=self.canh)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Ket:
    def __init__(self, mot=None, canh=None):
        self._mot, self._canh = mot, canh or []

    def single(self):
        return self._mot

    def data(self):
        return self._canh


class _Driver:
    def __init__(self, dem, canh=None, loi=None):
        self.dem, self.canh, self.loi = dem, canh or [], loi
        self.da_dong = False

    def verify_connectivity(self):
        if self.loi:
            raise self.loi

    def session(self):
        return _Session(self.dem, self.canh)

    def close(self):
        self.da_dong = True


def _gan_neo4j(monkeypatch, driver):
    import neo4j
    monkeypatch.setattr(neo4j.GraphDatabase, "driver", lambda *a, **k: driver)
    for k, v in [("NEO4J_URI", "bolt://x:7687"), ("NEO4J_USER", "neo4j"),
                 ("NEO4J_PASSWORD", "mk")]:
        monkeypatch.setenv(k, v)


def test_neo4j_du_du_lieu(monkeypatch):
    dem = {"Norm": 32, "Component": 900, "CTV": 900, "TextUnit": 950,
           "Theme": 3, "Jurisdiction": 3, "Concept": 40}
    d = _Driver(dem, canh=[{"t": "HAS_COMPONENT", "c": 900}, {"t": "IMPLEMENTS", "c": 20}])
    _gan_neo4j(monkeypatch, d)
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert kq.so_hong == 0, kq.muc
    assert any("32 Norm" in m[2] for m in kq.muc)
    assert any("HAS_COMPONENT 900" in m[2] for m in kq.muc)
    assert d.da_dong, "driver không được đóng → rò kết nối"


def test_neo4j_do_thi_rong_la_loi_bat_buoc(monkeypatch):
    _gan_neo4j(monkeypatch, _Driver({"Norm": 0, "Component": 0}))
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert kq.so_hong >= 1
    assert any("graph_builder" in (m[3] or "") for m in kq.muc)


def test_neo4j_ingest_do_dang_chi_canh_bao(monkeypatch):
    """Ít Norm hơn mong đợi = cảnh báo (có thể corpus đang đổi), không chặn."""
    _gan_neo4j(monkeypatch, _Driver({"Norm": 10, "Component": 100},
                                    canh=[{"t": "HAS_COMPONENT", "c": 100}]))
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert kq.so_hong == 0, kq.muc
    assert kq.so_canh_bao >= 1


def test_neo4j_co_norm_nhung_khong_component(monkeypatch):
    _gan_neo4j(monkeypatch, _Driver({"Norm": 32, "Component": 0}))
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert any("ingest dở dang" in m[2] for m in kq.muc)
    assert kq.so_hong >= 1


def test_neo4j_sai_mat_khau_goi_y_dung(monkeypatch):
    class AuthError(Exception):
        pass
    AuthError.__name__ = "AuthError"
    _gan_neo4j(monkeypatch, _Driver({}, loi=AuthError("sai mk")))
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert kq.so_hong >= 1
    assert any("NEO4J_AUTH" in (m[3] or "") for m in kq.muc)


def test_neo4j_thieu_env(monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert kq.so_hong == 1


# ---------------------------------------------------------------------------
# Qdrant giả
# ---------------------------------------------------------------------------

class _Cols:
    def __init__(self, ten):
        self.collections = [type("C", (), {"name": t})() for t in ten]


class _Client:
    def __init__(self, ten_col, so_diem=0, so_chieu=1024):
        self._ten, self._diem, self._chieu = ten_col, so_diem, so_chieu

    def get_collections(self):
        return _Cols(self._ten)

    def count(self, ten, exact=True):
        return type("R", (), {"count": self._diem})()

    def get_collection(self, ten):
        vectors = type("V", (), {"size": self._chieu})()
        params = type("P", (), {"vectors": vectors})()
        config = type("Cfg", (), {"params": params})()
        return type("Info", (), {"config": config})()


def _gan_qdrant(monkeypatch, client):
    import qdrant_client
    monkeypatch.setattr(qdrant_client, "QdrantClient", lambda *a, **k: client)


def test_qdrant_day_du(monkeypatch):
    _gan_qdrant(monkeypatch, _Client(["legal_texts"], so_diem=1200))
    kq = preflight.KetQua()
    preflight.kiem_qdrant(kq)
    assert kq.so_hong == 0, kq.muc
    assert any("1200 điểm" in m[2] and "1024 chiều" in m[2] for m in kq.muc)


def test_qdrant_thieu_collection(monkeypatch):
    _gan_qdrant(monkeypatch, _Client(["baseline_legal_texts"]))
    kq = preflight.KetQua()
    preflight.kiem_qdrant(kq)
    assert kq.so_hong >= 1
    assert any("vectorizer" in (m[3] or "") for m in kq.muc)


def test_qdrant_collection_rong(monkeypatch):
    _gan_qdrant(monkeypatch, _Client(["legal_texts"], so_diem=0))
    kq = preflight.KetQua()
    preflight.kiem_qdrant(kq)
    assert any("RỖNG" in m[2] for m in kq.muc)
    assert kq.so_hong >= 1


def test_qdrant_sai_so_chieu(monkeypatch):
    """Collection dựng bằng model khác → 768 chiều thay vì 1024 của BGE-M3."""
    _gan_qdrant(monkeypatch, _Client(["legal_texts"], so_diem=500, so_chieu=768))
    kq = preflight.KetQua()
    preflight.kiem_qdrant(kq)
    assert any("768" in m[2] and "1024" in m[2] for m in kq.muc)
    assert kq.so_hong >= 1


def test_qdrant_khong_ket_noi_duoc(monkeypatch):
    import qdrant_client

    def _no(*a, **k):
        raise ConnectionError("refused")

    monkeypatch.setattr(qdrant_client, "QdrantClient", _no)
    kq = preflight.KetQua()
    preflight.kiem_qdrant(kq)
    assert kq.so_hong == 1
    assert any("docker compose up -d" in (m[3] or "") for m in kq.muc)


# ---------------------------------------------------------------------------
# .env
# ---------------------------------------------------------------------------

def test_env_du_khoa_cho_mode_claude(monkeypatch):
    for k, v in [("NEO4J_URI", "bolt://x"), ("NEO4J_USER", "u"),
                 ("NEO4J_PASSWORD", "p"), ("LLM_MODE", "claude"),
                 ("ANTHROPIC_API_KEY", "sk-x")]:
        monkeypatch.setenv(k, v)
    kq = preflight.KetQua()
    assert preflight.kiem_env(kq) == "claude"
    assert kq.so_hong == 0, kq.muc


def test_env_mode_gemini_khong_doi_khoa_claude(monkeypatch):
    """`--llm-mode gemini` không đụng Claude → thiếu ANTHROPIC_API_KEY không phải lỗi chặn."""
    for k, v in [("NEO4J_URI", "bolt://x"), ("NEO4J_USER", "u"),
                 ("NEO4J_PASSWORD", "p"), ("LLM_MODE", "gemini"),
                 ("GEMINI_USE_VERTEX", "true"), ("GEMINI_VERTEX_PROJECT", "prj")]:
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    kq = preflight.KetQua()
    assert preflight.kiem_env(kq) == "gemini"
    assert kq.so_hong == 0, kq.muc


def test_env_thieu_mat_khau_neo4j(monkeypatch):
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    kq = preflight.KetQua()
    preflight.kiem_env(kq)
    assert any("NEO4J_PASSWORD" in m[1] and m[0] == preflight.HONG for m in kq.muc)


def test_env_khong_in_bi_mat(monkeypatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "mat-khau-that")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-that")
    kq = preflight.KetQua()
    preflight.kiem_env(kq)
    het = " ".join(m[2] for m in kq.muc)
    assert "mat-khau-that" not in het and "sk-that" not in het


# ---------------------------------------------------------------------------
# Fixture + exit code
# ---------------------------------------------------------------------------

def test_fixture_bat_fixture_viet_tay_tam(monkeypatch, tmp_path):
    import json
    (tmp_path / "a.json").write_text(json.dumps(
        {"question": "Câu A?", "tam": True, "events": [], "result": {}},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(preflight, "GOC", tmp_path.parent)
    (tmp_path.parent / "ui").mkdir(exist_ok=True)
    import shutil
    shutil.copytree(tmp_path, tmp_path.parent / "ui" / "fixtures", dirs_exist_ok=True)
    kq = preflight.KetQua()
    preflight.kiem_fixture(kq)
    assert any("VIẾT TAY" in m[1] or "viết tay" in m[1] for m in kq.muc)


def test_fixture_khong_co_thu_muc_KHONG_con_chan(monkeypatch, tmp_path):
    """Replay nay là dự phòng PHỤ (dự phòng chính là bản ghi màn hình) → thiếu
    fixture KHÔNG được chặn buổi bảo vệ."""
    monkeypatch.setattr(preflight, "GOC", tmp_path)
    kq = preflight.KetQua()
    preflight.kiem_fixture(kq)
    assert kq.so_hong == 0, kq.muc
    assert any("tùy chọn" in m[2] for m in kq.muc)


def test_fixture_rong_cung_khong_chan(monkeypatch, tmp_path):
    (tmp_path / "ui" / "fixtures").mkdir(parents=True)
    monkeypatch.setattr(preflight, "GOC", tmp_path)
    kq = preflight.KetQua()
    preflight.kiem_fixture(kq)
    assert kq.so_hong == 0, kq.muc


def test_exit_code_theo_so_muc_hong():
    kq = preflight.KetQua()
    kq.dat("x", "ok")
    assert kq.so_hong == 0
    kq.canh_bao("y", "cảnh báo")
    assert kq.so_hong == 0 and kq.so_canh_bao == 1
    kq.hong("z", "hỏng")
    assert kq.so_hong == 1


def test_moi_muc_hong_deu_kem_cach_sua(monkeypatch):
    """Ràng buộc của đề bài: mỗi mục hỏng PHẢI có một câu chỉ cách sửa."""
    _gan_qdrant(monkeypatch, _Client([]))
    _gan_neo4j(monkeypatch, _Driver({"Norm": 0, "Component": 0}))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    kq = preflight.KetQua()
    preflight.kiem_env(kq)
    preflight.kiem_neo4j(kq)
    preflight.kiem_qdrant(kq)
    thieu = [m[1] for m in kq.muc if m[0] == preflight.HONG and not m[3]]
    assert not thieu, f"mục hỏng không kèm cách sửa: {thieu}"


def test_neo4j_khong_co_canh(monkeypatch):
    """Có node nhưng 0 cạnh = Stage 2 duyệt đồ thị sẽ ra rỗng → phải là lỗi chặn."""
    _gan_neo4j(monkeypatch, _Driver({"Norm": 32, "Component": 900}, canh=[]))
    kq = preflight.KetQua()
    preflight.kiem_neo4j(kq)
    assert kq.so_hong >= 1
    assert any("0 cạnh" in m[2] and m[3] for m in kq.muc)


def test_preflight_bat_devmode_bo_quen(monkeypatch):
    """Quên tắt devmode = trang hiện TRỰC TIẾP với dữ liệu giả → phải là lỗi CHẶN."""
    for k, v in [("NEO4J_URI", "bolt://x"), ("NEO4J_USER", "u"),
                 ("NEO4J_PASSWORD", "p"), ("ANTHROPIC_API_KEY", "sk-x")]:
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("DEMO_DEVMODE", "1")
    kq = preflight.KetQua()
    preflight.kiem_env(kq)
    hong = [m for m in kq.muc if m[0] == preflight.HONG and "DEVMODE" in m[1]]
    assert hong, "preflight không bắt được devmode bỏ quên"
    assert hong[0][3], "mục hỏng phải kèm cách sửa"

    monkeypatch.setenv("DEMO_DEVMODE", "0")
    kq2 = preflight.KetQua()
    preflight.kiem_env(kq2)
    assert not [m for m in kq2.muc if m[0] == preflight.HONG and "DEVMODE" in m[1]]
