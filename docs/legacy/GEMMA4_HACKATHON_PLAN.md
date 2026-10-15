# Build with Gemma: GDG Pwani — Technical Implementation Plan
Track 3: Smart Health — AI-Driven Health Center & Supply Chain Management
Base repo: `github.com/57nyambu/inventory-system` (Django + DRF + Celery + Channels)

---

## 0. Environment prerequisites (do TODAY, before touching code)

| Task | Why it matters |
|---|---|
| Kaggle account created + **phone-verified** | Verification is required to run the notebooks; unverified accounts can't use GPU/internet in Kaggle notebooks |
| Generate a **Google AI Studio** API key (aistudio.google.com) — this is the only Gemma access path, no Vertex AI/Cloud billing involved | Free tier, ~1,500 requests/day. Confirm the live number in your own AI Studio dashboard the morning of — Google has adjusted this quota before without much notice |
| Set `GEMMA_API_KEY`, `GEMMA_MODEL_ASSISTANT=gemma-4-4b-it`, `GEMMA_MODEL_VISION=gemma-4-12b-it` as env vars | Store as env vars, never commit them. See `README.md`'s new "Smart Health Extension" section for the full var list |
| (Optional) Install Antigravity IDE | Speeds up scaffolding tomorrow. It is a *dev tool*, not the model going into your product — don't confuse the two in the writeup |
| **Smoke test before relying on anything**: 1 plain text call, 1 image call, 1 Swahili-language call | Confirms the key works, confirms multimodal input works, and confirms Gemma 4's Swahili output quality is actually demo-worthy — if it's weak, decide now to fall back to English narration with Swahili UI labels only |
| Locate the Showcase Template link | Not included in the organizer email you received — chase it down before building slides |

With a 1,500/day cap shared across the whole team's testing **and** the live demo, treat quota as a scarce resource from today onward — see §6 below.

---

## 1. What's already usable in the repo (no changes needed)

- `products.Inventory` — stock levels + `needs_restock`
- `warehouses.Warehouse` / `Branch` — facility + district structure, incl. `temperature_controlled` for cold chain
- `warehouses.StockTransfer` — inter-facility transfer + approval workflow (this **is** your redistribution mechanism)
- `suppliers.PurchaseOrder` / `PurchaseOrderItem` — restock pipeline (KEMSA/distributor-equivalent)
- `analytics.RTInventoryAlert` / `integrations.InventoryAlert` — low-stock/expired alert types already modeled
- `integrations.NotificationService` — SMS + email, already wired to AfricasTalking
- `analytics.consumers.py` — Channels websocket, already streaming for a live dashboard

**Do not touch these files.** Everything below is additive only.

---

## 2. New code — build in this exact order

### Step 1 — `apps/facility_ops` (new Django app)

```
apps/facility_ops/
  models.py       # FacilityDailyStats, FacilityAlert
  admin.py        # register both, so the team can eyeball seeded data
  management/commands/seed_facility_demo_data.py
  tasks.py        # flag_underperforming_facilities (Celery, mirrors analytics/tasks.py)
```

**Models:**
```python
class FacilityDailyStats(models.Model):
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.CASCADE)
    date = models.DateField()
    patient_footfall = models.PositiveIntegerField()
    beds_total = models.PositiveIntegerField()
    beds_occupied = models.PositiveIntegerField()
    doctors_scheduled = models.PositiveIntegerField()
    doctors_present = models.PositiveIntegerField()

class FacilityAlert(models.Model):
    warehouse = models.ForeignKey('warehouses.Warehouse', on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=30)  # understaffed | low_footfall | overcrowded | stockout_risk | custom
    message = models.TextField()
    severity = models.CharField(max_length=10)    # low | medium | high
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

Register in `INSTALLED_APPS` (`root/settings/base.py`), then:
```
python manage.py makemigrations facility_ops
python manage.py migrate
```

**Seed script is not optional.** You cannot collect real health data in one day. Seed ~5 warehouses × 30 days of `FacilityDailyStats`, and deliberately unbalance the data:
- 1–2 facilities with genuine low stock on a specific product
- 1–2 facilities with surplus of that same product
- 1 facility trending toward understaffing/low footfall

Without deliberately shaped data, your forecast/redistribution/flagging demos will have nothing interesting to say on stage.

### Step 2 — `apps/ai` (Gemma integration layer)

```
apps/ai/
  gemma_client.py   # thin requests-based wrapper, same style as integrations/services.py
  tools.py          # function-calling target functions
  serializers.py
  views.py
  urls.py
```

`gemma_client.py`:
```python
import requests
from django.conf import settings

class GemmaClient:
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, model=None):
        self.model = model or settings.GEMMA_MODEL_ASSISTANT  # e.g. "gemma-4-4b-it"
        self.key = settings.GEMMA_API_KEY

    def generate(self, contents, tools=None):
        payload = {"contents": contents}
        if tools:
            payload["tools"] = tools
        r = requests.post(
            f"{self.BASE}/{self.model}:generateContent?key={self.key}",
            json=payload, timeout=30,
        )
        r.raise_for_status()
        return r.json()
```

`tools.py` — the actual function-calling targets, thin queries against existing models:
```python
def get_low_stock_alerts(warehouse_id=None): ...      # queries products.Inventory / RTInventoryAlert
def get_facility_stats(warehouse_id, days=7): ...      # queries facility_ops.FacilityDailyStats
def get_transfer_candidates(product_id): ...           # queries products.Inventory across warehouses
def get_underperforming_facilities(): ...              # queries facility_ops.FacilityAlert
```

Register the app + `apps/ai/urls.py` under the project's root urls.

### Step 3 — Build endpoints in this priority order

1. `POST /api/v1/ai/assistant/` — function-calling Q&A. District officer asks a question (English or Swahili) → Gemma selects tool(s) from `tools.py` → synthesizes an answer. **Build this first and get it fully working before anything else** — it's the centerpiece demo moment and the clearest evidence of real Gemma integration.
2. `POST /api/v1/ai/ocr-intake/` — photo of a stock card/register → Gemma multimodal → structured JSON → optionally writes to `Inventory`/`FacilityDailyStats` after a confirm step.
3. `GET /api/v1/ai/forecast/<warehouse_id>/<product_id>/` — recent `OrderItem` consumption summarized → Gemma → forecast narrative + reorder qty.
4. `GET /api/v1/ai/redistribution-suggestions/` — current `Inventory` across warehouses → Gemma proposes specific `StockTransfer` drafts with reasoning.
5. Celery task `flag_underperforming_facilities` (same beat pattern as `analytics/tasks.py`) → writes `FacilityAlert` → sends via the **existing** `NotificationService`. No new notification code needed — this is your cleanest reuse story for the writeup.
6. (Only if time allows) extend `analytics/consumers.py` to push new `FacilityAlert` creation to a live dashboard channel.

**Cut scope from the bottom of this list if you're behind, never from the top.** A working #1–#3 beats a half-working #1–#6 on both the Functionality score and the demo.

Permission requirements, exact request/response shapes, and the three access tiers (Admin / Facility Staff / Read-Only) for every one of these endpoints are fully specified in `FRONTEND_AND_API_SPEC.md` — don't re-derive them here, that document is the source of truth.

---

## 3. Hour-by-hour sequence for hackathon day (31 July, 08:00–18:00)

| Time | Activity |
|---|---|
| 08:00–09:00 | Check-in. Confirm the Gemma API key works from venue wifi (not just from home). Confirm team roles. |
| 09:00–09:30 | Lock the pitch framing — no pivoting after this point. |
| 09:30–11:30 | Feature 1: function-calling assistant, end-to-end, against real seeded data. |
| 11:30–13:00 | Feature 2: OCR multimodal intake. |
| 13:00–13:30 | Break. |
| 13:30–15:00 | Features 3 + 4 (forecast + redistribution). Drop whichever isn't working by 15:00. |
| 15:00–16:00 | Bug fixes only. No new features. Dashboard/demo polish. |
| 16:00–16:30 | Finalize Kaggle Writeup, attach public repo + live demo links, submit. |
| 16:30–17:45 | Judging & demo session — rehearsed pitch. |

Since your infra (models, migrations, seed data, base Gemma client) can legitimately be prepped **before** the 31st, do that today/tomorrow so the sprint itself is spent entirely on the Gemma logic and the pitch — those are 80% of the rubric (30% Gemma Integration + 30% Innovation/Impact + 20% Presentation vs. 20% Functionality).

---

## 4. Gemma quota discipline (1,500 requests/day, AI Studio only)

That cap is shared across every teammate's testing plus the actual judged demo — it will not stretch if treated casually.

- Cache `/ai/forecast/` and `/ai/redistribution-suggestions/` responses (15–30 min) — they don't need to be regenerated on every page load.
- Stop ad-hoc testing against the live key at least an hour before judging; rehearse against logged/cached responses instead.
- The public/open API (`/api/v1/public/...`, see `FRONTEND_AND_API_SPEC.md`) is plain DB reads with no Gemma calls — external integrators and curious teammates poking at it won't burn your quota.
- If quota does run out mid-demo, have one pre-recorded fallback clip of the assistant working, as insurance — better than a live 429 error in front of judges.

---

## 5. Deliverables checklist

- [ ] **Kaggle Writeup** — ≤1,500 words, Track 3 selected, repo + demo attached. Match the pattern used by strong MedGemma Impact Challenge writeups: punchy title + one-line subtitle, problem stated with a concrete stat, then a section that names *exactly which Gemma 4 capability* (function calling / multimodal / generation) powers *which* feature — judges are explicitly scoring whether the model is core to the solution, so don't bury this in general architecture prose.
- [ ] **Public code repo** — your existing repo, extended with `apps/facility_ops` and `apps/ai`.
- [ ] **Live demo** — hosted app or clonable notebook.
- [ ] **5-minute video** (submitted via the Google Form) covering, in order: Background/Problem, Project Definition, Project Details, Demo. Suggested split for 5:00 total: ~40s problem, ~40s definition, ~2:00 technical detail (this is where you prove Gemma integration on camera), ~1:40 live demo, ~20s buffer. Going over 5:00 disqualifies you from being a live presenter — script it and rehearse against a timer before the final recording.
- [ ] **Showcase Template** — get the actual link from organizers before building slides.

**Companion documents** (created alongside this one):
- `DOMAIN_RELABELING.md` — health-domain display labels, applied without any schema changes
- `FRONTEND_AND_API_SPEC.md` — full endpoint spec, permission tiers, and the open/public API for third-party integrators
- Updated `README.md` — new "Smart Health Extension" section indexing all of the above

---

## 6. Open items to verify with organizers (don't guess on these)

- Whether the $300 GCP credit needs a specific promo/coupon code beyond a fresh account signup.
- Whether the Showcase Template is mandatory for the video, the live pitch, or both.
