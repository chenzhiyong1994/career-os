# Resume QA Checklist

正式交付前运行：

```bash
python skills/html-resume-builder/scripts/export_and_qa.py path/to/resume.html --pdf path/to/resume.pdf --strict-final
```

严格模式必须完成以下检查：

- Chrome/Chromium 成功生成新的 PDF，不能复用旧文件。
- `pdfinfo` 确认为一页 A4 竖版。
- `pdffonts` 或内置 PDF 检查库能读取字体列表；只有明确需要固定字体时才传 `--expected-font`。
- `pdftotext` 或内置 PDF 检查库能提取可读文本。
- `pdftoppm` 成功生成整页截图并完成底部留白测量。
- HTML 和 PDF 中没有模板文本占位符，引用的本地图片存在且不再使用内置示例头像。项目特有敏感词使用 `--forbid-term <term>` 追加。

人工检查生成的截图：

- 姓名、联系方式、日期、公司、项目、教育和链接均与确认内容一致。
- 阅读顺序清楚，没有重叠、裁切、断行异常或标题碰撞。
- 正文不全局加粗，层级和段落间距一致。
- 头像保持彩色、比例正确。
- 页面密度自然，正文底部留白不超过 15%。

常见处理顺序：

- 超过一页：先压缩正文，再调整行高和段落间距。
- 过于拥挤：先增加少量行高，不要用横向字距强行撑开。
- 过于空洞：适度增大字号、行高和模块节奏，不要编造成果填充。
- 高亮不换行：移除不必要的 `nowrap`。

任一严格检查失败，或截图尚未人工查看，都不能把简历标记为完成。
