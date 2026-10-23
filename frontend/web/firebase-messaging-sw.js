// Shows EchoSphere push notifications when the site is in the background or closed (Firebase Cloud Messaging).
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

firebase.initializeApp({
  "apiKey": "AIzaSyBJIPMXz1aEdpMcRJObrQ8ur_VYxrhVvKI",
  "authDomain": "echosphere-3bcc0.firebaseapp.com",
  "projectId": "echosphere-3bcc0",
  "storageBucket": "echosphere-3bcc0.firebasestorage.app",
  "messagingSenderId": "808301080990",
  "appId": "1:808301080990:web:9e3dbcb7e26f0937c1268f"
});

const messaging = firebase.messaging();

// Notifications with a title/body are shown by the browser itself; data-only messages are shown here.
messaging.onBackgroundMessage((payload) => {
  if (payload.notification) return;
  const data = payload.data || {};
  self.registration.showNotification(data.title || 'EchoSphere', {
    body: data.body || '',
    icon: '/icons/Icon-192.png',
    data,
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const id = (event.notification.data || {}).announcement_id;
  event.waitUntil(clients.openWindow(id ? `/announcement?id=${id}` : '/'));
});
