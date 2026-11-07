# ThinkSmart View 首页扩展

为半格的 ThinkSmart View Ubuntu 镜像增加国内天气、QQ 音乐和本地语音指令。

已在 Lenovo ThinkSmart View CD-18781Y、Ubuntu 24.04 ARM64、半格客户端 0.1.3 上验证。模块代码保存在 `/opt/thinksmart/extensions`，安装脚本将少量入口挂接到客户端及网关，适用于已有的半格系统。

## 当前功能

- 国内天气显示。中国天气网当地实况、今日高低温、每三小时预报及七天预报。
- 本地天气播报。“现在的天气怎么样”“现在多少度”直接读取天气数据，按固定模板回答，跳过大模型。
- QQ 音乐扫码。使用自己的 QQ 或微信账号登录，读取歌单、歌曲及账号有权播放的音源。
- 本地语音点歌。“播放周杰伦的晴天”“我想听稻香”“放一首陈奕迅的歌”直接搜索音乐。
- 本地播放控制。打开音乐、暂停、继续、停止、上一首、下一首。
- 首页内嵌播放器。右侧上方 75% 显示播放器，下方 25% 显示对话。点击封面切换同步歌词，图标控制，细线进度条可拖动。停止音乐恢复完整对话区。

音乐播放与天气播报使用本地规则路由。语音合成沿用网关现有配置，因此“跳过大模型”仍可能需要联网进行语音合成。

## 界面预览

预览使用测试曲目、占位封面和示例天气，不包含实际位置信息。

![音乐首页](docs/images/music-preview.png)

![天气详情](docs/images/weather-preview.png)

## 安装

在设备上以 `ubuntu` 用户运行。需要半格客户端、网关及系统原有的 `uv` 工具，安装时需要访问 GitHub 和 Python 包索引。

```bash
git clone https://github.com/gsyylove/thinksmart-view-extensions.git
cd thinksmart-view-extensions
bash install.sh all
```

可以单独安装 `weather` 或 `music`。脚本会备份挂接文件，安装音乐的隔离依赖和服务，再重启相关服务。安装时播放和对话会中断。

```bash
bash install.sh weather
bash install.sh music
```

在首页点击“音乐”，选择 QQ 或微信扫码。登录后点“我的歌单”选歌，或者使用语音点歌。社区接口可能发生变化，部分歌曲可能因账号权限、数字专辑或版权限制无法播放。

天气位置由设备的网络出口 IP 自动识别，无需填写自己的位置。IP 定位可能对应运营商或代理出口所在城市，不保证区县精度。

## 常用语音指令

| 场景 | 示例 |
| --- | --- |
| 天气 | 现在的天气怎么样、今天天气如何、现在多少度 |
| 点歌 | 播放周杰伦的晴天、我想听稻香、放一首陈奕迅的歌 |
| 控制 | 暂停音乐、继续播放、下一首、上一首、停止音乐 |

明确匹配歌名和歌手时自动播放。版本不明确时在屏幕显示候选，点选后继续播放。搜索队列最多保存本次 20 条结果，歌单队列按页取歌。第一版不会借助大模型纠正语音识别错字。

## 更新、恢复与移除

官方客户端或网关更新前，先移除挂接。模块文件与账号数据会保留。

```bash
bash uninstall.sh all
# 此时执行半格官方更新
bash install.sh all
```

更新本项目后也可重新运行安装命令。备份位于设备的 `/home/ubuntu/thinksmart-backups`。官方页面或语音入口结构变化时，挂接脚本会停止，需要检查兼容性。具体模块说明见 [天气模块](extensions/weather/README.md) 和 [音乐模块](extensions/music/README.md)。

## 数据与权限

音乐服务只监听 `127.0.0.1:8091`。QQ 授权凭据保存在设备的 `~/thinksmart-music/state/credential.json`，目录权限 700、凭据权限 600。服务没有读取凭据的接口，日志不输出授权地址或凭据。天气与音乐的本地语音控制只响应本机配置的设备标识。

设备账号数据、API Key、SSH 私钥、刷机镜像、安卓备份、聊天数据库都应保存在自己的设备上。仓库提供源码与安装脚本。

## 验证范围

实机验证过 QQ 扫码、个人歌单、会员标记歌曲播放链接及完整音频时长、封面、同步歌词、本地指令路由及控制确认。浏览器验证过 3:1 分区、封面歌词切换、暂停继续、停止恢复、细线拖动与搜索候选。现场唤醒及识别准确率取决于麦克风环境和原有 ASR 配置。

## 上游与许可

- [半格 Ubuntu 镜像](https://github.com/justhalfbit/thinksmart-ubuntu-image)
- [半格语音客户端](https://github.com/justhalfbit/xiaozhi-thinksmart-client)
- [半格小智网关](https://github.com/justhalfbit/xiaozhi-hub-server)
- [QQMusicApi Python SDK](https://github.com/L-1124/QQMusicApi)，固定提交 `7413b56183317381c3caf29bfbba855ca642135f`。
- [jsososo/QQMusicApi](https://github.com/jsososo/QQMusicApi)，早期接口参考。
- [中国天气网](https://www.weather.com.cn/)，天气数据来源。

项目采用 GPL-3.0，见 [LICENSE](LICENSE)。第三方组件和数据遵循各自许可、账号权益和服务条款，见 [THIRD_PARTY.md](THIRD_PARTY.md)。

定位优先读取 IP138 首页使用的公开本机 IP 页面，按省、市、区县匹配中国天气网天气编号。区县匹配失败时退回 IP138 所在城市；IP138 获取失败时使用腾讯新闻城市定位。IP138 无需 Token，公开页面结构变化可能影响解析；2026 年入口为 `https://2026.ip138.com/`，跨年或页面改版后可能需要更新。定位服务与中国天气网会接收到设备网络出口 IP，模块不保存或返回 IP。天气数据仍来自中国天气网。
