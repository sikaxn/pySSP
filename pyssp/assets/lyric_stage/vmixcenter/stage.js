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

window.lyricFontMax = Infinity;

window.OpenLP = {
  // Connect to the OpenLP Remote WebSocket to get pushed updates
  myWebSocket: function (data, status) {
    const host = window.location.hostname;
    const websocket_port = 4317;
    var myTwelve;
    window.currentLayer = "A";

    ws = new WebSocket(`ws://${host}:${websocket_port}`);
    ws.onmessage = (event) => {
      const reader = new FileReader();
      reader.onload = () => {
        data = JSON.parse(reader.result.toString()).results;
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
          window.lyricFontMax = Infinity;
          OpenLP.loadSlides();
        }
        else if (OpenLP.currentSlide != data.slide) {
          OpenLP.currentSlide = parseInt(data.slide, 10);
          OpenLP.updateSlide();
        }

        OpenLP.loadService();
      };
      reader.readAsText(event.data);
    };
  },

  loadService: function (event) {
    $.getJSON(
      "/api/v2/service/items",
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
      "/api/v2/controller/live-items",
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
updateSlide: function (forceResize = false) {
  let newHtml = "";  // default = blank

  const slides = OpenLP.currentSlides || [];
  const slide = slides[OpenLP.currentSlide];

  // ---------------------------------------------------------------
  // Determine whether the overlay MUST be blank
  // ---------------------------------------------------------------
  const forceBlank =
    OpenLP.display === "blank" ||
    OpenLP.display === "desktop" ||
    OpenLP.display === "theme" ||
    OpenLP.isBlank === true ||
    OpenLP.isThemeBlank === true;

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
  if (oldHtml === newHtml && !forceResize && window.lyricFontMax !== Infinity) return;

  // Find the largest size that fits both the lyric width and the viewport height.
  // Keep the smallest size seen in this song so slide changes do not grow/shrink.
  let fontSize = window.lyricFontMax;
  if (newHtml) {
    fontSize = Math.min(OpenLP.fitLyricText(newHtml), fontSize);
    window.lyricFontMax = fontSize;
  }
  if (oldHtml === newHtml) {
    if (Number.isFinite(fontSize)) $(".lyric-layer").css("font-size", fontSize + "px");
    return;
  }

  // ---------------------------------------------------------------
  // TRUE 2-layer crossfade (no flicker)
  // ---------------------------------------------------------------
  OpenLP.swapLayers(newHtml, fontSize);

  // NEXT SLIDE (kept hidden by CSS, unchanged)
  var nextText = "";
  if (OpenLP.currentSlide < slides.length - 1) {
    for (var idx = OpenLP.currentSlide + 1; idx < slides.length; idx++) {
      if (slides[idx]["text"])
        nextText += slides[idx]["text"];
      else
        nextText += slides[idx]["title"];
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

fitLyricText: function (html) {
  const container = document.getElementById("lyric-container");
  const overlay = document.getElementById("overlay-container");
  const measure = document.getElementById("lyric-measure");
  if (!container || !overlay || !measure) return 64;

  const styles = getComputedStyle(overlay);
  const maxWidth = Math.max(1, container.clientWidth);
  const maxHeight = Math.max(
    1,
    overlay.clientHeight - parseFloat(styles.paddingTop) - parseFloat(styles.paddingBottom)
  );
  const rootStyles = getComputedStyle(document.documentElement);
  const minSize = parseFloat(rootStyles.getPropertyValue("--lyric-min-font-size")) || 24;
  const maxSize = parseFloat(rootStyles.getPropertyValue("--lyric-max-font-size")) || 220;
  measure.style.width = maxWidth + "px";
  measure.innerHTML = html;

  let low = Math.floor(minSize);
  let high = Math.floor(maxSize);
  let best = low;
  while (low <= high) {
    const size = Math.floor((low + high) / 2);
    measure.style.fontSize = size + "px";
    if (measure.scrollWidth <= maxWidth + 1 && measure.scrollHeight <= maxHeight + 1) {
      best = size;
      low = size + 1;
    } else {
      high = size - 1;
    }
  }
  measure.style.fontSize = best + "px";
  return best;
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

  swapLayers: function(newHtml, fontSize) {
  const top = OpenLP.currentLayer === "A" ? "#lyricA" : "#lyricB";
  const bottom = OpenLP.currentLayer === "A" ? "#lyricB" : "#lyricA";

  // Size only the incoming layer. The outgoing lyric keeps its size as it fades.
  if (Number.isFinite(fontSize)) $(bottom).css("font-size", fontSize + "px");
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
$(window).on("resize", () => {
  window.lyricFontMax = Infinity;
  OpenLP.updateSlide(true);
});
if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(() => {
    window.lyricFontMax = Infinity;
    OpenLP.updateSlide(true);
  });
}
OpenLP.myWebSocket();
