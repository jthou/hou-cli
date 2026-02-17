"""心跳监控路由单元测试"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestHeartbeatRoutes:
    """心跳监控路由测试类"""
    
    def test_get_heartbeat_status_success(self, client):
        """测试获取心跳状态成功"""
        mock_status = {
            "uptime_seconds": 3600,
            "heartbeat_count": 120,
            "cpu_percent": 25.5,
            "memory_mb": 512.0,
            "last_heartbeat": "2024-01-01T12:00:00"
        }
        
        with patch('backend.infrastructure.monitoring.heartbeat.get_heartbeat_monitor') as mock_get_monitor:
            mock_monitor = MagicMock()
            mock_monitor.get_status = MagicMock(return_value=mock_status)
            mock_get_monitor.return_value = mock_monitor
            
            response = client.get("/api/heartbeat/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["status"]["uptime_seconds"] == 3600
            assert data["status"]["heartbeat_count"] == 120
            assert data["status"]["cpu_percent"] == 25.5
    
    def test_get_heartbeat_status_error(self, client):
        """测试获取心跳状态错误处理"""
        with patch('backend.infrastructure.monitoring.heartbeat.get_heartbeat_monitor') as mock_get_monitor:
            mock_get_monitor.side_effect = Exception("心跳监控器未初始化")
            
            response = client.get("/api/heartbeat/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "心跳监控器未初始化" in data["error"]

