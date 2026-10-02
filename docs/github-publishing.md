# GitHub 发布资料

## 仓库名称

`shanghai-news-insight`

## About / Description（英文，可直接复制）

Interactive Shanghai A-share research terminal with DeepSeek agents, evidence-linked news analysis, and a reproducible DCF valuation engine. Built with Next.js, FastAPI, and Python.

## 中文项目描述

沪讯是一个面向沪市 A 股的交互式研究工作台，结合 DeepSeek Agent、可追溯新闻证据与独立 DCF 引擎，支持公司研究、情景估值、专业提示词、批量新闻分析和报告导出。

## Topics

`fintech` `equity-research` `deepseek` `ai-agent` `dcf` `valuation` `financial-analysis` `nextjs` `fastapi` `typescript` `python` `echarts`

## 较长的展示简介

Shanghai News Insight connects company information, financial assumptions and valuation in a single research workflow. Its responsive terminal lets users inspect news evidence, adjust cash-flow assumptions, compare valuation scenarios and ask source-constrained follow-up questions. A deterministic Python engine produces the numerical results, while DeepSeek explains business drivers, risks and evidence gaps. Versioned prompts, saved snapshots and report exports make the research process visible and reproducible.

## 上传方式

1. 解压源码包。在 GitHub 创建空仓库，建议使用上述名称和英文 Description。
2. 将解压后的 `shanghai-news-insight` **目录内的内容**放到仓库根目录。不要只上传 ZIP，否则仓库首页不会展示 README 和项目结构。
3. 保留 `docs/screenshots/` 与 README 的相对位置，GitHub 会直接显示文档中的图片。
4. 可使用 GitHub Desktop 添加此目录并提交、发布。若使用 Git，请在项目目录执行下方命令，替换仓库地址。

```powershell
git init
git add .
git commit -m "Initial release: Shanghai News Insight"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/shanghai-news-insight.git
git push -u origin main
```

5. 在仓库 About 中填写 Description 和 Topics。当前没有公网应用地址，Website 留空，不要填写 localhost。

## 本次整理

- 首页为英文 README，附完整中文版。
- 图片均来自实际产品；茅台截图明确标注历史数据，旧版截图单独注明日期。
- 保留前后端源码、测试、迁移、锁文件、启动脚本、虚构 fixtures 和方法文档。
- 排除 `.env`、本地数据库、日志、运行缓存、依赖目录、构建产物及个人工作路径。
- 没有代替作者选择 MIT 等整体授权许可证；确定授权意愿后再添加 LICENSE。
- 本文件提供发布资料与步骤，尚未创建远程仓库或上传任何内容。

## 截图目录

| 文件 | 内容与时点 |
| --- | --- |
| `screenshots/maotai-research.jpg` | 公司研究；10 月 2 日截图，9 月 27 日准备的历史研究 |
| `screenshots/maotai-news.jpg` | 新闻证据与经营影响；同一历史研究 |
| `screenshots/maotai-dcf.jpg` | DCF 实验；同一历史研究 |
| `screenshots/prompt-library.jpg` | 当前专业提示词与版本记录 |
| 其他 PNG | 9 月 19 日的原有界面验收资料 |
