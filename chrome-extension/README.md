# Little Amigos Enquiry Importer

Private Manifest V3 Chrome extension for selectively importing Zumo
conversations into the Little Amigos Enquiry Tracker.

## 1. Create a revocable Tracker token

1. Sign in to the Tracker as Flora.
2. Open **Zumo → Extension connection**.
3. Select **Create one-time token**.
4. Keep the page open until the token has been pasted into Chrome. The full
   token is displayed only once; the Tracker stores only its SHA-256 hash.

For local development the settings page is:

```text
http://127.0.0.1:8000/zumo-imports/extension/
```

## 2. Load the extension privately

1. Open `chrome://extensions` in Chrome.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Choose this `chrome-extension` directory.
5. Pin **Little Amigos Enquiry Importer** to the toolbar.

This extension is private and is not intended for the Chrome Web Store.

## 3. Connect it to the Tracker

1. Select the extension toolbar icon.
2. Enter the Tracker URL. For local development use:

   ```text
   http://127.0.0.1:8000
   ```

3. Paste the one-time extension token.
4. Select **Save and test** and approve access to that Tracker host.

Use an HTTPS Tracker URL in production.

## 4. Review a Zumo conversation

1. Open a conversation under `https://app.zumocrm.com/`.
2. Select the coral **LA** button at the bottom-right.
3. Confirm the detected conversation status.
4. Review the visible-message snapshot and all parsed fields.
5. Correct any parsing or routing issue before selecting **Add to Tracker** or
   **Ignore**.
6. If duplicate matches appear, open them and review before selecting
   **Create anyway**.

An ignored conversation can be reopened with **Review again**. An imported
conversation links to its existing Tracker enquiry and is never silently
created again.

## Security and maintenance

- The Tracker password is never stored in the extension.
- Revoke a lost or unused token from **Zumo → Extension connection**.
- Permanent host access is limited to `https://app.zumocrm.com/*`.
- Tracker host access is requested only for the URL entered in settings.
- Cross-origin requests run in the extension service worker.
- The extension never connects directly to the database.
- Zumo-specific DOM selectors are isolated in `extractor.js`.
- No remotely hosted JavaScript is used.

## Troubleshooting

- **Extension not configured**: open the toolbar icon and save the Tracker URL
  and token.
- **Token missing, invalid or revoked**: create a new token in the Tracker and
  replace the saved token.
- **No matching Zumo message element found**: paste the visible enquiry message
  into the extension preview. Update `extractor.js` if Zumo has changed its DOM.
- **Local Tracker cannot connect**: confirm the Django development server is
  running at `127.0.0.1:8000`.
