# 本地天气模块

数据来自中国天气网当地实况和当天预报，显示当前温度、实况天气、今日高低温及观测时间。每 30 分钟缓存一次。实况检查城市编号、当天日期和三小时内的观测时间；获取失败时明确显示实况暂不可用，保留当天预报。

点击首页天气卡片打开详情，上排为每 3 小时预报，下排为未来七天。面板提供刷新和关闭按钮。手动刷新最短间隔一分钟。

设备上的独立目录为 `/opt/thinksmart/extensions/weather`。官方客户端更新后执行以下命令重新安装，脚本会读取 `current` 指向的新版本并核对挂接位置。

```sh
sudo python3 /opt/thinksmart/extensions/weather/install.py
systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
```

移除模块的页面和服务挂接后，重启客户端即可恢复官方首页。

```sh
sudo python3 /opt/thinksmart/extensions/weather/install.py --remove
systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
```

安装和移除前的文件保存在 `/home/ubuntu/thinksmart-backups/weather-module-时间`。本模块同时包含天气卡片样式、图标以及隐藏右上角小时间的定制。官方页面结构变化时安装脚本会停止，需要重新检查适配。

## 本地语音天气播报

支持现在的天气怎么样、今天天气如何、现在多少度、播报一下天气等明确的本地问题。识别文字后直接读取首页天气数据并按固定模板生成播报，跳过大模型。检查当天日期与观测时间，失败时播报暂不可用。语音只播报天气、温度及今日高低温，观测时间与来源保留在界面，不念出。第一版仅处理当前和今日的本地天气，其他城市及解释类问题保留原路由。

独立入口在 voice.py。install.py 会同时安装客户端页面、数据路由和网关语音挂接。官方网关更新前先执行 install.py --remove，完成更新后重新执行 install.py，并重启 xiaozhi-hub 和 thinksmart-client。
## 自动定位

按设备网络出口 IP 获取城市，每次天气缓存到期后重新定位。无需手填城市。定位失败时不猜测默认城市；IP 定位可能对应运营商或代理出口所在城市，不保证区县精度。公网 IP 不写入配置、响应或日志。

定位使用腾讯新闻 IP 城市接口，再通过中国天气网城市搜索匹配天气编号。这两个服务会接收到设备网络出口 IP，模块不保存或返回 IP。天气数据仍来自中国天气网。
