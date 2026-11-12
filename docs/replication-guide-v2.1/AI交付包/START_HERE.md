# MD版《三國志Ⅲ》完全复刻：AI接手入口

先阅读上一级目录的v2.1施工指南，重点是第19—38章。用户的最终目标是目标版本的UI与玩法完全一致，不允许自行改设计。本包是施工规范、台账和检查工具，不是已经完成的游戏。

## 第一次使用

1. 使用现有游戏仓库；先检查仓库指令、Git状态、README、已有应用和用户改动。不要覆盖已有配置，不额外创建worktree。
2. 阅读本包`AI执行约束.md`及`PROGRESS.md`，核实实际文件，不把进度文字当作已执行证据。
3. 将templates作为台账初始副本保存在项目合适位置，保留其名称；不要覆盖已有同名资料。填写路径和负责人，不填造原版事实。
4. 先运行结构检查。Python命令从本包目录执行：

```bash
python tools/validate_handoff.py --data templates --mode structure
```

5. 按tasks.json依赖选任务。初始DOC-001可执行；完成后REF-001和ENG-001可分别推进。没有原版资料时，不能假装REF-001完成，但可继续满足条件的工程工作。
6. 每个任务先写独立验收预期，再实现和实际运行，保存图、数值、回放和报告；更新台账与PROGRESS后继续下一任务，不逐项请求用户确认。

像素比较工具、固定依赖与命令见tools/README.md。compare_pixels.py生成零容差差异报告，不修改参考图片。

## 严格发布资料检查

```bash
python tools/validate_handoff.py --data templates --mode exact-release
```

初始包此命令应退出1：没有实际原版参考、显示基准、完整范围、已完成游戏或测试报告。这是正确的阻断结果，不是让你把字段手工全改passed。

实际项目中指定真实资料目录与产物根目录，例如：

```text
python <工具路径>/validate_handoff.py --data <台账目录> --artifact-root <仓库根目录> --mode structure
```

文件路径按artifact-root解析，默认artifact-root为台账目录的上一级。检查器只读文件，不修改台账。它不运行游戏、不比较图像、不证明资料真实，也不能证明已登记清单穷尽原版。

## 资料文件的字段约定

templates/记录数组初始可以为空；这表示没有资料，绝不是完整范围为零。

| 文件 | 记录必需字段 |
| --- | --- |
| references.json | id、kind、evidenceStatus；有本地原件再填path和sha256 |
| screens.json | id、referenceIds、caseIds、reportIds、evidenceStatus、implementationStatus、comparisonStatus、hasPlaceholder、dynamicCoverageStatus、pixelMode、diffPixels |
| features.json | id、kind、referenceIds、caseIds、reportIds、evidenceStatus、implementationStatus、comparisonStatus；随机另填validationLevel |
| reports.json | id、category、result、exitCode、executed、failed、skipped、artifactPaths、referenceIds；UI另填diffPixels |
| tasks.json | id、title、status、dependsOn、acceptance、reportIds、outputPaths、blockerIds、required |
| unknowns.json | id、question、affectedScope、status、disposition、referenceIds、exitCriteria |

JSON字段状态使用以下值：

- evidenceStatus：uncollected、collected、pending_verification、confirmed、conflict。
- implementationStatus：not_started、in_progress、implemented。
- comparisonStatus：not_run、failed、blocked、passed。
- task.status：todo、in_progress、verify、blocked、done。
- unknown.status：open、resolved；resolved需要resolution文字和有效referenceIds。
- dynamicCoverageStatus：not_run、failed、blocked、passed、not_applicable；not_applicable需理由。
- report.category：build、ui、dynamic、interaction、rules、data、ai、random、audio、save、compatibility。

原版参考kind使用original-screen、original-video、original-audio、original-rule-observation、original-data、original-manual；工程说明、网页实际、网页回归图片不得伪装成这些类型。手工观察记录也是原始材料，需保留完整前提、结果和来源，不能只写最终公式。

原件path与artifactPaths为artifact-root以内的本地文件路径；不允许跳出根目录。sha256为原件真实摘要。线上来源先记录URL与取得方式，需要验收时保存可复查原件或原始观察记录。不得为满足检查器创建空白截图或虚构日志。

屏幕caseIds关联实际测试系统案例，检查器只确认非空；案例存在、运行与覆盖由真实测试报告负责。reportIds引用reports.json；每份报告artifactPaths至少含一个真实非空报告或截图文件。检查器不把文本日志内容自行当成真实通过。

完整UI逐屏使用pixelMode=exact且diffPixels=0。动态区域若不适用，必须给理由；若适用，必须有dynamic报告。rules、interaction、ui、dynamic、data、ai、random、audio报告须引用已确认原版材料。random最终完整序列声明需validationLevel=sequence，分布相符只可单列阶段结果。

inventory.status只有在原版普查、交叉核查和来源完整后才设confirmed。更新范围修订号并记录增删原因，不能删掉未实现功能。所有必做任务与未知项仍分别受检查。

## 原始材料现状

用户已指定MD／Genesis繁体中文版，发行时间说法为1992年8月。上传《原版.md》是二进制ROM，前次仅做文件头观察；不等于已经拥有标题、城市、菜单、字库、玩法与AI参考。本包不附带、运行或提取ROM。

需要自主整理现有合法可用资料，设计采集与规则判别实验；不能访问或无法推断的部分登记具体阻断。资料未齐时继续独立工程工作，不擅自降低完全复刻目标。

## 最小交接

更新PROGRESS，保存实际修改、当前提交、命令退出码、报告、未知项、下一可执行任务与必要进程信息。新AI从这些文件和实际仓库恢复，继续同一目标。

## v2.1：开发到上线新增契约

先阅读上一级的《本次审查与补全.md》和指南第31—38章。任务已扩展为24组，新增早期最小战斗与纵向闭环、干净构建、根／子路径测试、部署准备和真实站点验收。

requiredCoverage新增dist、live；reports.category相应支持这两项。live报告需包含真实baseUrl（HTTPS）、expectedBuildId和testedBuildId，二者相同且来自实际网页运行检查。字段不能替代真实报告。

- structure：资料格式、引用、依赖检查；初始模板应通过。
- exact-release：发布前严格检查，要求全部相关实施任务与除live以外的报告。正在执行的RELEASE-EXACT和部署后的OPS-LIVE、FINAL-DELIVERY不要求先done，避免门禁循环。
- delivered：部署后检查，要求live及RELEASE-EXACT、OPS-LIVE完成；仅不要求正在执行的FINAL-DELIVERY先完成自身。此门禁通过后再登记最终汇总。

```bash
python tools/validate_handoff.py --data templates --mode delivered
```

初始包的exact-release和delivered都应失败，因为游戏和站点尚不存在。不要把实施任务改名为汇总任务来绕过检查。

verify_dist.py检查实际dist清单、文件摘要和HTML入口资源；Pages工作流与Vite配置以.example后缀提供，尚未启用，不能在空应用仓库直接开启并期待上线。工作流的应用脚本、资料渠道和报告传递详见templates/DEPLOYMENT.md。

当前候选构建填入project.candidate的commit、buildId、basePath。verify:release开始前分配本轮身份，所有报告必须写相同commit和buildId，build产物清单使用同一身份；旧报告不能借用。live.baseUrl路径还须匹配候选basePath。
