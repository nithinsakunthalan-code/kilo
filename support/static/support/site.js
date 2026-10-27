(function () {
    'use strict';
    var btn = document.getElementById('menu-btn');
    var nav = document.getElementById('nav');
    if (!btn || !nav) return;
    btn.addEventListener('click', function () {
        var open = nav.classList.toggle('open');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
})();
