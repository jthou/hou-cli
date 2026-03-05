"""网络审计目标配置单元测试"""
import pytest
from unittest.mock import patch


class TestNetworkAuditTargets:
    """审计目标配置测试"""

    def test_get_audit_targets_returns_list(self):
        """测试返回目标列表"""
        from backend.config.network_audit_targets import get_audit_targets

        targets = get_audit_targets()
        assert isinstance(targets, list)
        assert len(targets) >= 8

    def test_duckduckgo_fixed_url(self):
        """测试 DuckDuckGo 固定 URL"""
        from backend.config.network_audit_targets import get_audit_targets

        targets = get_audit_targets()
        ddg = next(t for t in targets if t["id"] == "duckduckgo")
        assert ddg["url"] == "https://html.duckduckgo.com/html/"
        assert ddg["configured"] is True

    def test_deepseek_from_env(self):
        """测试 DeepSeek 从环境变量解析"""
        from backend.config.network_audit_targets import get_audit_targets

        with patch.dict("os.environ", {"DEEPSEEK_BASE_URL": "https://custom.deepseek.com"}):
            targets = get_audit_targets()
        ds = next(t for t in targets if t["id"] == "deepseek")
        assert ds["url"] == "https://custom.deepseek.com/v1/models"
        assert ds["configured"] is True

    def test_deepseek_default_when_env_empty(self):
        """测试 DeepSeek 环境变量为空时使用默认值"""
        from backend.config.network_audit_targets import get_audit_targets

        with patch.dict("os.environ", {"DEEPSEEK_BASE_URL": ""}, clear=False):
            targets = get_audit_targets()
        ds = next(t for t in targets if t["id"] == "deepseek")
        assert ds["url"] == "https://api.deepseek.com/v1/models"

    def test_wechat_mp_requires_env(self):
        """测试微信公众号需要 APP_ID/SECRET"""
        from backend.config.network_audit_targets import get_audit_targets

        with patch.dict("os.environ", {}, clear=True):
            targets = get_audit_targets()
        wechat = next(t for t in targets if t["id"] == "wechat_mp")
        assert wechat["configured"] is False

        with patch.dict(
            "os.environ",
            {"WECHAT_MP_APP_ID": "id1", "WECHAT_MP_APP_SECRET": "sec1"},
            clear=False,
        ):
            targets = get_audit_targets()
        wechat = next(t for t in targets if t["id"] == "wechat_mp")
        assert wechat["configured"] is True

    def test_qweather_https_prefix(self):
        """测试和风天气 host 无协议时补 https"""
        from backend.config.network_audit_targets import get_audit_targets

        with patch.dict(
            "os.environ",
            {"QWEATHER_API_HOST": "xxx.re.qweatherapi.com"},
            clear=False,
        ):
            targets = get_audit_targets()
        qw = next(t for t in targets if t["id"] == "qweather")
        assert qw["url"].startswith("https://")
        assert "xxx.re.qweatherapi.com" in qw["url"]
