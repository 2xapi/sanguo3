# 上线模板安装条件与路径

本目录文件不是当前已运行配置，也没有实际发布站点。只有游戏工程和真实门禁齐备后，执行OPS-PREP。

## 固定位置

| 模板 | 应用工程中的位置 |
| --- | --- |
| pages.yml.example | .github/workflows/pages.yml |
| vite.config.ts.example | vite.config.ts，按已安装Vite／TypeScript版本验证 |
| tools/validate_handoff.py | 仓库根tools/validate_handoff.py |
| tools/verify_dist.py | 仓库根tools/verify_dist.py |
| tools/compare_pixels.py、requirements.txt | 根tools目录；按实际测试调用 |
| JSON台账 | reference/ledgers，保留文件名 |
| 原件 | reference受控子目录，不在public与dist |
| 真实报告与截图 | acceptance，报告路径与artifact-root一致 |
| release-manifest.example.json | 仅作结构参考；由build生成真实dist/release-manifest.json |

安装前检查已有同名文件并合并，不覆盖用户已有配置。原始待确认模板不能直接作为已确认正式数据。

## 必须先实现的命令

prepare:references、typecheck、test:unit、test:data、test:e2e、test:visual、verify:release、build、test:dist、test:live。所有用例、退出码和产物要求见指南第32章。不能用echo、空测试或无条件成功脚本占位。

prepare:references可以验证仓库已拥有的原件，也可以按已授权渠道取得私有原件；它必须校验来源与摘要，不能重置已经恢复的台账和当前报告。部署job会再次调用，因为它是独立机器。没有访问条件时停止相关门禁，不输出凭据或伪造原件。

两个job各自安装Python工具依赖，环境变量SANGUO_PYTHON指向.venv/bin/python。应用测试编排器须读取它，以参数数组调用图像脚本；建立虚拟环境不会自动让npm子进程改用该Python。仅用标准库的门禁脚本仍可由python3运行。

verify:release必须一次按序执行源码检查、build、test:dist、verify_dist.py，然后执行exact-release门禁；当前dist的真实报告和DIST-001完成记录必须先生成，不能让门禁等待尚未运行的构建。成功后写入真实报告并完成RELEASE-EXACT，所有报告与当前buildId／commit关联，随后把台账、报告和同一dist传给部署job。门禁之后不重新构建，也不以旧提交报告代替当前结果。

test:live只对BASE_URL运行，核对EXPECTED_BUILD_ID、运行中的版本、代表交互、资源和专用测试槽位；成功后保存live报告并完成OPS-LIVE。不要覆盖真实玩家数据，不要从本地结果复制线上passed。

最终delivered在部署job恢复的当前台账上执行。FINAL-DELIVERY是汇总门禁的执行任务，不要求它先done；通过后才归档和登记最终完成。不要在门禁之前把发布后的任务提前勾完。

## 构建与证据传递

GitHub Pages只接收dist。delivery-state是工作流内部的构建附件，用于传递同一个dist、reference/ledgers和acceptance；不要把原始私有参考、秘密或无关文件放进这些公共附件。

另一个job不能看到上一个job的临时文件。模板下载delivery-state，然后重新取得授权原件，保证台账引用的文件和报告仍能核验。最后以online-delivery-report保存实际线上检查结果，失败也保留证据，不能用always上传成功掩盖前面的失败。

实际项目应确认报告和资源在当前仓库可见范围内可以分享；受控材料留在受控渠道，不能为了CI通过而公开。若某证据必须受控，部署job同样需要合法访问它。

## Pages设置

确认本仓库可使用GitHub Pages，并将Settings → Pages → Build and deployment → Source设为GitHub Actions。模板默认/sanguo3/，原样用于本项目站点；自定义域名改为/时同步修改构建环境、静态检查和双路径测试，不只改一处。

Actions引用按完整SHA固定，来源记录见actions-pins.json。这些远程标签与action.yml已核对，云端运行本身没有执行，不能把此模板标成CI或部署已通过。

PR执行验证，不部署。main只有在真实游戏门禁与产物验证都通过后才部署。若流水线红灯，先诊断实际错误，不加continue-on-error或移除原版检查。

## 发布清单与静态检查

清单字段模板故意包含null，不能用于发布。构建程序填实际源码commit、buildId、时间、规则／数据／资源版本、工具版本、basePath和每个文件的真实SHA-256；files不包含清单自身。

从应用根目录运行：

```bash
python tools/verify_dist.py --dist dist --expected-base /sanguo3/ --github-pages
```

该工具只读文件；0为静态契约通过，1为缺失或不一致。检查器不覆盖JS／CSS全部动态引用和浏览器行为，所以还必须执行test:dist与test:live。

--github-pages额外采用保守的单文件100MiB、产物1GiB预算，这些是本模板选择的工程上限；平台当前限制仍以部署时官方设置为准。超过预算应诊断资源体积，不删除哈希检查。

运行verify:release前分配本轮project.candidate.commit和buildId，设置basePath；所有报告及dist清单使用该身份。单位测试先于产物生成仍记录本轮候选身份，但不能复制旧提交报告。工具不验证报告内容真实性，真实命令和图像仍须实际执行。
