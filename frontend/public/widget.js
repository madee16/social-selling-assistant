(function () {
  var scriptSrc = document.currentScript.src;
  var baseUrl = scriptSrc.substring(0, scriptSrc.lastIndexOf('/'));
  var widgetId = document.currentScript.getAttribute('data-widget-id');
  if (!widgetId) return;

  var state = 'loading';
  var convId = null;
  var config = null;
  try { convId = localStorage.getItem('ss_conv_' + widgetId) || null; } catch (e) { convId = null; }
  function persistConv(id) {
    try {
      if (id) { localStorage.setItem('ss_conv_' + widgetId, id); } else { localStorage.removeItem('ss_conv_' + widgetId); }
    } catch (e) {}
  }

  var container = document.createElement('div');
  container.id = 'ss-chat-widget';
  container.style.cssText = 'all:initial;position:fixed;bottom:20px;z-index:999999;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;';
  document.body.appendChild(container);

  var style = document.createElement('style');
  style.textContent =
    '@keyframes ss-bounce{0%,80%,100%{transform:scale(0)}40%{transform:scale(1)}}' +
    '.ss-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#999;margin:0 2px;animation:ss-bounce 1.4s infinite ease-in-out}' +
    '.ss-dot:nth-child(1){animation-delay:-0.32s}' +
    '.ss-dot:nth-child(2){animation-delay:-0.16s}';
  document.head.appendChild(style);

  function render() {
    if (state === 'loading') {
      container.innerHTML = '<div style="width:56px;height:56px;border-radius:50%;background:#2563eb;color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.15);margin-left:auto;font-size:24px;">...</div>';
      return;
    }
    if (state === 'error') {
      container.innerHTML = '';
      return;
    }
    if (state === 'closed') {
      var side = config.position === 'left' ? 'margin-right:auto' : 'margin-left:auto';
      container.innerHTML = '<div class="ss-btn" style="width:56px;height:56px;border-radius:50%;background:' + config.primary_color + ';color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.15);transition:transform 0.2s;' + side + ';font-size:24px;" onclick="document.getElementById(\'ss-chat-widget\').__open()"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></div>';
      return;
    }
    if (state === 'open') {
      var side = config.position === 'left' ? 'margin-right:auto' : 'margin-left:auto';
      container.innerHTML =
        '<div style="width:360px;max-width:90vw;height:520px;max-height:80vh;border-radius:16px;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,0.18);display:flex;flex-direction:column;background:#fff;' + side + ';">' +
        '<div style="background:' + config.primary_color + ';color:#fff;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;">' +
        '<span style="font-weight:600;font-size:14px;">' + escapeHtml(config.title) + '</span>' +
        '<span style="cursor:pointer;font-size:20px;line-height:1;" onclick="document.getElementById(\'ss-chat-widget\').__close()">&times;</span>' +
        '</div>' +
        '<div id="ss-msgs" style="flex:1;overflow-y:auto;padding:12px;background:#f5f5f5;font-size:13px;"></div>' +
        '<div style="padding:10px 12px;border-top:1px solid #e5e5e5;display:flex;gap:8px;background:#fff;">' +
        '<input id="ss-input" type="text" placeholder="Type a message..." style="flex:1;border:1px solid #ddd;border-radius:8px;padding:8px 12px;font-size:13px;outline:none;" />' +
        '<button id="ss-send" style="background:' + config.primary_color + ';color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-size:13px;font-weight:600;">Send</button>' +
        '</div>' +
        (config.show_branding ? '<div style="text-align:center;font-size:10px;color:#999;padding:4px 0;border-top:1px solid #eee;">Powered by Social Selling</div>' : '') +
        '</div>';

      var msgs = document.getElementById('ss-msgs');
      msgs.innerHTML = '<div style="background:#fff;border-radius:8px;padding:10px 12px;margin-bottom:8px;max-width:75%;width:fit-content;color:#333;">' + escapeHtml(config.greeting) + '</div>';

      document.getElementById('ss-send').onclick = sendMessage;
      document.getElementById('ss-input').onkeydown = function (e) { if (e.key === 'Enter') sendMessage(); };
      setTimeout(function () { document.getElementById('ss-input').focus(); }, 300);
    }
  }

  function showTyping() {
    var msgs = document.getElementById('ss-msgs');
    if (!msgs) return;
    if (document.getElementById('ss-typing')) return;
    var el = document.createElement('div');
    el.id = 'ss-typing';
    el.style.cssText = 'background:#fff;border-radius:8px;padding:10px 12px;margin-bottom:8px;max-width:75%;width:fit-content;color:#333;display:flex;align-items:center;gap:2px;';
    el.innerHTML = '<span class="ss-dot"></span><span class="ss-dot"></span><span class="ss-dot"></span>';
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function hideTyping() {
    var el = document.getElementById('ss-typing');
    if (el) el.remove();
  }

  function sendMessage() {
    var input = document.getElementById('ss-input');
    var text = input.value.trim();
    if (!text) return;
    input.value = '';

    var msgs = document.getElementById('ss-msgs');
    msgs.innerHTML += '<div style="background:' + config.primary_color + ';color:#fff;border-radius:8px;padding:10px 12px;margin-bottom:8px;max-width:75%;width:fit-content;margin-left:auto;text-align:right;">' + escapeHtml(text) + '</div>';
    msgs.scrollTop = msgs.scrollHeight;

    document.getElementById('ss-send').disabled = true;
    showTyping();

    var url = baseUrl + '/api/public/chat' + (convId ? '/' + convId : '');
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ widget_id: widgetId, message: text }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        convId = data.conversation_id;
        persistConv(convId);
        hideTyping();
        msgs.innerHTML += '<div style="background:#fff;border-radius:8px;padding:10px 12px;margin-bottom:8px;max-width:75%;width:fit-content;color:#333;">' + escapeHtml(data.reply) + '</div>';
        msgs.scrollTop = msgs.scrollHeight;
      })
      .catch(function () {
        hideTyping();
        msgs.innerHTML += '<div style="background:#fff5f5;color:#c00;border-radius:8px;padding:10px 12px;margin-bottom:8px;max-width:75%;width:fit-content;">Sorry, something went wrong. Try again.</div>';
      })
      .finally(function () {
        document.getElementById('ss-send').disabled = false;
      });
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  container.__open = function () { state = 'open'; render(); };
  container.__close = function () { state = 'closed'; render(); };

  fetch(baseUrl + '/api/widget/config/' + widgetId)
    .then(function (r) {
      if (!r.ok) throw new Error('not found');
      return r.json();
    })
    .then(function (c) {
      config = c;
      state = 'closed';
      render();
    })
    .catch(function () {
      state = 'error';
      render();
    });
})();
