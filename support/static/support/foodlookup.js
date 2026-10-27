(function () {
    'use strict';

    var box = document.getElementById('lookup');
    if (!box) return;
    var q = document.getElementById('lookup-q');
    var grams = document.getElementById('lookup-grams');
    var btn = document.getElementById('lookup-btn');
    var note = document.getElementById('lookup-note');
    var list = document.getElementById('lookup-results');

    function field(name) { return document.getElementById('id_' + name); }
    function round(n) { return Math.round(n); }

    function fill(food) {
        var g = Math.max(1, parseFloat(grams.value) || 100);
        var factor = g / 100;
        var label = food.name + ' (' + g + ' g)';
        field('name').value = label.slice(0, 120);
        field('calories').value = round(food.calories * factor);
        field('protein').value = round(food.protein * factor);
        field('carbs').value = round(food.carbs * factor);
        field('fat').value = round(food.fat * factor);
        note.textContent = 'Filled in for ' + g + ' g. Adjust any value before adding the meal.';
        field('name').focus();
    }

    function show(data) {
        list.textContent = '';
        if (!data.results || !data.results.length) {
            note.textContent = 'No matches. Try another word, or enter the calories yourself.';
            return;
        }
        note.textContent = data.source === 'openfoodfacts'
            ? 'Results from Open Food Facts (values per 100 g, scaled to your portion).'
            : 'Open Food Facts did not answer in time (KILO-2001), so these come from KILO’s built-in list of common foods.';
        data.results.forEach(function (food) {
            var li = document.createElement('li');
            var b = document.createElement('button');
            b.type = 'button';
            var name = document.createElement('span');
            name.textContent = food.name;
            var kcal = document.createElement('span');
            kcal.className = 'kcal';
            kcal.textContent = round(food.calories) + ' kcal / 100 g';
            b.appendChild(name);
            b.appendChild(kcal);
            b.addEventListener('click', function () { fill(food); });
            li.appendChild(b);
            list.appendChild(li);
        });
    }

    function search() {
        var term = q.value.trim();
        if (term.length < 2) { note.textContent = 'Type at least 2 characters.'; return; }
        btn.disabled = true;
        note.textContent = 'Searching…';
        list.textContent = '';
        fetch(box.dataset.url + '?q=' + encodeURIComponent(term), { credentials: 'same-origin' })
            .then(function (res) { return res.json().then(function (body) { return { ok: res.ok, body: body }; }); })
            .then(function (r) {
                if (r.ok) show(r.body);
                else note.textContent = (r.body.error || 'Lookup failed.') + (r.body.code ? ' (' + r.body.code + ')' : '');
            })
            .catch(function () { note.textContent = 'Could not reach the server. Try again.'; })
            .then(function () { btn.disabled = false; });
    }

    btn.addEventListener('click', search);
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); search(); } });
})();
