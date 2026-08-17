---
name: html-resume-builder
description: 将已经确认的简历内容制作成一页 A4 HTML/PDF，并完成模板复制、头像/二维码处理、导出和视觉 QA。用于纯排版、HTML/PDF 成品、打印优化和交付检查；不用于 JD 分析、事实判断、ATS 策略或简历措辞改写。
---

# HTML Resume Builder

## 职责边界

只渲染已经确认的 `resume version`。不得改变候选人事实、补写指标，或为了填满页面新增未经确认的内容。

- 内容需要分析或改写时，先使用 `jd-analysis` / `resume-tailor`。
- 用户只要求排版、导出或视觉修正时，直接使用本 skill；不要重复运行 JD 分析或重写内容。
- 内容不完整时，明确列出缺失项并暂停正式导出，不要用模板示例补位。

## 支持范围

正式模板只包含 `assets/templates/basic-a4/`。它是一页 A4、单栏、ATS 友好的稳定基线。不要引用或承诺其他模板；新增模板应作为独立任务完成设计、验证和用户确认后再纳入。

模板和脚本改编自 `KevinYoung-Kw/vibe-resume-skill`，遵循 CC BY-NC 4.0。保留归因；未经授权不得把借用资源用于商业分发。

## 工作流

1. 确认输入已经稳定：正文、联系方式、日期、链接、头像和二维码均来自用户确认的信息。
2. 创建独立工作目录：

   ```bash
   python skills/html-resume-builder/scripts/create_workspace.py --output <workspace>
   ```

3. 替换 `resume.html` 中全部示例内容和占位资源。保持经历类别真实，不得把实习、项目或正式工作互相挪用。
4. 按 `references/template-contract.md` 调整 A4 排版。优先调整字号、行高和间距，不得用弱内容填充页面。
5. 运行严格导出：

   ```bash
   python skills/html-resume-builder/scripts/export_and_qa.py <workspace>/resume.html --pdf <workspace>/resume.pdf --strict-final
   ```

6. 读取 JSON 结果并检查生成的整页截图。只有脚本退出成功、`ok` 为 `true` 且人工视觉检查通过，才可声明完成。

## 交付门禁

- PDF 必须是一页 A4 竖版，文字可提取，字体列表可读取。
- 不得残留示例姓名、示例联系方式或 `example.com`。
- 不得出现重叠、裁切、头像变形、二维码遮挡或大面积空洞。
- 正文底部留白不得超过页面高度的 15%。
- 项目特有的敏感词通过 `--forbid-term <term>` 显式传入，不设置会误伤正常简历内容的通用禁词。
- 严格检查缺少 Chrome 或所需 PDF 检查工具时必须视为未完成，不得绕过后声称交付成功。

最终检查时读取 `references/qa-checklist.md`。
