const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({channel: process.env.PLAYWRIGHT_CHANNEL || undefined, headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1280, height: 800}});
    const errors = [];
    const played = [];
    let commands = [];
    const acks = [];
    const songs = Array.from({length: 100}, (_, i) => ({mid: `hot${i + 1}`, title: `热歌${i + 1}`, singer: '测试歌手', duration: 180}));
    page.on('pageerror', error => errors.push(error.message));
    await page.route('http://127.0.0.1:8091/**', route => {
      const url = new URL(route.request().url());
      let data = {};
      if (url.pathname === '/api/commands') data = {commands};
      if (url.pathname === '/api/ack') {
        const ack = route.request().postDataJSON();
        acks.push(ack);
        commands = commands.filter(command => command.id !== ack.id);
      }
      if (url.pathname === '/api/status') data = {status: 'logged_in'};
      if (url.pathname === '/api/feed') data = {title: url.searchParams.get('kind') === 'recommend' ? '猜你喜欢' : '热歌榜', songs};
      if (url.pathname === '/api/play') {
        const mid = route.request().postDataJSON().mid;
        played.push(mid);
        data = {...songs.find(song => song.mid === mid), mid, quality: 'MP3', url: `http://example.invalid/${mid}.mp3`};
      }
      if (url.pathname === '/api/lyrics') data = {lines: []};
      if (url.pathname === '/api/playlists') data = {playlists: [{id: 1, dirid: 0, title: '我的测试歌单', count: 100}]};
      if (url.pathname === '/api/songs') data = {songs: songs.slice(0, 30), total: 100};
      if (url.pathname === '/api/search') data = {songs: songs.slice(0, 2), auto_mid: null};
      return route.fulfill({contentType: 'application/json', headers: {'Access-Control-Allow-Origin': '*'}, body: JSON.stringify(data)});
    });
    await page.setContent('<style>body{margin:0;background:#101a30;color:white}.main{display:flex;height:100vh}.side{position:relative;width:65%;height:100%}.right{width:35%}.convo{position:absolute}button{color:inherit}*{box-sizing:border-box}</style><div class="main"><section class="side"><div class="welcome"></div><div class="convo"></div></section><section class="right"><div id="clock"></div><div id="link">待机</div><button id="btnSettings">设置</button></section></div>');
    await page.evaluate(() => {
      Math.random = () => 0;
      HTMLMediaElement.prototype.play = function () { this.dispatchEvent(new Event('play')); return Promise.resolve(); };
      HTMLMediaElement.prototype.pause = function () { this.dispatchEvent(new Event('pause')); };
    });
    await page.addStyleTag({content: fs.readFileSync(path.resolve(__dirname, '../extensions/music/music.css'), 'utf8')});
    await page.addScriptTag({path: path.resolve(__dirname, '../extensions/music/music.js')});
    await page.route('**/extensions/weather/forecast*', route => route.fulfill({status: 503, contentType: 'application/json', body: '{}'}));
    await page.addStyleTag({content: fs.readFileSync(path.resolve(__dirname, '../extensions/weather/weather.css'), 'utf8')});
    await page.addScriptTag({path: path.resolve(__dirname, '../extensions/weather/weather.js')});
    assert.deepEqual(await page.locator('.right').evaluate(element => [...element.children].filter(child => child.id !== 'clock').map(child => child.id || child.className)), ['weather', 'music-entry', 'link', 'btnSettings']);
    assert.deepEqual(await page.locator('.music-home-heading button').allTextContents(), ['播放列表', '收起']);
    assert.equal(await page.locator('.music-entry').evaluate(element => element.getBoundingClientRect().width), 200);
    assert.equal(await page.locator('.weather-card').evaluate(element => element.getBoundingClientRect().height), 52);
    async function run(action) {
      const id = `${action}-${acks.length}`;
      commands.push({id, action, query: '测试', expires: Date.now() / 1000 + 30});
      await assert.doesNotReject(async () => {
        for (let i = 0; i < 100; i++) {
          const ack = acks.find(item => item.id === id);
          if (ack) { assert.equal(ack.ok, true); return; }
          await new Promise(resolve => setTimeout(resolve, 100));
        }
        throw new Error(`Command not acknowledged: ${action}`);
      });
    }
    await run('hot');
    await page.locator('audio').evaluate(audio => {
      Object.defineProperty(audio, 'duration', {configurable: true, value: 272});
      audio.currentTime = 68;
      audio.dispatchEvent(new Event('loadedmetadata'));
    });
    assert.equal(await page.locator('#musicElapsed').innerText(), '1:08');
    assert.equal(await page.locator('#musicDuration').innerText(), '4:32');
    assert.deepEqual(await page.locator('.music-home-controls').evaluate(element => [...element.children].map(child => child.id)), ['musicElapsed', 'musicPrevious', 'musicToggle', 'musicNext', 'musicDuration']);
    const controlRects = await page.locator('.music-home-controls').evaluate(element => [...element.children].map(child => { const rect = child.getBoundingClientRect(); return {x:rect.x, width:rect.width, center:rect.y+rect.height/2}; }));
    assert(controlRects.every(rect => Math.abs(rect.center-controlRects[2].center)<1));
    assert(controlRects[0].x+controlRects[0].width<=controlRects[1].x);
    assert(controlRects[3].x+controlRects[3].width<=controlRects[4].x);
    await page.locator('#musicSeek').evaluate(seek => { seek.value = 125; seek.dispatchEvent(new Event('input')); });
    assert.equal(await page.locator('#musicElapsed').innerText(), '2:05');
    await page.locator('audio').evaluate(audio => {
      Object.defineProperty(audio, 'duration', {configurable: true, value: NaN});
      audio.currentTime = 0;
      audio.dispatchEvent(new Event('emptied'));
    });
    assert.equal(await page.locator('#musicElapsed').innerText(), '0:00');
    assert.equal(await page.locator('#musicDuration').innerText(), '3:00');
    assert.match(await page.locator('.music-entry').getAttribute('aria-label'), /测试歌手.*热歌1/);
    assert.equal(await page.locator('.music-entry-scroll > span').count(), 2);
    assert.equal(await page.locator('.music-entry-scroll').evaluate(element => getComputedStyle(element).animationName), 'music-entry-scroll');
    await page.click('#musicChoose');
    assert.equal(await page.locator('.music-queue-song').count(), 100);
    assert.match(await page.locator('#musicQueue h3').innerText(), /热歌榜.*100 首/);
    assert.match(await page.locator('.music-queue-song.is-current').innerText(), /热歌1 ·/);
    await page.locator('.music-queue-song').nth(5).click();
    await page.waitForFunction(() => !document.querySelector('.music-dialog').open);
    assert.equal(played.at(-1), 'hot6');
    await run('next');
    assert.equal(played.at(-1), 'hot7');
    assert.match(await page.locator('.music-entry').getAttribute('aria-label'), /测试歌手.*热歌7/);
    await run('pause');
    assert.equal(await page.locator('.music-entry').innerText(), '♫ 音乐');
    await run('resume');
    assert.match(await page.locator('.music-entry').getAttribute('aria-label'), /测试歌手.*热歌7/);
    await run('shuffle');
    await page.click('#musicChoose');
    assert.match(await page.locator('#musicQueue h3').innerText(), /随机播放/);
    assert.match(await page.locator('.music-queue-song').first().innerText(), /热歌2 ·/);
    await page.locator('.music-queue-song').last().click();
    await page.waitForFunction(() => !document.querySelector('.music-dialog').open);
    assert.equal(played.at(-1), 'hot1');
    await run('next');
    assert.equal(played.at(-1), 'hot2');
    await run('recommend');
    await page.click('#musicChoose');
    assert.match(await page.locator('#musicQueue h3').innerText(), /猜你喜欢/);
    await page.click('#getLists');
    await page.locator('#musicQueue').waitFor({state: 'hidden'});
    assert.equal(await page.locator('#musicQueue').isVisible(), false);
    await page.click('.music-list');
    await page.locator('#musicSongs .music-song').first().click();
    await page.waitForFunction(() => !document.querySelector('.music-dialog').open);
    await page.click('#musicChoose');
    assert.match(await page.locator('#musicQueue h3').innerText(), /我的测试歌单.*100 首.*第 1 页/);
    assert.equal(await page.locator('.music-queue-song').count(), 30);
    await page.click('#musicClose');
    await run('search');
    assert.equal(played.at(-1), 'hot1');
    assert.match(acks.at(-1).message, /找到多首歌曲，先播放第一首/);
    assert.equal(await page.locator('.music-dialog').evaluate(element => element.open), false);
    await page.click('#musicChoose');
    assert.match(await page.locator('#musicQueue h3').innerText(), /搜索/);
    assert.equal(await page.locator('.music-queue-song').count(), 2);
    await page.locator('.music-queue-song').nth(1).click();
    await page.waitForFunction(() => !document.querySelector('.music-dialog').open);
    assert.equal(played.at(-1), 'hot2');
    await page.click('#musicChoose');
    for (const viewport of [{width: 1280, height: 800}, {width: 800, height: 1280}]) {
      await page.setViewportSize(viewport);
      assert(await page.locator('.music-queue-song').first().isVisible());
      assert.equal(await page.locator('.music-dialog').evaluate(element => element.scrollWidth <= element.clientWidth), true);
    }
    assert.deepEqual(errors, []);
    console.log('PASS button order/dimensions, elapsed/total/seek/unknown-duration, auto-first search with retained candidates, queues/selection/next/wrap, landscape/portrait layout');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
