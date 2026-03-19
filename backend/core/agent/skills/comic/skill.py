#!/usr/bin/env python3
"""漫画绘图技能 - 集成 baoyu-comic，子进程调用生成知识漫画

时间：2025-03-17；理由：用户要求先集成 baoyu；方法：npx skills add + Claude Agent SDK
完善：2025-03-18；环境检查、参数验证、日志、输出可配置、临时文件清理
"""
import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from backend.core.agent.skills.base import Skill, SkillResult, SkillParameter

logger = logging.getLogger(__name__)

# 项目根目录（skill.py 在 backend/core/agent/skills/comic/，需 5 层到根）
ROOT = Path(__file__).resolve().parents[5]
SCRIPTS_RUN = ROOT / "scripts" / "run_baoyu_comic"
RUN_MJS = SCRIPTS_RUN / "run.mjs"

ART_VALUES = ("ligne-claire", "manga", "realistic", "ink-brush", "chalk")
TONE_VALUES = ("neutral", "warm", "dramatic", "romantic", "energetic", "vintage", "action")
STYLE_VALUES = ("ohmsha", "wuxia", "shoujo")

# 图生 API 环境变量（与 baoyu-image-gen 一致；BAILIAN 与 DASHSCOPE 等效）
IMAGE_API_ENV_KEYS = (
    "DASHSCOPE_API_KEY", "BAILIAN_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY", "REPLICATE_API_TOKEN",
    "JIMENG_ACCESS_KEY_ID", "ARK_API_KEY",
)


# LLM API：支持 Anthropic 直连 或 TheTurbo.ai 网关
# 时间：2025-03-18；理由：用户要求支持 theturbo.ai；方法：TURBOGATEWAY_API_KEY + ANTHROPIC_BASE_URL
LLM_API_KEY_KEYS = ("ANTHROPIC_API_KEY", "TURBOGATEWAY_API_KEY")


def _check_env() -> Tuple[bool, str]:
    """环境检查：LLM API（Anthropic/TheTurbo 或 百炼+DASHSCOPE）、图生 API、Node/npx。返回 (通过, 错误信息)"""
    has_llm_key = any(os.environ.get(k) for k in LLM_API_KEY_KEYS)
    # 百炼模型：DASHSCOPE/BAILIAN 供 LiteLLM 代理 + 图生（时间：2025-03-19）
    if not has_llm_key and any(os.environ.get(k) for k in ("DASHSCOPE_API_KEY", "BAILIAN_API_KEY")):
        has_llm_key = True
    if not has_llm_key:
        return False, "未设置 ANTHROPIC_API_KEY 或 TURBOGATEWAY_API_KEY（TheTurbo.ai）"
    has_image_key = any(os.environ.get(k) for k in IMAGE_API_ENV_KEYS)
    # 也检查项目根 .env 及 .baoyu-skills/.env，并加载到 os.environ 供子进程使用（时间：2025-03-19；理由：用户 key 在 .env）
    if not has_image_key:
        for p in (ROOT / ".env", ROOT / ".baoyu-skills" / ".env", Path.home() / ".baoyu-skills" / ".env"):
            if p.exists():
                try:
                    for line in p.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key = line.split("=")[0].strip()
                            val = line.split("=", 1)[1].strip()
                            if key in IMAGE_API_ENV_KEYS and val:
                                if not os.environ.get(key):
                                    os.environ[key] = val
                                has_image_key = True
                                break
                except Exception:
                    pass
            if has_image_key:
                break
    if not has_image_key:
        return False, "未配置图生 API key，请在 .baoyu-skills/.env 中设置 DASHSCOPE_API_KEY 等"
    return True, ""


def _ensure_extend_md(cwd: Path) -> None:
    """
    确保 .baoyu-skills/baoyu-comic/EXTEND.md 存在，避免 Agent 卡在 first-time setup。
    时间：2025-03-19；理由：baoyu-comic 无 EXTEND.md 时会 AskUserQuestion 阻塞，非交互环境无法继续
    方法：在 project 下创建最小化 EXTEND.md（仅当 project 和 user 均不存在时）
    """
    project_extend = cwd / ".baoyu-skills" / "baoyu-comic" / "EXTEND.md"
    user_extend = Path.home() / ".baoyu-skills" / "baoyu-comic" / "EXTEND.md"
    if project_extend.exists() or user_extend.exists():
        return
    project_extend.parent.mkdir(parents=True, exist_ok=True)
    minimal = """---
version: 2
watermark:
  enabled: false
  content: ""
preferred_art: null
preferred_tone: null
preferred_layout: null
preferred_aspect: null
language: null
character_presets: []
---
"""
    project_extend.write_text(minimal, encoding="utf-8")
    logger.info("已创建默认 .baoyu-skills/baoyu-comic/EXTEND.md 以支持非交互运行")


def _ensure_claude_skills_path(cwd: Path) -> Tuple[bool, str]:
    """
    确保 .claude/skills/baoyu-comic 存在，供 Claude Agent SDK 加载。
    时间：2025-03-18；理由：SDK 从 .claude/skills/ 或 ~/.claude/skills/ 加载，backend/.agents 路径不被识别
    方法：若 backend/.agents/skills/baoyu-comic 存在则建符号链接到 .claude/skills/baoyu-comic
    """
    src = cwd / "backend" / ".agents" / "skills" / "baoyu-comic"
    dst_dir = cwd / ".claude" / "skills"
    dst = dst_dir / "baoyu-comic"
    if dst.exists() and (dst / "SKILL.md").exists():
        return True, ""
    if not src.exists() or not (src / "SKILL.md").exists():
        return False, f"未找到 baoyu-comic 技能目录: {src}，请先执行 npx skills add JimLiu/baoyu-skills --skill baoyu-comic -a cursor -y"
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        dst.symlink_to(src.resolve())
        return True, ""
    except OSError as e:
        return False, f"创建 .claude/skills/baoyu-comic 链接失败: {e}"


async def _ensure_baoyu_installed(cwd: Path) -> Tuple[bool, str]:
    """确保 baoyu-comic 已安装且 SDK 可加载。返回 (成功, 错误信息)"""
    # 优先：项目内 backend/.agents/skills/baoyu-comic 已存在则建链接
    ok, err = _ensure_claude_skills_path(cwd)
    if ok:
        return True, ""
    # 否则尝试 npx skills add
    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "skills", "add", "JimLiu/baoyu-skills", "--skill", "baoyu-comic",
            "-a", "cursor", "-y",
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()
        out = (await proc.stdout.read()).decode() if proc.stdout else ""
        err_out = (await proc.stderr.read()).decode() if proc.stderr else ""
    except FileNotFoundError:
        return False, "未找到 npx，请安装 Node.js"
    except Exception as e:
        logger.exception("baoyu-comic 安装异常")
        return False, str(e)

    if proc.returncode != 0:
        logger.warning("npx skills add 失败: %s", err_out or out)
        return False, f"npx skills add 失败: {err_out or out}"
    # 安装后再次确保 .claude 路径（npx 可能装到 ~/.claude，项目内也建链接以便 SDK 找到）
    ok, err = _ensure_claude_skills_path(cwd)
    return ok, err


def _is_bailian_comic_model(model: Optional[str]) -> bool:
    """判断是否为百炼漫画模型（需 LiteLLM 代理）。时间：2025-03-19；理由：百炼模型需代理转发 Anthropic 请求。"""
    if not model:
        return False
    from backend.api.model_config_routes import COMIC_MODELS_BY_PROVIDER
    bailian_models = [v for v, _ in COMIC_MODELS_BY_PROVIDER.get("bailian", [])]
    return model.strip() in bailian_models


def _build_comic_env(model: Optional[str] = None) -> Dict[str, str]:
    """构建子进程 env：支持 TheTurbo.ai、百炼（LiteLLM 代理）；BAILIAN_API_KEY 等效 DASHSCOPE。"""
    env = dict(os.environ)
    if not env.get("DASHSCOPE_API_KEY") and env.get("BAILIAN_API_KEY"):
        env["DASHSCOPE_API_KEY"] = env["BAILIAN_API_KEY"]
    # 百炼模型：走 LiteLLM 代理（时间：2025-03-19；理由：用户要求支持百炼；方法：代理将 Anthropic 请求转发到 DashScope）
    if model and _is_bailian_comic_model(model):
        proxy_url = env.get("LITELLM_COMIC_PROXY_URL") or "http://localhost:4000"
        env["ANTHROPIC_BASE_URL"] = proxy_url.rstrip("/")
        env["ANTHROPIC_API_KEY"] = env.get("ANTHROPIC_API_KEY") or "sk-litellm-comic"
        if model:
            env["ANTHROPIC_MODEL"] = model
        return env
    # TheTurbo.ai：无 ANTHROPIC_API_KEY 时用 TURBOGATEWAY_API_KEY
    if not env.get("ANTHROPIC_API_KEY") and env.get("TURBOGATEWAY_API_KEY"):
        env["ANTHROPIC_API_KEY"] = env["TURBOGATEWAY_API_KEY"]
        base = env.get("ANTHROPIC_BASE_URL") or env.get("TURBOGATEWAY_BASE_URL") or "https://gateway.theturbo.ai/v1"
        env["ANTHROPIC_BASE_URL"] = base.rstrip("/")
    if model:
        env["ANTHROPIC_MODEL"] = model
    return env


async def _run_comic_agent(
    source_path: str,
    art: str,
    tone: str,
    style: Optional[str],
    output_dir: Optional[str],
    cwd: Path,
    model: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """运行 Claude Agent 调用 baoyu-comic。返回 (成功, 输出, 错误)"""
    args = [str(source_path)]
    if art and art != "ligne-claire":
        args.extend(["--art", art])
    if tone and tone != "neutral":
        args.extend(["--tone", tone])
    if style:
        args.extend(["--style", style])
    if output_dir:
        args.extend(["--output-dir", output_dir])
    if model:
        args.extend(["--model", model])

    env = _build_comic_env(model)

    node_modules = SCRIPTS_RUN / "node_modules"
    if not node_modules.exists():
        return False, "", "未找到 run_baoyu_comic 依赖，请执行 make install-deps"

    if not RUN_MJS.exists():
        return False, "", f"未找到 {RUN_MJS}"

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", str(RUN_MJS), *args,
            cwd=str(cwd),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = (
            (await proc.stdout.read()).decode() if proc.stdout else "",
            (await proc.stderr.read()).decode() if proc.stderr else "",
        )
        await proc.wait()
    except FileNotFoundError:
        return False, "", "未找到 node，请安装 Node.js"
    except Exception as e:
        logger.exception("run_baoyu_comic 执行异常")
        return False, "", str(e)

    if proc.returncode != 0:
        logger.error("run_baoyu_comic 失败 code=%s stderr=%s", proc.returncode, stderr[:500])
        return False, stdout, stderr or "执行失败"
    return True, stdout, ""


class ComicSkill(Skill):
    """漫画绘图技能 - 集成 baoyu-comic"""

    def __init__(self):
        super().__init__(
            name="comic",
            description=(
                "知识漫画生成器，基于 baoyu-comic。将文章或故事转化为分镜漫画。"
                "适用于：知识漫画、教育漫画、传记漫画、教程漫画。"
                "需 ANTHROPIC_API_KEY 或 TURBOGATEWAY_API_KEY（TheTurbo.ai），及 .baoyu-skills/.env 中图生 API（含万相 DASHSCOPE）。"
            ),
            version="1.0.0",
            category="content_generation",
            priority="P2",
            parameters=[
                SkillParameter("source", "string", "源内容（Markdown 文件路径或直接文本）", required=True),
                SkillParameter("art", "string", "画风：ligne-claire, manga, realistic, ink-brush, chalk", required=False, default="ligne-claire", enum=list(ART_VALUES)),
                SkillParameter("tone", "string", "基调：neutral, warm, dramatic, romantic, energetic, vintage, action", required=False, default="neutral", enum=list(TONE_VALUES)),
                SkillParameter("style", "string", "预设：ohmsha, wuxia, shoujo", required=False, enum=list(STYLE_VALUES)),
                SkillParameter("output_dir", "string", "输出目录（须在用户主目录下）", required=False),
                SkillParameter("llm_model", "string", "LLM 模型（Claude/TheTurbo 等，留空用环境默认）", required=False),
            ],
        )

    async def execute(
        self, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        source = (parameters.get("source") or "").strip()
        if not source:
            return SkillResult(success=False, error="source 不能为空")

        art = (parameters.get("art") or "ligne-claire").strip()
        tone = (parameters.get("tone") or "neutral").strip()
        style = (parameters.get("style") or "").strip() or None
        output_dir = (parameters.get("output_dir") or "").strip() or None
        llm_model = (parameters.get("llm_model") or "").strip() or None
        if not llm_model:
            from backend.infrastructure.execution.task_handlers import get_comic_default_model
            llm_model = get_comic_default_model()

        # 参数验证
        if art not in ART_VALUES:
            return SkillResult(success=False, error=f"art 须为 {ART_VALUES} 之一")
        if tone not in TONE_VALUES:
            return SkillResult(success=False, error=f"tone 须为 {TONE_VALUES} 之一")
        if style and style not in STYLE_VALUES:
            return SkillResult(success=False, error=f"style 须为 {STYLE_VALUES} 之一")

        if context:
            self.set_progress_callback(context.get("progress_callback"))

        self.report_progress("环境检查...")
        from shared.load_env import load_env
        load_env(ROOT)
        ok, err = _check_env()
        if not ok:
            return SkillResult(
                success=False,
                error=f"{err}。配置说明见 config/baoyu_comic_setup.md",
            )

        # 解析 source：文件路径 or 直接文本
        # 时间：2025-03-18；理由：source 为长文本时 Path(source).exists() 会触发 OSError 63 File name too long；方法：先判是否像路径
        is_temp_work = False
        looks_like_path = "\n" not in source and len(source) < 260 and source.strip()
        if looks_like_path:
            try:
                p = Path(source).expanduser().resolve()
                if p.exists() and p.is_file():
                    source_path = p
                    if source_path.suffix.lower() not in (".md", ".markdown", ".txt"):
                        logger.warning("源文件非 .md/.txt，可能影响 baoyu 解析: %s", source_path)
                else:
                    looks_like_path = False
            except OSError:
                looks_like_path = False
        if not looks_like_path:
            work_dir = Path(tempfile.mkdtemp(prefix="comic_"))
            work_dir.mkdir(parents=True, exist_ok=True)
            source_path = work_dir / "source.md"
            source_path.write_text(source, encoding="utf-8")
            is_temp_work = True

        # 输出目录：限制在主目录下
        if output_dir:
            from shared.platform_utils import normalize_output_dir
            try:
                out_path = normalize_output_dir(output_dir, restrict_to_home=True)
                output_dir = str(out_path)
            except ValueError as e:
                return SkillResult(success=False, error=str(e))

        cwd = ROOT

        self.report_progress("检查 baoyu-comic 安装...")
        ok, err = await _ensure_baoyu_installed(cwd)
        if not ok:
            return SkillResult(
                success=False,
                error=f"baoyu-comic 安装失败: {err}",
            )

        _ensure_extend_md(cwd)

        self.report_progress("调用 baoyu-comic 生成漫画（可能需要数分钟，请耐心等待）...")
        logger.info("comic skill 开始执行 source=%s art=%s tone=%s", source_path, art, tone)

        ok, out, err = await _run_comic_agent(
            str(source_path), art, tone, style, output_dir, cwd, model=llm_model
        )

        # 临时工作目录清理
        if is_temp_work and source_path.parent.exists():
            try:
                shutil.rmtree(source_path.parent, ignore_errors=True)
            except Exception as e:
                logger.warning("清理临时目录失败: %s", e)

        if not ok:
            setup_hint = (
                "配置说明：\n"
                "1. 设置 ANTHROPIC_API_KEY 或 TURBOGATEWAY_API_KEY（TheTurbo.ai）\n"
                "2. 在 .baoyu-skills/.env 中配置图生 API：DASHSCOPE_API_KEY（万相）、OPENAI_API_KEY 等\n"
                "3. 确保已执行 make install-deps。详见 config/baoyu_comic_setup.md"
            )
            return SkillResult(
                success=False,
                error=f"{err}\n\n{setup_hint}",
            )

        # 时间：2025-03-19；理由：baoyu-comic 默认输出到 cwd/comic/{topic-slug}/，与用户指定的 output_dir 可能不同
        # 方法：优先在 output_dir 查找，若无则查 cwd/comic；若在 cwd/comic 找到则复制到 output_dir
        default_comic = cwd / "comic"
        target_dir = Path(output_dir) if output_dir else default_comic
        pdf_files = list(target_dir.glob("**/*.pdf")) if target_dir.exists() else []
        if not pdf_files and default_comic.exists():
            pdf_files = list(default_comic.glob("**/*.pdf"))
            if pdf_files and output_dir:
                try:
                    out_path = Path(output_dir)
                    out_path.mkdir(parents=True, exist_ok=True)
                    # 时间：2025-03-19；理由：用户反馈输出目录为空；方法：复制整个漫画子目录（含 storyboard、prompts、图片、PDF）
                    comic_subdir = pdf_files[0].parent
                    for f in comic_subdir.iterdir():
                        if f.is_file():
                            shutil.copy2(f, out_path / f.name)
                        elif f.is_dir():
                            shutil.copytree(f, out_path / f.name, dirs_exist_ok=True)
                    pdf_files = list(out_path.glob("**/*.pdf"))
                except Exception as e:
                    logger.warning("复制漫画到 output_dir 失败，回退仅复制 PDF: %s", e)
                    try:
                        for p in pdf_files:
                            shutil.copy2(p, out_path / p.name)
                        pdf_files = list(out_path.glob("*.pdf"))
                    except Exception as e2:
                        logger.warning("复制 PDF 到 output_dir 失败，使用默认位置: %s", e2)
        comic_dir = target_dir if pdf_files else (default_comic if default_comic.exists() else target_dir)

        # 时间：2025-03-18；理由：输出目录为空但任务被标为成功；方法：无 PDF 时判为失败
        if not pdf_files:
            log_preview = out[-2000:] if len(out) > 2000 else out
            # 时间：2025-03-19；理由：排查 Agent 未完成图生/PDF 的原因；方法：将完整 stdout 写入日志文件供排查
            _debug_log_path = None
            if out and len(out) > 500:
                try:
                    log_dir = ROOT / ".baoyu-skills" / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    from datetime import datetime
                    _debug_log_path = log_dir / f"comic_stdout_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    _debug_log_path.write_text(out, encoding="utf-8")
                    logger.info("漫画未生成 PDF，完整 stdout 已保存至 %s", _debug_log_path)
                except Exception as e:
                    logger.warning("保存 comic stdout 失败: %s", e)
            err_msg = (
                "未生成任何 PDF。Agent 可能未找到 baoyu-comic 技能或执行失败。\n"
                "请执行: npx skills add JimLiu/baoyu-skills --skill baoyu-comic -a cursor -y\n"
                f"输出目录: {comic_dir}\n"
            )
            if _debug_log_path:
                err_msg += f"完整日志: {_debug_log_path}\n"
            err_msg += f"日志预览:\n{log_preview[-800:] if len(log_preview) > 800 else log_preview}"
            return SkillResult(success=False, error=err_msg)

        logger.info("comic skill 完成 output_dir=%s pdf_count=%d", comic_dir, len(pdf_files))
        return SkillResult(
            success=True,
            data={
                "output_dir": str(comic_dir) if comic_dir.exists() else str(cwd),
                "pdf_files": [str(p) for p in pdf_files],
                "log_preview": out[-2000:] if len(out) > 2000 else out,
            },
        )


skill_instance = ComicSkill()
