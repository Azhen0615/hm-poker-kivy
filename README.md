# H&M 德扑值守 · Kivy 安卓版

这是把原 HTML 版按同一套业务规则重写的 **Python / Kivy** 安卓工程。

## 已对齐的核心规则

- 9 宫格、一屏显示 9 个座位，不滚动
- 最多 4 桌，桌台切换、开桌、改名
- 1 手 ¥48 送 1 张酒水卡；2 手 ¥98 送 2 张
- 活动免费一手（默认名“手气王”，可在设置改）
- 5 张卡换 1 手；10 张卡换 2 手
- 买手单流水、发卡/收卡、按人/按桌/全场统计
- 击杀：赢家收卡、输家淘汰、可恢复存活
- 赠送击杀卡，跨桌，余额校验
- 本桌前三、冠军标记
- 本场明细、历史场次、交班归档
- 撤销上一步、复制明细、JSON 备份导出/导入
- 无声音、无语音、无时间播报

## 构建 APK（GitHub Actions）

这台手机是 ARM proot，**不能直接编译 Kivy APK**。用 GitHub Actions：

1. 登录 GitHub，新建一个仓库。
2. 把本目录所有文件（包括隐藏的 `.github` 文件夹）上传到仓库。
3. 进入 **Actions** → **Build Kivy APK** → **Run workflow**。
4. 等 30–60 分钟，下载运行结果里的 `HM-Poker-Kivy-APK` 压缩包，里面的 `.apk` 可直接安装。

也可以在自己的 x86_64 Linux 电脑上：
```bash
pip install buildozer cython==0.29.36
buildozer android debug
```
