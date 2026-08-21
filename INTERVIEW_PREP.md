# PhishGuard — Interview Revision Guide (Beginner-Friendly)

Personal study doc, not for the public repo README. Written assuming you're
new to ML, cybersecurity, and dev in general — every term is explained the
first time it shows up, so you shouldn't need to look anything up while
revising from this file.

---

## 0. Basic vocabulary — read this first

A handful of words come up constantly below. Once these click, everything
else in this doc is easy.

- **Phishing**: a fake website pretending to be a real one (a fake PayPal
  login page, for example) to trick someone into typing a password or
  card number.
- **URL**: the web address, e.g. `https://www.google.com/search?q=hello`.
  It has parts: `https` (scheme), `www.google.com` (hostname/domain),
  `/search` (path), `?q=hello` (query string — extra info after `?`).
- **Feature** (in ML): one measurable property of something you're trying
  to classify. Here, a "feature" is one fact about a URL, e.g. "how many
  characters long is it" or "does it contain an `@` symbol." A model
  looks at a bunch of these to make a decision.
- **Model / training**: a model is a program that learns a pattern from
  examples instead of being told exact rules. "Training" = showing it
  thousands of URLs we already know are phishing or legit, so it learns
  which feature combinations tend to mean phishing.
- **Dataset**: the big pile of example URLs (with correct answers
  attached) used to train the model.
- **Accuracy / Precision / Recall / F1** — four different ways to grade
  how good a model is:
  - **Accuracy**: out of everything, what % did it get right?
  - **Precision**: of everything it *called* phishing, what % actually
    was phishing? (High precision = few false alarms.)
  - **Recall**: of everything that *was actually* phishing, what % did it
    catch? (High recall = doesn't miss real threats.)
  - **F1**: one combined number balancing precision and recall, so you
    don't have to look at two numbers separately. Used to pick a "winner"
    when comparing models.
- **API / endpoint**: a URL that a program (not a human in a browser)
  calls to ask a server to do something and get an answer back, e.g.
  `POST /scan` — "here's a URL, tell me if it's phishing."
- **Backend**: the server-side program that does the actual work (runs
  the ML model, talks to the database). The extension and dashboard are
  just "front doors" that call the backend.
- **Blocklist**: a public, shared list of "known-bad" URLs that security
  companies maintain. If a URL is on the list, it's confirmed malicious —
  not a guess.
- **Domain age**: how long ago a website's address (domain) was first
  registered. Old, well-known domains (`google.com`) are almost never
  fresh phishing sites; brand-new domains are used far more often for
  scams because attackers throw them away after a short campaign.
- **Cache**: temporarily remembering an answer you already looked up, so
  you don't have to redo the same slow work again immediately after.
- **Unit test**: a small, automatic check that verifies one specific piece
  of code does what it's supposed to — see §9 for more detail with real
  examples from this project.

---

## 1. The 30-second pitch (say this first in an interview)

"PhishGuard is a phishing URL detector. A Chrome extension watches every
page you visit and sends the URL to my backend. The backend combines
three separate signals into one plain-English verdict, instead of just a
raw number: (1) a machine learning model that looks at the URL's text and
structure, (2) a live check against a public blocklist of known-malicious
URLs, and (3) a live check of how old the website's domain is. Results are
saved and shown in a dashboard I built. I designed and built every part of
this myself — the training data, the ML model, the backend, the browser
extension, and the dashboard — and along the way I found and fixed several
real bugs where the model was wrong, by actually diagnosing *why*, not
just guessing and retraining."

---

## 2. How the whole system fits together

```
Chrome Extension (watches your browsing)
        │  sends the URL you just visited
        ▼
   POST /scan  (an API call to my backend)
        │
        ▼
   FastAPI Backend  ──────┬────────────────┬───────────────
        │                 │                │
        ▼                 ▼                ▼
   ML model          Blocklist check   Domain-age check
   (my own code,     (URLhaus —        (RDAP — a public
   trained by me)    a public          registry lookup)
                      security list)
        │                 │                │
        └────────┬────────┴────────────────┘
                 ▼
         Combine into one verdict
         ("phishing" or "safe", plus a reason)
                 │
                 ▼
         Save to a database
                 │
                 ▼
      Shown in the React dashboard (a website you look at)
```

**Four separate pieces of code, each with one job:**
- **`ml/`** — offline only. This is where I build the training dataset,
  turn URLs into features, and train the model. This code never runs
  while someone is actually using the extension — it only runs when *I*
  decide to retrain.
- **`backend/`** — the server. Loads the already-trained model once,
  and for every scan: turns the URL into features, runs the model,
  checks the blocklist, checks domain age, combines all three into one
  answer, saves it, and sends the answer back.
- **`extension/`** — runs inside Chrome. Watches what pages you visit and
  calls the backend. Doesn't do any thinking itself — it just displays
  whatever the backend says.
- **`dashboard/`** — a webpage (not part of Chrome) that shows a history
  of everything that's been scanned, some simple stats, and a button to
  export everything to a spreadsheet (CSV) file.

**One important design decision, explained simply**: the exact same
piece of code that turns a URL into "features" (`ml/features.py`) is used
both when I train the model *and* when the backend uses it live. If these
were two separate copies of similar-looking code, they could quietly
drift apart over time, and the model would end up being fed different
information live than what it was trained on — a very common, very
confusing bug in real ML systems. Using one shared file makes that bug
structurally impossible here.

---

## 3. Tech choices, explained simply

| What I used | What it is, in plain terms | Why I picked it |
|---|---|---|
| **FastAPI** | A Python tool for building a backend server/API quickly | It supports handling multiple slow network calls (blocklist + domain-age checks) without freezing up, and automatically checks incoming requests are well-formed |
| **XGBoost** | An ML algorithm that builds many small decision trees and combines their votes | Explained in detail in §7 — I compared 3 algorithms and this one held up best on real test cases |
| **SQLite** | A simple, file-based database (no separate server needed) | This project runs on one computer for one person — a heavier database (like Postgres) would be overkill |
| **Manifest V3** | The current required format for Chrome extensions | Older formats are deprecated by Google; this is what any new extension has to use today |
| **React + Tailwind** | React: a JS library for building interactive webpages. Tailwind: a way of styling pages using small utility classes instead of writing custom CSS | Standard, well-documented choice for a small dashboard; didn't need anything fancier |
| **URLhaus** (over a competitor called VirusTotal) | Both are public malicious-URL blocklists | VirusTotal's free plan only allows ~4 lookups/minute — too slow for scanning every page you browse. URLhaus doesn't have that limit |
| **RDAP** (over classic WHOIS) | Both let you look up "who registered this domain and when" | RDAP gives a clean, consistent, structured answer (like a form with labeled fields). Classic WHOIS gives back a big blob of plain text that's formatted differently by every provider — much harder to reliably read a date out of |
| **No Docker, no cloud deployment** | Docker = a way to package an app so it runs identically anywhere; deployment = putting it on the internet | Deliberately skipped — the goal of this project is to fully understand and explain every piece myself, not to prove I can package/deploy software |

---

## 4. The ML model, explained from scratch

**The dataset**: 130,000 example URLs, half labeled "legitimate," half
labeled "phishing." The legitimate ones came from Tranco (a public list of
the internet's most-visited domains). The phishing ones came from
PhishTank (a public list of confirmed phishing URLs that people have
reported). I always split off 20% of this as a "test set" the model never
trains on, so I can check honestly how well it does on URLs it's never
seen before.

**Why I didn't use a "smarter"-sounding approach (like reading the URL
character-by-character with a neural network)**: I used 17 simple,
countable facts about the URL instead (see below). This makes the model
extremely fast (no waiting), and — importantly for an interview — every
single decision it makes can be explained in plain English by pointing
at one of these facts. A more complex model might score similarly but
would be much harder for me to explain confidently.

**The 17 features** (all just facts you can read directly off the URL
text — no internet lookup needed, so this part is instant):
- **How long things are**: total URL length, hostname length, path length
- **How many of certain characters appear**: dots, hyphens, underscores,
  slashes, digits, "other" special characters, and `digit_ratio` (what
  fraction of the URL is digits)
- **Structure**: how many subdomains (e.g. `mail.google.com` has one:
  `mail`), how many `?key=value` query parameters
- **Red-flag checks**: is the hostname a raw IP address instead of a
  name? does it contain an `@` symbol (a classic trick to hide the real
  destination)? is it using HTTPS? does it contain a suspicious word like
  "login"/"verify"/"secure"? is it a known link-shortener like `bit.ly`?

**Comparing models — how I picked the algorithm**: I always train three
different algorithms on the same data and compare them:
- **Logistic Regression** — the simplest one, draws basically one
  straight-line-style boundary between "legit" and "phishing."
- **Random Forest** — builds many decision trees on random subsets of
  the data and lets them vote.
- **XGBoost** — also builds many decision trees, but each new tree is
  built specifically to fix the mistakes of the trees before it.

**Current scores** (see `ml/MODEL_REPORT.md` for the live numbers):

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 76.4% | 75.5% | 78.1% | 0.768 |
| Random Forest | 91.8% | 92.8% | 90.6% | **0.917** |
| XGBoost (the one I ship) | 91.8% | 93.1% | 90.3% | 0.916 |

Random Forest actually has a very slightly higher F1 score here — I still
ship XGBoost anyway. §7 explains exactly why that's not a contradiction.

**Why did my accuracy go DOWN over time, from an early 96.5%?** This is
one of the best stories in this whole project, and it sounds bad until
you understand it: every time the number dropped, it was because I'd
just *removed* a hidden flaw in my training data that was making the
model look better than it really was. A model scoring "too well" should
make you suspicious, not proud — see §8 for exactly how this played out,
multiple times.

---

## 5. Combining three signals into one verdict

`backend/app/verdict.py` is the piece of code that takes all three
signals and decides the final answer. Here's the plain-English logic, in
priority order:

1. **If the blocklist (URLhaus) confirms this exact URL is known-bad** →
   the verdict is phishing, full stop, no matter what the ML model or
   domain age say. This isn't a guess — someone has already confirmed it.
2. **Otherwise, the ML model's score decides the starting answer**
   (50%+ phishing-probability → call it phishing).
3. **If the domain is old and well-established** (registered ≥365 days
   ago) **and** the ML model's phishing score was *borderline* (under
   90%, not overwhelming) → flip the verdict to legitimate. This is
   exactly what fixed real false positives like `github.com/anthropics`
   getting flagged — GitHub itself is a 19-year-old, completely
   legitimate domain, the ML model just got confused by an unusual-
   looking path on it.
4. **If the domain is brand new** (<30 days old) but the ML model already
   said "legitimate" → I do **not** automatically flip this to phishing.
   I just add a note about it. New domains are common for genuinely new,
   harmless websites too (someone's personal blog, a new startup) — I
   didn't want to invent a new class of false alarms I hadn't actually
   tested.

**Why the asymmetry (point 3 can override, but point 4 can't)?** A
*positive*, confirmed piece of evidence (definitely old, definitely on a
blocklist) is trustworthy enough to override a guess. The *absence* of
evidence, or a weak hint (just "it's new"), isn't strong enough on its
own to override a different guess — that would risk trading one kind of
mistake for a different, unproven kind of mistake.

**Why doesn't an old domain get a free pass even at very high phishing
scores?** Because a domain being old doesn't mean it can never host
phishing — it could have been hacked, or an attacker could have
deliberately bought and "aged" an old domain to look trustworthy. So the
old-domain rescue only kicks in for *borderline* calls, not for cases
where the model is already extremely confident.

---

## 6. Why I added caching (and what that actually means)

Two of my three signals (blocklist check, domain-age check) require
actually reaching out over the internet, which is slow and, for the
domain-age one, can even hit rate limits (the provider getting annoyed if
you ask too often). The same website commonly gets scanned more than
once in a short time — reloading a page, or the extension's background
watcher and its popup both scanning the same tab.

So I added a small cache: basically a sticky-note system. The first time
I look something up, I write down the answer with an expiry time. Next
time the same question comes up, I check if my sticky note is still
"fresh" — if yes, I reuse it instead of asking again over the internet.

I use **different expiry times for the two signals**, because they
change at very different speeds:
- **Blocklist status**: expires after 15 minutes. Blocklists get updated
  constantly — a URL that's clean right now could get reported as
  malicious an hour from now, so I don't want to trust an old answer too
  long.
- **Domain age**: expires after 24 hours. A domain's registration date
  never changes — `github.com` was created in 2007, permanently. The only
  thing that could matter is which "bucket" it falls into (new/moderate/
  established), and that only shifts right at the 30-day or 365-day
  boundary. So it's safe to trust this answer for a whole day.

**One-line answer if asked**: "the expiry time should match how fast the
real answer can actually change — not just be a random number."

---

## 7. "Why didn't you just ship whichever model had the highest F1 score?"

This came up **three separate times** while I was fixing bugs: Random
Forest or XGBoost would win the raw F1 comparison by an extremely tiny
margin (less than 0.002 — basically a rounding difference).

Instead of blindly trusting that tiny margin, I built a small list of
real, hand-picked test URLs — known real phishing examples, plus the
specific tricky borderline cases I'd found bugs in before — and manually
compared both models against that list. **Every single time**, XGBoost
turned out to be meaningfully better on the URLs that actually mattered,
even when it lost the overall F1 metric by a hair. For example, in the
most recent check: on 5 real phishing URLs, XGBoost was 99-100% confident
they were phishing, while Random Forest was only 73-93% confident — a
real, meaningful gap that the F1 number alone completely hid.

**One-line answer if asked "how do you choose a model"**: "not by
trusting one leaderboard number blindly — I check how confidently
correct each model is on the specific real cases that actually matter,
especially when two models are basically tied on paper."

---

## 8. War stories — every real bug I found and fixed

This section is your best material for "tell me about a bug you
debugged" — each one follows the same pattern: **something looked wrong
→ I found actual evidence for why → I fixed the real cause → I checked it
didn't break anything else.**

### Bug 1 — the model scored suspiciously well (99.6%) on the very first try
- **What happened**: all three algorithms scored 99.6-99.7% right out of
  the gate. That's a red flag, not a win — see the "too good to be true"
  rule in §4.
- **Why**: my "legitimate" URL source only ever gave bare domains with no
  path (like `google.com`, never `google.com/search`), while almost all
  the phishing examples had *some* path. So the model wasn't really
  learning "what does phishing look like" — it was learning the much
  dumber trick "if it has any path at all, it's phishing," which would
  misfire constantly on real, everyday browsing.
- **Fix**: added realistic random paths onto the legitimate URLs so both
  groups had a similar range of path shapes.
- **What I learned**: a model that looks *too* good on paper is one of
  the clearest warning signs something's wrong with your data, not a
  reason to celebrate.

### Bug 2 — real Gmail/GitHub pages got flagged as phishing
- **Why**: my synthetic legitimate URLs only used a small fixed list of
  ~20 example paths, so the model never saw a realistically deep path
  (like `mail.google.com/mail/u/0/`) labeled as legitimate. It learned
  "a deep-looking path means phishing," which broke on totally normal
  pages.
- **First fix attempt (didn't fully work)**: I added more example paths
  to the list. Helped a little, but a fixed list can only ever cover a
  handful of exact shapes — real URLs vary too much.
- **Actual fix**: instead of a fixed list, I wrote a small generator that
  randomly builds realistic-looking paths (mixing route words, multi-word
  slugs, and random tokens) so the model sees a smooth range of
  possibilities instead of a few exact examples.
- **Method I started using from here on**: a systematic check — for
  every single feature, look for any value that shows up in one group
  (legit or phishing) but is completely missing from the other. That gap
  is almost always exactly where the next bug is hiding.

### Bug 3 — `launchpad.ccbp.in/` (just a domain plus a trailing slash) scored 72% phishing
- **Why**: I was randomly choosing between "no slash" and "a trailing
  slash" as a 50/50 coin flip when generating legitimate example URLs.
  But real browsers almost always add the trailing slash automatically
  when you visit a homepage — so real legitimate URLs should show the
  slash *far* more often than 50%, not as a coin flip.
- **Fix**: changed the odds so the trailing slash appears about 95% of
  the time for legitimate homepage-style URLs, matching how real
  browsers actually behave.
- **Trade-off, reported honestly rather than hidden**: fixing this made
  one previously-fixed case (`twitter.com/anthropicai`) get slightly worse
  again. I checked why — it wasn't a new bug, just a pre-existing, minor
  imbalance that became more noticeable once the bigger bug was gone. I
  didn't chase it further just to make one specific example look perfect.

### Bug 4 — a real Google search URL scored 99.9996% phishing
- **Why**: my legitimate training URLs were never longer than about 213
  characters, but a real Google search bar URL with all its tracking
  information attached can easily be 300+ characters. The model had
  simply never seen a long legitimate URL, so it assumed "long = phishing."
- **First fix attempt (didn't fully work)**: added one long tracking
  parameter to some legitimate URLs. Improved things a bit (down to ~95%
  phishing) but still wrong — a *different* feature (count of special
  characters like `=` and `&`) became the new problem, because I'd only
  added one parameter instead of several.
- **Actual fix**: real search-engine URLs stack multiple tracking
  parameters together, so I made my generator do the same.
- **Result**: 99.9996% phishing → 3.0% phishing.

### Bug 5 — a GitHub commit link scored 98.9% phishing
- **Why**: a git commit link ends in a 40-character code (like
  `fb66696c7e525f8afb17108c12e82d879e10e094`) that's about 65% digits.
  My "random token" generator for legitimate URLs was picking characters
  evenly from letters *and* digits, which only produces about 16% digits
  on average — nowhere close to a real commit hash. So the model had
  almost never seen a legitimate URL that digit-heavy, and flagged it as
  phishing on that basis alone.
- **Fix**: added two new ways to generate a random token — one that only
  uses hex characters (`0-9a-f`, like a real commit hash) and one that's
  purely digits (like a real order number or database ID).
- **Result**: 98.9% phishing → 0.03% phishing.
- **Bonus finding**: this is also when Random Forest narrowly "won" the
  automatic comparison again — see §7 for why I still shipped XGBoost.

### The one big lesson underneath all five bugs
Every single time, the actual ML model and algorithm were fine — the
problem was always that my *training examples* didn't look enough like
real browsing. I never once had to make the model itself more
complicated to fix any of these; I only had to make my training data more
realistic.

---

## 9. What "unit tests" actually are, and what I have

A **unit test** is just a small, automatic script that runs one tiny bit
of your code and checks the result is what you expect — instead of you
manually re-testing everything by hand every time you change something.

**Important distinction**: these only run when I (the developer) type a
command to run them. They are never part of what actually happens when
someone uses the real extension — a live user's browser never triggers a
test file. Tests exist purely so *I* can trust my own code.

What I actually test:
- `ml/features.py` — 9 tests checking each rule-based feature works
  correctly (does it correctly detect an IP address, an `@` symbol, a
  known shortener, etc.)
- `backend/` — tests that call the API the same way the extension would,
  but with the two live network checks replaced by fake, instant
  stand-ins (so tests never depend on the real internet or the real,
  constantly-changing blocklist/domain data)
- `TTLCache` (the caching class from §6) — 3 small tests: "if I store
  something, do I get it back," "if I ask for something never stored, do
  I get nothing instead of a crash," and "if I wait past the expiry time,
  is it gone."

27 tests total, all passing, all running in about 0.2 seconds (fast,
because none of them touch the real internet or a real slow database).

---

## 10. Known limitations — be upfront about these if asked

- **Domain-age lookups don't work for every website.** They're reliable
  for common endings like `.com`/`.org`/`.net`, but patchier for some
  country-specific domains (like `.de` or `.cn`). When it doesn't work, I
  just fall back to "unknown" rather than guessing or crashing.
- **The ML model only looks at the URL text itself** — it doesn't look at
  the actual page content, images, or login forms. A well-made fake page
  on a brand-new, not-yet-reported domain with an innocent-looking URL
  could theoretically slip through all three of my checks.
- **My cache is temporary and local to one running copy of the backend**
  — it resets if the server restarts, and wouldn't automatically share
  between multiple copies running at once. Fine for this project; a
  bigger production system would need a shared cache (like Redis).
- **No cloud deployment/Docker** — a deliberate choice, not something I
  ran out of time for. The goal was to deeply understand and be able to
  explain every layer myself.
- **My training data is partly synthetic (computer-generated), not 100%
  real browsing data** — and as §8 shows, every bug so far came from that
  fact. I'm disclosing this openly rather than pretending the dataset is
  perfect — it's a more honest and, I think, more impressive story than
  claiming zero flaws.

---

## 11. Quick numbers cheat sheet

| Thing | Value |
|---|---|
| Training examples | 130,000 URLs (65,000 legit / 65,000 phishing) |
| Where the data came from | Tranco (legit sites), PhishTank (phishing sites) |
| Number of features | 17, all readable directly from the URL text |
| Algorithm shipped | XGBoost |
| Current accuracy / F1 score | 91.8% / 0.916 |
| How much data is held back for testing | 20% |
| Blocklist cache expiry | 15 minutes |
| Domain-age cache expiry | 24 hours |
| "Brand new domain" cutoff | under 30 days old |
| "Well-established domain" cutoff | 365 days old or more |
| Ceiling for the "old domain rescues verdict" rule | only applies if ML phishing score is under 90% |
| Automated tests | 27, all passing |
| Real bugs found and fixed via actual user reports | 5 |

---

## 12. "What would you improve next?" — prepared answers

- Look at more than just domain age — e.g. who registered the domain,
  which country, whether the same hosting provider is linked to other
  known phishing sites.
- Move the cache from "in this one program's memory" to a shared system
  (like Redis) if this ever needed to run as more than one copy at once.
- I considered adding a check for "does this domain look suspiciously
  similar to a famous brand" (like `paypa1.com` vs `paypal.com`), but
  decided the existing three signals already cover that gap well enough
  — a genuine old domain doesn't need that check, and a brand-new
  lookalike domain already gets caught by the domain-age signal.
- Set up automatic testing (a "CI pipeline") that runs my test suite
  every time I change the code and push it, instead of me remembering to
  run it manually.
