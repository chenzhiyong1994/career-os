# 合成示例

这里的材料用于展示 Career OS 的核心对象如何衔接。所有人物、组织、日期、链接和数字均为虚构数据，不对应真实候选人或岗位。

> 这些文件是讨论中的数据骨架，不是已经稳定的 Schema。字段会随实际使用反馈继续调整。

## 文件

- [`candidate-profile.example.yaml`](./demo/candidate-profile.example.yaml)：候选人的稳定事实源与证据边界；
- [`jd-scorecard.example.yaml`](./demo/jd-scorecard.example.yaml)：从目标 JD 中提炼的要求、信号、关键词和风险；
- [`application-packet.example.md`](./demo/application-packet.example.md)：把岗位、简历版本、作品证据和后续任务放进一个申请材料包。

## 建议体验顺序

1. 把 `candidate-profile.example.yaml` 和一段目标 JD 交给 `$jd-analysis`；
2. 对照生成结果与 `jd-scorecard.example.yaml`，检查明确要求和推断是否分开；
3. 把 profile 与 scorecard 交给 `$resume-tailor`，观察它是否只使用已有证据；
4. 确认内容后，再交给 `$html-resume-builder` 生成一页 A4 成品；
5. 用 `$portfolio-curator` 检查 `proof_links` 与案例页还缺什么。

你可以自由修改这些合成数据来构造边界案例，但不要用真实简历直接替换后提交回仓库。
