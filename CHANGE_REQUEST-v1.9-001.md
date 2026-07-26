# CR-001：Server酱响应 readkey 脱敏

- 状态：Pending approval
- 提出日期：2026-07-26
- 原因：`data/run-status.json` 与 `data/run-history.json` 的既有响应预览会保存 Server酱成功响应中的 `readkey`。该字段不是 SendKey，但官方公开文档未说明其权限；公开仓库中应避免持续写入。

## 受影响需求

- NFR-007：安全与隐私透明。
- NFR-012：模型配置安全与范围控制。

## 建议方案

在 `src/outputs/serverchan.py` 中对响应预览 JSON 的 `readkey` 等敏感字段进行脱敏，并增加回归测试。未来运行不再写入该字段；不改变 Server酱请求、推送语义、新闻筛选或调度。

## 历史数据决策

该方案只阻止未来写入，不能删除 Git 历史中已有的值。是否重写公开 Git 历史、调整仓库公开性或轮换相关凭证属于更高影响的单独决策，未包含在建议方案中。

## 影响与验收

- 改动范围：`src/outputs/serverchan.py`、相关测试、PRD/验收记录。
- 验收：成功响应预览不含 `readkey`；原有 Server酱成功/失败诊断与测试继续通过。
- 推荐：批准“仅脱敏未来响应”作为 v1.10 的最小安全修复。
