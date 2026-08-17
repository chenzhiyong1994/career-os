# JD Analysis 的开源参考模式

调研日期：2026-07-01。

## 值得研究的项目

- Resume Matcher: https://github.com/srbhr/Resume-Matcher
  - 学习它的简历与 JD 匹配流程、ATS 风格评分、关键词缺口展示和可解释优化建议。
  - 可借鉴的产品模式：不要只给数字分数，要告诉用户为什么匹配或不匹配。

- JobSpy: https://github.com/speedyapply/JobSpy
  - 学习岗位来源归一化、不同招聘站点的通用字段，以及岗位去重方式。
  - 可借鉴的产品模式：把来源、发布日期、地点、公司、岗位名称和规范化 JD 正文分开存储。

- JSON Resume schema: https://github.com/jsonresume/resume-schema
  - 可作为 `candidate profile` 的数据交换层参考，尤其适合工作经历、教育、技能、项目和链接。
  - 可借鉴的产品模式：先保存结构化资料，再生成自然语言文本。

## Career OS 的 JD 对象

进入下游流程前，优先捕获这些字段：

- `source`：URL、粘贴文本、猎头消息或手动备注。
- `role`：岗位名称、公司、部门、级别、地点、雇佣类型。
- `requirements`：按类别整理的明确要求。
- `signals`：带置信度的推断优先级。
- `keywords`：原始关键词和可用同义表达。
- `evidence_needed`：候选人需要补充的事实或材料。
- `risks`：弱匹配、职责范围模糊、信息缺失或筛选风险。

## 评分建议

评分只用于导航，不用于给候选人下结论：

- 5：有直接证据，并且是岗位核心要求。
- 4：有强相关证据。
- 3：有相邻证据，但需要翻译成岗位语言。
- 2：只有弱证据或间接证据。
- 1：目前没有证据。

每个分数都要同时说明：补充什么证据可以提高匹配度。
