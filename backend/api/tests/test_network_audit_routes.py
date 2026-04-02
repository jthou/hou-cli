"""网络审计路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


class TestNetworkAuditRoutes:
    """网络审计路由测试类"""

    def test_get_targets_success(self, client: TestClient):
        """测试获取审计目标列表成功"""
        response = client.get("/api/network/audit/targets")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "targets" in data
        targets = data["targets"]
        assert isinstance(targets, list)
        ids = [t["id"] for t in targets]
        assert "duckduckgo" in ids
        assert "outbound_ip" in ids
        assert "deepseek" in ids
        for t in targets:
            assert "id" in t and "name" in t and "configured" in t

    def test_get_targets_error_handling(self, client: TestClient):
        """测试获取目标时异常处理"""
        with patch(
            "backend.api.network_audit_routes.get_audit_targets"
        ) as mock_get:
            mock_get.side_effect = RuntimeError("配置加载失败")
            response = client.get("/api/network/audit/targets")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "配置加载失败" in data["error"]
            assert data["targets"] == []

    def test_run_audit_success(self, client: TestClient):
        """测试执行审计成功（mock 网络请求）"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200

        with patch(
            "backend.api.network_audit_routes.requests.get",
            return_value=mock_response,
        ):
            response = client.post("/api/network/audit/run")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "results" in data
            results = data["results"]
            assert isinstance(results, list)
            for r in results:
                assert "id" in r and "name" in r and "status" in r
                assert r["status"] in ("ok", "fail", "skip")

    def test_run_audit_error_handling(self, client: TestClient):
        """测试执行审计时异常处理"""
        with patch(
            "backend.api.network_audit_routes._run_audit_async",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.side_effect = RuntimeError("并发执行失败")
            response = client.post("/api/network/audit/run")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "并发执行失败" in data["error"]
            assert data["results"] == []

    def test_run_audit_includes_created_at(self, client: TestClient):
        """测试执行审计返回 created_at"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200

        with patch(
            "backend.api.network_audit_routes.requests.get",
            return_value=mock_response,
        ):
            response = client.post("/api/network/audit/run")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "created_at" in data
            assert "T" in data["created_at"]

    def test_get_history_success(self, client: TestClient):
        """测试获取历史记录"""
        response = client.get("/api/network/audit/history")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "history" in data
        assert isinstance(data["history"], list)

    def test_get_env_success(self, client: TestClient):
        """测试获取环境信息"""
        response = client.get("/api/network/audit/env")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "local_ips" in data
        assert "proxy_settings" in data
        assert isinstance(data["local_ips"], list)
        assert isinstance(data["proxy_settings"], dict)
        assert "httpx_uses_environment_proxy" in data
        assert isinstance(data["httpx_uses_environment_proxy"], bool)

    def test_run_audit_includes_env(self, client: TestClient):
        """测试执行审计返回 env"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "1.2.3.4"
        mock_response.json = MagicMock(side_effect=ValueError("not json"))

        with patch(
            "backend.api.network_audit_routes.requests.get",
            return_value=mock_response,
        ):
            response = client.post("/api/network/audit/run")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "env" in data
            assert "local_ips" in data["env"]
            assert "proxy_settings" in data["env"]
            assert "summary" in data["env"]
            assert "httpx_uses_environment_proxy" in data["env"]
