# bili-course-to-notes

把 B 站上的课程视频，转成一份能反复看的结构化笔记。

```
课程视频（30 分钟 ~ 20 小时）
    ↓  取字幕 / 无字幕时转写音频
文字（带时间戳）
    ↓  按考点时间戳定点抽帧
课件截图（规律总结页）
    ↓  结构化提取 + 人工校订
笔记.md / .html（带图、带时间戳、可回看）
    ↓  按考点切片
片段/*.mp4（每段 10-15 分钟）
```

## 解决什么问题

看完一门 20 小时的课，三周后你只记得「好像讲过」。想复习某个具体方法，得重新拖进度条找。

这个工具把课程拆成：

- **一份带图的笔记** —— 每个方法至少一张课件截图，配时间戳，忘了能跳回去
- **一堆按考点切的片段** —— 每个 10-15 分钟，切点落在完整句子之间，不会从半句话开始

产出规模参考（21 小时课程）：约 2 万字笔记、39 张图、26 张表、93 个片段。

## 快速开始

```bash
# 依赖
pip install playwright yt-dlp markdown pillow numpy
playwright install chromium
# 另需系统装好 ffmpeg

# 1. 选片 —— 先看分P结构，不要只看标题
python scripts/fetch.py info BV1xxxxxxxxx

# 2. 查字幕
python scripts/fetch.py subs BV1xxxxxxxxx --cookies cookies.txt

# 3. 没字幕就下音频（几秒完成）
python scripts/fetch.py audio BV1xxxxxxxxx -o audio/

# 4. 有字幕就下字幕
python scripts/fetch.py subs BV1xxxxxxxxx --cookies cookies.txt --save -o subs/

# 5. 字幕转文本
python scripts/extract.py srt2text subs/*.srt -o text/

# 6. 摸骨架 + 提考点
python scripts/extract.py outline text/*.txt --every 600
python scripts/extract.py concepts text/*.txt

# 7. 下载视频并定点抽帧
python scripts/fetch.py video BV1xxxxxxxxx -o video/
python scripts/frames.py pick video/P01.mp4 --at 120,300,450 -o images/

# 8. 写笔记 → 生成 HTML
python scripts/build.py notes.md
python scripts/check.py notes.md      # 交付前自检
```

## 七个踩过的坑

这些是实际做完整套流程后才发现的，写在 SKILL.md 里的时候还是猜测。

**1. 视频标题是营销文案，不是内容目录**

一个标题写《3 小时速通 XX 所有知识点》的视频，210 分钟全在讲其中一个分支，另外三类一字未提。下载了 200MB、做完字幕和抽帧才发现覆盖不到一半。

→ **选片第一步永远是看分P结构**，`fetch.py info` 就是干这个的。

**2. B 站 cookie 会过期，而且失败是静默的**

症状：所有视频的字幕列表突然只剩 `danmaku`，`--list-subs` 不报错，只是没有 `ai-zh`。很容易误判成「这些视频本来就没字幕」。

→ **拿一个已知有字幕的老视频做对照**。它也没了 = cookie 过期；它还有 = 才是这个视频真没字幕。

**3. 没字幕不等于放弃这个视频**

用 ASR 转写音频即可。30 分钟音频约 1 万字，质量够用（专业词会有同音错，如「交点→教练」，不影响理解）。

**4. 均匀抽帧会把视频切碎**

`fps=1/3` 抽 36 分钟视频，得到 279 页——绝大多数是老师讲题的中间过程，翻着全是废图。

→ **按考点时间戳定点单抽**。这类课件的结构是「标题页 → 规律总结页 → 例题页」，总结页就在每个知识点开头的 5–20 秒。19 个点抽 19 张，命中率接近 100%。

**5. 配图要按「方法」算，不是按「章节」算**

一章放一张图看着齐了，但章内可能有 5 个方法。做判断推理那套时，位置规律一节配了 1 张图，可这一节下面有平移、旋转、翻转、九宫格、标号法 5 个方法。

→ 用 `check.py` 逐小节盘点，把「方法类」的无图项全揪出来。

**6. 30 万字以上不要通读**

33.6 万字的课程字幕，逐字读既装不进上下文，边际收益也极低（大量口语和重复）。

→ **每 10 分钟采样一句摸骨架 + 正则抓考点命名句 + 按分P 分批读**。写脚本做结构化提取，永远优于硬读。

**7. 视频切片会切在半句话上**

按固定时长切，切点随机落在句中，开头缺半句话。

→ **切点吸附到字幕的句子起始时间**（句子之间的静默点），吸附范围 ±90 秒。实测切出来正好落在一道题的题干开头。

## 目录结构

```
scripts/
├── search.py    搜 B 站（Playwright，可选带登录态）
├── fetch.py     看分P结构 / 查字幕 / 下视频 / 下音频
├── extract.py   SRT→文本、采样骨架、抓考点命名句、提信号句
├── frames.py    定点抽帧、密集抽帧、按差异分页、拼联系表
├── cut.py       按时间轴切片，切点吸附句子边界
├── build.py     Markdown → 单页 HTML
└── check.py     交付前自检（配图覆盖率 / 路径可达 / 时间戳）
```

## 适用范围

**适合**：有课件的课程视频——PPT 精讲、系统课、速通课、公开课。

**不适合**：真人 Vlog、游戏录屏、访谈、纯口播无课件。这套流程依赖「课件画面」和「结构化讲解」，换类型会失效。

## 注意

- 本工具只处理**你自己有权访问**的内容。下载的视频仅供个人学习，请遵守平台条款和著作权法。
- B 站登录态（cookie）只用于获取字幕，不要提交到版本库。
- 转写和截图的质量取决于你使用的视觉 / 语音模型能力。

## License

MIT
