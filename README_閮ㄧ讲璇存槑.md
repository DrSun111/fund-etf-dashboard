# 基金ETF专业分析看板 PWA 外壳包

这个外壳包用于解决 Streamlit 默认 manifest 和图标无法自定义的问题。部署后，再把新的 GitHub Pages 网址放进 PWABuilder，就可以生成带自定义图标的 Android 安装包。

## 文件说明

- `index.html`：手机 App 外壳页面，会嵌入你的 Streamlit 看板。
- `manifest.json`：PWA 配置文件，已配置名称、启动路径、主题色、图标。
- `service-worker.js`：PWA 缓存脚本，仅缓存外壳文件，Streamlit 实时数据仍联网读取。
- `icon-192.png`：192×192 图标。
- `icon-512.png`：512×512 图标。
- `.nojekyll`：让 GitHub Pages 正常发布静态文件。

## GitHub Pages 部署步骤

1. 回到你的 GitHub 仓库 `fund-etf-dashboard`。
2. 点击 `Add file → Upload files`。
3. 上传本压缩包内的全部文件。
4. 点击 `Commit changes`。
5. 进入仓库 `Settings → Pages`。
6. Source 选择 `Deploy from a branch`。
7. Branch 选择 `main`，目录选择 `/root`。
8. 点击 `Save`。
9. 等待 1 到 3 分钟，得到网址：

   `https://DrSun111.github.io/fund-etf-dashboard/`

## 用 PWABuilder 打包

1. 打开 `https://www.pwabuilder.com/`。
2. 输入 GitHub Pages 新网址，例如：

   `https://DrSun111.github.io/fund-etf-dashboard/`

3. 点击 Start。
4. 检测通过后，进入 Platform / Android。
5. 下载 Test Package 或 Package For Stores。

## 注意

如果 GitHub Pages 网址打开后能看到顶部深色标题栏和你的 Streamlit 看板，说明外壳部署成功。
如果 Streamlit 看板不能嵌入，会出现“进入看板”按钮，点击后仍能打开原看板。
