# sanguo3

MD／Genesis 繁体中文版《三國志Ⅲ》独立网页重写项目。目标是按照指定原版证据还原 UI 与玩法，不加载 ROM，不依赖 MOD 或模拟器运行。

目前仓库提供施工指南和 AI 交付包，尚未实现网页游戏。原版截图、操作录像、数据和规则证据仍需采集与核对，不能把文档或工具检查通过视为游戏还原完成。

## v2.1 完整交付与上线执行指南

指南共 38 章、6 个附录。除逐屏像素、菜单状态图和规则取证外，v2.1 补齐启动脚本、早期玩法闭环、干净构建、根／子路径、发布清单、CI／Pages 模板、线上复测与回滚，并修正发布验收依赖自身完成的问题。

- [本次审查与补全结论](docs/replication-guide-v2.1/本次审查与补全.md)
- [Markdown 指南](docs/replication-guide-v2.1/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v2.1.md)
- [Word 指南](docs/replication-guide-v2.1/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v2.1.docx)
- [PDF 指南](docs/replication-guide-v2.1/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v2.1.pdf)
- [完整交付包 ZIP](docs/MD版三国志Ⅲ_完全复刻施工指南_v2.1_完整交付包.zip)

项目书不能代替实际原版事实与运行验证。目前尚无游戏应用或已部署站点；部署文件以 `.example` 提供，未启用。达到完全一致需先补齐原版字库、画面、数据与玩法证据，再实际开发和对照。

## 交给 AI 开发

先阅读[给 AI 的第一句话](docs/replication-guide-v2.1/给AI的第一句话.txt)和[接手入口 START_HERE](docs/replication-guide-v2.1/AI交付包/START_HERE.md)，再核实实际仓库并从 DOC-001 开始。

交付包包含 24 个任务组、JSON／CSV 台账、执行约束、跨会话进度文件、资料检查器、零容差像素比较器与产物静态检查器。每项工作须保留真实证据和运行报告，不允许猜公式、擅改 UI 或通过更新错误基准掩盖差异。

从仓库根目录检查初始台账：

```bash
python docs/replication-guide-v2.1/AI交付包/tools/validate_handoff.py \
  --data docs/replication-guide-v2.1/AI交付包/templates --mode structure
```

初始结构检查应通过；发布前 `--mode exact-release` 与部署后 `--mode delivered` 均应被阻断，因为真实资料、游戏和线上报告尚未完成。每轮报告须匹配当前候选构建的 commit 和 buildId，不能借用旧结果。

工具说明见 [tools/README](docs/replication-guide-v2.1/AI交付包/tools/README.md)，部署契约见 [DEPLOYMENT](docs/replication-guide-v2.1/AI交付包/templates/DEPLOYMENT.md)。人工夹具的工具自测不代表原版游戏验收。此前 [v2.0 文档](docs/replication-guide-v2.0) 保留供查阅。
