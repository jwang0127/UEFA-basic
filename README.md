# 2026-27赛季欧冠36队资料站

离线静态中文资料站：首页仅提供36支球队导航，每支球队拥有独立页面，展示联赛阶段赛程、2026年夏窗转会、教练与阵型资料。

## 构建

```powershell
python scripts/collect_data.py
python scripts/build_site.py
python scripts/validate_site.py
```

数据保存在 `data/site_data.json`，页面生成至根目录与 `teams/`。所有页面可直接通过 `file://` 打开，不在运行时请求 JSON。

主要资料源：UEFA 官方、Transfermarkt、FootballDatabase。每条赛程与转会记录的来源 URL 保存在结构化数据中。
