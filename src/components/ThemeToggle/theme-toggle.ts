const KEY = 'kg-theme';
const THEME_COLOR = { light: '#F5F3EE', dark: '#17181E' } as const;
type Theme = keyof typeof THEME_COLOR;

const button = document.getElementById('theme-toggle') as HTMLButtonElement | null;
const system = window.matchMedia('(prefers-color-scheme: dark)');
const root = document.documentElement;

const current = (): Theme => (root.dataset.theme === 'dark' ? 'dark' : 'light');

// Storage can throw in private windows; the choice then lasts for this page.
function stored(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function apply(theme: Theme) {
  root.dataset.theme = theme;
  document.querySelector<HTMLMetaElement>('meta[name="theme-color"]')!.content = THEME_COLOR[theme];
  if (!button) return;
  const label = theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
  button.setAttribute('aria-label', label);
  button.title = label;
}

apply(current());

if (button) {
  button.hidden = false;
  button.addEventListener('click', () => {
    const next: Theme = current() === 'dark' ? 'light' : 'dark';
    apply(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // Nothing to keep it in: the switch still holds until the next page.
    }
  });
}

// Until the visitor chooses, keep following the system (sunset schedules).
system.addEventListener('change', (event) => {
  if (!stored()) apply(event.matches ? 'dark' : 'light');
});

// A choice made in another tab applies here too.
window.addEventListener('storage', (event) => {
  if (event.key === KEY && (event.newValue === 'dark' || event.newValue === 'light')) apply(event.newValue);
});
