# Slow Web

[Open Slow Web](https://coolcode.ca/slowweb/) · [Browse the dated task records](https://coolcode.ca/slowweb/records/)

<!-- coolcode:guide -->
Start with the Alderney ferry timetable to see which date and departure time remained readable with JavaScript off. Compare the Dartmouth archive page with the interactive map, inspect the actual browser evidence and change the assumed line rate to recalculate the transfer estimate.
<!-- /coolcode:guide -->

Slow Web follows everyday tasks on selected public pages from Halifax Transit, CoolCode, Chebucto Community Net, Vancouver Community Network, W3C and NPR. Every homepage result can be read with JavaScript off. The optional browser filters and line-rate selector run locally. The first published collection contains two separate observations on 27 November 2026. Seven tasks were in the first pass and eight in the second. This provides a same-day comparison, not a long-term trend.

## What a receipt measures

A new Chromium context opens one fixed public URL at 390 × 844 with JavaScript and the browser cache disabled and service workers blocked. The observer waits up to 25 seconds for DOMContentLoaded, then up to ten more seconds for load, then 1.2 seconds. It checks rendered text, visible links or the specified control. No credentials, visitor URLs or form submissions are involved. A task is completed only if all its named criteria succeeded. A failed criterion on an available document and an inaccessible document have separate outcomes. A published ferry example has its own service date. Use the source for travel decisions.

The monitor uses Chrome DevTools Protocol Network events on the page target. It sums encodedDataLength for finished HTTP(S) responses and separately reported redirects. These are Chromium’s response-transfer bytes, not disk sizes or decoded DOM lengths. Unfinished and failed responses can have bytes we cannot count. Cross-process child frames have separate network sessions. If there are child frames, outstanding or failed requests, or the page itself could not be assessed, the transfer estimate is withheld. Other hosts are classified by comparing the request hostname with the configured publisher domain and its subdomains. The result reports requested hosts, not the ownership or purpose of their servers.

The launch receipts used a managed HTTPS proxy. Future hosted runners can use direct network access. Browser, route type, date and original URL accompany every receipt. Proxy and upstream cache behavior, browser versions, geographic location and publisher changes may affect the received representation. The line-rate comparison is the formula bytes × 8 ÷ (kb/s × 1,000). It does not time a real connection or include DNS, TCP, TLS, server latency, retransmissions, compression negotiation or browser work. No physical dial-up line, service provided by VCN or Chebucto, vintage browser, or Windows XP machine was tested.

## Refresh and publication

The weekly workflow is scheduled for **Mondays at 10:17 UTC** and can also be dispatched manually. It opens at most three pages at a time and checks the fixed configured set. A separate guard monitors the refresh workflow for inactivity. Each successful collection retains its timestamped JSON edition. Individual unavailable pages are recorded honestly. A systemic outage that leaves every document unavailable stops publication and preserves earlier results.

Run the collector with Python 3.12+ and Playwright Chromium. The browser is only required for collection and browser tests. The static build uses only the Python standard library.

```sh
python -m pip install -r tests/browser-requirements.txt
python -m playwright install chromium
python scripts/measure.py
python scripts/build.py
python -m unittest discover -s tests -v
node --test tests/*.test.mjs
python tests/browser_smoke.py
```

Set CHROMIUM_PATH to an existing compatible executable if available. A managed collection runner can set SLOWWEB_PROXY and optionally SLOWWEB_TRUSTED_SPKI to its previously trusted network certificate public-key pins. The default GitHub workflow uses ordinary certificate validation. The receipt records the access path.

The site publishes a permanent subject profile and a timestamped task receipt under records/ for each observed visit, plus a machine-readable JSON edition and status probe. The site preserves older editions if the current set of tasks changes. The same offline build runs on a source change and after a successful scheduled refresh. A failed test does not deploy new pages.

## Expand or customize

Edit **config/subjects.json** to add a reviewed public subject, its stable ID, task, publisher domain, HTTPS URL, notes and concrete success criteria. Each check may supply a CSS selector and a case-insensitive text pattern. A stable short public fact such as a date may opt into show_match; other criteria retain only their labels and pass/fail results. The optional select action identifies a single control and its intended value. Keep captures bounded and the task narrow enough to answer with visible evidence. A newly added task first appears when it has a real observation. To change the collection frequency, change the workflow cron, documented cadence and hub freshness registration together. Retain existing source records.

The source repository is jsdyer/slowweb-. Its checks build the full static site. The CoolCode hub serves the built site at /slowweb/ and supplies the canonical result URLs. The repository’s Pages deployment stays inactive while its name differs from the native slug.
