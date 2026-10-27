(function () {
    'use strict';

    var root = document.getElementById('chat');
    if (!root) return;

    var panel = document.getElementById('chat-panel');
    var toggle = document.getElementById('chat-toggle');
    var closeBtn = document.getElementById('chat-close');
    var log = document.getElementById('chat-log');
    var form = document.getElementById('chat-form');
    var input = document.getElementById('chat-input');
    var suggestionsBox = document.getElementById('chat-suggestions');
    var csrf = (form.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';

    function safeGet(store, key) { try { return store.getItem(key); } catch (e) { return null; } }
    function safeSet(store, key, value) { try { store.setItem(key, value); } catch (e) { /* private mode */ } }

    var sessionId = safeGet(localStorage, 'chat_session');
    if (!sessionId) {
        sessionId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2);
        safeSet(localStorage, 'chat_session', sessionId);
    }

    var history = [];
    try { history = JSON.parse(safeGet(sessionStorage, 'chat_history') || '[]'); } catch (e) { history = []; }
    function saveHistory() { safeSet(sessionStorage, 'chat_history', JSON.stringify(history.slice(-40))); }

    // ---------- panel open / close ----------
    function setOpen(open) {
        panel.hidden = !open;
        root.classList.toggle('open', open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        safeSet(sessionStorage, 'chat_open', open ? '1' : '0');
        if (open) { input.focus(); scrollDown(); }
    }
    toggle.addEventListener('click', function () { setOpen(panel.hidden); });
    closeBtn.addEventListener('click', function () { setOpen(false); toggle.focus(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) setOpen(false); });

    function scrollDown() { log.scrollTop = log.scrollHeight; }

    // ---------- rendering (always textContent: no HTML injection) ----------
    function bubble(role, text) {
        var el = document.createElement('div');
        el.className = 'msg ' + role;
        el.textContent = text;
        log.appendChild(el);
        scrollDown();
        return el;
    }

    function addFeedback(el, entry) {
        var bar = document.createElement('div');
        bar.className = 'msg-actions';
        [['up', 'Helpful'], ['down', 'Not helpful']].forEach(function (pair) {
            var b = document.createElement('button');
            b.type = 'button';
            b.textContent = pair[1];
            b.addEventListener('click', function () {
                post(root.dataset.feedbackUrl, { session_id: sessionId, message_id: entry.id, rating: pair[0] })
                    .then(function () { bar.textContent = 'Thanks for the feedback.'; });
            });
            bar.appendChild(b);
        });
        el.appendChild(bar);
    }

    function addTicketForm(el, entry) {
        var f = document.createElement('form');
        f.className = 'ticket-form';
        var i = document.createElement('input');
        i.type = 'email'; i.placeholder = 'you@example.com'; i.required = true; i.setAttribute('aria-label', 'Your email');
        var b = document.createElement('button');
        b.type = 'submit'; b.textContent = 'Save email';
        f.appendChild(i); f.appendChild(b);
        f.addEventListener('submit', function (e) {
            e.preventDefault();
            post(root.dataset.emailUrl, { session_id: sessionId, reference: entry.ticket, email: i.value })
                .then(function (r) { f.textContent = r.ok ? 'Saved. We will reply to ' + i.value + '.' : 'Could not save that email.'; });
        });
        el.appendChild(f);
    }

    function renderEntry(entry, live) {
        var el = bubble(entry.role, entry.text);
        if (entry.role === 'bot' && live) {
            if (entry.id) addFeedback(el, entry);
            if (entry.ticket) addTicketForm(el, entry);
        }
    }

    function renderSuggestions(list) {
        suggestionsBox.textContent = '';
        (list || []).forEach(function (text) {
            var b = document.createElement('button');
            b.type = 'button'; b.className = 'chip'; b.textContent = text;
            b.addEventListener('click', function () { send(text); });
            suggestionsBox.appendChild(b);
        });
    }

    // ---------- network ----------
    function post(url, data) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        }).then(function (res) {
            return res.json().catch(function () { return {}; }).then(function (body) {
                body.ok = res.ok; body.status = res.status; return body;
            });
        });
    }

    var busy = false;
    function send(text) {
        text = (text || '').trim();
        if (!text || busy) return;
        busy = true;
        renderSuggestions([]);
        history.push({ role: 'user', text: text });
        bubble('user', text);
        var typing = bubble('bot typing', 'Thinking…');

        post(root.dataset.url, { message: text, session_id: sessionId })
            .then(function (r) {
                typing.remove();
                var entry;
                if (r.ok) {
                    entry = { role: 'bot', text: r.reply, id: r.message_id, ticket: r.ticket };
                    renderSuggestions(r.suggestions);
                } else if (r.status === 429) {
                    entry = { role: 'bot', text: 'You are sending messages too fast (error 429). Please wait a minute and try again.' };
                } else if (r.error) {
                    entry = { role: 'bot', text: r.error + (r.code ? ' (' + r.code + ')' : '') };
                } else {
                    entry = { role: 'bot', text: 'Something went wrong (error ' + r.status + '). Please try again.' };
                }
                history.push({ role: 'bot', text: entry.text });
                renderEntry(entry, true);
            })
            .catch(function () {
                typing.remove();
                var text = 'I could not reach the server. Check your connection and try again.';
                history.push({ role: 'bot', text: text });
                bubble('bot', text);
            })
            .then(function () { busy = false; saveHistory(); input.focus(); });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = input.value;
        input.value = '';
        send(text);
    });

    // Any element with data-ask opens the assistant (and sends its text, if any).
    document.addEventListener('click', function (e) {
        var trigger = e.target.closest('[data-ask]');
        if (!trigger) return;
        e.preventDefault();
        setOpen(true);
        var text = trigger.getAttribute('data-ask');
        if (text) send(text);
    });

    // ---------- restore previous conversation ----------
    if (history.length) {
        history.forEach(function (h) { renderEntry(h, false); });
    } else {
        renderEntry({ role: 'bot', text: 'Hi! Ask me how KILO works, or paste an error code like 404 or 429 and I will explain it.' }, false);
        renderSuggestions(['How do I log a meal?', 'What does error 404 mean?', 'How are remaining calories calculated?']);
    }
    if (safeGet(sessionStorage, 'chat_open') === '1') setOpen(true);
})();
