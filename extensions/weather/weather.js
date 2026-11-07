(() => {
  const right = document.querySelector('.right');
  if (!right) return;
  const card = document.createElement('button');
  card.id = 'weather';
  card.className = 'weather-card';
  card.setAttribute('aria-label', '本地天气，点击展开详情');
  card.innerHTML = '<svg id="weatherIcon" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"></svg><span class="weather-place"><b>本地天气</b><small>中国天气网</small></span><span class="weather-values"><span id="weatherSummary">天气加载中</span><span id="weatherDetail">正在获取预报</span></span>';
  right.insertBefore(card, document.getElementById('clock'));
  const box = document.getElementById('weather');
  const summary = document.getElementById('weatherSummary');
  const detail = document.getElementById('weatherDetail');
  const icon = document.getElementById('weatherIcon');
  const icons = {
    sun: '<circle cx="24" cy="24" r="8"/><path d="M24 3v7m0 28v7M3 24h7m28 0h7M9 9l5 5m20 20 5 5M9 39l5-5m20-20 5-5"/>',
    cloud: '<path d="M12 35a9 9 0 0 1-1-18 13 13 0 0 1 25-1 10 10 0 0 1 0 20H12z"/>',
    rain: '<path d="M10 29a8 8 0 0 1 0-16 12 12 0 0 1 23-1 9 9 0 0 1 4 17H10zM15 36l-3 7m14-7-3 7m14-7-3 7"/>',
    snow: '<path d="M24 4v40M7 14l34 20M7 34l34-20M19 8l5 5 5-5M19 40l5-5 5 5"/>',
    storm: '<path d="M10 27a8 8 0 0 1 0-16 12 12 0 0 1 23-1 9 9 0 0 1 4 17H10zM26 27l-8 11h8l-3 8 12-14h-9l4-5"/>',
    fog: '<path d="M10 23a8 8 0 0 1 0-16 12 12 0 0 1 23-1 9 9 0 0 1 4 17H10zM5 31h38M9 38h30M15 45h18"/>'
  };
  const url = '/extensions/weather/forecast';
  const panel = document.createElement('dialog');
  panel.className = 'weather-dialog';
  panel.setAttribute('aria-labelledby', 'weatherPanelTitle');
  panel.innerHTML = '<header><div><h2 id="weatherPanelTitle">本地天气</h2><small id="weatherPanelStatus">中国天气网</small></div><button id="weatherRefresh">刷新</button><button id="weatherClose" aria-label="关闭天气详情">关闭</button></header><h3>小时预报 <small>每 3 小时</small></h3><div class="weather-row" id="weatherHours"></div><h3>未来一周</h3><div class="weather-row" id="weatherWeek"></div>';
  document.body.appendChild(panel);
  const status = panel.querySelector('#weatherPanelStatus');
  const refreshButton = panel.querySelector('#weatherRefresh');
  panel.querySelector('#weatherClose').addEventListener('click', () => panel.close());
  panel.addEventListener('click', event => { if (event.target === panel) {
    const bounds = panel.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) panel.close();
  }});

  function weatherIcon(weather) {
    let kind = 'cloud';
    if (weather.includes('晴')) kind = 'sun';
    if (weather.includes('雾') || weather.includes('霾')) kind = 'fog';
    if (weather.includes('雨')) kind = 'rain';
    if (weather.includes('雪')) kind = 'snow';
    if (weather.includes('雷')) kind = 'storm';
    return icons[kind];
  }

  function renderRow(id, entries) {
    const row = panel.querySelector(id);
    row.replaceChildren();
    if (!entries.length) {
      row.textContent = '预报暂不可用，请稍后刷新';
      return;
    }
    entries.forEach(entry => {
      const tile = document.createElement('div');
      tile.className = 'weather-tile';
      const title = document.createElement('b');
      title.textContent = entry.label;
      const picture = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      picture.setAttribute('viewBox', '0 0 48 48');
      picture.setAttribute('aria-hidden', 'true');
      picture.innerHTML = weatherIcon(entry.weather);
      const weather = document.createElement('span');
      weather.textContent = entry.weather;
      const temperature = document.createElement('strong');
      temperature.textContent = entry.temperature;
      tile.append(title, picture, weather, temperature);
      row.appendChild(tile);
    });
  }

  function renderDetails(data) {
    status.textContent = `中国天气网 · 预报 ${data.published} 发布`;
    renderRow('#weatherHours', (data.hourly || []).map(item => ({label: item.time, weather: item.weather, temperature: item.temperature})));
    renderRow('#weatherWeek', (data.days || []).map(item => ({label: item.label, weather: item.weather,
      temperature: item.high === null ? `${item.low}°` : `${item.low}～${item.high}°`})));
  }
  let busy = false;
  let last = null;

  async function refresh(force = false) {
    if (busy) return;
    busy = true;
    refreshButton.disabled = true;
    refreshButton.textContent = '更新中';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 35000);
    try {
      const response = await fetch(force ? `${url}?refresh=1` : url, {signal: controller.signal});
      if (!response.ok) throw new Error('Weather unavailable');
      const data = await response.json();
      if (!Number.isFinite(data.low) || !Number.isFinite(data.high) || !data.weather) throw new Error('Invalid weather');
      const hasCurrent = Number.isFinite(data.temperature);
      const weather = hasCurrent ? data.current_weather : data.weather;
      last = hasCurrent ? `${data.temperature}° ${weather}` : weather;
      summary.textContent = last;
      icon.innerHTML = weatherIcon(weather);
      detail.textContent = hasCurrent
        ? `今日 ${data.low}～${data.high}° · ${data.observed.slice(11)} 实况`
        : `${data.low}～${data.high}° · 实况暂不可用`;
      box.title = '中国天气网实况与预报，点击展开';
      const place = data.location?.name || '本地';
      card.querySelector('.weather-place b').textContent = place;
      panel.querySelector('#weatherPanelTitle').textContent = `${place}天气`;
      renderDetails(data);
    } catch (_) {
      summary.textContent = last || '天气暂不可用';
      detail.textContent = last ? '更新失败 · 点击重试' : '请检查网络 · 点击重试';
      status.textContent = '更新失败，已有预报可能过期，请稍后刷新';
    } finally {
      clearTimeout(timeout);
      busy = false;
      refreshButton.disabled = false;
      refreshButton.textContent = '刷新';
    }
  }

  box.addEventListener('click', () => {
    panel.showModal();
    if (!last) refresh();
  });
  refreshButton.addEventListener('click', () => refresh(true));
  refresh();
  setInterval(refresh, 30 * 60 * 1000);
})();
