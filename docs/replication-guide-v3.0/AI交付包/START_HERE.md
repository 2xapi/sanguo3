# 三国志Ⅲ独立网页重写 接手入口 v3.0

本包是项目书、资料台账和辅助工具。当前仓库尚无游戏应用或已验收站点。目标仍是用户指定MD／Genesis繁体中文版的UI与玩法完整还原，网页运行、构建和玩家使用不依赖ROM、MOD或模拟器。

先读上一级指南第19、20、29、31—38章，再读AI执行约束、PROGRESS和templates/DEPLOYMENT.md。核实实际仓库、已有资料和用户改动后从DOC-001开始；不要覆盖其他工作的文件。

## 第一次运行

从本包目录执行；Python要求3.10以上，精确像素检查依赖requirements.txt中的Pillow。

```bash
python tools/validate_handoff.py --data templates --mode structure
python tools/selftest_delivery.py
```

初始structure应通过。初始exact-release和delivered都应退出1：资料、冻结范围、真实游戏、实际产物与线上证据仍未形成。工具自测使用人工小图和JSON，不是原版验证。

已有游戏项目先迁移台账到schemaVersion=2，保留旧记录作为历史，禁止覆盖；将必要工具安装到项目tools。没有应用时先做工程任务及资料采集，不能照搬未实现的npm命令。

## 台账与冻结规格

| 文件 | 当前格式 |
| --- | --- |
| project.json | schemaVersion=2；target/display/inventory/strictTarget/requiredCoverage/candidate |
| scope.json | 独立冻结版本、显示、正式来源、原版来源路径摘要及屏幕/功能/案例/任务完整清单；初始draft |
| references.json | id、kind、evidenceStatus、path、sha256；严格验收只接受可核对原版来源 |
| screens.json | id、referenceIds、caseIds、reportIds、证据/实现/对照状态、hasPlaceholder；每屏覆盖ui/dynamic/interaction |
| features.json | id、kind、referenceIds、caseIds、reportIds及状态；random最终需validationLevel=sequence |
| cases.json | id、category、specificationPath、specificationSha256、referenceIds、reportIds |
| reports.json | id、path、sha256，链接原始运行报告；不再使用旧汇总计数格式 |
| tasks.json | id、phase、required、dependsOn、acceptance、caseIds、status、reportIds、outputPaths、blockerIds |
| unknowns.json | id、status、问题、影响、解除条件；resolved必须有resolution和有效referenceIds |

JSON路径以--artifact-root为根，不能逃出该目录。所有ID均须有效、唯一、能关联；任务依赖不能循环。模板中的空数组表示未采集，不能解释成原版范围为零。

来源核对与原版全量普查完成后独立复核scope，再将其SHA256存入台账之外的CI变量TRUSTED_SCOPE_SHA256。禁止用验收程序自动更新该变量以适配删减范围。范围和预期变更必须记录原因，重新复核。

案例规格包含caseId、category、referenceIds及逐条assertions。非像素断言冻结expected或expectedFrom两者之一；像素断言冻结referencePath、referenceSha256，指向已冻结original-screen。例子见templates/case-spec.example.json；它只示范格式，不能注册成真实案例。

原始报告保存当前commit/buildId、实际命令、runner、exitCode、带摘要的artifacts和results。结果逐案例逐断言登记；非像素断言从actualFrom的已归档JSON路径与JSON Pointer读取实际值，像素断言从actualPath读取实际PNG。工具会重新计算比较，手改passed或计数不能替代执行。

## 发布前和部署后

先在独立环境分配当前候选commit和buildId。CI使用GITHUB_SHA、runId与attempt；门禁依赖外部EXPECTED_CANDIDATE_COMMIT和EXPECTED_CANDIDATE_BUILD_ID核对，不能只相信台账内部一致。

```bash
python tools/validate_handoff.py --data reference/ledgers --artifact-root . \
  --mode exact-release --write-report acceptance/release-gate.json
```

此命令依赖环境中的TRUSTED_SCOPE_SHA256、EXPECTED_CANDIDATE_COMMIT、EXPECTED_CANDIDATE_BUILD_ID；也可用同名对应CLI选项明确传入。仅在实际构建与dist测试后运行，成功后完成RELEASE-EXACT并记录收据。所有bootstrap/implementation任务及除live外全部案例必须完成。

实际部署同一dist并通过test:live后同步OPS-LIVE，再运行：

```bash
python tools/validate_handoff.py --data reference/ledgers --artifact-root . \
  --mode delivered --write-report acceptance/final-gate.json
```

delivered要求包含live在内的全部案例和前置任务完成，允许当前FINAL-DELIVERY尚未done；通过后才做最终汇总。严格模式还会直接检查实际dist、全部文件摘要、候选身份、完整正式HTTPS来源，以及真实PNG差异。

## 顺序和信任边界

CI跨job传递验证先于完整门禁；OPS-PREP只依赖ENG-001。完整游戏和报告完成后才能过exact-release，随后部署、真实网页检查和delivered，最后发布持久可用归档。模板的失败恢复保留新候选的失败状态，恢复报告单独保存。

检查器不能证明来源真伪、普查穷尽、截图确由应用产生或执行器诚实。必须实际进入游戏验证，保留独立原版预期，人工复核来源和冻结范围。旧规格与本地逆向材料先作为候选，不能自动确认为当前基准。原始缺口的采集字段与解除条件见指南第31章。

每轮更新PROGRESS、实际报告、未解差异和下一可执行任务。持续推进已具备前提的工作，不把文档、工具自测或一次绿灯写成整款游戏完成。
