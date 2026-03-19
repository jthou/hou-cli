#!/usr/bin/env node
/**
 * 通过 Claude Agent SDK 调用 baoyu-comic 生成漫画
 * 时间：2025-03-17；理由：hou-cli 集成 baoyu；方法：子进程调用
 * 时间：2025-03-18；理由：支持 TheTurbo.ai、模型选择；方法：ANTHROPIC_BASE_URL、--model
 *
 * 用法: node run.mjs <source_path> [--art manga] [--tone warm] [--style ohmsha] [--model claude-3-5-sonnet] [--output-dir path]
 * 需: ANTHROPIC_API_KEY 或 TURBOGATEWAY_API_KEY；.baoyu-skills/.env 中至少一个图生 API key（含万相 DASHSCOPE）
 */
import { query } from "@anthropic-ai/claude-agent-sdk";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, "../..");

const args = process.argv.slice(2);
const sourcePath = args[0];
if (!sourcePath) {
  console.error(JSON.stringify({ success: false, error: "缺少 source_path 参数" }));
  process.exit(1);
}

// 解析 --output-dir、--art、--tone、--style、--model
let extraParts = [];
for (let i = 1; i < args.length; i++) {
  if (args[i] === "--output-dir" && args[i + 1]) {
    extraParts.push(`将输出保存到 ${args[i + 1]}`);
    i++;
  } else if (args[i] === "--model" && args[i + 1]) {
    process.env.ANTHROPIC_MODEL = args[i + 1];
    i++;
  } else if (args[i] === "--art" || args[i] === "--tone" || args[i] === "--style") {
    if (args[i + 1]) extraParts.push(`${args[i]}=${args[i + 1]}`);
    i++;
  }
}
// 时间：2025-03-19；理由：非交互环境 Agent 不能等待 AskUserQuestion；方法：明确要求跳过所有确认步骤
const outputHint = extraParts.find((p) => p.startsWith("将输出保存")) || "将输出保存到 comic/ 目录";
const nonInteractiveHint = `【非交互模式 - 必须遵守】当前无用户可交互，你必须：
1. 跳过 Step 2 确认：直接使用 analysis 推荐的 style（或 ligne-claire + neutral）
2. 跳过 Step 4 outline 审查：skip_outline_review=true
3. 跳过 Step 6 prompt 审查：skip_prompt_review=true
4. 执行完整流程至 Step 9：分析→故事板→角色→prompts→图生（先 characters.png 再每页）→merge-to-pdf
5. 勿调用 AskUserQuestion，遇确认一律选推荐/默认并继续`;
const prompt = `请使用 baoyu-comic 技能，根据文件 ${sourcePath} 创建知识漫画。${extraParts.length ? extraParts.join("，") + "。" : ""} ${outputHint}。${nonInteractiveHint}`;

async function main() {
  try {
    const output = [];
    for await (const message of query({
      prompt,
      options: {
        cwd: projectRoot,
        settingSources: ["user", "project"],
        allowedTools: ["Skill", "Read", "Write", "Bash"],
      },
    })) {
      const text = typeof message === "string" ? message : message?.text ?? JSON.stringify(message);
      output.push(text);
      process.stdout.write(text);
    }
    console.log(JSON.stringify({ success: true, output: output.join("") }));
  } catch (err) {
    console.error(JSON.stringify({ success: false, error: err.message }));
    process.exit(1);
  }
}

main();
