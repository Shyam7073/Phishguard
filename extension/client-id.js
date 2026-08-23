// Per-install ID: generated once, stored in chrome.storage.local, sent with
// every /scan call so the backend can keep each install's history separate.
// This is identification, not authentication -- clearing extension storage
// or reinstalling generates a new ID and orphans the old history.

const CLIENT_ID_KEY = "phishguard_client_id";

async function getOrCreateClientId() {
  const stored = await chrome.storage.local.get(CLIENT_ID_KEY);
  if (stored[CLIENT_ID_KEY]) {
    return stored[CLIENT_ID_KEY];
  }
  const clientId = crypto.randomUUID();
  await chrome.storage.local.set({ [CLIENT_ID_KEY]: clientId });
  return clientId;
}
