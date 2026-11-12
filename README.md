# 三国志Ⅲ独立网页重写项目

按用户提供的MD／Genesis《三國志Ⅲ》样本进行独立网页重写。目标原版实测为简繁字形混排；游戏正式运行、构建和玩家使用不依赖ROM、MOD或模拟器。当前仓库交付项目书与辅助工具，尚未实现独立游戏或发布站点。

## v3.1 原版对齐版

依据用户提供的原版核对样本身份、六个剧本年份、第一剧本刘备开局、平原城和军事菜单；修正旧规格的字形、编成命令、城市字段及战场索引问题。原版文件与游戏画面保存在本地私有目录，不在本仓库分发。部分规则和原生像素基准仍待验证。

- [Markdown项目书](docs/replication-guide-v3.1/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.1.md)
- [Word项目书](docs/replication-guide-v3.1/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.1.docx)
- [PDF项目书](docs/replication-guide-v3.1/MD版三国志Ⅲ_独立网页游戏项目施工开发指南书_v3.1.pdf)
- [完整交付包ZIP](docs/MD版三国志Ⅲ_完全复刻施工指南_v3.1_完整交付包.zip)
- [原版对齐证据与分歧](docs/replication-guide-v3.1/原版证据/原版对齐与分歧.md)
- [接手入口](docs/replication-guide-v3.1/AI交付包/START_HERE.md)
- [上一版审查修复结果](docs/replication-guide-v3.0/本次审查与补全.md)

初始模板仅应通过结构检查；真实发布门禁必须等待原版普查、应用实现和独立案例完成：

```bash
python docs/replication-guide-v3.1/AI交付包/tools/validate_handoff.py \
  --data docs/replication-guide-v3.1/AI交付包/templates --mode structure
```
