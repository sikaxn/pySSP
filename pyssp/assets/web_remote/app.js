  const groups = ['A','B','C','D','E','F','G','H','I','J'];
  const wsApiPort = (() => {
    const token = window.location.port ? parseInt(window.location.port, 10) : ((window.location.protocol === 'https:') ? 443 : 80);
    return (Number.isFinite(token) ? token : 5050) + 1;
  })();
  let selectedGroup = 'A';
  let selectedPage = 1;
  let pageMeta = [];
  let lastState = null;
  let transportMode = 'http';
  let wsApiSocket = null;
  let wsApiConnectPromise = null;
  let wsApiRequestCounter = 1;
  const wsPendingRequests = new Map();

  function openLyricDisplay(view){
    const url = '/lyric/' + String(view || '').toLowerCase() + '/';
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function setStatus(text){ document.getElementById('lastStatus').textContent = text; }

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
              setStatus('WS Error: ' + (message.error?.message || 'unknown error'));
            }
          }catch(_err){}
        };
        ws.onerror = () => {
          setStatus('WS Error: transport error');
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

  async function callApi(path){
    try{
      const data = await apiRequest(path, 'POST');
      if(!data.ok){ setStatus('Error: ' + (data.error?.message || 'request failed')); }
      else { setStatus('OK'); }
      await refreshAll(false);
      return data;
    }catch(err){ setStatus('Error: ' + err); }
  }

  async function sendAlert(){
    const textEl = document.getElementById('alertText');
    const keepEl = document.getElementById('alertKeep');
    const secondsEl = document.getElementById('alertSeconds');
    const text = (textEl?.value || '').trim();
    if(!text){ setStatus('Error: alert text required'); return; }
    const keep = !!(keepEl && keepEl.checked);
    const seconds = Math.max(1, Math.min(600, parseInt(secondsEl?.value || '10', 10) || 10));
    try{
      const data = await apiRequest('/api/alert', 'POST', {text, keep, seconds});
      if(!data.ok){ setStatus('Error: ' + (data.error?.message || 'request failed')); }
      else { setStatus('OK'); }
      await refreshAll(false);
      return data;
    }catch(err){ setStatus('Error: ' + err); }
  }

  async function clearAlert(){
    await callApi('/api/alert/clear');
  }

  async function setVolumeFromInput(){
    const input = document.getElementById('volumeLevel');
    const raw = parseInt(input?.value || '0', 10);
    const level = Math.max(0, Math.min(100, Number.isFinite(raw) ? raw : 0));
    if(input){ input.value = String(level); }
    await callApi('/api/volume/' + level);
  }

  function escapeHtml(value){
    return String(value ?? '').replace(/[&<>"']/g, function(ch){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
    });
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
    root.innerHTML = groups.map(g =>
      `<button class="small ${g===selectedGroup?'active':''}" onclick="selectGroup('${g}')">${g}</button>`
    ).join('');
  }

  function renderPages(){
    const root = document.getElementById('pages');
    const source = pageMeta.length ? pageMeta : Array.from({length:18}, (_, i) => ({page:i+1,page_name:'',page_color:null}));
    root.innerHTML = source.map(info => {
      const p = Number(info.page || 0);
      const color = info.page_color || '';
      const style = color ? `background:${color};color:${idealTextColor(color)};` : '';
      const pageName = (info.page_name || '').trim();
      const label = pageName ? `${p}<br>${escapeHtml(pageName)}` : `${p}`;
      return `<button class="${p===selectedPage?'active':''}" style="${style}" onclick="selectPage(${p})" title="${escapeHtml(pageName || ('Page ' + p))}">${label}</button>`;
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
    root.innerHTML = (buttons || []).map(b => {
      let title = '';
      if(b.marker){
        title = (b.marker_text && b.marker_text.trim()) ? b.marker_text : (b.title || '').trim();
      }else{
        title = (b.title && b.title.trim()) ? b.title : ('Button ' + b.button);
      }
      const safeTitle = escapeHtml(title);
      return `<button class="${buttonClass(b)}" onclick="playButton('${b.button_id}')">${b.button}<br>${safeTitle}</button>`;
    }).join('');
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
      const ok = window.confirm(
        'Automation lock is active. Unlock only for troubleshooting when you are sure pySSP should stop being remotely controlled.'
      );
      if(!ok){ return; }
    }
    await callApi('/api/unlock');
  }

  function renderTracks(tracks){
    const root = document.getElementById('tracksView');
    if(!tracks || tracks.length===0){ root.innerHTML = '<div class="track">None</div>'; return; }
    root.innerHTML = tracks.map(t =>
      `<div class="track"><strong>${t.button_id}</strong> - ${t.title || '(untitled)'}<br>` +
      `Remaining: ${t.remaining} (${t.remaining_ms} ms)</div>`
    ).join('');
  }

  async function refreshState(updateSelection){
    const payload = await apiRequest('/api/query', 'GET');
    if(!payload.ok){ setStatus('Error: ' + (payload.error?.message || 'query failed')); return null; }
    const s = payload.result || {};
    lastState = s;
    if(updateSelection){
      if(s.current_group && groups.includes(s.current_group)){ selectedGroup = s.current_group; }
      if(s.current_page){ selectedPage = Math.max(1, Math.min(18, s.current_page)); }
    }
    document.getElementById('stateView').textContent = JSON.stringify({
      current_group: s.current_group,
      current_page: s.current_page,
      is_playing: s.is_playing,
      screen_locked: s.screen_locked,
      automation_locked: s.automation_locked,
      talk_active: s.talk_active,
      playlist_enabled: s.playlist_enabled,
      shuffle_enabled: s.shuffle_enabled,
      multi_play_enabled: s.multi_play_enabled,
      web_remote_url: s.web_remote_url
    }, null, 2);
    const automationWarning = document.getElementById('automationWarning');
    if(automationWarning){
      if(s.automation_locked){
        automationWarning.textContent =
          'Automation lock is active. pySSP is expected to be controlled remotely. Unlock only for troubleshooting when you are sure.';
        automationWarning.style.display = 'block';
      }else{
        automationWarning.textContent = '';
        automationWarning.style.display = 'none';
      }
    }
    renderTracks(s.playing_tracks || []);
    renderGroups();
    renderPages();
    return s;
  }

  async function refreshPageButtons(){
    const id = selectedGroup.toLowerCase() + '-' + selectedPage;
    const payload = await apiRequest('/api/query/page/' + id, 'GET');
    if(!payload.ok){
      setStatus('Error: ' + (payload.error?.message || 'page query failed'));
      return;
    }
    renderButtons(payload.result?.buttons || []);
  }

  async function refreshPageMeta(){
    const payload = await apiRequest('/api/query/pagegroup/' + selectedGroup.toLowerCase(), 'GET');
    if(!payload.ok){
      setStatus('Error: ' + (payload.error?.message || 'pagegroup query failed'));
      return;
    }
    pageMeta = payload.result?.pages || [];
    renderPages();
  }

  async function refreshAll(updateSelection=true){
    try{
      await refreshState(updateSelection);
      await refreshPageMeta();
      await refreshPageButtons();
      setStatus('State refreshed');
    }catch(err){
      setStatus('Error: ' + err);
    }
  }

  const transportSelect = document.getElementById('transportMode');
  if(transportSelect){
    transportSelect.value = transportMode;
    transportSelect.addEventListener('change', async () => {
      transportMode = String(transportSelect.value || 'http').toLowerCase() === 'ws' ? 'ws' : 'http';
      if(transportMode !== 'ws'){
        closeWsApi();
      }else{
        try{
          await ensureWsApiConnected();
        }catch(err){
          setStatus('Error: ' + err);
          transportMode = 'http';
          transportSelect.value = 'http';
          closeWsApi();
        }
      }
      await refreshAll(false);
    });
  }

  refreshAll(true);
  setInterval(() => refreshAll(false), 1800);
