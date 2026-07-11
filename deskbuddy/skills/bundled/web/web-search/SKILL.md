---
name: web-search
description: Open the browser and search the web for something the user asked about.
triggers: [search, google, look up, look it up, find online, search the web]
---
# Web search

When the user wants something looked up online:

1. Call `open_app` with a browser command (`firefox`, or `google-chrome`,
   `brave-browser` — try firefox first).
2. Give the window a moment to focus.
3. Use `type_text` to type the search into the address bar. A reliable phrasing:
   type the full search URL directly, e.g.
   `https://www.google.com/search?q=YOUR+QUERY+HERE` (spaces become `+`).
4. Call `press_key` with `Return` to go.
5. Tell the user out loud what you searched for — keep it to one sentence.

If `type_text`/`press_key` report the input provider is unavailable (common on
Wayland), tell the user briefly that hands-off typing needs an Xorg session, and
offer to just open the browser to the results URL via `open_app` instead:
`open_app "firefox https://www.google.com/search?q=YOUR+QUERY"`.
