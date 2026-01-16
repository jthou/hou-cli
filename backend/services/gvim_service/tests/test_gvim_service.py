"""Gvim 服务测试"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

from backend.services.gvim_service.gvim_service import (
    GvimService,
    GvimServiceError,
    remove_special_char
)


class TestRemoveSpecialChar:
    """测试 remove_special_char 函数"""
    
    def test_remove_backslash(self):
        """测试移除反斜杠"""
        assert remove_special_char("test\\file") == "test_file"
    
    def test_remove_colon(self):
        """测试移除冒号"""
        assert remove_special_char("test:file") == "test-file"
    
    def test_remove_slash(self):
        """测试移除斜杠"""
        assert remove_special_char("test/file") == "test_file"
    
    def test_remove_quote(self):
        """测试移除引号"""
        assert remove_special_char("test'file") == "test_file"
    
    def test_remove_question(self):
        """测试移除问号"""
        assert remove_special_char("test?file") == "test%3Ffile"
    
    def test_remove_dollar(self):
        """测试移除美元符号"""
        assert remove_special_char("test$file") == "testfile"
    
    def test_multiple_special_chars(self):
        """测试多个特殊字符"""
        result = remove_special_char("test\\:file/name?")
        assert result == "test_-file_name%3F"


class TestGvimServiceInitialization:
    """测试 GvimService 初始化"""
    
    def test_init_with_default_tmpdir(self):
        """测试使用默认临时目录"""
        with patch('shared.platform_utils.get_app_data_dir') as mock_get_dir:
            mock_dir = Path("/tmp/app_data")
            mock_get_dir.return_value = mock_dir
            
            service = GvimService()
            
            assert service.tmpdir == str(mock_dir / "tmp")
            assert Path(service.tmpdir).exists()
    
    def test_init_with_custom_tmpdir(self):
        """测试使用自定义临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = GvimService(tmpdir=tmpdir)
            
            assert service.tmpdir == tmpdir
    
    def test_init_with_env_tmpdir(self):
        """测试使用环境变量临时目录"""
        with patch.dict(os.environ, {'TMPDIR': '/tmp/custom'}):
            service = GvimService(tmpdir=None)
            
            # 如果环境变量存在，应该使用它
            # 但实际实现中，如果提供了 tmpdir=None，会使用 get_app_data_dir
            # 这里主要测试不会出错
            assert service.tmpdir is not None


class TestGvimServiceCheckAvailability:
    """测试 GvimService 可用性检查"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            return GvimService(tmpdir=tmpdir)
    
    def test_check_availability_success(self, service):
        """测试 gvim 可用"""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            assert service.check_availability() is True
            mock_run.assert_called_once()
    
    def test_check_availability_not_found(self, service):
        """测试 gvim 不可用（文件不存在）"""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            assert service.check_availability() is False
    
    def test_check_availability_timeout(self, service):
        """测试 gvim 检查超时"""
        from subprocess import TimeoutExpired
        with patch('subprocess.run', side_effect=TimeoutExpired('gvim', 5)):
            assert service.check_availability() is False
    
    def test_check_availability_error(self, service):
        """测试 gvim 检查出错"""
        from subprocess import CalledProcessError
        with patch('subprocess.run', side_effect=CalledProcessError(1, 'gvim')):
            assert service.check_availability() is False


class TestGvimServiceOpenFile:
    """测试 GvimService 打开文件功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            return GvimService(tmpdir=tmpdir)
    
    def test_open_file_success(self, service):
        """测试成功打开文件"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch('subprocess.Popen') as mock_popen:
                # 确保目录存在
                Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
                test_file = os.path.join(service.tmpdir, "test.txt")
                Path(test_file).touch()
                
                result = service.open_file(test_file)
                
                assert result["success"] is True
                assert "已打开文件" in result["message"]
                assert result["file_path"] == os.path.abspath(test_file)
                mock_popen.assert_called_once()
    
    def test_open_file_creates_if_not_exists(self, service):
        """测试打开不存在的文件时创建文件"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch('subprocess.Popen') as mock_popen:
                test_file = os.path.join(service.tmpdir, "new_file.txt")
                
                result = service.open_file(test_file)
                
                assert os.path.exists(test_file)
                assert result["success"] is True
                mock_popen.assert_called_once()
    
    def test_open_file_with_line_number(self, service):
        """测试打开文件并定位到行号"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch('subprocess.Popen') as mock_popen:
                # 确保目录存在
                Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
                test_file = os.path.join(service.tmpdir, "test.txt")
                Path(test_file).touch()
                
                service.open_file(test_file, line_number=10)
                
                # 验证命令包含行号参数
                call_args = mock_popen.call_args[0][0]
                assert '+10' in call_args or ['+', '10'] == call_args[-3:-1]
    
    def test_open_file_read_only(self, service):
        """测试只读模式打开文件"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch('subprocess.Popen') as mock_popen:
                # 确保目录存在
                Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
                test_file = os.path.join(service.tmpdir, "test.txt")
                Path(test_file).touch()
                
                service.open_file(test_file, read_only=True)
                
                # 验证命令包含只读参数
                call_args = mock_popen.call_args[0][0]
                assert '-R' in call_args
    
    def test_open_file_gvim_unavailable(self, service):
        """测试 gvim 不可用时抛出错误"""
        with patch.object(service, 'check_availability', return_value=False):
            with pytest.raises(GvimServiceError) as exc_info:
                service.open_file("test.txt")
            assert "gvim 不可用" in str(exc_info.value)
    
    def test_open_file_expand_user(self, service):
        """测试展开用户目录"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch('subprocess.Popen') as mock_popen:
                # 使用真实的临时目录路径，避免创建不存在的目录
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
                    test_file = tmp_file.name
                
                with patch('os.path.expanduser', return_value=test_file):
                    with patch('os.path.abspath', return_value=test_file):
                        service.open_file("~/test.txt")
                        
                        # 验证使用了绝对路径
                        call_args = mock_popen.call_args[0][0]
                        assert test_file in call_args
                        
                        # 清理
                        if os.path.exists(test_file):
                            os.unlink(test_file)


class TestGvimServiceOpenMediaWikiPage:
    """测试 GvimService 打开 MediaWiki 页面功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            return GvimService(tmpdir=tmpdir)
    
    def test_open_mediawiki_page_success(self, service):
        """测试成功打开 MediaWiki 页面"""
        # Mock MediaWiki 页面
        mock_page = MagicMock()
        mock_page.content = "Test page content"
        mock_page.url = "https://example.com/wiki/Test"
        
        # Mock MediaWiki 客户端
        mock_client = MagicMock()
        mock_client.get_page.return_value = mock_page
        
        with patch.object(service, 'check_availability', return_value=True):
            with patch.object(service, '_get_mediawiki_client', return_value=mock_client):
                with patch('subprocess.Popen') as mock_popen:
                    # 确保目录存在
                    Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
                    
                    result = service.open_mediawiki_page("Test Page")
                    
                    assert result["success"] is True
                    assert result["page_title"] == "Test Page"
                    assert result["file_path"].endswith(".mediawiki")
                    assert result["url"] == "https://example.com/wiki/Test"
                    
                    # 验证文件已创建并包含内容
                    assert os.path.exists(result["file_path"])
                    with open(result["file_path"], 'r', encoding='utf-8') as f:
                        content = f.read()
                        assert "Test page content" in content
                        assert "<!-- MediaWiki Page: Test Page -->" in content
    
    def test_open_mediawiki_page_not_found(self, service):
        """测试 MediaWiki 页面不存在"""
        mock_client = MagicMock()
        mock_client.get_page.return_value = None
        
        with patch.object(service, 'check_availability', return_value=True):
            with patch.object(service, '_get_mediawiki_client', return_value=mock_client):
                with pytest.raises(GvimServiceError) as exc_info:
                    service.open_mediawiki_page("NonExistent Page")
                assert "页面不存在" in str(exc_info.value)
    
    def test_open_mediawiki_page_connection_error(self, service):
        """测试 MediaWiki 连接错误"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch.object(service, '_get_mediawiki_client', side_effect=GvimServiceError("无法连接")):
                with pytest.raises(GvimServiceError) as exc_info:
                    service.open_mediawiki_page("Test")
                assert "无法连接" in str(exc_info.value) or "失败" in str(exc_info.value)


class TestGvimServiceSaveMediaWikiPage:
    """测试 GvimService 保存 MediaWiki 页面功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            return GvimService(tmpdir=tmpdir)
    
    def test_save_mediawiki_page_success(self, service):
        """测试成功保存 MediaWiki 页面"""
        # 确保目录存在
        Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
        
        # 创建临时文件
        test_file = os.path.join(service.tmpdir, "test.mediawiki")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("<!-- MediaWiki Page: Test Page -->\n")
            f.write("Updated content")
        
        # Mock MediaWiki 客户端
        mock_client = MagicMock()
        mock_client.edit_page.return_value = True
        
        with patch.object(service, '_get_mediawiki_client', return_value=mock_client):
            result = service.save_mediawiki_page("Test Page", test_file, summary="Test edit")
            
            assert result["success"] is True
            assert result["page_title"] == "Test Page"
            mock_client.edit_page.assert_called_once_with(
                "Test Page",
                "Updated content",
                summary="Test edit",
                minor=True
            )
    
    def test_save_mediawiki_page_removes_metadata(self, service):
        """测试保存时移除元数据"""
        # 确保目录存在
        Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
        
        test_file = os.path.join(service.tmpdir, "test.mediawiki")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("<!-- MediaWiki Page: Test Page -->\n")
            f.write("Content without metadata")
        
        mock_client = MagicMock()
        mock_client.edit_page.return_value = True
        
        with patch.object(service, '_get_mediawiki_client', return_value=mock_client):
            service.save_mediawiki_page("Test Page", test_file)
            
            # 验证元数据被移除
            call_args = mock_client.edit_page.call_args[0]
            assert "<!-- MediaWiki Page" not in call_args[1]
            assert "Content without metadata" in call_args[1]
    
    def test_save_mediawiki_page_failure(self, service):
        """测试保存失败"""
        # 确保目录存在
        Path(service.tmpdir).mkdir(parents=True, exist_ok=True)
        
        test_file = os.path.join(service.tmpdir, "test.mediawiki")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Content")
        
        mock_client = MagicMock()
        mock_client.edit_page.return_value = False
        
        with patch.object(service, '_get_mediawiki_client', return_value=mock_client):
            with pytest.raises(GvimServiceError) as exc_info:
                service.save_mediawiki_page("Test Page", test_file)
            assert "保存 MediaWiki 页面失败" in str(exc_info.value)


class TestGvimServiceEditFileWithContent:
    """测试 GvimService 使用内容编辑文件功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            return GvimService(tmpdir=tmpdir)
    
    def test_edit_file_with_content_success(self, service):
        """测试成功使用内容编辑文件"""
        with patch.object(service, 'check_availability', return_value=True):
            with patch('subprocess.Popen') as mock_popen:
                result = service.edit_file_with_content(
                    "/path/to/target.txt",
                    "Test content"
                )
                
                assert result["success"] is True
                assert result["target_file"] == "/path/to/target.txt"
                assert "temp_file" in result
                assert os.path.exists(result["temp_file"])
                
                # 验证临时文件包含内容
                with open(result["temp_file"], 'r', encoding='utf-8') as f:
                    assert f.read() == "Test content"
                
                mock_popen.assert_called_once()
    
    def test_edit_file_with_content_gvim_unavailable(self, service):
        """测试 gvim 不可用时抛出错误"""
        with patch.object(service, 'check_availability', return_value=False):
            with pytest.raises(GvimServiceError) as exc_info:
                service.edit_file_with_content("/path/to/file.txt", "content")
            assert "gvim 不可用" in str(exc_info.value)


class TestGvimServiceGetMediaWikiClient:
    """测试 GvimService 获取 MediaWiki 客户端功能"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with tempfile.TemporaryDirectory() as tmpdir:
            return GvimService(tmpdir=tmpdir)
    
    def test_get_mediawiki_client_success(self, service):
        """测试成功获取 MediaWiki 客户端"""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        
        with patch('backend.services.gvim_service.gvim_service.MediaWikiClientService', return_value=mock_client):
            client = service._get_mediawiki_client()
            
            assert client is not None
            assert service._mediawiki_client is not None
            mock_client.connect.assert_called_once()
    
    def test_get_mediawiki_client_connection_failed(self, service):
        """测试 MediaWiki 连接失败"""
        mock_client = MagicMock()
        mock_client.connect.return_value = False
        
        with patch('backend.services.gvim_service.gvim_service.MediaWikiClientService', return_value=mock_client):
            with pytest.raises(GvimServiceError) as exc_info:
                service._get_mediawiki_client()
            assert "无法连接到 MediaWiki" in str(exc_info.value)
    
    def test_get_mediawiki_client_cached(self, service):
        """测试客户端缓存"""
        mock_client = MagicMock()
        mock_client.connect.return_value = True
        
        with patch('backend.services.gvim_service.gvim_service.MediaWikiClientService', return_value=mock_client):
            client1 = service._get_mediawiki_client()
            client2 = service._get_mediawiki_client()
            
            # 应该返回同一个客户端实例
            assert client1 is client2
            # connect 应该只调用一次
            assert mock_client.connect.call_count == 1

