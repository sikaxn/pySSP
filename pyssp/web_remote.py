from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict

from flask import Flask, jsonify, render_template_string
from werkzeug.serving import WSGIRequestHandler, make_server


DispatchFn = Callable[[str, Dict[str, Any]], Dict[str, Any]]


class QuietRequestHandler(WSGIRequestHandler):
    def log_request(self, _code: int | str = "-", _size: int | str = "-") -> None:
        return

    def log_message(self, _format: str, *args) -> None:
        return


class WebRemoteServer:
    def __init__(self, dispatch: DispatchFn, host: str = "0.0.0.0", port: int = 5050) -> None:
        self._dispatch = dispatch
        self.host = host
        self.port = int(port)
        self._app = Flask("pyssp_web_remote")
        self._server = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._configure_logging()
        self._register_routes()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        with self._lock:
            if self.is_running:
                return
            self._server = make_server(
                self.host,
                self.port,
                self._app,
                threaded=True,
                request_handler=QuietRequestHandler,
            )
            self._thread = threading.Thread(target=self._server.serve_forever, name="pyssp-web-remote", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
        if server is not None:
            server.shutdown()
        if thread is not None:
            thread.join(timeout=2.0)

    def _configure_logging(self) -> None:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self._app.logger.setLevel(logging.ERROR)

    def _register_routes(self) -> None:
        app = self._app

        def send(command: str, **params: Any):
            payload = self._dispatch(command, params)
            status = int(payload.get("status", 200))
            body = {k: v for k, v in payload.items() if k != "status"}
            return jsonify(body), status

        @app.get("/")
        def index():
            return render_template_string(
                """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pySSP Web Remote</title>
  <style>
    :root{
      --bg:#eef3f6; --panel:#ffffff; --ink:#1d2b34; --muted:#4f6472;
      --accent:#0b868a; --danger:#c13f29; --ok:#2e7d32; --line:#d5e1e7;
      --empty:#0B868A; --assigned:#B0B0B0; --playing:#66FF33; --played:#FF3B30; --missing:#7B3FB3; --locked:#F2D74A; --marker:#111111;
    }
    *{box-sizing:border-box}
    body{margin:0;padding:14px;background:linear-gradient(180deg,#edf3f7,#dde8ef);font-family:Segoe UI,Arial,sans-serif;color:var(--ink)}
    .shell{max-width:1280px;margin:0 auto;display:grid;grid-template-columns:320px 1fr;gap:12px}
    @media (max-width:980px){.shell{grid-template-columns:1fr}}
    .card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px}
    h1{margin:0 0 8px 0;font-size:20px}
    .row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:7px}
    .row:last-child{margin-bottom:0}
    button{height:32px;padding:0 10px;border:0;border-radius:6px;background:#8da1af;color:#fff;font-weight:600;cursor:pointer}
    button.primary{background:var(--accent)}
    button.warn{background:var(--danger)}
    button.good{background:var(--ok)}
    button.small{height:28px;padding:0 8px;font-size:12px}
    .status{font-size:12px;color:var(--muted)}
    .mono{font-family:Consolas,Menlo,monospace}
    .group-list,.page-list{display:grid;grid-template-columns:repeat(6,1fr);gap:4px}
    .group-list button{height:28px;padding:0;font-size:12px}
    .page-list button{height:48px;padding:2px 4px;font-size:11px;line-height:1.15}
    .group-list button.active,.page-list button.active{outline:2px solid #1f4f66}
    .btn-grid{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:4px}
    .btn-grid button{height:62px;padding:4px;font-size:11px;line-height:1.2;color:#111;overflow:hidden}
    .btn-grid button.empty{background:var(--empty);color:#fff}
    .btn-grid button.assigned{background:var(--assigned)}
    .btn-grid button.playing{background:var(--playing)}
    .btn-grid button.played{background:var(--played);color:#fff}
    .btn-grid button.missing{background:var(--missing);color:#fff}
    .btn-grid button.locked{background:var(--locked)}
    .btn-grid button.marker{background:var(--marker);color:#fff}
    .tracks{margin-top:8px;border-top:1px solid var(--line);padding-top:8px}
    .track{padding:4px 0;border-bottom:1px dotted #d9e5eb}
    .track:last-child{border-bottom:0}
  </style>
</head>
<body>
<div class="shell">
  <div class="card">
    <h1>Web Remote</h1>
    <div class="row">
      <button class="good" onclick="refreshAll()">Refresh</button>
      <span id="lastStatus" class="status">Ready</span>
    </div>
    <div class="row">
      <button onclick="callApi('/api/pause')">Pause</button>
      <button onclick="callApi('/api/resume')">Resume</button>
      <button onclick="callApi('/api/stop')">Stop</button>
      <button class="warn" onclick="callApi('/api/forcestop')">Force Stop</button>
      <button onclick="callApi('/api/playnext')">Next</button>
      <button onclick="callApi('/api/rapidfire')">Rapid Fire</button>
    </div>
    <div class="row">
      <button onclick="callApi('/api/talk/toggle')">Talk</button>
      <button onclick="callApi('/api/playlist/toggle')">Playlist</button>
      <button onclick="callApi('/api/playlist/shuffle/toggle')">Shuffle</button>
      <button onclick="callApi('/api/multiplay/toggle')">Multi</button>
    </div>
    <div class="row">
      <button onclick="callApi('/api/fadein/toggle')">Fade In</button>
      <button onclick="callApi('/api/fadeout/toggle')">Fade Out</button>
      <button onclick="callApi('/api/crossfade/toggle')">Crossfade</button>
    </div>
    <div class="row">
      <button onclick="callApi('/api/resetpage/current')">Reset Page</button>
      <button class="warn" onclick="callApi('/api/resetpage/all')">Reset All</button>
    </div>
    <div id="stateView" class="status mono"></div>
    <div class="tracks">
      <strong>Now Playing</strong>
      <div id="tracksView" class="status"></div>
    </div>
  </div>

  <div class="card">
    <div class="row"><strong>Groups</strong></div>
    <div id="groups" class="group-list"></div>
    <div class="row" style="margin-top:8px;"><strong>Pages</strong></div>
    <div id="pages" class="page-list"></div>
    <div class="row" style="margin-top:8px;"><strong>Buttons</strong></div>
    <div id="buttons" class="btn-grid"></div>
  </div>
</div>

<script>
  const groups = ['A','B','C','D','E','F','G','H','I','J'];
  let selectedGroup = 'A';
  let selectedPage = 1;
  let pageMeta = [];

  function setStatus(text){ document.getElementById('lastStatus').textContent = text; }

  async function callApi(path){
    try{
      const res = await fetch(path, {method:'POST'});
      const data = await res.json();
      if(!data.ok){ setStatus('Error: ' + (data.error?.message || 'request failed')); }
      else { setStatus('OK'); }
      await refreshAll(false);
      return data;
    }catch(err){ setStatus('Error: ' + err); }
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

  function renderTracks(tracks){
    const root = document.getElementById('tracksView');
    if(!tracks || tracks.length===0){ root.innerHTML = '<div class="track">None</div>'; return; }
    root.innerHTML = tracks.map(t =>
      `<div class="track"><strong>${t.button_id}</strong> - ${t.title || '(untitled)'}<br>` +
      `Remaining: ${t.remaining} (${t.remaining_ms} ms)</div>`
    ).join('');
  }

  async function refreshState(updateSelection){
    const res = await fetch('/api/query');
    const payload = await res.json();
    if(!payload.ok){ setStatus('Error: ' + (payload.error?.message || 'query failed')); return null; }
    const s = payload.result || {};
    if(updateSelection){
      if(s.current_group && groups.includes(s.current_group)){ selectedGroup = s.current_group; }
      if(s.current_page){ selectedPage = Math.max(1, Math.min(18, s.current_page)); }
    }
    document.getElementById('stateView').textContent = JSON.stringify({
      current_group: s.current_group,
      current_page: s.current_page,
      is_playing: s.is_playing,
      talk_active: s.talk_active,
      playlist_enabled: s.playlist_enabled,
      shuffle_enabled: s.shuffle_enabled,
      multi_play_enabled: s.multi_play_enabled,
      web_remote_url: s.web_remote_url
    }, null, 2);
    renderTracks(s.playing_tracks || []);
    renderGroups();
    renderPages();
    return s;
  }

  async function refreshPageButtons(){
    const id = selectedGroup.toLowerCase() + '-' + selectedPage;
    const res = await fetch('/api/query/page/' + id);
    const payload = await res.json();
    if(!payload.ok){
      setStatus('Error: ' + (payload.error?.message || 'page query failed'));
      return;
    }
    renderButtons(payload.result?.buttons || []);
  }

  async function refreshPageMeta(){
    const res = await fetch('/api/query/pagegroup/' + selectedGroup.toLowerCase());
    const payload = await res.json();
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

  refreshAll(true);
  setInterval(() => refreshAll(false), 1800);
</script>
</body>
</html>"""
            )

        @app.get("/api/health")
        def api_health():
            return send("health")

        @app.route("/api/play/<string:button_id>", methods=["GET", "POST"])
        def api_play(button_id: str):
            return send("play", button_id=button_id)

        @app.route("/api/pause", methods=["GET", "POST"])
        def api_pause():
            return send("pause")

        @app.route("/api/resume", methods=["GET", "POST"])
        def api_resume():
            return send("resume")

        @app.route("/api/stop", methods=["GET", "POST"])
        def api_stop():
            return send("stop")

        @app.route("/api/forcestop", methods=["GET", "POST"])
        def api_forcestop():
            return send("forcestop")

        @app.route("/api/rapidfire", methods=["GET", "POST"])
        def api_rapidfire():
            return send("rapidfire")

        @app.route("/api/playnext", methods=["GET", "POST"])
        def api_playnext():
            return send("playnext")

        @app.route("/api/talk/<string:mode>", methods=["GET", "POST"])
        def api_talk(mode: str):
            return send("talk", mode=mode)

        @app.route("/api/playlist/<string:mode>", methods=["GET", "POST"])
        def api_playlist(mode: str):
            return send("playlist", mode=mode)

        @app.route("/api/playlist/shuffle/<string:mode>", methods=["GET", "POST"])
        def api_playlist_shuffle(mode: str):
            return send("playlist_shuffle", mode=mode)

        @app.route("/api/playlist/enableshuffle", methods=["GET", "POST"])
        def api_playlist_enable_shuffle():
            return send("playlist_shuffle", mode="enable")

        @app.route("/api/playlist/disableshuffle", methods=["GET", "POST"])
        def api_playlist_disable_shuffle():
            return send("playlist_shuffle", mode="disable")

        @app.route("/api/goto/<string:target>", methods=["GET", "POST"])
        def api_goto(target: str):
            return send("goto", target=target)

        @app.route("/api/resetpage/<string:scope>", methods=["GET", "POST"])
        def api_resetpage(scope: str):
            return send("resetpage", scope=scope)

        @app.route("/api/multiplay/<string:mode>", methods=["GET", "POST"])
        def api_multiplay(mode: str):
            return send("multiplay", mode=mode)

        @app.route("/api/fadein/<string:mode>", methods=["GET", "POST"])
        def api_fadein(mode: str):
            return send("fade", kind="fadein", mode=mode)

        @app.route("/api/fadeout/<string:mode>", methods=["GET", "POST"])
        def api_fadeout(mode: str):
            return send("fade", kind="fadeout", mode=mode)

        @app.route("/api/crossfade/<string:mode>", methods=["GET", "POST"])
        def api_crossfade(mode: str):
            return send("fade", kind="crossfade", mode=mode)

        @app.get("/api/query")
        def api_query_all():
            return send("query_all")

        @app.get("/api/query/button/<string:button_id>")
        def api_query_button(button_id: str):
            return send("query_button", button_id=button_id)

        @app.get("/api/query/pagegroup/<string:group_id>")
        def api_query_pagegroup(group_id: str):
            return send("query_pagegroup", group_id=group_id)

        @app.get("/api/query/page/<string:page_id>")
        def api_query_page(page_id: str):
            return send("query_page", page_id=page_id)
