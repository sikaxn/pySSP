/******************************************************************************
 * LED Banner Caption JS (single- or two-line, auto-scaling, crossfade, stable size)
 ******************************************************************************/

window.bannerFontMax = Infinity;   // global font memory (consistent size)

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
    window.currentBannerLayer = "A";

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

        // reset global font max when item changes
        if (OpenLP.currentItem != info.item ||
            OpenLP.currentService != info.service) {

          OpenLP.currentItem = info.item;
          OpenLP.currentService = info.service;

          window.bannerFontMax = Infinity;  // RESET FONT SIZE FOR NEW SONG
          OpenLP.loadSlides();
        }
        else if (OpenLP.currentSlide != info.slide) {
          OpenLP.currentSlide = parseInt(info.slide, 10);
          OpenLP.updateBanner();
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
      data.forEach(item => {
        if (item.selected) OpenLP.songTitle = item.title || "";
      });
      OpenLP.updateBanner();
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
   * updateBanner() — autoscale + global size memory + perfect crossfade
   ***********************************************************************/
  updateBanner: function () {

    let newHtml = "";

    const slide = OpenLP.currentSlides[OpenLP.currentSlide];

    // Blank logic
    const forceBlank =
      OpenLP.display === "blank" ||
      OpenLP.display === "desktop" ||
      OpenLP.display === "theme" ||
      OpenLP.isBlank === true;

    if (!forceBlank && slide) {

      const rawText = slide.text || "";
      const html = slide.html || "";
      const imgSrc = slide.img || "";

      const hasImage =
        (imgSrc && imgSrc.trim() !== "") ||
        html.includes("<img") ||
        rawText.includes("<img");

      if (!hasImage) {
        const lines = rawText
          .replace(/\r/g, "")
          .split("\n")
          .map(line => line.trim())
          .filter(line => line !== "");

        const clipped = lines.slice(0, 2);
        if (clipped.length > 0) newHtml = clipped.join("<br>");
      }
    }

    // Determine active layer
    const active = (OpenLP.currentBannerLayer === "A")
      ? "#banner-layerA"
      : "#banner-layerB";

    const oldHtml = $(active).html();

    if (oldHtml === newHtml) return;

    // Determine incoming layer (bottom)
    const bottom = (OpenLP.currentBannerLayer === "A") ? "#banner-layerB" : "#banner-layerA";

    // 1. compute raw autoscale size
    let rawSize = OpenLP.fitBannerTextToWidth(newHtml);

    // 2. apply global font memory (stable size across lines)
    let fontSize;
    if (window.bannerFontMax === Infinity) {
      // first line sets baseline
      window.bannerFontMax = rawSize;
      fontSize = rawSize;
    } else {
      // keep consistent appearance
      fontSize = Math.min(rawSize, window.bannerFontMax);
      window.bannerFontMax = fontSize;
    }

    // 3. apply font size ONLY to incoming layer
    $(bottom).css("font-size", fontSize + "px");

    // 4. perform proper crossfade
    OpenLP.swapBannerLayers(newHtml, fontSize);
  },

  /***********************************************************************
   * swapBannerLayers — final version (no resize of outgoing layer)
   ***********************************************************************/
  swapBannerLayers: function(newHtml, fontSize) {
    const isA = OpenLP.currentBannerLayer === "A";
    const top = isA ? "#banner-layerA" : "#banner-layerB";   // outgoing
    const bottom = isA ? "#banner-layerB" : "#banner-layerA"; // incoming

    // 1. prepare incoming layer
    $(bottom).html(newHtml);
    $(bottom).css("opacity", 0);  // reset
    const b = $(bottom)[0];
    void b.offsetHeight;          // force layout BEFORE transition (critical)

    // 2. fade transition
    $(top).css("opacity", 0);
    $(bottom).css("opacity", 1);

    // 3. after fade completes, sync hidden layer WITHOUT flashing
    setTimeout(() => {
      $(top).css("font-size", fontSize + "px");
      $(top).html(newHtml);
      $(top).css("opacity", 0);
    }, 100); // slightly > 0.08s fade duration

    // 4. swap active layer
    OpenLP.currentBannerLayer = isA ? "B" : "A";
  },

  /***********************************************************************
   * Width-based autoscaling — corrected measurement logic
   ***********************************************************************/
  fitBannerTextToWidth: function (text) {
    const measure = $("#text-measure");
    const container = $("#banner-container");

    const styles = getComputedStyle(document.documentElement);
    const maxWidth = container.width();
    const paddingStr = styles.getPropertyValue("--vertical-padding") || "0";
    const padding = parseFloat(paddingStr) || 0;
    const paddingHStr = styles.getPropertyValue("--horizontal-padding") || "0";
    const paddingH = parseFloat(paddingHStr) || 0;
    const availableWidth = Math.max(0, maxWidth - paddingH * 2);
    const maxHeight = container.height() - padding * 2;

    let size = maxHeight; // start from available vertical space
    const minSize = 32;

    measure.css({
      "font-size": size + "px",
      "max-width": availableWidth + "px",
      "white-space": "pre-line",
      "display": "inline-block",
      "text-align": "center"
    });
    measure.html(text || "");

    const box = () => measure[0].getBoundingClientRect();

    while ((box().width > maxWidth || box().height > maxHeight) && size > minSize) {
      size -= 2;
      measure.css("font-size", size + "px");
    }

    return size;
  },

  updateClock: function () {}
};

$(window).on("resize", () => {
  OpenLP.updateBanner();
});

$.ajaxSetup({ cache: false });
OpenLP.myWebSocket();

