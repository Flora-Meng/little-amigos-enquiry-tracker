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
    const optionChoices = [...addonBuilder.querySelectorAll('[data-addon-option]')];
    const quantityChoices = [...addonBuilder.querySelectorAll('[data-addon-quantity]')];
    const allInputs = [...addonBuilder.querySelectorAll('input')];
    const summary = addonBuilder.querySelector('[data-addon-summary]');
    const total = addonBuilder.querySelector('[data-addon-total]');

    function updateAddons() {
      const selected = optionChoices.filter(item => item.checked);
      const selections = selected.map(item => ({
        name: item.dataset.addonName,
        amount: Number(item.dataset.price || 0),
      }));

      quantityChoices.forEach(input => {
        const quantity = Math.max(0, Number.parseInt(input.value, 10) || 0);
        input.value = String(quantity);
        if (quantity) {
          selections.push({
            name: `${input.dataset.addonName} × ${quantity}`,
            amount: quantity * Number(input.dataset.unitPrice || 0),
          });
        }
      });

      addonBuilder.querySelectorAll('[data-addon-card]').forEach(card => {
        const selectedOption = card.querySelector('[data-addon-option]:checked');
        const quantity = Number.parseInt(card.querySelector('[data-addon-quantity]')?.value || '0', 10);
        card.classList.toggle('is-selected', Boolean(selectedOption || quantity > 0));
      });

      const amount = selections.reduce((sum, item) => sum + item.amount, 0);
      summary.textContent = selections.length ? selections.map(item => item.name).join(', ') : 'No add-ons selected yet';
      total.textContent = `$${amount.toLocaleString('en-AU', { maximumFractionDigits: 0 })}`;
    }

    allInputs.forEach(input => {
      input.addEventListener('change', updateAddons);
      input.addEventListener('input', updateAddons);
    });
    updateAddons();
  }
})();
