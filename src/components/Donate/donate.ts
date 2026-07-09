function initDonate() {
  const btn = document.getElementById('share-btn');
  if (btn) {
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
        toast?.classList.remove('opacity-0');
        setTimeout(() => toast?.classList.add('opacity-0'), 1800);
      }
    });
  }

  document.querySelectorAll<HTMLButtonElement>('[data-open]').forEach((opener) => {
    const id = opener.getAttribute('data-open');
    const dialog = document.getElementById(`donate-${id}`) as HTMLDialogElement | null;
    if (!dialog) return;
    opener.addEventListener('click', () => dialog.showModal());
  });

  document.querySelectorAll<HTMLDialogElement>('dialog.donate-dialog').forEach((dialog) => {
    dialog.querySelector('[data-close]')?.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
}

initDonate();
