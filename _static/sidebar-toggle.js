/* The PMC book header and its base theme both supply a contents button.
 * The base theme binds its drawer to the first button. Forward the additional
 * header button to that existing control, retaining the theme's focus handling.
 */
document.addEventListener('DOMContentLoaded', () => {
  const contentsButtons = [...document.querySelectorAll('.secondary-toggle')];
  const drawerButton = contentsButtons[0];
  for (const headerButton of contentsButtons.slice(1)) {
    headerButton.addEventListener('click', () => drawerButton.click());
  }
});
