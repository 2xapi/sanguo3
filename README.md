# sanguo3

MD／Genesis 繁体中文版《三國志Ⅲ》独立网页重写项目。目标是按照指定原版证据还原 UI 与玩法，不加载 ROM，不依赖 MOD 或模拟器运行。

目前仓库提供施工指南和 AI 交付包，尚未实现网页游戏。原版截图、操作录像、数据和规则证据仍需采集与核对，不能把文档或工具检查通过视为游戏还原完成。

## v2.0 严格复刻施工指南

指南共 30 章、6 个附录，PDF 为 46 页，包含逐屏像素规格、菜单状态图、规则取证、阶段验收、存档恢复与 AI 持续施工规范。

- [Markdown 指南](docs/replication-guide-v2.0/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v2.0.md)
- [Word 指南](docs/replication-guide-v2.0/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v2.0.docx)
- [PDF 指南](docs/replication-guide-v2.0/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v2.0.pdf)
- [完整交付包 ZIP](docs/MD版三国志Ⅲ_完全复刻施工指南_v2.0_完整交付包.zip)

## 交给 AI 开发

先阅读[给 AI 的第一句话](docs/replication-guide-v2.0/给AI的第一句话.txt)和[接手入口 START_HERE](docs/replication-guide-v2.0/AI交付包/START_HERE.md)，再核实实际仓库并从 DOC-001 开始。

交付包包含 17 个任务组、JSON／CSV 台账、执行约束、跨会话进度文件，以及资料检查器和零容差像素比较器。每项工作须保留真实证据和运行报告，不允许猜公式、擅改 UI 或通过更新错误基准掩盖差异。

从仓库根目录检查初始台账：

```bash
python docs/replication-guide-v2.0/AI交付包/tools/validate_handoff.py \
  --data docs/replication-guide-v2.0/AI交付包/templates --mode structure
```

初始结构检查应通过；`--mode exact-release` 应被阻断，因为真实资料与游戏尚未完成。工具使用说明见[tools/README](docs/replication-guide-v2.0/AI交付包/tools/README.md)。
