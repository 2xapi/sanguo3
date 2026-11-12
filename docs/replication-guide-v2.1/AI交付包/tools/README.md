# 施工辅助工具

这些工具不运行游戏，不更改原版参考，不把工具自测当作游戏验收。

## 台账检查

validate_handoff.py只依赖Python标准库，使用Python 3.10及以上版本。

从AI交付包目录运行：

```bash
python tools/validate_handoff.py --data templates --mode structure
python tools/validate_handoff.py --data templates --mode exact-release
```

退出0表示所选模式的台账检查通过，退出1表示结构错误或验收资料阻断。严格模式初始必须失败。它无法检查人伪造的报告、图片来源真伪或原版范围是否穷尽；必须配合真实游戏测试和来源核查。

## 零容差像素比较

compare_pixels.py依赖Pillow，版本固定在requirements.txt。优先复用已有兼容环境；需要安装时在仓库外的工具虚拟环境中安装，保持项目已有锁文件不变：

```bash
python -m venv /tmp/sanguo3-guide-tools
/tmp/sanguo3-guide-tools/bin/python -m pip install -r tools/requirements.txt
```

执行示例（替换为真实输入；必须使用全新的输出目录）：

```text
python tools/compare_pixels.py --reference <锁定参考.png> --actual <网页实际.png> --out <新报告目录>
```

若使用上方虚拟环境，python替换为/tmp/sanguo3-guide-tools/bin/python。

退出码：0为这两张输入图逐像素一致；1为存在差异；2为输入不符合要求或输出会覆盖已有文件。无阈值、无遮罩、无缩放、无自动色彩校正，不提供更新参考功能。

仅接受单帧8位或可无损展开的PNG模式；调色板图按明确像素颜色展开为RGBA。高位深或多帧输入拒绝，不能静默量化。要求双方尺寸与颜色元数据一致；有差异先完成有记录的归一化，不能用工具偷偷修正。

比较解码后的全部RGBA通道，包括透明像素背后的RGB值。并排、叠加预览使用黑色背景，差异图用红色标出非零差异。报告记录输入哈希、尺寸、差异像素数、最大通道差与右下界不包含在内的差异包围盒。

逐窗口或元素验收时，先按已登记裁切框产生可追溯区域图，再分别比较，不任意裁掉错误。全画面精确比较与区域比较同时保留。动态画面先按明确时刻导出单帧，动态案例另验证时序。

comparison-report.json是底层像素结果，不直接等同reports.json中的完整验收记录。后者还需真实案例计数、退出码、原版referenceIds、场景与时刻证据，以及报告和图像路径；不能仅复制result字段当作完整UI通过。

自测使用人工生成小图，证明工具能发现预设差异；它们不是原版素材、网页游戏截图或还原验收基准。

## v2.1：静态产物与部署后门禁

```bash
python tools/verify_dist.py --dist dist --expected-base /sanguo3/ --github-pages
python tools/validate_handoff.py --data templates --mode delivered
```

verify_dist.py只依赖Python标准库，检查真实dist发布清单、文件摘要、HTML入口资源、基址和非运行目录混入，不运行游戏、不自动调路径、不创建清单。dist缺失时必须失败。详细契约和模板安装路径见templates/DEPLOYMENT.md及指南第34—38章。

delivered新增部署后门禁，初始资料必然阻断。exact-release允许发布验收汇总和部署后任务尚未done，delivered只允许最终汇总尚未done，避免让门禁等待自己的完成记录。修改此阶段划分不能削弱真实实施、测试与线上验证要求。
