# sanguo3

按用户指定MD／Genesis繁体中文版《三國志Ⅲ》独立重写的施工项目。网页运行、构建与玩家使用不依赖ROM、MOD或模拟器。当前仓库交付项目书与辅助工具，尚未实现游戏或发布站点。

## v3.0 审查修复版

保留38章、6个附录与24个任务组，修复旧版本/错误域名误放行、案例引用与任务覆盖遗漏、首发依赖矛盾和不可执行回滚。新增冻结范围、真实逐案例报告、直接PNG对比、CI前置传递、持久发布归档及完整产物恢复。

- [修复结果和实际边界](docs/replication-guide-v3.0/本次审查与补全.md)
- [Markdown项目书](docs/replication-guide-v3.0/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.0.md)
- [Word项目书](docs/replication-guide-v3.0/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.0.docx)
- [PDF项目书](docs/replication-guide-v3.0/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.0.pdf)
- [完整交付包ZIP](docs/MD版三国志Ⅲ_完全复刻施工指南_v3.0_完整交付包.zip)
- [接手入口](docs/replication-guide-v3.0/AI交付包/START_HERE.md)
- [构建、发布与恢复契约](docs/replication-guide-v3.0/AI交付包/templates/DEPLOYMENT.md)

80项工具检查通过，全部使用人工夹具、模拟接口和本地脚本；不是原版游戏或真实线上验收。原版画面、字库、完整数据、公式与AI仍需按第31章采集核对；已有本地旧规格只登记为候选。不能从项目书篇幅或工具通过推导完全还原。

从仓库根检查初始台账：

```bash
python docs/replication-guide-v3.0/AI交付包/tools/validate_handoff.py \
  --data docs/replication-guide-v3.0/AI交付包/templates --mode structure
```

初始structure应通过；exact-release与delivered应阻断。v3严格模式要求独立复核的scope摘要、外部当前commit/buildId、真实dist、实际案例报告和正式HTTPS来源。工作流以.example提供，未自动启用。

[v2.1](docs/replication-guide-v2.1)与[v2.0](docs/replication-guide-v2.0)保留供追溯。v3台账schema与原始报告格式已变化，迁移需重新核对真实证据，禁止只改passed状态。
