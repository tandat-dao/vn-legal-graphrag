"""Test ontology_mapper — chạy Gemini Flash (không gọi API thật, dùng client giả)."""
import sys
from types import ModuleType, SimpleNamespace

import pytest

from src.ingestion import ontology_mapper as om


@pytest.fixture(autouse=True)
def khong_ngu_that(monkeypatch):
    """Chặn mọi time.sleep — test retry/throttle không được chờ thật."""
    da_ngu = []
    monkeypatch.setattr(om.time, "sleep", lambda s: da_ngu.append(s))
    monkeypatch.setattr(om, "_last_call_ts", None)
    return da_ngu


@pytest.fixture(autouse=True)
def stub_genai_types(monkeypatch):
    """Cho phép chạy test khi máy chưa cài `google-genai` (module chỉ cần `types`)."""
    try:
        from google.genai import types  # noqa: F401
        return
    except ImportError:
        pass

    fake_types = ModuleType("google.genai.types")
    fake_types.GenerateContentConfig = lambda **kw: SimpleNamespace(**kw)
    fake_genai = ModuleType("google.genai")
    fake_genai.types = fake_types
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

CORE_DATA = {
    "concepts": [
        {"id": "ho-so-giay-to", "name": "Hồ sơ, giấy tờ"},
        {"id": "nghia-vu-tai-chinh", "name": "Nghĩa vụ tài chính"},
    ]
}


class FakeGenaiClient:
    """Giả lập client google-genai: `.models.generate_content(...)` → object có `.text`.

    `raise_err` ném lỗi ở MỌI lượt; `raise_lan_dau=n` chỉ ném ở n lượt đầu rồi
    trả kết quả (mô phỏng 429 tạm thời khỏi sau retry).
    """

    def __init__(self, text="[]", raise_err=None, raise_lan_dau=0):
        self._text = text
        self._raise = raise_err
        self._raise_lan_dau = raise_lan_dau
        self.calls = []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise is not None and (
            self._raise_lan_dau == 0 or len(self.calls) <= self._raise_lan_dau
        ):
            raise self._raise
        return SimpleNamespace(text=self._text)


class LoiGemini(Exception):
    """Lỗi google-genai giả, có `.code` như ClientError/ServerError thật."""

    def __init__(self, code, message=""):
        super().__init__(message or f"{code} error")
        self.code = code


def test_parse_va_loc_concept_ngoai_lai():
    client = FakeGenaiClient('["ho-so-giay-to", "bia-dat", "nghia-vu-tai-chinh"]')
    assert om.map_component_to_concepts(client, "nội dung", CORE_DATA) == [
        "ho-so-giay-to",
        "nghia-vu-tai-chinh",
    ]


def test_strip_markdown_fence():
    client = FakeGenaiClient('```json\n["ho-so-giay-to"]\n```')
    assert om.map_component_to_concepts(client, "nội dung", CORE_DATA) == ["ho-so-giay-to"]


def test_json_hong_tra_ve_rong():
    client = FakeGenaiClient("không phải JSON")
    assert om.map_component_to_concepts(client, "nội dung", CORE_DATA) == []


def test_429_retry_het_luot_thi_RAISE(khong_ngu_that):
    """Không được nuốt lỗi: graph_builder phải dừng thay vì ghi cờ đã-map sai."""
    client = FakeGenaiClient(raise_err=LoiGemini(429, "RESOURCE_EXHAUSTED"))
    with pytest.raises(LoiGemini):
        om.map_component_to_concepts(client, "nội dung", CORE_DATA)
    # 1 lượt đầu + MAX_RETRIES lượt thử lại
    assert len(client.calls) == om.MAX_RETRIES + 1
    # backoff luỹ thừa 15 → 30 → 60 (ngoài các lần sleep của throttle)
    assert [s for s in khong_ngu_that if s >= om.DEFAULT_RETRY_DELAY] == [15.0, 30.0, 60.0]


def test_429_tam_thoi_thi_retry_roi_thanh_cong(khong_ngu_that):
    client = FakeGenaiClient('["han-muc"]', raise_err=LoiGemini(503), raise_lan_dau=2)
    CORE = {"concepts": [{"id": "han-muc", "name": "Hạn mức"}]}
    assert om.map_component_to_concepts(client, "nội dung", CORE) == ["han-muc"]
    assert len(client.calls) == 3


def test_mat_ket_noi_httpx_duoc_retry(khong_ngu_that):
    """Lỗi tầng vận chuyển từng làm chết mẻ Pass 4 ở component 2300/4553."""
    import httpx
    err = httpx.RemoteProtocolError("Server disconnected without sending a response.")
    client = FakeGenaiClient('["han-muc"]', raise_err=err, raise_lan_dau=1)
    CORE = {"concepts": [{"id": "han-muc", "name": "Hạn mức"}]}
    assert om.map_component_to_concepts(client, "nội dung", CORE) == ["han-muc"]
    assert len(client.calls) == 2


def test_timeout_httpx_duoc_retry(khong_ngu_that):
    import httpx
    client = FakeGenaiClient("[]", raise_err=httpx.ReadTimeout("timed out"), raise_lan_dau=1)
    assert om.map_component_to_concepts(client, "nội dung", CORE_DATA) == []
    assert len(client.calls) == 2


def test_loi_logic_400_khong_retry(khong_ngu_that):
    client = FakeGenaiClient(raise_err=LoiGemini(400, "INVALID_ARGUMENT"))
    with pytest.raises(LoiGemini):
        om.map_component_to_concepts(client, "nội dung", CORE_DATA)
    assert len(client.calls) == 1  # lỗi của ta → không thử lại


def test_doc_retry_delay_tu_thong_bao_cua_api(khong_ngu_that):
    err = LoiGemini(429, "Quota exceeded. Please retry in 51.4s.")
    client = FakeGenaiClient(raise_err=err, raise_lan_dau=1, text="[]")
    om.map_component_to_concepts(client, "nội dung", CORE_DATA)
    assert 51.4 in khong_ngu_that


def test_doc_header_retry_after(khong_ngu_that):
    err = LoiGemini(429, "quota")
    err.response = SimpleNamespace(headers={"retry-after": "7"})
    client = FakeGenaiClient(raise_err=err, raise_lan_dau=1, text="[]")
    om.map_component_to_concepts(client, "nội dung", CORE_DATA)
    assert 7.0 in khong_ngu_that


def test_throttle_gian_cach_giua_hai_lan_goi(khong_ngu_that, monkeypatch):
    monkeypatch.setattr(om, "THROTTLE_SEC", 3.0)
    gio = iter([100.0, 100.5, 100.5])  # lượt 2 gọi chỉ sau 0.5s
    monkeypatch.setattr(om.time, "monotonic", lambda: next(gio))
    client = FakeGenaiClient("[]")
    om.map_component_to_concepts(client, "a", CORE_DATA)
    om.map_component_to_concepts(client, "b", CORE_DATA)
    assert khong_ngu_that == [2.5]  # phải chờ bù 2.5s cho đủ 3s


def test_core_data_rong_khong_goi_llm():
    client = FakeGenaiClient('["ho-so-giay-to"]')
    assert om.map_component_to_concepts(client, "nội dung", {"concepts": []}) == []
    assert client.calls == []


def test_dung_model_planner_va_temperature_0(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL_PLANNER", "gemini-2.5-flash-custom")
    client = FakeGenaiClient("[]")
    om.map_component_to_concepts(client, "nội dung", CORE_DATA)
    kwargs = client.calls[0]
    assert kwargs["model"] == "gemini-2.5-flash-custom"
    assert kwargs["config"].temperature == 0.0
    assert kwargs["config"].max_output_tokens == om.MAX_OUTPUT_TOKENS
    assert kwargs["contents"] == "nội dung"


def test_model_mac_dinh_khi_thieu_env(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL_PLANNER", raising=False)
    assert om._planner_model() == "gemini-2.5-flash"


def test_client_anthropic_cu_bi_bo_qua(monkeypatch):
    """Call site cũ truyền client Anthropic → module tự dựng client Gemini thay thế."""
    anthropic_like = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **kw: pytest.fail("không được gọi Claude")),
        models=SimpleNamespace(retrieve=lambda *a, **kw: None),
    )
    gemini = FakeGenaiClient('["ho-so-giay-to"]')
    monkeypatch.setattr(om, "_get_gemini_client", lambda: gemini)

    assert om.map_component_to_concepts(anthropic_like, "nội dung", CORE_DATA) == [
        "ho-so-giay-to"
    ]
    assert len(gemini.calls) == 1
