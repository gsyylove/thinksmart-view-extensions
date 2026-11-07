# QQ 音乐账号验证模块

使用 L-1124/QQMusicApi 的固定源码提交 7413b56183317381c3caf29bfbba855ca642135f，安装器按 requirements.txt 在独立虚拟环境安装该提交。音乐服务只监听 127.0.0.1:8091，由设备首页提供 QQ／微信扫码验证入口。登录后可以读取创建的歌单，分页列出歌曲，以账号权限取得 MP3 320kbps 播放地址。页面支持播放、暂停和进度拖动。已抽查会员标记歌曲的音频时长与曲库一致。已接入明确指令的本地分流，指令不请求大模型。播放时首页右侧时间及提示词区域显示封面、同步歌词、进度和控制按钮，左侧小麦形象与语音按钮保留，歌单选择保留在弹出面板。喊醒及回复期间音乐音量降低。

独立代码目录 `/opt/thinksmart/extensions/music`，依赖环境 `/home/ubuntu/thinksmart-music/venv`。凭据保存在 `/home/ubuntu/thinksmart-music/state/credential.json`，目录权限 700，文件权限 600。不要上传 state 目录。服务不提供凭据读取接口，不记录请求访问日志。

官方更新后重新挂接首页：

```sh
sudo python3 /opt/thinksmart/extensions/music/install.py
sudo systemctl daemon-reload
systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
```

停用音乐模块：

```sh
sudo python3 /opt/thinksmart/extensions/music/install.py --remove
sudo systemctl disable --now thinksmart-music
sudo systemctl daemon-reload
systemctl --user restart xiaozhi-hub
sudo systemctl restart thinksmart-client
```

服务管理 `systemctl status thinksmart-music`。源码来自 https://github.com/L-1124/QQMusicApi 。jsososo/QQMusicApi 作为接口参考，没有部署其公网服务。
## 语音控制

支持打开音乐、播放音乐、暂停音乐、继续播放、停止播放、上一首、下一首、换一首。只匹配明确指令，否定句和普通聊天不拦截。控制仅作用于本机 ThinkSmart 客户端设备标识。

网关挂接点在 `core/handle/receiveAudioHandle.py` 的本地识别文字处理之后、意图分析之前。独立实现位于本模块 `voice.py`。网关更新前先运行 `install.py --remove`，更新完成后重新运行 `install.py`，然后重启网关和客户端。安装脚本会备份原文件并核对挂接位置；官方结构变化会停止安装。

## 主页播放器

点音乐选择歌单、歌曲后，播放器在首页展开，播放器嵌入原时间提示词区域，上方封面和控制、下方同步歌词。回到对话保持播放，点顶部正在播放返回播放视图。支持细线进度条拖动及暂停、继续、上/下一首。暂无同步歌词时明确显示提示。封面、歌词接口失败不阻止音频播放。

手动点选的当前歌单与语音切歌共用队列，跨页取歌，尾部循环到第一首。指令由服务发出并由浏览器确认，避免反馈成功但未执行。封面和歌词由账号正常访问的 QQ 音乐接口提供，模块不保存音乐文件。

## 首页分区布局

播放时，右侧原对话区域上方 75% 显示播放器，下方 25% 保留可滚动对话。默认显示封面，点击封面翻转到同步歌词，再点击歌词返回封面。每首新曲目默认恢复封面。停止音乐恢复完整对话区。

## 本地语音点歌

支持“播放晴天”“播放周杰伦的晴天”“我想听稻香”“放一首陈奕迅的歌”。本地识别文字后直接提取搜索词并调用 QQ 音乐，跳过大模型。明确匹配歌名和歌手时自动播放；歌名有多个歌手版本或没有准确匹配时，弹出候选供点选。新点播沿本次最多 20 条搜索结果切换上/下一首，原歌单队列保留原有分页逻辑。是否可播放由账号授权结果决定。

歌名包含“的”时，可以使用书名号明确标记整首歌名，避免与“歌手的歌名”混淆。第一版不使用大模型纠正识别错字。