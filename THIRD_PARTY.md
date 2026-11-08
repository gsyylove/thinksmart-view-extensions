# 第三方组件、外部数据与致谢

本项目增加首页扩展和少量挂接脚本，系统、语音能力、音乐曲库、天气和定位数据依托下面的项目与服务。感谢原作者、维护者和贡献者提供的基础工作。

## 系统与语音基础

| 项目 | 引用关系 | 使用方式 |
| --- | --- | --- |
| [rickx/ubuntu-thinksmart](https://github.com/rickx/ubuntu-thinksmart) | ThinkSmart View Ubuntu 适配、驱动和刷机基础，半格镜像的上游 | 间接基础；本仓库不打包其镜像 |
| [justhalfbit/thinksmart-ubuntu-image](https://github.com/justhalfbit/thinksmart-ubuntu-image) | 本扩展运行所需的半格系统镜像 | 用户先单独安装 |
| [justhalfbit/xiaozhi-thinksmart-client](https://github.com/justhalfbit/xiaozhi-thinksmart-client) | 首页、唤醒检测、音频上传与播放、页面状态 | 安装脚本给官方首页和天气数据路由添加挂接 |
| [justhalfbit/xiaozhi-hub-server](https://github.com/justhalfbit/xiaozhi-hub-server) | 语音识别与合成、模型路由、固定语音回复 | 在识别文字后、模型意图分析前挂接本地指令；音乐使用原有回复后结束会话机制 |

这些项目需按各自仓库说明安装、更新并遵循其许可。安装路径与入口结构会影响兼容性。本项目不替换它们的维护职责。

2026-11-08 本项目已验证的组合为半格系统层 0.2.1、客户端 0.1.6、Ubuntu 24.04 ARM64。版本号属于上游组件，不是本扩展的版本；此次在线更新未重新刷写镜像、升级内核或执行 Ubuntu 全量软件包升级。

## 音乐 SDK 与开发依赖

实际音乐依赖为 [L-1124/QQMusicApi](https://github.com/L-1124/QQMusicApi)，安装来源由 [requirements.txt](extensions/music/requirements.txt) 固定在提交 `7413b56183317381c3caf29bfbba855ca642135f`。扫码、个人歌单、搜索、热歌榜、猜你喜欢、播放地址和歌词均通过该 SDK 访问 QQ 音乐。安装时从上游 Git 仓库构建，未在本仓库打包 SDK 源码或账号凭据。上游采用 GPL-3.0 系列许可，具体以该版本的 LICENSE 为准。

[jsososo/QQMusicApi](https://github.com/jsososo/QQMusicApi) 是早期调研参考项目，另有[项目文档](https://jsososo.github.io/QQMusicApi/)。当前实现未安装其 Node 服务，也不依赖公共第三方音乐中转站。感谢其公开接口研究与文档。

[aiohttp](https://github.com/aio-libs/aiohttp) 用于异步 HTTP 服务和请求，见[文档](https://docs.aiohttp.org/en/stable/)及[许可](https://github.com/aio-libs/aiohttp/blob/master/LICENSE.txt)。音乐模块声明 `aiohttp>=3.9,<4`；天气模块沿用客户端和网关已有的 aiohttp。SDK 的间接依赖由安装工具解析，许可信息保留在对应软件包内。

## 运行时外部服务

以下地址是数据来源或实现入口，不是本项目提供的稳定公共 API。公开网页和非正式接口可能变更、限流或不可用。

| 服务 | 链接／当前入口 | 提供内容与使用条件 |
| --- | --- | --- |
| QQ 音乐 | [平台首页](https://y.qq.com/) | 登录、歌曲、歌单、热歌榜、猜你喜欢、音频、封面与歌词；使用自己的账号权益，部分歌曲可能不可播放 |
| QQ 音乐开放平台 | [官方开发文档](https://y.qq.com/music_developer/#/docs/openid#/overview) | 调研参考；当前音乐实现使用社区 SDK，没有接入官方开发者应用接口 |
| 中国天气网 | [首页](https://www.weather.com.cn/)、[城市搜索](https://toy1.weather.com.cn/search) | 城市编号、当天及七天预报、每 3 小时预报、实况；当前实现无需天气 Key |
| IP138 | [首页](https://www.ip138.com/)、[2026 年公开本机 IP 页面](https://2026.ip138.com/) | 优先定位来源；解析首页使用的公开组件，提取省、市及可用区县，不使用付费 API、Token 或离线数据库 |
| IP138 正式 API | [官方接口文档](https://user.ip138.com/ip/doc/) | 仅作方案参考，当前未使用；API 与公开网页是不同接入方式，不应把网页免 Token 理解为 API 免 Token |
| 腾讯新闻定位 | [当前城市接口](https://r.inews.qq.com/api/ip2city) | IP138 读取或匹配失败时的城市后备，不需要在本项目填写 Key |

天气模块用运行时得到的 `city_id` 拼接下列路径，不在源码保存个人城市：

- 当天预报：`https://www.weather.com.cn/weather1d/{city_id}.shtml`
- 当前实况：`https://d1.weather.com.cn/sk_2d/{city_id}.html`
- 七天和小时预报：`https://www.weather.com.cn/weather/{city_id}.shtml`

IP138 的公开组件含年份，跨年或页面改版后可能需要更新入口或解析。区县无法匹配时先退回其所在城市，IP138 不可用时使用腾讯城市信息。IP 定位可能反映运营商或代理出口，不保证定位到真实区县。模块不保存或返回公网 IP；上述服务仍能看到请求设备的出口 IP，定位后的地名会显示在设备首页。

音频、封面、歌词、天气和定位数据由对应平台提供，不因本仓库采用开源许可而转为可自由再分发的内容。账号、会员和平台服务分别遵循各自使用条件。

## 安装时的外部下载

安装音乐模块需要 [GitHub](https://github.com/)、[Python 包索引 PyPI](https://pypi.org/) 及 SDK 间接依赖的下载源，见 [install.sh](install.sh) 和 [requirements.txt](extensions/music/requirements.txt)。安装器使用设备已有的 [uv](https://docs.astral.sh/uv/)，不会安装新的系统镜像。天气单独安装不需要 QQ 账号。

## 许可与归属

本项目源码采用 [GPL-3.0](LICENSE)。上游项目、依赖包和第三方数据遵循各自许可或服务条件。修改或再分发时请保留适用的版权与许可声明，并检查所分发版本的要求。致谢和链接用于说明来源，不表示上游作者或平台参与维护本扩展或为其背书。
