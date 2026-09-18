# Agentic Content Pipelines

[English](#english) · [中文](#中文)

## English

Auditable, multi-stage Codex skills for content workflows that can read files, call network services, run media tools, and produce release artifacts.

The first included skill is [`audio-first-video`](skills/audio-first-video/SKILL.md). It separates content, audio/timing, and visual/release work into fresh tasks; binds handoffs and authoritative media with SHA-256; preserves explicit human approvals; and validates encoded output before promotion.

### Why this exists

Long agent runs fail in predictable ways: old context leaks into new decisions, generated files drift from approved inputs, a successful render is mistaken for a releasable artifact, and untrusted content reaches tools with filesystem or network authority. This repository turns those boundaries into executable contracts.

### Security model

The skill processes untrusted text, JSON, paths, media metadata, and project files. It can invoke Python, Node, browsers, FFmpeg, speech services, and transcription tools. Read [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md) before using it with sensitive projects.

### Requirements

- Python 3.10 or newer
- Node.js for a selected video composition runtime
- FFmpeg and FFprobe
- Optional: DashScope for the bundled TTS adapter
- Optional: whisper.cpp or faster-whisper for alignment

The repository does not include credentials, model weights, browsers, media binaries, or a video composition framework. Pin and verify those dependencies for your environment.

### Install as a Codex skill

Copy or symlink `skills/audio-first-video` into your Codex skills directory. Then validate the skill and its context architecture:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py skills/audio-first-video
python3 skills/audio-first-video/scripts/validate_context_budget.py \
  skills/audio-first-video/context-budget.json
```

The repository currently records a passing isolated cold-start check in `context-budget.json`. Regenerate that evidence after changing the entrypoint, context architecture, stage router, handoff, approval, path, provider, subprocess, validation, or release-authority code.

### Development

Run the deterministic unit suite from the skill directory:

```bash
python3 -m unittest discover -s tests -v
```

Some end-to-end media checks require native browser, GPU, codec, model, or provider access and are not silently downgraded in CI.

### Project status

Pre-release. APIs and file contracts may change before `v1.0.0`. Public metrics should be read from GitHub; this repository does not claim downloads or adoption it cannot verify.

### License

Apache-2.0. See [LICENSE](LICENSE).

---

## 中文

本项目提供可审计的多阶段 Codex Skill，用于需要读取文件、访问网络服务、执行媒体工具并生成发布产物的内容工作流。

首个 Skill 是 [`audio-first-video`](skills/audio-first-video/SKILL.md)。它把内容、音频与时间轴、视觉与发布拆分到互不继承对话历史的新任务中；用 SHA-256 绑定阶段交接和权威媒体文件；保留明确的人工批准点；并在发布前校验编码后的实际成片。

### 为什么建立这个项目

长链路 Agent 工作流会以几种可重复的方式失效：旧上下文污染新决策，生成文件偏离已经批准的输入，渲染成功被误认为可以发布，以及不可信内容进入拥有文件系统或网络权限的工具。本项目把这些边界变成可执行、可验证的契约。

### 安全模型

该 Skill 会处理不可信文本、JSON、路径、媒体元数据和项目文件，并可能调用 Python、Node、浏览器、FFmpeg、语音服务和转录工具。将它用于敏感项目之前，请先阅读 [SECURITY.md](SECURITY.md) 和 [docs/threat-model.md](docs/threat-model.md)。

### 环境要求

- Python 3.10 或更高版本
- 所选视频合成运行时需要的 Node.js
- FFmpeg 和 FFprobe
- 可选：用于内置 TTS 适配器的 DashScope
- 可选：用于音频对齐的 whisper.cpp 或 faster-whisper

仓库不包含凭证、模型权重、浏览器、媒体二进制文件或视频合成框架。使用者需要针对自己的环境固定并验证这些依赖。

### 作为 Codex Skill 安装

把 `skills/audio-first-video` 复制或链接到 Codex Skill 目录，然后验证 Skill 结构和上下文架构：

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py skills/audio-first-video
python3 skills/audio-first-video/scripts/validate_context_budget.py \
  skills/audio-first-video/context-budget.json
```

当前 `context-budget.json` 已记录一次通过的隔离冷启动检查。如果修改入口文件、上下文架构、阶段路由、交接、审批、路径、网络提供商、子进程、校验器或发布权限代码，必须重新生成验证证据。

### 开发与测试

在 Skill 目录运行确定性测试：

```bash
python3 -m unittest discover -s tests -v
```

部分端到端媒体检查需要本机浏览器、GPU、编码器、模型或服务商访问权限，CI 不会把这些检查静默降级为通过。

### 项目状态

当前为预发布版本。`v1.0.0` 之前，API 和文件契约仍可能变化。公开指标以 GitHub 为准；本项目不会声称无法验证的下载量或采用情况。

### 许可证

Apache-2.0，详见 [LICENSE](LICENSE)。
