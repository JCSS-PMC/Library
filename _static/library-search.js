/* Add work-level results while retaining Sphinx's full-text search below. */
document.addEventListener('DOMContentLoaded', async () => {
  const section = document.getElementById('library-search-results');
  if (!section) return;
  const query = new URLSearchParams(window.location.search).get('q')?.trim();
  if (!query) return;
  const status = document.getElementById('library-search-status');
  const list = document.getElementById('library-search-list');
  section.hidden = false;
  status.textContent = 'Searching library entries…';

  function normalise(value) {
    return value.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();
  }
  function paragraph(text, className) {
    const node = document.createElement('p');
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  try {
    const response = await fetch('_static/library-search-index.json');
    if (!response.ok) throw new Error('Catalogue index unavailable');
    const entries = await response.json();
    const terms = normalise(query).split(/\s+/).filter(Boolean);
    const results = entries.filter(entry => terms.every(term => normalise(entry.search_text).includes(term)));
    // Prefer a title match, then author matches, without changing source titles.
    function score(entry) {
      return terms.reduce((total, term) => total
        + (normalise(entry.title).includes(term) ? 4 : 0)
        + (normalise(entry.authors + ' ' + entry.editors).includes(term) ? 2 : 0), 0);
    }
    results.sort((left, right) => score(right) - score(left) || left.title.localeCompare(right.title));
    status.textContent = `${results.length} library ${results.length === 1 ? 'entry' : 'entries'} found.`;
    for (const entry of results) {
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.href = entry.href;
      link.textContent = entry.title;
      item.append(link);
      const contributors = [entry.authors, entry.editors ? `Editor: ${entry.editors}` : ''].filter(Boolean);
      const date = entry.date ? `${entry.date_kind}: ${entry.date}` : '';
      item.append(paragraph([date, ...contributors, entry.type].filter(Boolean).join(' · ')));
      if (entry.status) item.append(paragraph(entry.status, 'library-search-details'));
      item.append(paragraph(entry.activity, 'library-search-details'));
      const fileLabel = entry.external ? 'Publisher and reference links'
        : `${entry.file_count} ${entry.file_count === 1 ? 'file' : 'files'} (${entry.formats.join(', ')})`;
      item.append(paragraph([entry.has_reader ? 'Reading edition' : '', fileLabel].filter(Boolean).join(' · '), 'library-search-details'));
      list.append(item);
    }
  } catch (error) {
    status.textContent = 'Catalogue search is unavailable. Use the page text matches below.';
  }
});
