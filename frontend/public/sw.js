self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { body: event.data?.text() };
  }
  event.waitUntil(self.registration.showNotification(data.title || 'VALSHOP', {
    body: data.body || 'A wishlist skin is available.',
    icon: '/favicon-v3.png',
    badge: '/favicon-v3.png',
    image: data.image || undefined,
    tag: data.tag || 'valshop-wishlist',
    renotify: true,
    actions: [{ action: 'open-shop', title: 'Open shop' }],
    data: { url: data.url || '/shop' },
  }));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  let destination = `${self.location.origin}/shop`;
  try {
    const requested = new URL(event.notification.data.url || '/shop', self.location.origin);
    if (requested.origin === self.location.origin) destination = requested.href;
  } catch {
    // Keep the safe shop fallback for malformed notification data.
  }
  event.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
    const existing = windows.find((client) => client.url.startsWith(self.location.origin));
    if (existing) return existing.navigate(destination).then(() => existing.focus());
    return clients.openWindow(destination);
  }));
});
