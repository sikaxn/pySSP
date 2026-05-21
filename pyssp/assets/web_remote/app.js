const groups = ['A','B','C','D','E','F','G','H','I','J'];
const wsApiPort = (() => {
  const token = window.location.port ? parseInt(window.location.port, 10) : ((window.location.protocol === 'https:') ? 443 : 80);
  return (Number.isFinite(token) ? token : 5050) + 1;
})();
const transportCookieName = 'pyssp_webremote_transport';
const languageCookieName = 'pyssp_webremote_language';
const strings = {
  en: {
    pageTitle: 'pySSP Web Remote',
    refresh: 'Refresh',
    legacyLink: 'Open Legacy Layout',
    transport: 'Transport',
    language: 'Language',
    status: 'Status',
    ready: 'Ready',
    auto: 'Auto',
    english: 'English',
    chinese: 'Chinese',
    selectAndPlay: 'Select And Play',
    selectHelp: 'Choose a group, then a page, then tap a button to play.',
    groups: 'Groups',
    pages: 'Pages',
    buttons: 'Buttons',
    quickControls: 'Quick Controls',
    pause: 'Pause',
    resume: 'Resume',
    stop: 'Stop',
    forceStop: 'Force Stop',
    next: 'Next',
    rapidFire: 'Rapid Fire',
    jog: 'Jog',
    jogHint: 'Drag to seek the current track.',
    modeToggles: 'Mode Toggles',
    talk: 'Talk',
    vocalRemoved: 'Vocal Removed',
    playlist: 'Playlist',
    shuffle: 'Shuffle',
    multiPlay: 'Multi Play',
    mute: 'Mute',
    playbackMore: 'Playback More',
    fadeIn: 'Fade In',
    fadeOut: 'Fade Out',
    crossfade: 'Crossfade',
    playSelected: 'Play Selected',
    playSelectedPause: 'Play Sel/Pause',
    resetPage: 'Reset Page',
    videoDisplayTitle: 'Video Display',
    videoDisplayFollow: 'Follow Sound Button Display Focus',
    videoDisplayManualSource: 'Manual Source',
    videoDisplaySetOverride: 'Set Source And Disable Follow',
    videoDisplaySetKeepFollow: 'Set Source Keep Follow',
    videoDisplayActiveSource: 'Active Source',
    videoDisplayStatusLabel: 'Video Route',
    lyricAndStage: 'Lyric And Stage',
    lyricCaption: 'Caption View',
    lyricOverhead: 'Overhead View',
    lyricBanner: 'Banner View',
    lyricOverlay: 'vMix Overlay',
    lyricShow: 'Lyric Show',
    lyricBlank: 'Lyric Blank',
    lyricToggle: 'Lyric Toggle',
    lyricWsNote: 'Lyric WebSocket uses the Web Remote port plus 1.',
    navigationLock: 'Navigation And Lock',
    prevGroup: 'Prev Group',
    nextGroup: 'Next Group',
    prevPage: 'Prev Page',
    nextPage: 'Next Page',
    prevButton: 'Prev Button',
    nextButton: 'Next Button',
    lock: 'Lock',
    automationLock: 'Automation Lock',
    unlock: 'Unlock',
    resetAll: 'Reset All',
    alertTitle: 'Stage Alert',
    alertMessage: 'Message',
    alertPlaceholder: 'Type alert text...',
    keepOnScreen: 'Keep On Screen',
    seconds: 'Seconds',
    sendAlert: 'Send Alert',
    clearAlert: 'Clear Alert',
    volumeTitle: 'Volume',
    setVolume: 'Set',
    nowPlaying: 'Now Playing',
    remoteSummary: 'Remote Summary',
    diagnostics: 'Diagnostics',
    aboutTitle: 'About',
    versionLabel: 'Version',
    buildLabel: 'Build',
    aboutText: 'pySSP is open source soundboard software.',
    websiteLink: 'Website',
    latestLink: 'Get the Latest Version',
    aboutLink: 'Find out more about pySSP',
    registerNote: 'pySSP is free software. No registration is required.',
    connectedMode: 'Transport',
    selectedGroup: 'Group',
    selectedPage: 'Page',
    automationOn: 'Automation Lock',
    normalLockOn: 'Screen Lock',
    playingState: 'Playback',
    active: 'Active',
    inactive: 'Off',
    playing: 'Playing',
    idle: 'Idle',
    none: 'None',
    untitled: '(untitled)',
    remaining: 'Remaining',
    pageLabel: 'Page',
    buttonLabel: 'Button',
    stateRefreshed: 'State refreshed',
    ok: 'OK',
    alertRequired: 'Error: alert text required',
    transportHttp: 'HTTP',
    transportWs: 'WebSocket',
    wsErrorPrefix: 'WS Error: ',
    errorPrefix: 'Error: ',
    automationWarning: 'Automation lock is active. pySSP is expected to be controlled remotely. Unlock only for troubleshooting when you are sure.',
    unlockConfirm: 'Automation lock is active. Unlock only for troubleshooting when you are sure pySSP should stop being remotely controlled.'
  },
  zh: {
    pageTitle: 'pySSP 网页遥控',
    refresh: '刷新',
    legacyLink: '打开旧版布局',
    transport: '传输方式',
    language: '语言',
    status: '状态',
    ready: '就绪',
    auto: '自动',
    english: '英文',
    chinese: '中文',
    selectAndPlay: '选择并播放',
    selectHelp: '先选组别，再选页面，然后点按钮播放。',
    groups: '组别',
    pages: '页面',
    buttons: '按钮',
    quickControls: '快速控制',
    pause: '暂停',
    resume: '继续',
    stop: '停止',
    forceStop: '强制停止',
    next: '下一首',
    rapidFire: '快速触发',
    jog: '滑动定位',
    jogHint: '拖动可定位当前曲目。',
    modeToggles: '模式开关',
    talk: '讲话',
    vocalRemoved: '去人声',
    playlist: '播放列表',
    shuffle: '随机',
    multiPlay: '多重播放',
    mute: '静音',
    playbackMore: '更多播放控制',
    fadeIn: '淡入',
    fadeOut: '淡出',
    crossfade: '交叉淡化',
    playSelected: '播放选中',
    playSelectedPause: '选中播放/暂停',
    resetPage: '重置页面',
    videoDisplayTitle: '视频显示',
    videoDisplayFollow: '跟随音效按钮显示焦点',
    videoDisplayManualSource: '手动来源',
    videoDisplaySetOverride: '设置来源并关闭跟随',
    videoDisplaySetKeepFollow: '设置来源并保留跟随',
    videoDisplayActiveSource: '当前输出',
    videoDisplayStatusLabel: '视频路由',
    lyricAndStage: '歌词与舞台',
    lyricCaption: '字幕视图',
    lyricOverhead: '投影视图',
    lyricBanner: '横幅视图',
    lyricOverlay: 'vMix 叠加',
    lyricShow: '显示歌词',
    lyricBlank: '黑屏歌词',
    lyricToggle: '切换歌词',
    lyricWsNote: '歌词 WebSocket 使用网页遥控端口加 1。',
    navigationLock: '导航与锁定',
    prevGroup: '上一组',
    nextGroup: '下一组',
    prevPage: '上一页',
    nextPage: '下一页',
    prevButton: '上一个按钮',
    nextButton: '下一个按钮',
    lock: '锁定',
    automationLock: '自动化锁定',
    unlock: '解锁',
    resetAll: '全部重置',
    alertTitle: '舞台提示',
    alertMessage: '内容',
    alertPlaceholder: '输入提示文字...',
    keepOnScreen: '保持显示',
    seconds: '秒数',
    sendAlert: '发送提示',
    clearAlert: '清除提示',
    volumeTitle: '音量',
    setVolume: '设置',
    nowPlaying: '正在播放',
    remoteSummary: '遥控摘要',
    diagnostics: '诊断信息',
    aboutTitle: '关于',
    versionLabel: '版本',
    buildLabel: '构建',
    aboutText: 'pySSP 是开源音效板软件。',
    websiteLink: '官网',
    latestLink: '获取最新版本',
    aboutLink: '了解更多 pySSP 信息',
    registerNote: 'pySSP 是免费软件，不需要注册。',
    connectedMode: '传输方式',
    selectedGroup: '组别',
    selectedPage: '页面',
    automationOn: '自动化锁定',
    normalLockOn: '屏幕锁定',
    playingState: '播放状态',
    active: '开启',
    inactive: '关闭',
    playing: '播放中',
    idle: '空闲',
    none: '无',
    untitled: '（未命名）',
    remaining: '剩余',
    pageLabel: '页面',
    buttonLabel: '按钮',
    stateRefreshed: '状态已刷新',
    ok: '成功',
    alertRequired: '错误：提示文字不能为空',
    transportHttp: 'HTTP',
    transportWs: 'WebSocket',
    wsErrorPrefix: 'WebSocket 错误：',
    errorPrefix: '错误：',
    automationWarning: '自动化锁定已启用。此时 pySSP 预期由远端控制。只有在明确要停止远端控制时才解锁。',
    unlockConfirm: '自动化锁定已启用。只有在你确认 pySSP 不应再由远端控制时才解锁。'
  }
};

let localePreference = readCookie(languageCookieName);
let locale = resolveLocale(localePreference);
let selectedGroup = 'A';
let selectedPage = 1;
let pageMeta = [];
let lastState = null;
let transportMode = readCookie(transportCookieName) === 'http' ? 'http' : 'ws';
let wsApiSocket = null;
let wsApiConnectPromise = null;
let wsApiRequestCounter = 1;
let jogSliderActive = false;
const wsPendingRequests = new Map();

function detectLocale(){
  const probe = Array.isArray(navigator.languages) && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
  return probe.some((token) => /^zh\b/i.test(String(token || ''))) ? 'zh' : 'en';
}

function resolveLocale(preference){
  return preference === 'zh' || preference === 'en' ? preference : detectLocale();
}

function t(key){
  const pack = strings[locale] || strings.en;
  return pack[key] || strings.en[key] || key;
}

function readCookie(name){
  const parts = String(document.cookie || '').split(';');
  for(const part of parts){
    const trimmed = part.trim();
    if(trimmed.startsWith(name + '=')){
      return decodeURIComponent(trimmed.slice(name.length + 1));
    }
  }
  return '';
}

function writeCookie(name, value){
  document.cookie = `${name}=${encodeURIComponent(String(value || ''))}; path=/; max-age=31536000; samesite=lax`;
}

function applyStaticText(){
  locale = resolveLocale(localePreference);
  document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  document.title = t('pageTitle');
  for(const node of document.querySelectorAll('[data-i18n]')){
    node.textContent = t(node.getAttribute('data-i18n'));
  }
  for(const node of document.querySelectorAll('[data-i18n-placeholder]')){
    node.setAttribute('placeholder', t(node.getAttribute('data-i18n-placeholder')));
  }
  const transportSelect = document.getElementById('transportMode');
  if(transportSelect){
    const options = Array.from(transportSelect.options);
    if(options[0]){ options[0].textContent = t('transportWs'); }
    if(options[1]){ options[1].textContent = t('transportHttp'); }
  }
  const languageSelect = document.getElementById('languageMode');
  if(languageSelect){
    languageSelect.value = localePreference === 'en' || localePreference === 'zh' ? localePreference : 'auto';
  }
}

function setStatus(text){
  const node = document.getElementById('lastStatus');
  if(node){ node.textContent = String(text || ''); }
  renderSummaryBox(lastState);
}

function currentWsUrl(){
  const proto = (window.location.protocol === 'https:') ? 'wss:' : 'ws:';
  return `${proto}//${window.location.hostname}:${wsApiPort}/ws`;
}

function closeWsApi(){
  if(wsApiSocket){
    try{ wsApiSocket.close(); }catch(_err){}
  }
  wsApiSocket = null;
  wsApiConnectPromise = null;
  for(const [, pending] of wsPendingRequests){
    try{ pending.reject(new Error('WebSocket disconnected')); }catch(_err){}
  }
  wsPendingRequests.clear();
}

function ensureWsApiConnected(){
  if(wsApiSocket && wsApiSocket.readyState === WebSocket.OPEN){
    return Promise.resolve(wsApiSocket);
  }
  if(wsApiConnectPromise){
    return wsApiConnectPromise;
  }
  wsApiConnectPromise = new Promise((resolve, reject) => {
    try{
      const ws = new WebSocket(currentWsUrl());
      wsApiSocket = ws;
      const timeout = setTimeout(() => {
        if(ws.readyState !== WebSocket.OPEN){
          try{ ws.close(); }catch(_err){}
          wsApiConnectPromise = null;
          reject(new Error('WebSocket connect timeout'));
        }
      }, 3000);
      ws.onopen = () => {
        clearTimeout(timeout);
        wsApiConnectPromise = null;
        resolve(ws);
      };
      ws.onmessage = (event) => {
        try{
          const message = JSON.parse(String(event.data || '{}'));
          if(!message || typeof message !== 'object'){ return; }
          if(message.type === 'api_response'){
            const id = String(message.id ?? '');
            const pending = wsPendingRequests.get(id);
            if(!pending){ return; }
            wsPendingRequests.delete(id);
            pending.resolve(message.payload || {ok:false,error:{message:'Missing payload'}});
            return;
          }
          if(message.type === 'ws_error'){
            setStatus(t('wsErrorPrefix') + (message.error?.message || 'unknown error'));
          }
        }catch(_err){}
      };
      ws.onerror = () => {
        setStatus(t('wsErrorPrefix') + 'transport error');
      };
      ws.onclose = () => {
        if(wsApiSocket === ws){
          wsApiSocket = null;
        }
        wsApiConnectPromise = null;
        for(const [, pending] of wsPendingRequests){
          try{ pending.reject(new Error('WebSocket disconnected')); }catch(_err){}
        }
        wsPendingRequests.clear();
      };
    }catch(err){
      wsApiConnectPromise = null;
      reject(err);
    }
  });
  return wsApiConnectPromise;
}

async function apiRequest(path, method='GET', body=null){
  if(transportMode === 'ws'){
    const ws = await ensureWsApiConnected();
    const id = String(wsApiRequestCounter++);
    const message = {
      type: 'api_request',
      id,
      path: String(path || ''),
      method: String(method || 'GET').toUpperCase()
    };
    if(body && typeof body === 'object'){
      message.body = body;
    }
    return await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        wsPendingRequests.delete(id);
        reject(new Error('WS request timeout'));
      }, 5000);
      wsPendingRequests.set(id, {
        resolve: (payload) => { clearTimeout(timer); resolve(payload); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      });
      try{
        ws.send(JSON.stringify(message));
      }catch(err){
        wsPendingRequests.delete(id);
        clearTimeout(timer);
        reject(err);
      }
    });
  }
  const init = {method: String(method || 'GET').toUpperCase()};
  if(body && typeof body === 'object'){
    init.headers = {'Content-Type':'application/json'};
    init.body = JSON.stringify(body);
  }
  const res = await fetch(path, init);
  return await res.json();
}

function escapeHtml(value){
  return String(value ?? '').replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}

function videoRouteLabel(value){
  const token = String(value || 'blank').trim().toLowerCase();
  switch(token){
    case 'video': return 'Video';
    case 'image': return 'Image';
    case 'lyric_display': return 'Lyric Display';
    case 'stage_display': return 'Stage Display';
    case 'metronome_display': return 'Metronome Display';
    case 'backdrop': return 'Backdrop';
    case 'blank': return 'Blank';
    case 'white_screen': return 'White Screen';
    case 'colour_bars': return 'Colour Bars';
    default: return token || 'Blank';
  }
}

function idealTextColor(hex){
  if(!hex || !/^#[0-9a-fA-F]{6}$/.test(hex)){ return '#111'; }
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  const yiq = ((r*299)+(g*587)+(b*114))/1000;
  return yiq >= 140 ? '#111' : '#fff';
}

function renderGroups(){
  const root = document.getElementById('groups');
  if(!root){ return; }
  root.innerHTML = groups.map((group) =>
    `<button class="${group===selectedGroup?'active':''}" type="button" data-group="${group}">${group}</button>`
  ).join('');
}

function renderPages(){
  const root = document.getElementById('pages');
  if(!root){ return; }
  const source = pageMeta.length ? pageMeta : Array.from({length:18}, (_, index) => ({page:index+1,page_name:'',page_color:null}));
  root.innerHTML = source.map((info) => {
    const page = Number(info.page || 0);
    const color = info.page_color || '';
    const style = color ? `background:${color};color:${idealTextColor(color)};` : '';
    const pageName = (info.page_name || '').trim();
    const label = pageName ? `${page}<br>${escapeHtml(pageName)}` : `${page}`;
    return `<button class="${page===selectedPage?'active':''}" type="button" data-page="${page}" style="${style}" title="${escapeHtml(pageName || (t('pageLabel') + ' ' + page))}">${label}</button>`;
  }).join('');
}

function buttonClass(button){
  if(button.marker) return 'marker';
  if(button.locked) return 'locked';
  if(button.missing) return 'missing';
  if(button.is_playing) return 'playing';
  if(button.played) return 'played';
  if(button.assigned) return 'assigned';
  return 'empty';
}

function renderButtons(buttons){
  const root = document.getElementById('buttons');
  if(!root){ return; }
  root.innerHTML = (buttons || []).map((button) => {
    let title = '';
    if(button.marker){
      title = (button.marker_text && button.marker_text.trim()) ? button.marker_text : (button.title || '').trim();
    }else{
      title = (button.title && button.title.trim()) ? button.title : (t('buttonLabel') + ' ' + button.button);
    }
    return `<button class="${buttonClass(button)}" type="button" data-button-id="${escapeHtml(button.button_id)}">${button.button}<br>${escapeHtml(title)}</button>`;
  }).join('');
}

function renderTracks(tracks){
  const root = document.getElementById('tracksView');
  if(!root){ return; }
  if(!tracks || tracks.length === 0){
    root.innerHTML = `<div class="track">${t('none')}</div>`;
    return;
  }
  root.innerHTML = tracks.map((track) =>
    `<div class="track"><strong>${escapeHtml(track.button_id)}</strong> - ${escapeHtml(track.title || t('untitled'))}<br>${t('remaining')}: ${escapeHtml(track.remaining)} (${escapeHtml(track.remaining_ms)} ms)</div>`
  ).join('');
}

function renderSummaryBox(state){
  const root = document.getElementById('summaryBox');
  if(!root){ return; }
  const rows = [
    [t('transport'), transportMode === 'ws' ? t('transportWs') : t('transportHttp')],
    [t('selectedGroup'), state?.current_group || selectedGroup],
    [t('selectedPage'), state?.current_page || selectedPage],
    [t('playingState'), state?.is_playing ? t('playing') : t('idle')],
    [t('videoDisplayStatusLabel'), state?.video_display_follow_sound_button_focus ? `${t('videoDisplayFollow')} ON` : `${t('videoDisplayFollow')} OFF`],
    [t('videoDisplayActiveSource'), videoRouteLabel(state?.video_display_active_source || 'blank')],
    [t('normalLockOn'), state?.screen_locked ? t('active') : t('inactive')],
    [t('automationOn'), state?.automation_locked ? t('active') : t('inactive')],
    [t('status'), document.getElementById('lastStatus')?.textContent || t('ready')],
  ];
  root.innerHTML = rows.map(([label, value]) =>
    `<div class="summary-row-item"><span class="summary-row-label">${escapeHtml(label)}</span><span class="summary-row-value">${escapeHtml(value)}</span></div>`
  ).join('');
}

function renderAboutMeta(state){
  const root = document.getElementById('aboutMeta');
  if(!root){ return; }
  const versionValue = String(state?.app_version || '').trim() || '-';
  const buildValue = String(state?.app_build || '').trim() || '-';
  root.innerHTML = [
    [t('versionLabel'), versionValue],
    [t('buildLabel'), buildValue],
  ].map(([label, value]) =>
    `<div class="about-meta-item"><span class="about-meta-label">${escapeHtml(label)}</span><span class="about-meta-value">${escapeHtml(value)}</span></div>`
  ).join('');
}

function applyToggleStates(state){
  const payload = state || {};
  for(const button of document.querySelectorAll('[data-state-key]')){
    const key = String(button.getAttribute('data-state-key') || '').trim();
    let isOn = false;
    if(key === 'muted_like'){
      isOn = false;
    }else if(key === 'lyric_display_visible'){
      isOn = String(payload.lyric_display || '').toLowerCase() === 'show';
    }else{
      isOn = !!payload[key];
    }
    button.classList.toggle('is-on', isOn);
  }
}

function syncVideoDisplayControls(state){
  const payload = state || {};
  const followCheckbox = document.getElementById('videoFollowSoundButtonFocus');
  const sourceSelect = document.getElementById('videoDisplayManualSource');
  const statusNode = document.getElementById('videoDisplayStatus');
  const followEnabled = !!payload.video_display_follow_sound_button_focus;
  if(followCheckbox){
    followCheckbox.checked = followEnabled;
  }
  if(sourceSelect){
    const manualSource = String(payload.video_display_manual_source || 'blank').trim().toLowerCase();
    if(Array.from(sourceSelect.options).some((option) => option.value === manualSource)){
      sourceSelect.value = manualSource;
    }
  }
  if(statusNode){
    const active = videoRouteLabel(payload.video_display_active_source || 'blank');
    const manual = videoRouteLabel(payload.video_display_manual_source || 'blank');
    const follow = followEnabled ? t('active') : t('inactive');
    statusNode.textContent = `${t('videoDisplayFollow')}: ${follow} | ${t('videoDisplayManualSource')}: ${manual} | ${t('videoDisplayActiveSource')}: ${active}`;
  }
}

async function setVideoDisplaySourceFromCurrentControls(){
  const sourceSelect = document.getElementById('videoDisplayManualSource');
  const followCheckbox = document.getElementById('videoFollowSoundButtonFocus');
  const source = String(sourceSelect?.value || 'blank').trim().toLowerCase();
  const keepFollow = !!followCheckbox?.checked;
  const path = keepFollow
    ? `/api/video-display/source/${encodeURIComponent(source)}/keepfollow`
    : `/api/video-display/source/${encodeURIComponent(source)}`;
  await callApi(path);
}

async function setVideoDisplayFollow(enabled){
  await callApi(`/api/video-display/follow/${enabled ? 'enable' : 'disable'}`);
}

async function callApi(path){
  try{
    const data = await apiRequest(path, 'POST');
    if(!data.ok){
      setStatus(t('errorPrefix') + (data.error?.message || 'request failed'));
    }else{
      setStatus(t('ok'));
    }
    await refreshAll(false);
    return data;
  }catch(err){
    setStatus(t('errorPrefix') + err);
  }
}

async function sendAlert(){
  const textEl = document.getElementById('alertText');
  const keepEl = document.getElementById('alertKeep');
  const secondsEl = document.getElementById('alertSeconds');
  const text = (textEl?.value || '').trim();
  if(!text){
    setStatus(t('alertRequired'));
    return;
  }
  const keep = !!(keepEl && keepEl.checked);
  const seconds = Math.max(1, Math.min(600, parseInt(secondsEl?.value || '10', 10) || 10));
  try{
    const data = await apiRequest('/api/alert', 'POST', {text, keep, seconds});
    if(!data.ok){
      setStatus(t('errorPrefix') + (data.error?.message || 'request failed'));
    }else{
      setStatus(t('ok'));
    }
    await refreshAll(false);
    return data;
  }catch(err){
    setStatus(t('errorPrefix') + err);
  }
}

async function clearAlert(){
  await callApi('/api/alert/clear');
}

async function setVolumeFromInput(){
  const input = document.getElementById('volumeLevel');
  const slider = document.getElementById('volumeSlider');
  const raw = parseInt(input?.value || slider?.value || '0', 10);
  const level = Math.max(0, Math.min(100, Number.isFinite(raw) ? raw : 0));
  if(input){ input.value = String(level); }
  if(slider){ slider.value = String(level); }
  await callApi('/api/volume/' + level);
}

async function setVolumeFromSlider(){
  const slider = document.getElementById('volumeSlider');
  const input = document.getElementById('volumeLevel');
  const raw = parseInt(slider?.value || input?.value || '0', 10);
  const level = Math.max(0, Math.min(100, Number.isFinite(raw) ? raw : 0));
  if(slider){ slider.value = String(level); }
  if(input){ input.value = String(level); }
  await callApi('/api/volume/' + level);
}

function formatSeekTime(ms){
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if(hours > 0){
    return `${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`;
  }
  return `${String(minutes).padStart(2,'0')}:${String(seconds).padStart(2,'0')}`;
}

async function jogBySeconds(deltaSeconds){
  const track = Array.isArray(lastState?.playing_tracks) && lastState.playing_tracks.length ? lastState.playing_tracks[0] : null;
  if(!track){
    setStatus(t('errorPrefix') + 'no active playback');
    return;
  }
  const durationMs = Math.max(0, parseInt(track.duration_ms || 0, 10) || 0);
  const positionMs = Math.max(0, parseInt(track.position_ms || 0, 10) || 0);
  if(durationMs <= 0){
    setStatus(t('errorPrefix') + 'no active seek range');
    return;
  }
  const targetMs = Math.max(0, Math.min(durationMs, positionMs + (deltaSeconds * 1000)));
  await callApi('/api/seek/time/' + formatSeekTime(targetMs));
}

function updateJogLabel(value, durationMs=0){
  const node = document.getElementById('jogValue');
  if(!node){ return; }
  const numeric = parseInt(value || 0, 10) || 0;
  const duration = Math.max(0, parseInt(durationMs || 0, 10) || 0);
  if(duration <= 0){
    node.textContent = t('jogHint');
    return;
  }
  const targetMs = Math.round((numeric / 100) * duration);
  node.textContent = `${formatSeekTime(targetMs)} / ${formatSeekTime(duration)}`;
}

function syncJogSliderFromState(){
  const slider = document.getElementById('jogSlider');
  const start = document.getElementById('jogStart');
  const end = document.getElementById('jogEnd');
  if(!slider || !start || !end){ return; }
  const track = Array.isArray(lastState?.playing_tracks) && lastState.playing_tracks.length ? lastState.playing_tracks[0] : null;
  if(!track){
    slider.value = '0';
    slider.disabled = true;
    start.textContent = '00:00';
    end.textContent = '00:00';
    updateJogLabel(0, 0);
    return;
  }
  const durationMs = Math.max(0, parseInt(track.duration_ms || 0, 10) || 0);
  const positionMs = Math.max(0, parseInt(track.position_ms || 0, 10) || 0);
  slider.disabled = durationMs <= 0;
  start.textContent = formatSeekTime(positionMs);
  end.textContent = formatSeekTime(durationMs);
  if(!jogSliderActive){
    const percent = durationMs > 0 ? Math.round((positionMs / durationMs) * 100) : 0;
    slider.value = String(Math.max(0, Math.min(100, percent)));
    updateJogLabel(slider.value, durationMs);
  }
}

async function seekFromSlider(){
  const slider = document.getElementById('jogSlider');
  const track = Array.isArray(lastState?.playing_tracks) && lastState.playing_tracks.length ? lastState.playing_tracks[0] : null;
  if(!slider || !track){
    jogSliderActive = false;
    syncJogSliderFromState();
    return;
  }
  const durationMs = Math.max(0, parseInt(track.duration_ms || 0, 10) || 0);
  const percent = Math.max(0, Math.min(100, parseInt(slider.value || '0', 10) || 0));
  jogSliderActive = false;
  if(durationMs <= 0){
    syncJogSliderFromState();
    return;
  }
  const targetMs = Math.round((percent / 100) * durationMs);
  await callApi('/api/seek/time/' + formatSeekTime(targetMs));
}

function openLyricDisplay(view){
  const url = '/lyric/' + String(view || '').toLowerCase() + '/';
  window.open(url, '_blank', 'noopener,noreferrer');
}

async function selectGroup(group){
  selectedGroup = group;
  selectedPage = 1;
  renderGroups();
  renderPages();
  await callApi('/api/goto/' + group.toLowerCase() + '-1');
}

async function selectPage(page){
  selectedPage = page;
  renderPages();
  await callApi('/api/goto/' + selectedGroup.toLowerCase() + '-' + page);
}

async function playButton(buttonId){
  await callApi('/api/play/' + buttonId);
}

async function unlockFromRemote(){
  if(lastState?.automation_locked){
    const ok = window.confirm(t('unlockConfirm'));
    if(!ok){ return; }
  }
  await callApi('/api/unlock');
}

async function refreshState(updateSelection){
  const payload = await apiRequest('/api/query', 'GET');
  if(!payload.ok){
    setStatus(t('errorPrefix') + (payload.error?.message || 'query failed'));
    return null;
  }
  const state = payload.result || {};
  lastState = state;
  if(updateSelection){
    if(state.current_group && groups.includes(state.current_group)){ selectedGroup = state.current_group; }
    if(state.current_page){ selectedPage = Math.max(1, Math.min(18, state.current_page)); }
  }
  const stateView = document.getElementById('stateView');
  if(stateView){
    stateView.textContent = JSON.stringify({
      current_group: state.current_group,
      current_page: state.current_page,
      is_playing: state.is_playing,
      screen_locked: state.screen_locked,
      automation_locked: state.automation_locked,
      talk_active: state.talk_active,
      vocal_removed_active: state.vocal_removed_active,
      playlist_enabled: state.playlist_enabled,
      shuffle_enabled: state.shuffle_enabled,
      multi_play_enabled: state.multi_play_enabled,
      video_display_follow_sound_button_focus: state.video_display_follow_sound_button_focus,
      video_display_manual_source: state.video_display_manual_source,
      video_display_active_source: state.video_display_active_source,
      web_remote_url: state.web_remote_url
    }, null, 2);
  }
  const automationWarning = document.getElementById('automationWarning');
  if(automationWarning){
    if(state.automation_locked){
      automationWarning.textContent = t('automationWarning');
      automationWarning.classList.remove('hidden');
    }else{
      automationWarning.textContent = '';
      automationWarning.classList.add('hidden');
    }
  }
  renderTracks(state.playing_tracks || []);
  applyToggleStates(state);
  syncVideoDisplayControls(state);
  renderSummaryBox(state);
  renderAboutMeta(state);
  syncJogSliderFromState();
  renderGroups();
  renderPages();
  return state;
}

async function refreshPageMeta(){
  const payload = await apiRequest('/api/query/pagegroup/' + selectedGroup.toLowerCase(), 'GET');
  if(!payload.ok){
    setStatus(t('errorPrefix') + (payload.error?.message || 'pagegroup query failed'));
    return;
  }
  pageMeta = payload.result?.pages || [];
  renderPages();
}

async function refreshPageButtons(){
  const id = selectedGroup.toLowerCase() + '-' + selectedPage;
  const payload = await apiRequest('/api/query/page/' + id, 'GET');
  if(!payload.ok){
    setStatus(t('errorPrefix') + (payload.error?.message || 'page query failed'));
    return;
  }
  renderButtons(payload.result?.buttons || []);
}

async function refreshAll(updateSelection=true){
  try{
    await refreshState(updateSelection);
    await refreshPageMeta();
    await refreshPageButtons();
    setStatus(t('stateRefreshed'));
  }catch(err){
    if(transportMode === 'ws'){
      transportMode = 'http';
      writeCookie(transportCookieName, transportMode);
      const transportSelect = document.getElementById('transportMode');
      if(transportSelect){ transportSelect.value = transportMode; }
      closeWsApi();
      renderSummaryBox(lastState);
    }
    setStatus(t('errorPrefix') + err);
  }
}

function bindEvents(){
  const refreshButton = document.getElementById('refreshButton');
  if(refreshButton){
    refreshButton.addEventListener('click', () => { refreshAll(true); });
  }
  const transportSelect = document.getElementById('transportMode');
  if(transportSelect){
    transportSelect.value = transportMode;
    transportSelect.addEventListener('change', async () => {
      transportMode = String(transportSelect.value || 'ws').toLowerCase() === 'http' ? 'http' : 'ws';
      writeCookie(transportCookieName, transportMode);
      if(transportMode !== 'ws'){
        closeWsApi();
      }else{
        try{
          await ensureWsApiConnected();
        }catch(err){
          setStatus(t('errorPrefix') + err);
          transportMode = 'http';
          transportSelect.value = 'http';
          writeCookie(transportCookieName, transportMode);
          closeWsApi();
        }
      }
      renderSummaryBox(lastState);
      await refreshAll(false);
    });
  }
  const languageSelect = document.getElementById('languageMode');
  if(languageSelect){
    languageSelect.value = localePreference === 'en' || localePreference === 'zh' ? localePreference : 'auto';
    languageSelect.addEventListener('change', () => {
      localePreference = String(languageSelect.value || 'auto').toLowerCase();
      if(localePreference !== 'en' && localePreference !== 'zh'){
        localePreference = 'auto';
      }
      writeCookie(languageCookieName, localePreference);
      applyStaticText();
      renderGroups();
      renderPages();
      renderButtons([]);
      renderTracks(lastState?.playing_tracks || []);
      renderSummaryBox(lastState);
      refreshAll(false);
    });
  }
  document.body.addEventListener('click', async (event) => {
    const target = event.target.closest('button, [data-group], [data-page], [data-button-id]');
    if(!target){ return; }
    if(target.dataset.api){
      await callApi(target.dataset.api);
      return;
    }
    if(target.dataset.lyricView){
      openLyricDisplay(target.dataset.lyricView);
      return;
    }
    if(target.dataset.group){
      await selectGroup(target.dataset.group);
      return;
    }
    if(target.dataset.page){
      await selectPage(parseInt(target.dataset.page, 10));
      return;
    }
    if(target.dataset.buttonId){
      await playButton(target.dataset.buttonId);
    }
  });
  const slider = document.getElementById('volumeSlider');
  const levelInput = document.getElementById('volumeLevel');
  if(slider && levelInput){
    slider.addEventListener('input', () => { levelInput.value = slider.value; });
    slider.addEventListener('change', setVolumeFromSlider);
    levelInput.addEventListener('input', () => { slider.value = levelInput.value; });
  }
  if(levelInput){
    levelInput.addEventListener('change', setVolumeFromInput);
  }
  const jogSlider = document.getElementById('jogSlider');
  if(jogSlider){
    jogSlider.addEventListener('input', () => {
      jogSliderActive = true;
      const track = Array.isArray(lastState?.playing_tracks) && lastState.playing_tracks.length ? lastState.playing_tracks[0] : null;
      updateJogLabel(jogSlider.value, track?.duration_ms || 0);
    });
    jogSlider.addEventListener('change', seekFromSlider);
  }
  const sendAlertButton = document.getElementById('sendAlertButton');
  if(sendAlertButton){
    sendAlertButton.addEventListener('click', sendAlert);
  }
  const clearAlertButton = document.getElementById('clearAlertButton');
  if(clearAlertButton){
    clearAlertButton.addEventListener('click', clearAlert);
  }
  const unlockButton = document.getElementById('unlockButton');
  if(unlockButton){
    unlockButton.addEventListener('click', unlockFromRemote);
  }
  const automationLockButton = document.getElementById('automationLockButton');
  if(automationLockButton){
    automationLockButton.addEventListener('click', () => callApi('/api/automation-lock'));
  }
  const videoFollowSoundButtonFocus = document.getElementById('videoFollowSoundButtonFocus');
  if(videoFollowSoundButtonFocus){
    videoFollowSoundButtonFocus.addEventListener('change', async () => {
      await setVideoDisplayFollow(videoFollowSoundButtonFocus.checked);
    });
  }
  const videoDisplayManualSource = document.getElementById('videoDisplayManualSource');
  if(videoDisplayManualSource){
    videoDisplayManualSource.addEventListener('change', setVideoDisplaySourceFromCurrentControls);
  }
}

applyStaticText();
setStatus(t('ready'));
applyToggleStates(null);
syncVideoDisplayControls(null);
renderSummaryBox(null);
renderAboutMeta(null);
syncJogSliderFromState();
bindEvents();
refreshAll(true);
setInterval(() => refreshAll(true), 1800);
