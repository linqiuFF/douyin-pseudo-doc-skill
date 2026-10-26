# 抖音 AI 伪纪录片图文 Skill

发一个故事（一句梗概或完整情节），自动做出整套"手机随手拍"风格的伪纪录片图文：

- 场景设定卡：定好贯穿全篇的地点、标记物、时间线，保证每张图一致
- 分镜表：每张的第一人称文案和画面描述
- 图片：调用 OpenAI 生图接口一次出完，自动保持标记物一致，自动加日期水印和配图文案
- 标题、正文、发布清单

没有 OpenAI API Key 时，会改为输出发给 GPT 的提示词，复制过去一张张生成。

故事节奏按这类图文的套路来：前几张平淡日常，第 4 张左右出现小异常，之后一点点升级，结尾留悬念或冷反转、不解释。温情和哲思类故事也能做。

## 在 GPT 里用（不用安装）

在 ChatGPT 新开一个对话，发这一句，把故事换成你自己的：

```
打开这个链接，读完里面的指令后照着执行：
https://raw.githubusercontent.com/linqiuFF/douyin-pseudo-doc-skill/main/skills/douyin-pseudo-doc-workflow/gpt-master-prompt.md

我的故事：我在旧书摊买了一本日记本，里面写的都是我下周会发生的事，最后一页写着一个日期。
```

GPT 会先给出分镜表，回"开始"生成定妆照，之后一路回"继续"，最后给出标题和正文。

GPT 打不开链接时（没开联网搜索，或者链接被拦），就打开上面的链接，全选复制里面的内容，粘贴到对话开头，再发故事，效果一样。

## 安装

### Claude Code

```
/plugin marketplace add linqiuFF/douyin-pseudo-doc-skill
/plugin install douyin-pseudo-doc@linqiuff-skills
```

也可以手动安装：把 `skills/douyin-pseudo-doc-workflow` 文件夹复制到 `~/.claude/skills/`（所有项目可用），或复制到项目里的 `.claude/skills/`（只在该项目可用）。

### Claude.ai

把 `skills/douyin-pseudo-doc-workflow` 文件夹打包成 zip，在 Claude.ai 的技能（Skills）设置里上传。Claude.ai 一般连不上 OpenAI 接口，所以在那里只能用"输出 GPT 提示词"的方式，自动生图请用 Claude Code。

## 自动生图的准备

1. 安装依赖：`pip install openai pillow`
2. 在 [OpenAI 后台](https://platform.openai.com/api-keys) 创建 API Key，设成环境变量 `OPENAI_API_KEY`
   - macOS / Linux：`export OPENAI_API_KEY=sk-...`（写进 `~/.zshrc` 或 `~/.bashrc` 以后就不用再设）
   - Windows：`setx OPENAI_API_KEY sk-...`，然后重开终端
3. 按张付费，默认 medium 画质，一套 10 张加定妆照大约几块钱人民币，以 OpenAI 官网价格为准

生成的图在故事文件夹的 `output/` 里：`final/` 是带日期水印的，`captioned/` 是又加了配图文案的，可以直接发。

脚本也能单独用，分镜格式见 [`examples/diary.json`](skills/douyin-pseudo-doc-workflow/examples/diary.json)：

```
python skills/douyin-pseudo-doc-workflow/scripts/generate_images.py 你的分镜.json
```

## 使用

直接说：

> 把这个故事做成伪纪录片图文：我手机相册每天凌晨三点会多一张照片，拍的是另一个我

可选：指定张数（8–15，默认 10）、风格（恐怖/悬案/志怪/温情/哲思）、结局（留悬念/揭晓/反转）。

## 只用 GPT，不装 Skill

[`skills/douyin-pseudo-doc-workflow/gpt-master-prompt.md`](skills/douyin-pseudo-doc-workflow/gpt-master-prompt.md) 是一份 GPT 总指令。粘贴到 ChatGPT 对话里，或者放进自建 GPT 的"指令"设置，之后只发故事，GPT 会自己拆分镜、逐张生图，最后写好标题和正文。

## 内容边界

只做明确虚构的故事：不涉及真实案件、灾难和能认出来的真人，不伪造新闻、警情或官方通知。改编在世作者的作品时，只借设定并注明灵感来源。发布时记得勾选"内容由AI生成"声明。
