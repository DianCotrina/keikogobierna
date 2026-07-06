export function initDonate() {
  const btn = document.getElementById('share-btn');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const data = { title: document.title, url: location.href };
    if (navigator.share) {
      try { await navigator.share(data); } catch {}
    } else {
      try {
        await navigator.clipboard.writeText(location.href);
      } catch {
        return;
      }
      const toast = document.getElementById('share-toast');
      toast.classList.remove('opacity-0');
      setTimeout(() => toast.classList.add('opacity-0'), 1800);
    }
  });
}
