# 构建 发布和恢复契约 v3.1

当前仓库只有指南和工具，以下是游戏实施阶段必须落实的契约；工作流均以.example提供，未启用，也未实际发布网站。

## 先完成CI准备

在项目根安装工具与依赖、锁定Node/npm/Python及应用版本后，将pages.yml.example和rollback.yml.example分别安装到.github/workflows。Pages来源设为GitHub Actions，并设置PRODUCTION_BASE_URL（完整HTTPS主机、端口与带尾斜杠目录）及TRUSTED_SCOPE_SHA256（负责人独立复核后的scope文件摘要）。资料渠道和附件可见性必须符合既定来源范围。

pages工作流可用bootstrap_only=true先试跑：独立发送job创建随机校验物，接收job下载并核对摘要、提交、runId与attempt，生成bootstrap-transport.json。OPS-PREP不再等待DIST-001或完整游戏门禁。每次正式构建都会重新执行传递验证；应用test:bootstrap将本次实际证明转成冻结案例的原始报告，不能拿历史结果冒用新构建。

## 命令顺序

verify:release由应用实现，顺序如下：

1. 从外部环境取得当前commit/buildId；核对干净源码与锁文件，复核本次bootstrap证明。
2. 执行类型、规则、数据、存档、随机、AI、声音、浏览器与视觉测试，保留原始结果；各测试不得为空。
3. 在独立诊断目录验证根基址；使用正式/sanguo3/基址构建指定候选到dist，清单记录该候选身份。
4. 运行test:dist和verify_dist.py。所有正式候选报告必须使用同一身份，不能混用根路径诊断构建的报告。
5. 根据真实结果同步本轮实施任务、cases、reports，保留历史但只索引本次选定执行。
6. 最后运行exact-release并保存acceptance/release-gate.json；成功后完成RELEASE-EXACT。
7. 上传同一个dist与本次台账/报告。部署job恢复后复核exact-release，禁止再次构建。
8. 取得上一可用持久归档并验证存档兼容，保存当前候选草稿归档，再部署。
9. test:live读取实际网页commit/buildId和URL并运行代表流程；成功后evidence:sync -- --phase live完成OPS-LIVE，运行delivered。
10. 全部通过才发布verified-BUILD_ID Release并标记最新。失败则恢复旧dist，独立验证服务恢复，新候选仍退出失败。

门禁使用TRUSTED_SCOPE_SHA256、EXPECTED_CANDIDATE_COMMIT、EXPECTED_CANDIDATE_BUILD_ID。scope的摘要不能从当前台账临时生成后直接作为可信值。candidate的manifestPath必须指向实际dist/release-manifest.json；完整正式来源从冻结scope核对。

## 应用必须实现的线上测试

test:live接受BASE_URL、EXPECTED_BUILD_ID、EXPECTED_COMMIT、LIVE_REPORT_DIR，实际导航网页、核对最终URL与运行时版本、检查资源/控制台、执行代表输入与存读档，并保存实际观察JSON、截图、日志及原始案例报告。不得只请求一个自填version文件。最终URL需在冻结正式来源与路径内，页面运行版本须等于实际清单和当前候选。

LIVE_LEDGER_MODE=isolated时，测试同样严格执行，但只写独立恢复报告，绝不能更新当前候选cases/reports或OPS-LIVE。自动与手动恢复都使用acceptance/rollback和旧版本身份。普通线上检查使用acceptance/live。

test:rollback-compatibility接受ROLLBACK_DIST与当前候选，验证旧产物可读取更新后产生的存档，或验证受支持备份恢复路径。手动回滚时还需要核对当前正式版本。只操作专用测试槽位。无法证明兼容时在生产变更前失败，另行制定迁移或前向修复，不能降级代码后冒险读取玩家档。

## 持久归档和恢复命令

成功版本的完整运行文件保存在GitHub Release中，不依赖会过期的Actions附件。草稿仅表示候选已留存；只有delivered成功才发布为可用版本。prepare_rollback核对已发布tag所指提交、构建ID、归档SHA256和所有运行文件；任何访问或网络错误应失败。

本地人工恢复示例，须替换为真实已发布的标签与版本；输出目录必须不存在：

```bash
gh release download verified-BUILD_ID --repo OWNER/REPO \
  --pattern release.tar.gz --pattern release.tar.gz.sha256 --dir rollback-input
python tools/release_archive.py restore \
  --archive rollback-input/release.tar.gz \
  --checksum-file rollback-input/release.tar.gz.sha256 \
  --output rollback-dist --expected-base /sanguo3/ \
  --expected-commit FULL_SOURCE_COMMIT --expected-build-id BUILD_ID
```

推荐用prepare_rollback.py自动从标签解析并核对源码身份：

```bash
python tools/prepare_rollback.py --repo OWNER/REPO --tag verified-BUILD_ID \
  --output rollback-input --expected-base /sanguo3/
```

工作流恢复时把验证后的rollback-input/dist完整上传Pages，不运行build。手动工作流接受同样精确标签，共用pages-production并发锁；实际网页与代表流程通过后才更新可用标记。

首次发布没有旧产物可恢复。模板会明确记录available=false；失败候选仍失败，不声称回滚成功。正式首发前需完成预发布环境的全流程演练。取消工作流或运行器中断不保证自动恢复分支执行；发生这种情况，使用持久归档触发手动恢复并核对线上状态。

## 资料与平台边界

原始私有参考不进入dist或公开Release。delivery-state只传台账、运行报告与dist，原版原件通过独立受控渠道重新取得；若这些报告也包含私有内容，实施时配置合适可见性，禁止将其公开上传。静态站点没有后端或云存档要求。

Actions按完整commit固定。v3.1核对了这些官方action.yml及输入名，仍未在GitHub实际执行该游戏流水线。生产安装前需完成bootstrap、真实构建、失败恢复和权限演练。

来源：GitHub的[Pages工作流与权限](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)、[deploy-pages输入与产物依赖](https://github.com/actions/deploy-pages)、[创建持久Release与草稿](https://cli.github.com/manual/gh_release_create)、[下载发布产物](https://cli.github.com/manual/gh_release_download)。
