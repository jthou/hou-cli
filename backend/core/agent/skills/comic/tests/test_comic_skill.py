"""漫画技能 ComicSkill 单元测试

时间：2025-03-19；理由：用户要求「没有通过测试的工具就是狗屎」，需自测验证后再集成
方法：mock 子进程/环境，验证 _ensure_extend_md、_ensure_claude_skills_path、_build_comic_env、ComicSkill.execute 全流程
"""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 在导入 skill 前 patch ROOT，使测试使用临时目录
_TEST_ROOT = None


@pytest.fixture
def project_root(tmp_path):
    """创建临时项目结构：backend/.agents/skills/baoyu-comic/SKILL.md、.claude/skills/baoyu-comic
    使用 tmp_path（pytest 默认在 /tmp 或 /var/folders）时，output_dir 会被 normalize_output_dir 回退到 ~/hou-cli/outputs。
    因此测试 output_dir 时改用 home 下的临时目录，确保路径一致。
    """
    root = tmp_path / "project"
    root.mkdir()
    # baoyu-comic 源
    baoyu = root / "backend" / ".agents" / "skills" / "baoyu-comic"
    baoyu.mkdir(parents=True)
    (baoyu / "SKILL.md").write_text("name: baoyu-comic\n")
    # run_baoyu_comic 依赖（_run_comic_agent 会检查）
    scripts_run = root / "scripts" / "run_baoyu_comic"
    scripts_run.mkdir(parents=True)
    (scripts_run / "node_modules").mkdir()
    (scripts_run / "run.mjs").write_text("// mock")
    return root


@pytest.fixture(autouse=True)
def patch_comic_root(project_root):
    """patch skill 模块的 ROOT、SCRIPTS_RUN、RUN_MJS 为临时项目路径"""
    with patch(
        "backend.core.agent.skills.comic.skill.ROOT",
        project_root,
    ), patch(
        "backend.core.agent.skills.comic.skill.SCRIPTS_RUN",
        project_root / "scripts" / "run_baoyu_comic",
    ), patch(
        "backend.core.agent.skills.comic.skill.RUN_MJS",
        project_root / "scripts" / "run_baoyu_comic" / "run.mjs",
    ):
        yield project_root


class TestEnsureExtendMd:
    """_ensure_extend_md 单元测试"""

    def test_creates_extend_md_when_missing(self, project_root):
        """project 和 user 均无 EXTEND.md 时，在 project 下创建"""
        from backend.core.agent.skills.comic.skill import _ensure_extend_md

        extend = project_root / ".baoyu-skills" / "baoyu-comic" / "EXTEND.md"
        assert not extend.exists()
        _ensure_extend_md(project_root)
        assert extend.exists()
        content = extend.read_text()
        assert "version: 2" in content
        assert "watermark:" in content
        assert "preferred_art: null" in content

    def test_skips_when_project_extend_exists(self, project_root):
        """project 已有 EXTEND.md 时不再创建"""
        from backend.core.agent.skills.comic.skill import _ensure_extend_md

        extend = project_root / ".baoyu-skills" / "baoyu-comic" / "EXTEND.md"
        extend.parent.mkdir(parents=True, exist_ok=True)
        extend.write_text("custom content")
        _ensure_extend_md(project_root)
        assert extend.read_text() == "custom content"

    def test_skips_when_user_extend_exists(self, project_root):
        """user 已有 EXTEND.md 时不再创建 project 的"""
        from backend.core.agent.skills.comic.skill import _ensure_extend_md

        user_extend = Path.home() / ".baoyu-skills" / "baoyu-comic" / "EXTEND.md"
        user_extend.parent.mkdir(parents=True, exist_ok=True)
        user_extend.write_text("user config")
        try:
            _ensure_extend_md(project_root)
            project_extend = project_root / ".baoyu-skills" / "baoyu-comic" / "EXTEND.md"
            assert not project_extend.exists()
        finally:
            if user_extend.exists():
                user_extend.unlink()
                user_extend.parent.rmdir()
                if user_extend.parent.parent.exists() and not list(user_extend.parent.parent.iterdir()):
                    user_extend.parent.parent.rmdir()


class TestEnsureClaudeSkillsPath:
    """_ensure_claude_skills_path 单元测试"""

    def test_returns_true_when_symlink_exists(self, project_root):
        """已有 .claude/skills/baoyu-comic 且 SKILL.md 存在时返回 True"""
        from backend.core.agent.skills.comic.skill import _ensure_claude_skills_path

        dst_dir = project_root / ".claude" / "skills"
        dst_dir.mkdir(parents=True)
        dst = dst_dir / "baoyu-comic"
        dst.symlink_to((project_root / "backend" / ".agents" / "skills" / "baoyu-comic").resolve())
        ok, err = _ensure_claude_skills_path(project_root)
        assert ok is True
        assert err == ""

    def test_creates_symlink_when_src_exists(self, project_root):
        """backend/.agents/skills/baoyu-comic 存在时创建符号链接"""
        from backend.core.agent.skills.comic.skill import _ensure_claude_skills_path

        dst = project_root / ".claude" / "skills" / "baoyu-comic"
        assert not dst.exists()
        ok, err = _ensure_claude_skills_path(project_root)
        assert ok is True
        assert dst.exists()
        assert dst.is_symlink()
        assert (dst / "SKILL.md").exists()

    def test_returns_false_when_src_missing(self, project_root):
        """backend/.agents/skills/baoyu-comic 不存在时返回 False"""
        from backend.core.agent.skills.comic.skill import _ensure_claude_skills_path

        shutil.rmtree(project_root / "backend" / ".agents" / "skills" / "baoyu-comic")
        ok, err = _ensure_claude_skills_path(project_root)
        assert ok is False
        assert "未找到 baoyu-comic" in err


class TestBuildComicEnv:
    """_build_comic_env 单元测试"""

    def test_sets_anthropic_from_turbogateway_when_missing(self):
        """无 ANTHROPIC_API_KEY 时用 TURBOGATEWAY_API_KEY 填充"""
        from backend.core.agent.skills.comic.skill import _build_comic_env

        with patch.dict(os.environ, {"TURBOGATEWAY_API_KEY": "tk", "TURBOGATEWAY_BASE_URL": "https://x"}, clear=False):
            env = _build_comic_env()
        assert env.get("ANTHROPIC_API_KEY") == "tk"
        assert "https://x" in (env.get("ANTHROPIC_BASE_URL") or "")

    def test_sets_model_when_provided(self):
        """model 参数会设置 ANTHROPIC_MODEL"""
        from backend.core.agent.skills.comic.skill import _build_comic_env

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "k"}, clear=False):
            env = _build_comic_env(model="claude-3-5-sonnet")
        assert env.get("ANTHROPIC_MODEL") == "claude-3-5-sonnet"


class TestComicSkillExecute:
    """ComicSkill.execute 完整流程单元测试（mock 子进程）"""

    @pytest.fixture
    def env_ok(self):
        """模拟环境检查通过、LLM+图生 API 已配置"""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "k", "DASHSCOPE_API_KEY": "d"},
            clear=False,
        ):
            yield

    @pytest.mark.asyncio
    async def test_empty_source_returns_error(self, project_root, env_ok):
        """source 为空时返回错误"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._ensure_baoyu_installed",
            new_callable=AsyncMock,
            return_value=(True, ""),
        ):
            skill = ComicSkill()
            result = await skill.execute(parameters={"source": ""})
        assert result.success is False
        assert "source 不能为空" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invalid_art_returns_error(self, project_root, env_ok):
        """art 非法时返回错误"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._ensure_baoyu_installed",
            new_callable=AsyncMock,
            return_value=(True, ""),
        ):
            skill = ComicSkill()
            result = await skill.execute(
                parameters={"source": "hello", "art": "invalid-art"},
            )
        assert result.success is False
        assert "art 须为" in (result.error or "")

    @pytest.mark.asyncio
    async def test_env_check_fails_returns_error(self, project_root):
        """环境检查失败时返回错误"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(False, "未设置 API key"),
        ):
            skill = ComicSkill()
            result = await skill.execute(parameters={"source": "hello"})
        assert result.success is False
        assert "未设置" in (result.error or "")

    @pytest.mark.asyncio
    async def test_run_agent_fails_returns_error(self, project_root, env_ok):
        """_run_comic_agent 返回失败时返回错误"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._ensure_baoyu_installed",
            new_callable=AsyncMock,
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._run_comic_agent",
            new_callable=AsyncMock,
            return_value=(False, "stdout", "stderr error"),
        ):
            skill = ComicSkill()
            result = await skill.execute(parameters={"source": "hello world"})
        assert result.success is False
        assert "stderr error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_success_when_pdf_in_output_dir(self, project_root, env_ok):
        """PDF 在 output_dir 时返回成功"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        output_dir = project_root / "outputs" / "comic"
        output_dir.mkdir(parents=True)
        pdf_file = output_dir / "topic-slug.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 mock")

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._ensure_baoyu_installed",
            new_callable=AsyncMock,
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._run_comic_agent",
            new_callable=AsyncMock,
            return_value=(True, "log output", ""),
        ), patch(
            "shared.platform_utils.normalize_output_dir",
            return_value=output_dir,
        ):
            skill = ComicSkill()
            result = await skill.execute(
                parameters={"source": "hello world", "output_dir": str(output_dir)},
            )
        assert result.success is True
        assert result.data
        assert len(result.data.get("pdf_files", [])) >= 1
        assert "topic-slug.pdf" in str(result.data.get("pdf_files", []))

    @pytest.mark.asyncio
    async def test_success_when_pdf_in_default_comic_copies_to_output_dir(
        self, project_root, env_ok
    ):
        """PDF 在 cwd/comic 时复制到 output_dir 并返回成功"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        # baoyu-comic 默认输出到 comic/{topic-slug}/
        default_comic = project_root / "comic" / "test-topic"
        default_comic.mkdir(parents=True)
        pdf_file = default_comic / "test-topic.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 mock")

        output_dir = project_root / "outputs" / "comic"
        assert not output_dir.exists()

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._ensure_baoyu_installed",
            new_callable=AsyncMock,
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._run_comic_agent",
            new_callable=AsyncMock,
            return_value=(True, "log", ""),
        ), patch(
            "shared.platform_utils.normalize_output_dir",
            return_value=output_dir,
        ):
            skill = ComicSkill()
            result = await skill.execute(
                parameters={"source": "hello", "output_dir": str(output_dir)},
            )
        assert result.success is True
        assert result.data
        assert len(result.data.get("pdf_files", [])) >= 1
        # 应复制到 output_dir
        copied = output_dir / "test-topic.pdf"
        assert copied.exists(), "PDF 应已复制到 output_dir"

    @pytest.mark.asyncio
    async def test_fails_when_no_pdf_generated(self, project_root, env_ok):
        """run 成功但无 PDF 时返回失败"""
        from backend.core.agent.skills.comic.skill import ComicSkill

        # 使用空的 output_dir，且确保 project_root/comic 下也无 PDF（避免污染）
        output_dir = project_root / "empty_out"
        output_dir.mkdir(parents=True, exist_ok=True)

        with patch(
            "backend.core.agent.skills.comic.skill._check_env",
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._ensure_baoyu_installed",
            new_callable=AsyncMock,
            return_value=(True, ""),
        ), patch(
            "backend.core.agent.skills.comic.skill._run_comic_agent",
            new_callable=AsyncMock,
            return_value=(True, '{"usage":{}}', ""),
        ), patch(
            "shared.platform_utils.normalize_output_dir",
            return_value=output_dir,
        ):
            skill = ComicSkill()
            result = await skill.execute(
                parameters={"source": "hello", "output_dir": str(output_dir)},
            )
        assert result.success is False
        assert "未生成任何 PDF" in (result.error or "")
