# 测试说明

## Python

使用已具备 aiohttp 的客户端或音乐隔离环境，在仓库根目录运行：

```bash
python -m unittest discover -s tests -v
```

当前 13 项用例覆盖天气定位匹配及降级、音乐指令识别、回复后结束会话和不相关聊天行为。不读取真实凭据，不请求真实账号数据。

## 浏览器

需要 Node.js、可解析的 Playwright 模块及已安装的浏览器。使用已有开发工具环境，或在独立开发目录安装 Playwright 并通过 NODE_PATH 指定模块目录；无需给设备安装 Node.js。

```bash
node tests/music_queue_check.cjs
```

默认使用 Playwright Chromium，需先在开发环境安装对应浏览器（`npx playwright install chromium`）。使用系统 Edge 时设置 `PLAYWRIGHT_CHANNEL=msedge`；PowerShell 写法为 `$env:PLAYWRIGHT_CHANNEL='msedge'`。

用例使用独立页面、模拟歌曲和 HTTP 返回，不接触用户浏览器、音乐账号或设备麦克风。覆盖：

- 顶部顺序和新增控件尺寸，播放器操作顺序。
- 热歌、随机、推荐、个人歌单与搜索队列，点选、高亮、下一首及队尾循环。
- 多匹配自动播放第一首及候选保留，滚动歌手歌名和暂停／恢复。
- 当前时间、总时长、拖动及未知时长，同排控制居中和无重叠。
- 横竖屏测试夹具的列表可见性和无横向溢出。

用例不验证真实音频解码、外部 API 稳定性、现场语音识别或账号版权权限。上游真实页面布局、服务状态和实际接口还需要设备端检查。
