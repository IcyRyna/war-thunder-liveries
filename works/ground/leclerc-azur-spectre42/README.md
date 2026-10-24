# 勒克莱尔 AZUR · SPECTRE42

深灰与石墨黑的结构迷彩、五档灰色模块对比块、蜂窝侧装甲和克制的青橙色标。LECLERC 采用低矮宽体的运动字标，AZUR 为次级身份；后部保留橙黑工业警示。

车体与炮塔具有磨砂金属光泽，火控壳体以更深的黑色金属形成焦点。玻璃镜片、橡胶和结构细节分别处理；左右侧的上、中间带与狭窄肩部补齐相邻对比块。

**状态：修订中 · 游戏包与源码重建已核验，光学反光仍待游戏视觉确认。**

![当前整车效果](hero-front.png)

## 下载

- [游戏涂装 ZIP](https://github.com/IcyRyna/war-thunder-liveries/releases/download/works/leclerc-azur-spectre42/v29/leclerc-azur-spectre42-game.zip)
- [完整可编辑工程与源码 ZIP](https://github.com/IcyRyna/war-thunder-liveries/releases/download/works/leclerc-azur-spectre42/v29/leclerc-azur-spectre42-source.zip)
- [当前整车与侧面局部预览](https://github.com/IcyRyna/war-thunder-liveries/releases/download/works/leclerc-azur-spectre42/v29/leclerc-azur-spectre42-preview.zip)

游戏包约 65 MB，解压约 382 MB，包含运行所需的配置与纹理。源码为独立 ZIP，包括五份 CMPS、完整原生 UV 模型、分层 PNG 与重建脚本，无需合并分卷。

## 使用

将游戏包内的 `Leclerc_AZUR_SPECTRE42` 文件夹解压至客户端 `UserSkins/`，在 AZUR 用户涂装列表中刷新选择。覆盖旧文件后，切换其他涂装再切回，让客户端重新读取。

源码可以按需提取 CMPS 和模型。验证时可直接读取源码 ZIP，逐张生成临时纹理，避免保留完整解压副本：

```powershell
python -B compact_export.py --source 源码包.zip --verify-only
```

需要导出游戏文件时，将 `--verify-only` 改为 `--out 新目录`。依赖 Python、Pillow、NumPy、SciPy。全部图层解压后也可使用 `rebuild.py --out 新目录`。

当前页面展示本次整车图与局部图；历史七视图保留于对应历史发布。

![侧面对比块](side-blocks.png)

风格参考：[Fying_ 的 SPECTRE42 / WT Live 1192186](https://live.warthunder.com/post/1192186/en/)。当前作品按 AZUR 原生结构重制。参考、游戏资源和自编代码的许可范围见[仓库许可说明](../../../docs/licensing.md)。
