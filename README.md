# 抖音 AI 伪纪录片图文 Skill

发一个故事（一句梗概或完整情节），自动做出整套"手机随手拍"风格的伪纪录片图文：

- 场景设定卡：定好贯穿全篇的地点、标记物、时间线，保证每张图一致
- 分镜表：每张的第一人称文案和画面描述
- GPT 生图提示词：一段设定加逐张提示词，复制给 GPT 就能出图
- 标题、正文、发布清单

故事节奏按这类图文的套路来：前几张平淡日常，第 4 张左右出现小异常，之后一点点升级，结尾留悬念或冷反转、不解释。温情和哲思类故事也能做。

## 安装

### Claude Code

```
/plugin marketplace add linqiuFF/douyin-pseudo-doc-skill
/plugin install douyin-pseudo-doc@linqiuff-skills
```

也可以手动安装：把 `skills/douyin-pseudo-doc-workflow` 文件夹复制到 `~/.claude/skills/`（所有项目可用），或复制到项目里的 `.claude/skills/`（只在该项目可用）。

### Claude.ai

把 `skills/douyin-pseudo-doc-workflow` 文件夹打包成 zip，在 Claude.ai 的技能（Skills）设置里上传。

## 使用

直接说：

> 把这个故事做成伪纪录片图文：我手机相册每天凌晨三点会多一张照片，拍的是另一个我

可选：指定张数（8–15，默认 10）、风格（恐怖/悬案/志怪/温情/哲思）、结局（留悬念/揭晓/反转）。

## 只用 GPT，不装 Skill

[`skills/douyin-pseudo-doc-workflow/gpt-master-prompt.md`](skills/douyin-pseudo-doc-workflow/gpt-master-prompt.md) 是一份 GPT 总指令。粘贴到 ChatGPT 对话里，或者放进自建 GPT 的"指令"设置，之后只发故事，GPT 会自己拆分镜、逐张生图，最后写好标题和正文。

## 内容边界

只做明确虚构的故事：不涉及真实案件、灾难和能认出来的真人，不伪造新闻、警情或官方通知。改编在世作者的作品时，只借设定并注明灵感来源。发布时记得勾选"内容由AI生成"声明。
