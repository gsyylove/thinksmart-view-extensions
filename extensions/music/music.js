(() => {
  const right = document.querySelector('.right');
  if (!right) return;
  const base = 'http://127.0.0.1:8091';
  const entry = document.createElement('button');
  entry.className = 'music-entry';
  entry.textContent = '♫ 音乐';
  right.insertBefore(entry, right.firstChild);
  const panel = document.createElement('dialog');
  panel.className = 'music-dialog';
  panel.setAttribute('aria-label', 'QQ 音乐账号验证');
  panel.innerHTML = '<header><b>QQ 音乐</b><button id="musicClose">返回小麦</button></header><main><div class="music-actions"><button id="qqLogin">QQ 扫码</button><button id="wxLogin">微信扫码</button><button id="getLists">我的歌单</button></div><p id="musicStatus">正在检查登录状态</p><img id="musicQr" alt="登录二维码" hidden><div class="music-player"><b id="musicTrack">尚未播放</b><audio id="musicAudio" preload="metadata"></audio><input id="musicSeek" class="music-seek" type="range" min="0" max="100" step="0.1" value="0" disabled aria-label="播放进度"></div><div id="musicLists"></div><div id="musicSongs"></div><div class="music-actions"><button id="musicPrevPage" hidden>上一页</button><button id="musicNextPage" hidden>下一页</button></div></main>';
  document.body.appendChild(panel);
  const status = panel.querySelector('#musicStatus');
  const qr = panel.querySelector('#musicQr');
  let busy = false;
  let loadingLists = false;
  let loggedIn = false;
  let playlist = null;
  let page = 1;
  let loadingSongs = false;
  let playRequest = 0;
  const audio = panel.querySelector('#musicAudio');
  const track = panel.querySelector('#musicTrack');
  const previous = panel.querySelector('#musicPrevPage');
  const next = panel.querySelector('#musicNextPage');
  const home = document.createElement('section');
  home.className = 'music-home';
  home.innerHTML = '<div class="music-home-heading"><span>QQ 音乐</span><button id="musicToChat">收起</button><button id="musicChoose">选歌</button></div><button class="music-art-toggle" aria-label="切换到歌词" aria-pressed="false"><div class="music-cover"><span aria-hidden="true">♫</span><img alt="专辑封面" hidden></div><div class="music-lyrics" aria-label="当前歌词"></div></button><div class="music-meta"><p id="musicArtist"></p><div class="music-player-slot"></div></div><div class="music-home-controls"><button id="musicPrevious" aria-label="上一首" title="上一首"></button><button id="musicToggle" aria-label="播放" title="播放"></button><button id="musicNext" aria-label="下一首" title="下一首"></button></div>';
  const side = document.querySelector('.main > .side');
  if (side) side.appendChild(home);
  home.querySelector('.music-player-slot').appendChild(panel.querySelector('.music-player'));
  const cover = home.querySelector('.music-cover img');
  const lyricBox = home.querySelector('.music-lyrics');
  const artToggle = home.querySelector('.music-art-toggle');
  artToggle.addEventListener('click', () => {
    const showLyrics = home.classList.toggle('show-lyrics');
    artToggle.setAttribute('aria-pressed', String(showLyrics));
    artToggle.setAttribute('aria-label', showLyrics ? '切换到封面' : '切换到歌词');
  });
  const toggle = home.querySelector('#musicToggle');
  const svgIcon = path => `<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">${path}</svg>`;
  const playIcon = svgIcon('<path d="M8 4.8v14.4a.8.8 0 0 0 1.2.7l11-7.2a.8.8 0 0 0 0-1.4l-11-7.2a.8.8 0 0 0-1.2.7z"/>');
  const pauseIcon = svgIcon('<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>');
  home.querySelector('#musicPrevious').innerHTML = svgIcon('<rect x="4" y="4" width="3" height="16" rx="1"/><path d="M19 4 8 12l11 8z"/>');
  home.querySelector('#musicNext').innerHTML = svgIcon('<rect x="17" y="4" width="3" height="16" rx="1"/><path d="m5 4 11 8-11 8z"/>');
  toggle.innerHTML = playIcon;
  const seek = home.querySelector('#musicSeek');
  let draggingSeek = false;
  function updateSeek() {
    const duration = audio.duration;
    const usable = Number.isFinite(duration) && duration > 0;
    seek.disabled = !usable;
    if (!usable) {
      seek.style.setProperty('--progress', '0%');
      return;
    }
    seek.max = duration;
    if (!draggingSeek) seek.value = audio.currentTime;
    seek.style.setProperty('--progress', `${Math.min(100, Number(seek.value) / duration * 100)}%`);
    const clock = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
    seek.setAttribute('aria-valuetext', `${clock(Number(seek.value))} / ${clock(duration)}`);
  }
  seek.addEventListener('pointerdown', () => {draggingSeek = true;});
  seek.addEventListener('pointerup', () => {draggingSeek = false; updateSeek();});
  seek.addEventListener('pointercancel', () => {draggingSeek = false; updateSeek();});
  seek.addEventListener('change', () => {draggingSeek = false;});
  seek.addEventListener('input', () => {
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      audio.currentTime = Number(seek.value);
      updateSeek();
    }
  });
  for (const name of ['timeupdate', 'durationchange', 'loadedmetadata', 'emptied']) audio.addEventListener(name, updateSeek);
  let lyricLines = [];
  let lyricIndex = -2;
  let queue = [];
  let queueIndex = -1;
  let queuePage = 1;
  let queueTotal = 0;
  let queuePlaylist = null;
  let queueSource = 'playlist';
  let handlingCommand = false;
  const commandResults = new Map();
  cover.addEventListener('error', () => {cover.hidden = true;});
  home.querySelector('#musicToChat').addEventListener('click', () => document.body.classList.remove('music-mode'));
  home.querySelector('#musicChoose').addEventListener('click', () => {if (!panel.open) panel.showModal();});
  home.querySelector('#musicPrevious').addEventListener('click', () => stepMusic(-1).catch(error => {track.textContent = error.message;}));
  home.querySelector('#musicNext').addEventListener('click', () => stepMusic(1).catch(error => {track.textContent = error.message;}));
  toggle.addEventListener('click', () => {
    if (audio.paused) audio.play().catch(() => {track.textContent = '播放失败，请重新选歌';});
    else audio.pause();
  });
  audio.addEventListener('play', () => {
    toggle.innerHTML = pauseIcon;
    toggle.setAttribute('aria-label', '暂停');
    toggle.title = '暂停';
    entry.textContent = '♫ 正在播放';
  });
  audio.addEventListener('pause', () => {
    toggle.innerHTML = playIcon;
    toggle.setAttribute('aria-label', '播放');
    toggle.title = '播放';
    entry.textContent = '♫ 音乐';
  });
  function updateLyrics() {
    if (!lyricLines.length) return;
    let index = lyricLines.findIndex(item => item.time > audio.currentTime);
    index = index === -1 ? lyricLines.length - 1 : index - 1;
    if (index === lyricIndex) return;
    lyricIndex = index;
    lyricBox.replaceChildren();
    for (let offset = -2; offset <= 2; offset++) {
      const row = document.createElement('p');
      row.className = offset === 0 ? 'active' : '';
      row.textContent = lyricLines[index + offset]?.text || '　';
      lyricBox.appendChild(row);
    }
  }
  audio.addEventListener('timeupdate', updateLyrics);
  audio.addEventListener('seeked', updateLyrics);
  async function call(path, options) {
    const response = await fetch(base + path, {...options, signal: AbortSignal.timeout(35000)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || '服务暂不可用');
    return data;
  }
  async function login(kind) {
    if (busy) return;
    busy = true;
    qr.hidden = true;
    status.textContent = '正在获取二维码，请稍候';
    try {
      await call('/api/qr', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({kind})});
      qr.src = `${base}/api/qr.png?t=${Date.now()}`;
      qr.hidden = false;
      status.textContent = kind === 'qq' ? '请用手机QQ扫码并确认' : '请用微信扫码并确认';
    } catch (error) { status.textContent = error.message; }
    finally { busy = false; }
  }
  async function poll() {
    if (!panel.open || busy) return;
    try {
      if (loggedIn) return;
      const data = await call('/api/status');
      if (data.status === 'logged_in') {
        loggedIn = true;
        status.textContent = '已登录，点“我的歌单”开始选歌';
        qr.hidden = true;
      } else if (data.message) status.textContent = data.message;
    } catch (_) { status.textContent = '音乐服务连接失败，请稍后重试'; }
  }
  entry.addEventListener('click', () => {
    if (audio.getAttribute('src')) document.body.classList.add('music-mode');
    else if (!panel.open) panel.showModal();
    poll();
  });
  panel.querySelector('#musicClose').addEventListener('click', () => panel.close());
  panel.querySelector('#qqLogin').addEventListener('click', () => login('qq'));
  panel.querySelector('#wxLogin').addEventListener('click', () => login('wx'));
  async function play(song) {
    const request = ++playRequest;
    status.textContent = '正在获取歌曲播放地址';
    audio.pause();
    try {
      const data = await call('/api/play', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({mid: song.mid})});
      if (request !== playRequest) return;
      track.textContent = `${data.title} · ${data.quality}`;
      audio.src = data.url;
      await audio.play();
      document.body.classList.add('music-mode');
      if (panel.open) panel.close();
      home.querySelector('#musicArtist').textContent = data.singer || '';
      home.classList.remove('show-lyrics');
      artToggle.setAttribute('aria-pressed', 'false');
      artToggle.setAttribute('aria-label', '切换到歌词');
      cover.hidden = !data.cover;
      if (data.cover) cover.src = data.cover;
      lyricLines = [];
      lyricIndex = -2;
      lyricBox.textContent = '正在加载歌词';
      call(`/api/lyrics?mid=${encodeURIComponent(data.mid)}`).then(result => {
        if (request !== playRequest) return;
        lyricLines = result.lines;
        lyricBox.textContent = lyricLines.length ? '' : '暂无同步歌词';
        updateLyrics();
      }).catch(() => {if (request === playRequest) lyricBox.textContent = '歌词暂不可用';});
      status.textContent = '正在播放，可用进度条拖动或暂停';
      return true;
    } catch (error) {
      if (request === playRequest) status.textContent = error.message;
      return false;
    }
  }
  audio.addEventListener('error', () => {status.textContent = '音频加载失败，请重新选歌或检查网络';});
  audio.addEventListener('loadedmetadata', () => {
    track.title = `音频时长 ${Math.round(audio.duration)} 秒`;
  });
  async function loadSongs(targetPage) {
    if (loadingSongs || !playlist) return;
    loadingSongs = true;
    status.textContent = '正在读取歌曲';
    try {
      const data = await call(`/api/songs?id=${playlist.id}&dirid=${playlist.dirid}&page=${targetPage}`);
      page = targetPage;
      const list = panel.querySelector('#musicSongs');
      list.replaceChildren();
      data.songs.forEach((song, index) => {
        const row = document.createElement('button');
        row.className = 'music-song';
        row.textContent = `${song.title} · ${song.singer}  ${Math.floor(song.duration / 60)}:${String(song.duration % 60).padStart(2, '0')}`;
        row.addEventListener('click', () => {
          queueSource = 'playlist';
          queue = data.songs;
          queueIndex = index;
          queuePage = targetPage;
          queuePlaylist = {...playlist};
          queueTotal = data.total;
          play(song);
        });
        list.appendChild(row);
      });
      previous.hidden = page <= 1;
      next.hidden = page * 30 >= data.total;
      status.textContent = `${playlist.title} · 共 ${data.total} 首 · 第 ${page} 页，点歌曲播放`;
    } catch (error) { status.textContent = error.message; }
    finally { loadingSongs = false; }
  }
  previous.addEventListener('click', () => loadSongs(page - 1));
  next.addEventListener('click', () => loadSongs(page + 1));
  async function startPlaylist() {
    const lists = await call('/api/playlists');
    const selected = lists.playlists.find(item => item.count > 0);
    if (!selected) throw new Error('账号里还没有可播放的歌单');
    const data = await call(`/api/songs?id=${selected.id}&dirid=${selected.dirid}&page=1`);
    if (!data.songs.length) throw new Error('歌单里还没有歌曲');
    queuePlaylist = selected;
    queueSource = 'playlist';
    queue = data.songs;
    queuePage = 1;
    queueIndex = 0;
    queueTotal = data.total;
    if (!await play(queue[0])) throw new Error('这首歌曲暂时无法播放，请在音乐页面选择其他歌曲');
    return '开始播放音乐';
  }
  async function startFeed(kind) {
    status.textContent = kind === 'recommend' ? '正在获取猜你喜欢' : '正在获取热歌榜';
    const data = await call(`/api/feed?kind=${kind === 'recommend' ? 'recommend' : 'hot'}`);
    const selected = [...data.songs];
    if (kind === 'shuffle') {
      for (let i = selected.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [selected[i], selected[j]] = [selected[j], selected[i]];
      }
    }
    if (!selected.length) throw new Error('暂时没有获取到歌曲');
    queueSource = 'feed';
    queue = selected;
    queuePlaylist = null;
    queuePage = 1;
    queueTotal = selected.length;
    queueIndex = 0;
    if (!await play(queue[0])) throw new Error('这首歌曲暂时无法播放，请说下一首');
    return kind === 'shuffle' ? '开始随机播放热歌榜' : `开始播放${data.title}`;
  }
  async function resumeMusic() {
    if (!audio.getAttribute('src')) return startFeed('shuffle');
    await audio.play();
    document.body.classList.add('music-mode');
    return '继续播放';
  }
  audio.addEventListener('ended', () => stepMusic(1).catch(error => {track.textContent = error.message;}));
  async function stepMusic(direction) {
    if ((queueSource === 'search' || queueSource === 'feed') && queue.length) {
      queueIndex = (queueIndex + direction + queue.length) % queue.length;
      if (!await play(queue[queueIndex])) throw new Error('这首歌曲暂时无法播放，请换一首');
      return direction > 0 ? '已切换下一首' : '已切换上一首';
    }
    if (!queuePlaylist || !queue.length) return startFeed('shuffle');
    const absolute = ((queuePage - 1) * 30 + queueIndex + direction + queueTotal) % queueTotal;
    const targetPage = Math.floor(absolute / 30) + 1;
    const targetIndex = absolute % 30;
    if (targetPage !== queuePage) {
      const data = await call(`/api/songs?id=${queuePlaylist.id}&dirid=${queuePlaylist.dirid}&page=${targetPage}`);
      queue = data.songs;
      queuePage = targetPage;
      queueTotal = data.total;
    }
    if (!queue[targetIndex]) throw new Error('歌单内容发生变化，请重新选择歌单');
    queueIndex = targetIndex;
    if (!await play(queue[queueIndex])) throw new Error('这首歌曲暂时无法播放，请换一首');
    return direction > 0 ? '已切换下一首' : '已切换上一首';
  }
  async function searchMusic(command) {
    status.textContent = '正在搜索歌曲';
    audio.pause();
    const result = await call('/api/search', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: command.query, title: command.title, singer: command.singer})});
    if (!result.songs.length) throw new Error('没有找到这首歌，请补充歌手或换个歌名');
    const select = async index => {
      queueSource = 'search';
      queue = result.songs;
      queueIndex = index;
      queuePlaylist = null;
      queuePage = 1;
      queueTotal = queue.length;
      if (!await play(queue[index])) throw new Error('这首歌曲暂时无法播放，请选择其他版本');
    };
    const index = result.songs.findIndex(item => item.mid === result.auto_mid);
    if (index >= 0) {
      await select(index);
      return `正在播放${result.songs[index].singer}的${result.songs[index].title}`;
    }
    panel.querySelector('#musicLists').replaceChildren();
    const list = panel.querySelector('#musicSongs');
    list.replaceChildren();
    result.songs.forEach((song, position) => {
      const row = document.createElement('button');
      row.className = 'music-song';
      row.textContent = `${song.title} · ${song.singer}`;
      row.addEventListener('click', () => select(position).catch(error => {status.textContent = error.message;}));
      list.appendChild(row);
    });
    previous.hidden = true;
    next.hidden = true;
    status.textContent = `搜索“${command.query}”找到多个候选，请点选歌曲`;
    if (!panel.open) panel.showModal();
    return '找到多个候选版本，请在屏幕上选择歌曲';
  }
  async function runCommand(action, command) {
    if (action === 'search') return searchMusic(command);
    if (action === 'open') {
      if (audio.getAttribute('src')) document.body.classList.add('music-mode');
      else if (!panel.open) panel.showModal();
      return '音乐已打开';
    }
    if (action === 'pause' || action === 'stop') {
      audio.pause();
      if (action === 'stop') {
        if (audio.getAttribute('src')) audio.currentTime = 0;
        document.body.classList.remove('music-mode');
      }
      return action === 'pause' ? '音乐已暂停' : '音乐已停止';
    }
    if (action === 'play' || action === 'shuffle') return startFeed('shuffle');
    if (action === 'hot' || action === 'recommend') return startFeed(action);
    if (action === 'playlist') return startPlaylist();
    if (action === 'resume') return resumeMusic();
    return stepMusic(action === 'next' ? 1 : -1);
  }
  async function checkCommands() {
    if (handlingCommand) return;
    handlingCommand = true;
    try {
      const data = await call('/api/commands');
      for (const command of data.commands) {
        if (commandResults.has(command.id)) {
          await call('/api/ack', {method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(commandResults.get(command.id))});
          continue;
        }
        let ok = false;
        let message = '指令已过期，请再说一次';
        try {
          if (command.expires * 1000 > Date.now()) {
            message = await runCommand(command.action, command);
            ok = true;
          }
        } catch (error) {message = error.message;}
        const result = {id: command.id, ok, message};
        commandResults.set(command.id, result);
        if (commandResults.size > 32) commandResults.delete(commandResults.keys().next().value);
        await call('/api/ack', {method: 'POST', headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(result)});
      }
    } catch (_) {
      // The service can restart independently; reconnect on the next poll.
    } finally {handlingCommand = false;}
  }
  const voiceState = new MutationObserver(() => {
    audio.volume = document.body.dataset.state && document.body.dataset.state !== 'idle' ? 0.15 : 1;
  });
  voiceState.observe(document.body, {attributes: true, attributeFilter: ['data-state']});
  setInterval(checkCommands, 750);
  checkCommands();
  panel.querySelector('#getLists').addEventListener('click', async () => {
    if (loadingLists) return;
    loadingLists = true;
    status.textContent = '正在读取歌单';
    try {
      const data = await call('/api/playlists');
      const list = panel.querySelector('#musicLists');
      list.replaceChildren();
      data.playlists.forEach(item => {
        const row = document.createElement('button');
        row.className = 'music-list';
        row.textContent = `${item.title} · ${item.count} 首`;
        row.addEventListener('click', () => { if (!loadingSongs) { playlist = item; loadSongs(1); } });
        list.appendChild(row);
      });
      status.textContent = `成功读取 ${data.playlists.length} 个歌单`;
    } catch (error) { status.textContent = error.message; }
    finally { loadingLists = false; }
  });
  setInterval(poll, 2500);
})();
