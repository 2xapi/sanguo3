# 施工与交付辅助工具 v3.0

Python 3.10以上。validate_handoff的精确PNG检查和compare_pixels依赖requirements.txt里的Pillow；其余工具使用标准库。优先使用现有兼容环境；需要时在独立虚拟环境安装工具依赖，不改游戏锁文件。

```bash
python -m venv /tmp/sanguo3-guide-tools
/tmp/sanguo3-guide-tools/bin/python -m pip install -r tools/requirements.txt
python tools/validate_handoff.py --data templates --mode structure
python tools/selftest_delivery.py
python tools/selftest_release_store.py
python tools/selftest_workflows.py
```

命令从AI交付包目录运行；如使用独立环境，将python替换为该环境可执行路径。初始structure退出0，exact-release和delivered应退出1。

## 冻结范围与实际执行

validate_handoff.py读取project/scope/references/screens/features/cases/reports/tasks/unknowns九份JSON。v3台账不兼容旧reports汇总格式，迁移需保留历史并生成新案例与真实原始报告，不能机械地把旧passed复制过去。

严格模式需要--scope-sha256、--expected-commit、--expected-build-id；也可分别从TRUSTED_SCOPE_SHA256、EXPECTED_CANDIDATE_COMMIT、EXPECTED_CANDIDATE_BUILD_ID读取。scope摘要必须经独立复核并保存在可变台账之外，不能每次验收现场重算后作为可信值。

```bash
python tools/validate_handoff.py --data reference/ledgers --artifact-root . \
  --mode exact-release --write-report acceptance/release-gate.json
python tools/validate_handoff.py --data reference/ledgers --artifact-root . \
  --mode delivered --write-report acceptance/final-gate.json
```

检查器比较冻结清单、案例规格摘要和实际输出。原始报告的artifacts必须带SHA256；非像素实际值用actualFrom={path,pointer}从观察JSON读取，像素实际用actualPath。仅写passed、diffPixels=0或executed>0不能通过。规范例子见templates/case-spec.example.json与runner-report.example.json；示例不是真实游戏验证。

严格模式直接复核真实dist和当前身份；线上报告与live断言同时核对当前候选commit/buildId及完整正式HTTPS来源。报告过旧、引用不存在、任务删减、实际值错误、实际PNG差异、失败或跳过均阻断。

## 精确PNG比较

```text
python tools/compare_pixels.py --reference <锁定原版.png> --actual <实际截图.png> --out <全新目录>
```

退出0为这两张图一致；1为有差异；2为输入不合格或会覆盖输出。无缩放、遮罩、阈值与色彩自动修正。拒绝自比较、多帧、高位深、尺寸或颜色元数据不符。输出包含底层JSON、差异图、叠加图和并排图。截图的来源、状态与时刻仍需独立核查；零差异不自动证明整款游戏还原。

## 完整产物与归档

```bash
python tools/verify_dist.py --dist dist --expected-base /sanguo3/ --github-pages
python tools/release_archive.py pack --dist dist --output release-store/release.tar.gz \
  --expected-base /sanguo3/ --expected-commit FULL_SOURCE_COMMIT --expected-build-id BUILD_ID
python tools/prepare_rollback.py --repo OWNER/REPO --tag verified-BUILD_ID \
  --output rollback-input --expected-base /sanguo3/
```

pack先检查产物、生成完整归档与校验文件，再实际解包核对，拒绝覆盖已有归档。restore拒绝非空目标、恶意路径、重复条目、链接、摘要或版本不符。prepare_rollback需要GitHub CLI与相应仓库读取权限；只有实际CI环境才会访问GitHub。持久Release、存档兼容、线上恢复与首次发布限制详见templates/DEPLOYMENT.md。

本包不运行游戏，也不证明原版来源真实性、普查穷尽或执行器诚实。所有自测是人工夹具；工作流验证是静态检查，不能写成游戏已开发或站点已部署。

额外模板自测优先使用requirements-test.txt中的PyYAML；macOS无该模块时可回退到系统Ruby/Psych进行静态解析。生产验收工具无需YAML库。原始执行日志与回归图片的来源仍须实际审核。
