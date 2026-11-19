/* MathJax changes the height of long documents after the theme starts tracking
 * headings. Derive the active contents entry from the current layout so a jump
 * into a long section does not leave an unrelated heading highlighted.
 */
document.addEventListener('DOMContentLoaded', () => {
  const article = document.querySelector('.bd-article');
  const contents = document.querySelector('.bd-sidebar-secondary');
  if (!article?.querySelector('[data-source-math]') || !contents) return;

  const links = [...contents.querySelectorAll('a[href^="#"]')];
  const entries = links.map(link => ({
    link,
    section: document.getElementById(decodeURIComponent(link.hash.slice(1))),
  })).filter(entry => entry.section);
  let scheduled = false;

  function updateCurrentHeading() {
    scheduled = false;
    let current = entries[0];
    for (const entry of entries) {
      if (entry.section.getBoundingClientRect().top <= 110) current = entry;
    }
    if (!current) return;
    for (const node of contents.querySelectorAll('.active')) {
      node.classList.remove('active');
    }
    for (const link of links) link.removeAttribute('aria-current');
    current.link.classList.add('active');
    current.link.setAttribute('aria-current', 'location');
    let item = current.link.closest('li');
    while (item && contents.contains(item)) {
      item.classList.add('active');
      item = item.parentElement.closest('li');
    }
  }

  function scheduleUpdate() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(updateCurrentHeading);
  }

  document.addEventListener('scroll', scheduleUpdate, {capture: true, passive: true});
  window.addEventListener('resize', scheduleUpdate);
  new ResizeObserver(scheduleUpdate).observe(article);
  scheduleUpdate();
});
