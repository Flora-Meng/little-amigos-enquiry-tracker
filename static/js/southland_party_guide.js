(() => {
  const packageTabs = [...document.querySelectorAll('[data-package-tab]')];
  const packagePanels = [...document.querySelectorAll('[data-package-panel]')];
  const foodPanels = [...document.querySelectorAll('[data-food-panel]')];

  function showPackage(key, scroll = false) {
    packageTabs.forEach(tab => {
      const active = tab.dataset.packageTab === key;
      tab.classList.toggle('is-active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    packagePanels.forEach(panel => { panel.hidden = panel.dataset.packagePanel !== key; });
    foodPanels.forEach(panel => { panel.hidden = panel.dataset.foodPanel !== key; });
    if (scroll) document.querySelector('#packages')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  packageTabs.forEach(tab => tab.addEventListener('click', () => showPackage(tab.dataset.packageTab)));

  const recommender = document.querySelector('[data-room-recommender]');
  const kidsInput = recommender?.querySelector('[data-kids-count]');
  const result = recommender?.querySelector('[data-recommendation-result]');
  const recommendations = [
    { max: 8, key: 'essential', room: 'Single room', range: '1–8 children' },
    { max: 15, key: 'signature', room: 'Double room', range: '9–15 children' },
    { max: 25, key: 'ultimate', room: 'Triple room', range: '16–25 children' },
    { max: Infinity, key: 'private', room: 'Private party', range: '26 or more children' },
  ];

  kidsInput?.addEventListener('input', () => {
    const count = Number.parseInt(kidsInput.value, 10);
    if (!Number.isFinite(count) || count < 1) {
      result.classList.remove('is-ready');
      result.querySelector('small').textContent = 'Our guide';
      result.querySelector('strong').textContent = '1–8 Single · 9–15 Double · 16–25 Triple · 26+ Private';
      result.querySelector('p').textContent = 'Enter a number and we’ll highlight your recommended package below.';
      return;
    }
    const recommendation = recommendations.find(item => count <= item.max);
    result.classList.add('is-ready');
    result.querySelector('small').textContent = `Recommended for ${count} ${count === 1 ? 'child' : 'children'}`;
    result.querySelector('strong').textContent = recommendation.room;
    result.querySelector('p').textContent = `${recommendation.range}. We’ll still confirm the final room and availability with you.`;
    showPackage(recommendation.key);
  });

  const catalog = document.querySelector('[data-theme-catalog]');
  if (catalog) {
    const cards = [...catalog.querySelectorAll('[data-theme-card]')];
    const search = catalog.querySelector('[data-theme-search]');
    const filters = [...catalog.querySelectorAll('[data-theme-filter]')];
    const empty = catalog.querySelector('[data-theme-empty]');
    let category = 'all';

    function filterThemes() {
      const query = search.value.trim().toLocaleLowerCase();
      let visible = 0;
      cards.forEach(card => {
        const matchesCategory = category === 'all' || card.dataset.category === category;
        const matchesSearch = !query || card.dataset.name.toLocaleLowerCase().includes(query);
        card.hidden = !(matchesCategory && matchesSearch);
        if (!card.hidden) visible += 1;
      });
      empty.hidden = visible !== 0;
    }

    filters.forEach(button => button.addEventListener('click', () => {
      category = button.dataset.themeFilter;
      filters.forEach(item => {
        const active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', String(active));
      });
      filterThemes();
    }));
    search.addEventListener('input', filterThemes);

    cards.forEach(card => card.addEventListener('click', () => {
      catalog.querySelector(`[data-theme-dialog="${card.dataset.themeOpen}"]`)?.showModal();
    }));
    catalog.querySelectorAll('[data-theme-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
    catalog.querySelectorAll('dialog').forEach(dialog => dialog.addEventListener('click', event => {
      if (event.target === dialog) dialog.close();
    }));
  }

  const addonBuilder = document.querySelector('[data-addon-builder]');
  if (addonBuilder) {
    const choices = [...addonBuilder.querySelectorAll('[data-addon-choice]')];
    const summary = addonBuilder.querySelector('[data-addon-summary]');
    const total = addonBuilder.querySelector('[data-addon-total]');
    choices.forEach(choice => choice.addEventListener('change', () => {
      const selected = choices.filter(item => item.checked);
      const amount = selected.reduce((sum, item) => sum + Number(item.dataset.price || 0), 0);
      summary.textContent = selected.length ? selected.map(item => item.dataset.addonName).join(', ') : 'No add-ons selected yet';
      total.textContent = `$${amount.toLocaleString('en-AU', { maximumFractionDigits: 0 })}+`;
    }));
  }
})();
