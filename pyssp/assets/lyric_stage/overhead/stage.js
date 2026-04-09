/******************************************************************************
 * Caption Stage View (Adaptive 4 lines + highlight + title)
 * + Image support: if slide has an image, show ONLY that image
 ******************************************************************************/

window.OpenLP = {
  basePath: function () {
    const path = (window.location.pathname || '').toLowerCase();
    return (path === '/stage' || path.startsWith('/stage/')) ? '/stage' : '/lyric';
  },

  apiUrl: function (suffix) {
    const path = String(suffix || "");
    return path.startsWith("/") ? path : `/${path}`;
  },

  wsUrl: function () {
    const wsScheme = (window.location.protocol === 'https:') ? 'wss:' : 'ws:';
    const params = new URLSearchParams(window.location.search || "");
    const wsPortRaw = (params.get("ws_port") || "").trim();
    const wsPathRaw = (params.get("ws_path") || "/ws").trim();
    const wsPath = wsPathRaw.startsWith("/") ? wsPathRaw : `/${wsPathRaw}`;
    if (wsPortRaw) {
      const wsPort = parseInt(wsPortRaw, 10);
      if (Number.isFinite(wsPort) && wsPort >= 1 && wsPort <= 65535) {
        return `${wsScheme}//${window.location.hostname}:${wsPort}${wsPath}`;
      }
    }
    const defaultPort = parseInt(
      window.location.port || ((window.location.protocol === 'https:') ? '443' : '80'),
      10
    );
    if (Number.isFinite(defaultPort)) {
      const nextPort = defaultPort + 1;
      if (nextPort >= 1 && nextPort <= 65535) {
        return `${wsScheme}//${window.location.hostname}:${nextPort}${wsPath}`;
      }
    }
    return `${wsScheme}//${window.location.host}${wsPath}`;
  },
  _pollTimer: null,
  _wsConnected: false,
  startPollingFallback: function () {
    if (OpenLP._pollTimer) return;
    const tick = () => {
      OpenLP.loadSlides();
      OpenLP.loadService();
    };
    tick();
    OpenLP._pollTimer = setInterval(tick, 600);
  },
  myWebSocket: function () {
    ws = new WebSocket(OpenLP.wsUrl());
    ws.onopen = () => { OpenLP._wsConnected = true; };
    ws.onerror = () => {
      if (!OpenLP._wsConnected) OpenLP.startPollingFallback();
    };
    ws.onclose = () => { OpenLP.startPollingFallback(); };

    ws.onmessage = (event) => {
      const applyPayload = (rawText) => {
        const info = JSON.parse(String(rawText || "{}")).results || {};

        OpenLP.myTwelve = info.twelve;

        if (OpenLP.currentItem != info.item ||
            OpenLP.currentService != info.service) {

          OpenLP.currentItem = info.item;
          OpenLP.currentService = info.service;
          OpenLP.loadSlides();
        }
        else if (OpenLP.currentSlide != info.slide) {
          OpenLP.currentSlide = parseInt(info.slide, 10);
          OpenLP.updateCaption();
        }

        OpenLP.loadService();
      };

      if (typeof event.data === "string") {
        applyPayload(event.data);
        return;
      }
      if (event.data instanceof Blob) {
        const reader = new FileReader();
        reader.onload = () => applyPayload(reader.result);
        reader.readAsText(event.data);
        return;
      }
      if (event.data && typeof event.data.text === "function") {
        event.data.text().then(applyPayload).catch(() => {});
        return;
      }
      try {
        applyPayload(event.data);
      } catch (_err) {}
    };
  },

  loadService: function () {
    $.getJSON(OpenLP.apiUrl("/api/v2/service/items"), function (data) {
      $("#notes").html("");

      data.forEach(function (item, index) {
        if (item.selected) {
          OpenLP.songTitle = item.title || "";

          if (data.length > index + 1)
            OpenLP.nextSong = data[index + 1].title;
          else
            OpenLP.nextSong = "End of Service";
        }
      });

      OpenLP.updateCaption();
    });
  },

  loadSlides: function () {
    $.getJSON(OpenLP.apiUrl("/api/v2/controller/live-items"), function (data) {
      OpenLP.currentSlides = data.slides;
      OpenLP.currentSlide = 0;

      data.slides.forEach((slide, idx) => {
        if (slide["selected"]) OpenLP.currentSlide = idx;
      });

      OpenLP.loadService();
    });
  },

  /***********************************************************************
   * updateCaption() — Smart 4-line caption with conditional highlight
   * - NEW: If slide has an image → show the image ONLY
   * - Skip empty slides
   * - Always show up to 4 lines
   * - Highlight ONLY if the actual current slide had text
   ***********************************************************************/
  updateCaption: function () {
    const slide = OpenLP.currentSlides[OpenLP.currentSlide];
    const linesElem = $("#lines");
    const titleElem = $("#song-title");

    if (!slide) {
      linesElem.html("");
      titleElem.html("");
      return;
    }

// ----------- IMAGE SUPPORT -----------
const imgSrc = slide.img || "";
if (imgSrc.trim() !== "") {
  // Tell CSS we're in image mode
  $("#caption-container").addClass("image-mode");

  linesElem.html(`
    <div class="line line-current">
      <img class="caption-image" src="${imgSrc}">
    </div>
  `);
  titleElem.html(OpenLP.songTitle || "");
  return;
}
// -------------------------------------

    // -------------------------------------

    // Helper: fetch slide text
    function getText(idx) {
      if (!OpenLP.currentSlides[idx]) return "";
      var t = OpenLP.currentSlides[idx]["text"] || "";
      return t.replace(/\r/g, "").replace(/\n/g, "<br>").trim();
    }

// Ensure normal text mode layout
$("#caption-container").removeClass("image-mode");

var collected = [];


    var collected = [];

    // Step 1: Detect if CURRENT slide has text
    var currentText = getText(OpenLP.currentSlide);
    var currentHasText = currentText !== "";

    // Step 2: Collect up to 4 non-empty lines starting at currentSlide
    var idx = OpenLP.currentSlide;
    while (collected.length < 4 && idx < OpenLP.currentSlides.length) {
      var txt = getText(idx);
      if (txt !== "") collected.push(txt);
      idx++;
    }

    // Step 3: If nothing exists, clear
    if (collected.length === 0) {
      linesElem.html("");
      titleElem.html("");
      return;
    }

    // Step 4: Build final HTML
    var html = "";
    for (var i = 0; i < collected.length; i++) {
      if (i === 0 && currentHasText)
        html += `<div class="line line-current">${collected[i]}</div>`;
      else
        html += `<div class="line">${collected[i]}</div>`;
    }

    // Step 5: Pad to always show 4 lines
    while (collected.length < 4) {
      html += `<div class="line">&nbsp;</div>`;
      collected.push("");
    }

    linesElem.html(html);
    titleElem.html(OpenLP.songTitle || "");
  },

  updateClock: function () {
    var t = new Date();
    var h = t.getHours();
    if (OpenLP.myTwelve && h > 12) h -= 12;
    var m = t.getMinutes();
    if (m < 10) m = "0" + m;
    $("#clock").html(h + ":" + m);
  }
};

$.ajaxSetup({ cache: false });
setInterval(() => OpenLP.updateClock(), 500);
OpenLP.myWebSocket();

