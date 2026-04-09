/******************************************************************************
 * OpenLP - Open Source Lyrics Projection                                      *
 * --------------------------------------------------------------------------- *
 * Copyright (c) 2008-2021 OpenLP Developers                                   *
 * --------------------------------------------------------------------------- *
 * This program is free software; you can redistribute it and/or modify it     *
 * under the terms of the GNU General Public License as published by the Free  *
 * Software Foundation; version 2 of the License.                              *
 *                                                                             *
 * This program is distributed in the hope that it will be useful, but WITHOUT *
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or       *
 * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for    *
 * more details.                                                               *
 *                                                                             *
 * You should have received a copy of the GNU General Public License along     *
 * with this program; if not, write to the Free Software Foundation, Inc., 59  *
 * Temple Place, Suite 330, Boston, MA 02111-1307 USA                          *
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
  // Connect to the OpenLP Remote WebSocket to get pushed updates
  myWebSocket: function (data, status) {
    var myTwelve;
    window.currentLayer = "A";

    ws = new WebSocket(OpenLP.wsUrl());
    ws.onopen = () => { OpenLP._wsConnected = true; };
    ws.onerror = () => {
      if (!OpenLP._wsConnected) OpenLP.startPollingFallback();
    };
    ws.onclose = () => { OpenLP.startPollingFallback(); };
    ws.onmessage = (event) => {
      const applyPayload = (rawText) => {
        data = JSON.parse(String(rawText || "{}")).results || {};
        // set some global var
        OpenLP.myTwelve = data.twelve;
        // Save display mode from WebSocket
        OpenLP.display = data.display || "";   // "show", "blank", "theme", "desktop"
        OpenLP.isBlank = data.blank || false;  // true = blanked
        OpenLP.isThemeBlank = data.theme || false; // true = blank to theme/background

        if (OpenLP.currentItem != data.item ||
            OpenLP.currentService != data.service) {

          OpenLP.currentItem = data.item;
          OpenLP.currentService = data.service;
          OpenLP.loadSlides();
        }
        else if (OpenLP.currentSlide != data.slide) {
          OpenLP.currentSlide = parseInt(data.slide, 10);
          OpenLP.updateSlide();
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

  loadService: function (event) {
    $.getJSON(
      OpenLP.apiUrl("/api/v2/service/items"),
      function (data, status) {
        OpenLP.nextSong = "";
        $("#notes").html("");

        data.forEach(function (item, index, array) {
          if (item.selected) {
            $("#notes").html(item.notes);

            if (data.length > index + 1)
              OpenLP.nextSong = data[index + 1].title;
            else
              OpenLP.nextSong = "End of Service";
          }
        });

        OpenLP.updateSlide();
      }
    );
  },

  loadSlides: function (event) {
    $.getJSON(
      OpenLP.apiUrl("/api/v2/controller/live-items"),
      function (data, status) {
        OpenLP.currentSlides = data.slides;
        OpenLP.currentSlide = 0;
        OpenLP.currentTags = Array();

        var div = $("#verseorder");
        div.html("");

        var tag = "";
        var tags = 0;
        var lastChange = 0;

        $.each(data.slides, function (idx, slide) {
          var prevtag = tag;
          tag = slide["tag"];

          if (tag != prevtag) {
            lastChange = idx;
            tags = tags + 1;
            div.append("&nbsp;<span>");
            $("#verseorder span")
              .last()
              .attr("id", "tag" + tags)
              .text(tag);
          }
          else {
            if ((slide["text"] == data.slides[lastChange]["text"]) &&
                (data.slides.length >= idx + (idx - lastChange))) {

              var match = true;

              for (var idx2 = 0; idx2 < idx - lastChange; idx2++) {
                if (data.slides[lastChange + idx2]["text"] != data.slides[idx + idx2]["text"]) {
                  match = false;
                  break;
                }
              }

              if (match) {
                lastChange = idx;
                tags = tags + 1;
                div.append("&nbsp;<span>");
                $("#verseorder span")
                  .last()
                  .attr("id", "tag" + tags)
                  .text(tag);
              }
            }
          }

          OpenLP.currentTags[idx] = tags;

          if (slide["selected"])
            OpenLP.currentSlide = idx;
        });

        OpenLP.loadService();
      }
    );
  },

/***********************************************************************
 * updateSlide() — Lyric Overlay Version with TRUE 2-layer crossfade
 * - Handles: text→text, text→blank, blank→text, image→blank
 * - Uses layer swap for flicker-free transitions
 ***********************************************************************/
updateSlide: function () {
  let newHtml = "";  // default = blank

  const slide = OpenLP.currentSlides[OpenLP.currentSlide];

  // ---------------------------------------------------------------
  // Determine whether the overlay MUST be blank
  // ---------------------------------------------------------------
  const forceBlank =
    OpenLP.display === "blank" ||
    OpenLP.display === "desktop" ||
    OpenLP.display === "theme" ||
    OpenLP.isBlank === true;

  // ---------------------------------------------------------------
  // If not forced blank, attempt to extract text
  // ---------------------------------------------------------------
  if (!forceBlank && slide) {
    const imgSrc = slide.img || "";
    const html = slide.html || "";
    const rawText = slide.text || "";

    const hasImage =
      (imgSrc && imgSrc.trim() !== "") ||
      html.includes("<img") ||
      rawText.includes("<img");

    if (!hasImage) {
      const cleaned = rawText
        .replace(/\r/g, "")
        .replace(/\n/g, "<br>")
        .trim();

      if (cleaned !== "")
        newHtml = cleaned;
    }
  }

  // ---------------------------------------------------------------
  // Determine which layer is currently visible
  // ---------------------------------------------------------------
  const active = (OpenLP.currentLayer === "A") ? "#lyricA" : "#lyricB";
  const oldHtml = $(active).html();

  // ---------------------------------------------------------------
  // If content did not change → do nothing
  // ---------------------------------------------------------------
  if (oldHtml === newHtml) return;

  // ---------------------------------------------------------------
  // TRUE 2-layer crossfade (no flicker)
  // ---------------------------------------------------------------
  OpenLP.swapLayers(newHtml);

  // NEXT SLIDE (kept hidden by CSS, unchanged)
  var nextText = "";
  if (OpenLP.currentSlide < OpenLP.currentSlides.length - 1) {
    for (var idx = OpenLP.currentSlide + 1; idx < OpenLP.currentSlides.length; idx++) {
      if (OpenLP.currentSlides[idx]["text"])
        nextText += OpenLP.currentSlides[idx]["text"];
      else
        nextText += OpenLP.currentSlides[idx]["title"];
      nextText += "<br />";
    }
    nextText = nextText.replace(/\n/g, "<br />");
    $("#nextslide").html(nextText);
  } else {
    nextText =
      "<p class=\"nextslide\">" +
      $("#next-text").val() + ": " +
      OpenLP.nextSong +
      "</p>";
    $("#nextslide").html(nextText);
  }
},



fadeOut: function(callback) {
  const elem = $("#currentslide");
  elem.css("opacity", "0");
  setTimeout(() => {
    if (callback) callback();
  }, 80); // match 0.08s transition
},

fadeIn: function() {
  $("#currentslide").css("opacity", "1");
},

  updateClock: function (data) {
    var div = $("#clock");
    var t = new Date();
    var h = t.getHours();

    if (OpenLP.myTwelve && h > 12)
      h = h - 12;

    var m = t.getMinutes();
    if (m < 10)
      m = "0" + m;

    div.html(h + ":" + m);
  },

  swapLayers: function(newHtml) {
  const top = OpenLP.currentLayer === "A" ? "#lyricA" : "#lyricB";
  const bottom = OpenLP.currentLayer === "A" ? "#lyricB" : "#lyricA";

  // bottom becomes new content
  $(bottom).html(newHtml);

  // fade out current
  $(top).css("opacity", 0);

  // fade in new
  $(bottom).css("opacity", 1);

  // switch active layer
  OpenLP.currentLayer = OpenLP.currentLayer === "A" ? "B" : "A";
},

};



$.ajaxSetup({ cache: false });
setInterval("OpenLP.updateClock();", 500);
OpenLP.myWebSocket();

