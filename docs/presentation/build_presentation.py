"""Build editable PowerPoint, matching PDF/PNGs, and an offline narrated video.

Usage: python docs/presentation/build_presentation.py [--video]
Requires python-pptx, Pillow, DejaVu Sans fonts; video also requires espeak-ng/ffmpeg.
All illustrations are original diagrams. They are not screenshots of a deployment.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "presentation"
DEMO = ROOT / "demo"
FRAMES = OUT / "slides"
WIDTH, HEIGHT = 1600, 900
BG = "101820"
PANEL = "192630"
PANEL2 = "22313C"
INK = "F4F2EB"
MUTED = "A9BAC4"
TEAL = "76E0BD"
ORANGE = "FFAE79"
BLUE = "91BDF0"
GRID = "324653"
VIDEO_NARRATION = {
3: "Stock Pilot combines several stacks with specific responsibilities. React and Type Script provide the interface. Fast A P I, SQL Alchemy and Alembic implement validated transactions and migrations. Postgres owns durable inventory. Redis and Celery handle asynchronous reports. Docker and Helm package the runtime, while GitHub Actions, Argo C D and Terraform define delivery and infrastructure.",
4: "The browser reaches the A P I through a proxy or ingress, and the A P I reads and writes Postgres. Report requests and the scheduler enqueue work in Redis. Celery workers read the database and write timestamped reports into the cache. Workers and A P I replicas have separate responsibilities. Redis never owns authoritative stock.",
5: "Suppliers connect to products and purchase orders. Each balance belongs to one product and one warehouse. Database constraints require nonnegative stock and prevent reserved units from exceeding physical stock. Movements record receipts, issues and transfers. Reservations record commitments. Foreign keys preserve the meaning of inventory history when catalogue records are changed or removed.",
6: "Eight views organize the frontend: overview, inventory, movements, reservations, purchase orders, warehouses, suppliers and reports. Users can search products, export C S V data, manage catalogue records and perform stock workflows. Forms include validation and recoverable errors. Thirteen frontend tests exercise components and request payloads. This feature map is a diagram, not a browser screenshot.",
7: 'In this illustrative transfer, twenty units move from Delhi to Bengaluru. Delhi falls from one hundred to eighty, while Bengaluru rises from forty to sixty. The total remains one hundred and forty. Both balances and the movement commit together. Available stock excludes reservations. An identical idempotent retry returns the existing movement instead of moving stock again.',
8: 'Available stock equals on hand minus reserved. Releasing a reservation restores availability. Fulfilling creates the matching issue transaction. The same completion can be retried safely, while conflicting changes after closure are rejected. This preserves both physical stock and customer promises.',
9: 'Purchase orders move from draft to ordered to received. Lines must match the selected supplier. Receiving commits all receipt movements together, with deterministic keys preventing duplicate stock. Drafts are editable. Partial deliveries and invoice matching remain future work.',
10: 'The scheduler or report endpoint queues work in Redis. A Celery worker reads Postgres and caches a timestamped report for three minutes. The live dashboard uses its own database request, so report cache failures do not change authoritative inventory.',
11: 'Postgres row locks coordinate competing stock changes across replicas. Stable product ordering reduces deadlock risk, while request fingerprints protect retries. SQLite tests verify rules, not production locking. Concurrent Postgres tests and measured load tests are still required before capacity claims.',
12: 'The delivery workflow connects tests and security gates to image builds, scans and a temporary kind deployment. Commit S H A tags make releases traceable. Promotion updates Git only after its prerequisites pass. Hosted execution and registry publication require separate evidence.',
13: 'Kubernetes defines replicas, Services, Ingress, probes, storage and one migration job. Autoscaling, disruption budgets and resource limits express operational expectations. Readiness checks database access. A rendered chart validates configuration; actual rollout, persistence and scaling still need a running cluster.',
14: 'Release checks cover source, dependencies, secrets, infrastructure and images. Runtime controls reduce privileges and restrict access. The product currently has no sign in or role based permissions, so demo write endpoints remain private. Scan results apply to their specific revision.',
15: 'Prometheus records request counts, errors and latency. Grafana panels and alerts organize those metrics, while structured logs support investigation. Argo C D reconciles the desired Helm release from Git. Live graphs and healthy synchronized status require real runtime evidence.',
16: 'Terraform defines networking, E K S workers and storage. NAT is optional, with its tradeoffs documented. No cloud deployment is claimed without account access. Planning, applying, verification and teardown are separate milestones, and retained data requires deliberate cleanup decisions.',
17: 'The evidence register separates implementation from execution. Local tests and builds have captured results. Docker and Chromium are blocked in this environment, so this video shows architecture rather than a simulated live application. Hosted delivery and cloud deployment remain unclaimed.',
18: 'The live runbook starts with stock receiving, transfers, reservations and purchase orders, then demonstrates delivery, persistence, monitoring and GitOps. Capture each result only after execution. Thank you.',
}
FONT_DIR = Path("/usr/share/fonts/google-noto")


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR / ("NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf")), size)


def color(value):
    return RGBColor.from_string(value)


class Scene:
    def __init__(self, presentation, number, title, kicker):
        self.number = number
        self.title = title
        self.slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        self.slide.background.fill.solid()
        self.slide.background.fill.fore_color.rgb = color(BG)
        self.canvas = Image.new("RGB", (WIDTH, HEIGHT), "#" + BG)
        self.draw = ImageDraw.Draw(self.canvas)
        self.rect(60, 57, 10, 32, TEAL)
        self.text(88, 55, kicker.upper(), 20, TEAL, bold=True, width=1360)
        self.text(60, 112, title, 53, INK, bold=True, width=1470)
        self.line(60, 824, 1540, 824, GRID, 2)
        self.text(60, 847, "STOCKPILOT  /  VIMAL KUMAR YADAV · 24BCS10273", 16, MUTED, width=1100)
        self.text(1405, 845, f"{number:02d} / 18", 18, MUTED, width=150)

    def rect(self, x, y, w, h, fill=PANEL, radius=12, outline=None):
        self.draw.rounded_rectangle((x, y, x+w, y+h), radius, fill="#"+fill, outline="#"+outline if outline else None, width=2)
        shape = self.slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                           Inches(x/120), Inches(y/120), Inches(w/120), Inches(h/120))
        shape.fill.solid()
        shape.fill.fore_color.rgb = color(fill)
        shape.line.fill.background()
        if outline:
            shape.line.color.rgb = color(outline)
        if radius:
            shape.adjustments[0] = .06
        return shape

    def text(self, x, y, text, size=30, fill=INK, bold=False, width=1420, linespace=1.30):
        face = font(size, bold)
        wrapped = []
        for para in text.split("\n"):
            words = para.split()
            line = ""
            for word in words:
                candidate = (line + " " + word).strip()
                if self.draw.textlength(candidate, font=face) > width and line:
                    wrapped.append(line)
                    line = word
                else:
                    line = candidate
            wrapped.append(line)
        line_height = round(size * linespace)
        for i, line in enumerate(wrapped):
            self.draw.text((x, y+i*line_height), line, font=face, fill="#"+fill)
        box = self.slide.shapes.add_textbox(Inches(x/120), Inches(y/120), Inches((width+8)/120), Inches((line_height*len(wrapped)+12)/120))
        tf = box.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.word_wrap = False
        for i, line in enumerate(wrapped):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.text = line
            para.font.name = "Noto Sans"
            para.font.size = Pt(size * .60)
            para.font.bold = bold
            para.font.color.rgb = color(fill)
            para.space_before = para.space_after = Pt(0)
            para.line_spacing = linespace
        return line_height*len(wrapped)

    def line(self, x1, y1, x2, y2, fill=TEAL, thickness=3, arrow=False):
        self.draw.line((x1,y1,x2,y2), fill="#"+fill, width=thickness)
        connector = self.slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1/120), Inches(y1/120), Inches(x2/120), Inches(y2/120))
        connector.line.color.rgb = color(fill)
        connector.line.width = Pt(thickness*.6)
        if arrow:
            angle = math.atan2(y2-y1, x2-x1)
            for delta in (-.55, .55):
                ax = x2-16*math.cos(angle+delta)
                ay = y2-16*math.sin(angle+delta)
                self.line(x2,y2,ax,ay,fill,thickness)

    def card(self, x, y, w, h, title, body, accent=TEAL, number=None):
        self.rect(x,y,w,h)
        self.rect(x,y,5,h,accent,0)
        ty=y+26
        if number:
            self.text(x+25, ty, number, 22, accent, True, w-50)
            ty+=42
        self.text(x+25,ty,title,30,INK,True,w-50)
        self.text(x+25,ty+55,body,24,MUTED,width=w-50)

    def pill(self,x,y,text,accent=TEAL,width=None):
        width = width or round(self.draw.textlength(text,font=font(19,True)))+32
        self.rect(x,y,width,38,PANEL2,10)
        self.text(x+16,y+7,text,19,accent,True,width-28)

    def note(self,text):
        self.text(65,772,text,20,MUTED,width=1450)

    def finish(self,narration,source):
        self.slide.notes_slide.notes_text_frame.text = narration + "\n\nSource / provenance: " + source
        filename = FRAMES / f"{self.number:02d}.png"
        self.canvas.save(filename)
        return {"number":self.number,"title":self.title,"narration":narration,"source":source,"image":str(filename.relative_to(ROOT))}


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    FRAMES.mkdir(exist_ok=True)
    DEMO.mkdir(exist_ok=True)
    prs=Presentation()
    prs.slide_width=Inches(WIDTH/120)
    prs.slide_height=Inches(HEIGHT/120)
    prs.core_properties.title="StockPilot — Inventory, engineered for operations"
    prs.core_properties.author="Vimal Kumar Yadav"
    prs.core_properties.last_modified_by="Vimal Kumar Yadav"
    prs.core_properties.comments="Original StockPilot inventory and DevOps capstone presentation."
    prs.core_properties.subject="Session 21 DevOps capstone · 24BCS10273"
    records=[]

    s=Scene(prs,1,"Inventory, engineered for operations.","Session 21 / Original capstone")
    s.text(60,236,"StockPilot",114,TEAL,True,width=1100)
    s.text(65,401,"From a warehouse transaction\nto a reproducible release.",39,width=1000)
    for x,label in [(65,"MULTI-WAREHOUSE"),(353,"PROCUREMENT"),(596,"DEVSECOPS")]:
        s.pill(x,553,label)
    s.rect(1130,246,360,400,PANEL)
    for y,w,c in [(285,260,TEAL),(365,200,BLUE),(445,285,ORANGE)]:
        s.rect(1165,y,w,45,c,6)
    s.text(1165,542,"RECEIVE / RESERVE\nTRANSFER / REPLENISH",20,MUTED,True,285)
    s.text(65,669,"Vimal Kumar Yadav · 24BCS10273",27,INK,True)
    s.note("Original explanatory diagrams · synthetic English narration · deployment evidence stated explicitly")
    records.append(s.finish("Welcome to StockPilot, a multi warehouse inventory and procurement platform, built as an original DevOps capstone. The product follows a physical item from a supplier purchase through receiving, reservation, transfer and fulfilment. Around that product is a delivery platform using containers, Kubernetes, automated security gates, monitoring and infrastructure as code. This presentation explains the implemented design and the available verification. The diagrams are original illustrations, not screenshots of a live cluster. The audio is synthetic English narration.","README.md; backend/app/models.py; docs/DELIVERY.md"))

    s=Scene(prs,2,"One stock count. Many competing decisions.","The product problem")
    s.card(60,255,470,360,"Sell without overselling","Available stock must exclude reservations. A customer promise cannot be consumed by a warehouse transfer.",TEAL,"01 / AVAILABILITY")
    s.card(565,255,470,360,"Move without losing stock","A transfer changes both warehouses in one transaction. Retries must not duplicate the movement.",BLUE,"02 / CONSISTENCY")
    s.card(1070,255,470,360,"Replenish with context","Low-stock signals connect the catalogue, supplier, purchase order and receiving workflow.",ORANGE,"03 / PROCUREMENT")
    s.text(65,662,"The complexity is in the rules, not just the number of services.",32,TEAL,True,width=1450)
    s.note("Example business workflows; capacity and production scale have not been benchmarked.")
    records.append(s.finish("Inventory management is a demanding domain because several workflows compete for the same stock. A sales reservation promises units to a customer. A transfer moves those units between warehouses. A purchase order brings more units into the business. A simple counter is not enough. StockPilot keeps the available quantity separate from the physical quantity, makes transfers atomic, and records stock movement history. The architecture is designed to support multiple replicas, but no production capacity or load test result is claimed here.","backend/app/inventory.py; backend/app/orders.py; backend/app/models.py"))

    s=Scene(prs,3,"A different stack for each responsibility.","Technology choices")
    rows=[("EXPERIENCE","React · TypeScript · Vite","Typed forms and a responsive operational workspace",TEAL),
          ("TRANSACTIONS","FastAPI · SQLAlchemy · Alembic","Validated requests, business rules and schema migrations",BLUE),
          ("DATA + ASYNC","PostgreSQL · Redis · Celery","Durable stock ledger and separately scheduled reports",ORANGE),
          ("PLATFORM","Docker · Kubernetes · Helm","Repeatable packaging, health checks and scaling controls",TEAL),
          ("DELIVERY","GitHub Actions · Argo CD · Terraform","Release gates, reconciliation and infrastructure definitions",BLUE)]
    for i,(label,tech,purpose,accent) in enumerate(rows):
        y=235+i*102
        s.rect(60,y,1480,88,PANEL)
        s.text(85,y+28,label,19,accent,True,235)
        s.text(337,y+16,tech,27,INK,True,1150)
        s.text(337,y+52,purpose,20,MUTED,width=1130)
    s.note("Stack selection follows the instructor's Python/full-stack path; this is separate from the Java Typeahead project.")
    records.append(s.finish("The platform deliberately uses several technology stacks with clear responsibilities. React and TypeScript provide the operational interface. FastAPI, SQLAlchemy and Alembic handle validated requests, database access and schema evolution. PostgreSQL owns durable inventory records. Redis and Celery support background report generation, rather than owning authoritative stock. Docker and Helm package the runtime. GitHub Actions defines delivery gates, Argo CD reconciles desired state, and Terraform describes the cloud infrastructure. Each technology serves an identifiable part of the workflow.","frontend/package.json; backend/app; docker-compose.yml; helm; terraform; .github/workflows"))

    s=Scene(prs,4,"Two paths: serve requests and refresh reports.","Application architecture")
    boxes=[(60,275,280,140,"BROWSER","React + TypeScript",TEAL),(440,275,310,140,"API REPLICAS","FastAPI / SQLAlchemy",BLUE),(850,275,300,140,"SOURCE OF TRUTH","PostgreSQL",ORANGE),(850,565,300,140,"TASK BROKER","Redis",TEAL),(440,565,310,140,"BACKGROUND","Celery worker",BLUE),(1230,565,310,140,"SCHEDULE","Celery beat",ORANGE)]
    for x,y,w,h,a,b,c in boxes:
        s.rect(x,y,w,h,PANEL,12,c);s.text(x+20,y+24,a,18,c,True,w-40);s.text(x+20,y+65,b,25,INK,True,w-40)
    s.line(340,345,430,345,TEAL,4,True);s.line(750,345,840,345,BLUE,4,True)
    s.line(750,625,840,625,TEAL,4,True);s.line(840,625,760,625,TEAL,4,True);s.line(1230,625,1160,625,ORANGE,4,True)
    s.line(750,390,950,555,TEAL,4,True);s.line(665,565,900,425,BLUE,4,True)
    s.text(60,496,"LIVE DASHBOARD",20,TEAL,True,340)
    s.text(60,533,"Reads current database\nstate on demand.",24,MUTED,width=330)
    s.note("Redis failure affects background reports; database-backed inventory endpoints remain a separate path.")
    records.append(s.finish("The request path starts in the browser and reaches the FastAPI service through the frontend proxy or ingress. The API reads and writes PostgreSQL. Reporting is a separate path. A request or the Celery beat scheduler queues report generation through Redis. A worker reads the authoritative database and caches a report with a timestamp and expiry. This separation allows report workers and API replicas to scale independently. If the report cache is unavailable, the report endpoint reports that failure while the live dashboard still reads the database.","backend/app/main.py; backend/app/tasks.py; backend/app/reporting.py; frontend/nginx.conf"))

    s=Scene(prs,5,"Model the relationships before the screens.","Data model")
    positions=[(60,255,310,145,"Supplier","lead time · contact",TEAL),(470,255,310,145,"Product","SKU · price · threshold",BLUE),(880,255,310,145,"Warehouse","code · location",ORANGE),(470,520,310,145,"Balance","on hand · reserved",TEAL),(880,520,310,145,"Movement","kind · quantity · retry key",BLUE),(60,520,310,145,"Purchase order","status · order lines",ORANGE)]
    for x,y,w,h,title,body,accent in positions:s.card(x,y,w,h,title,body,accent)
    s.line(370,325,460,325,TEAL,3,True);s.line(625,400,625,510,BLUE,3,True);s.line(1035,400,780,520,ORANGE,3,True);s.line(215,400,215,510,TEAL,3,True)
    s.rect(1250,255,290,410,PANEL2)
    s.text(1275,284,"INVARIANTS",22,TEAL,True,240)
    s.text(1275,341,"One balance per\nproduct + warehouse\n\n0 ≤ reserved\nreserved ≤ on hand\n\nPositive quantities",23,INK,width=240)
    s.note("Additional entity: Reservation. Foreign keys protect referenced inventory history from accidental deletion.")
    records.append(s.finish("The core model connects suppliers, products and warehouses. A balance belongs to one product and one warehouse, with a unique constraint on that pair. Database checks require nonnegative stock and prevent the reserved count from exceeding the on hand count. Movements record receipts, issues and transfers. Reservations record customer commitments. Purchase orders contain supplier-linked lines and a controlled lifecycle. Foreign keys preserve important relationships, so deleting a catalogue record cannot silently erase the meaning of historical stock records.","backend/app/models.py; backend/app/catalog.py"))

    s=Scene(prs,6,"A practical operations workspace.","Frontend feature walkthrough")
    s.card(60,245,710,215,"Overview + inventory","Warehouse distribution, stock value, available units, low-stock signals and recent activity.",TEAL)
    s.card(830,245,710,215,"Products + suppliers","Searchable catalogue, categories, supplier associations, reorder thresholds and editable records.",BLUE)
    s.card(60,500,710,215,"Movements + reservations","Receive, issue or transfer stock; reserve units; release a promise or fulfil it into a stock issue.",ORANGE)
    s.card(830,500,710,215,"Procurement","Create purchase orders and advance permitted transitions from draft to ordered to received.",TEAL)
    s.note("Feature map based on application source; this diagram is not a captured browser screenshot.")
    records.append(s.finish("The frontend organizes the application around operational tasks. The overview explains stock value, warehouse distribution and low stock. The catalogue connects products to suppliers and reorder thresholds. Inventory and movement screens handle receiving, issuing and transferring units. Reservation controls separate a customer promise from fulfilment. Procurement connects supplier selection to purchase order lines and receiving. Forms expose validation and recoverable error states. This slide is a source-based feature map, not a browser screenshot; the environment's browser restriction is documented in the evidence register.","frontend/src/App.tsx; frontend/src/styles.css; docs/evidence.md"))

    s=Scene(prs,7,"A transfer is one transaction, not two edits.","Workflow 01 / Stock movement")
    s.text(65,229,"Illustrative example: transfer 20 keyboards from Delhi to Bengaluru",27,MUTED,width=1450)
    s.card(60,315,460,250,"DELHI / SOURCE","Before: 100 on hand\nReserved: 10\nAfter: 80 on hand",TEAL)
    s.card(1080,315,460,250,"BENGALURU / TARGET","Before: 40 on hand\nReserved: 0\nAfter: 60 on hand",BLUE)
    s.line(535,429,1065,429,ORANGE,5,True)
    s.pill(622,365,"TRANSFER 20 UNITS",ORANGE,330)
    s.text(580,464,"140 total > 140 total",29,INK,True,460)
    s.rect(60,615,1480,109,PANEL)
    s.text(90,641,"Validate > lock product > check available > update both balances > append movement > commit",25,TEAL,True,1420)
    s.note("The numbers above illustrate the rule; real execution results are recorded separately in the evidence files.")
    records.append(s.finish("Consider an illustrative transfer of twenty keyboards. Delhi begins with one hundred units, ten already reserved. Bengaluru begins with forty. After the transfer, Delhi holds eighty and Bengaluru sixty. The combined total is unchanged. The API locks the relevant product, checks available stock, updates both balances and appends the movement before committing. A repeated request with the same idempotency key returns the existing movement. Reusing the key for different data produces a conflict. This protects normal client retries from duplicating stock changes.","backend/app/inventory.py: apply_movement, duplicate, lock_products"))

    s=Scene(prs,8,"A reservation changes availability first.","Workflow 02 / Reservation lifecycle")
    s.text(65,225,"AVAILABLE = ON HAND − RESERVED",43,TEAL,True,1470)
    s.card(60,338,430,240,"ACTIVE","Reserve units without immediately reducing physical stock.",TEAL)
    s.card(600,338,430,240,"RELEASED","Return units to availability. Physical stock remains unchanged.",BLUE)
    s.card(1110,338,430,240,"FULFILLED","Reduce reserved stock and create the matching issue movement.",ORANGE)
    s.line(490,405,585,405,BLUE,4,True);s.line(490,615,1325,615,ORANGE,4,True);s.line(275,578,275,615,ORANGE,4);s.line(1325,615,1325,590,ORANGE,4,True)
    s.text(65,670,"Closed reservations cannot switch to a conflicting final state.",30,INK,True,1460)
    s.note("Repeated completion of the same action is safe; insufficient available stock returns a conflict.")
    records.append(s.finish("Reservations change what can be promised without immediately changing what is physically present. Available stock is the on hand count minus the reserved count. Releasing an active reservation returns those units to availability. Fulfilling it reduces the reserved count and creates a corresponding issue movement in the same transaction. Repeating the same completion action returns the existing final state. Attempting a different action after closure returns a conflict. These rules are more important than a screen that merely lets a user edit a stock number.","backend/app/inventory.py: reserve, finish_reservation; backend/app/models.py: Balance"))

    s=Scene(prs,9,"Receiving closes the procurement loop.","Workflow 03 / Purchase order lifecycle")
    states=[(60,"DRAFT","Editable supplier,\nwarehouse and lines",TEAL),(565,"ORDERED","Confirmed intent\nto purchase",BLUE),(1070,"RECEIVED","Atomic receipts\nfor every order line",ORANGE)]
    for x,title,body,c in states:s.card(x,295,470,250,title,body,c)
    s.line(535,415,555,415,TEAL,4,True);s.line(1040,415,1060,415,BLUE,4,True)
    s.rect(60,597,1480,133,PANEL)
    s.text(90,622,"GUARDS",21,ORANGE,True,200)
    s.text(290,621,"Supplier consistency · positive line quantities · valid transitions\nIdempotent receiving · no edits after the draft stage",26,INK,width=1200)
    s.note("Draft and ordered purchases may be cancelled. Full-order receiving is supported; partial receipt is future work.")
    records.append(s.finish("A purchase order begins as a draft containing a supplier, destination warehouse and product lines. Every line must belong to the selected supplier. Drafts can be edited before they are ordered. Receiving is allowed only after ordering, and it creates the receipt movements for all lines in one database transaction. Deterministic receipt keys prevent double counting if the same receive operation is retried. The current implementation receives whole orders. Partial deliveries, invoice matching and multi currency accounting are useful extensions rather than claimed features.","backend/app/orders.py; backend/app/schemas.py"))

    s=Scene(prs,10,"Background work must not own the stock ledger.","Asynchronous processing")
    s.card(60,255,470,260,"TRIGGER","POST /api/reports\nA scheduled beat every 60 seconds",TEAL,"01 / REQUEST")
    s.card(565,255,470,260,"COMPUTE","Celery worker reads the current database snapshot",BLUE,"02 / PROCESS")
    s.card(1070,255,470,260,"CACHE","Redis report + generated_at\n180-second cache expiry",ORANGE,"03 / SERVE")
    s.rect(60,570,1480,150,PANEL2)
    s.text(90,598,"Graceful degradation",31,TEAL,True,1400)
    s.text(90,650,"Report cache unavailable > explicit report error. Live dashboard > database-backed request.",26,INK,width=1400)
    s.note("Redis/Celery execution requires a runnable service environment; configuration alone is not a worker execution result.")
    records.append(s.finish("Background reporting adds a separate Python worker stack to the application. The report endpoint queues a task, and the scheduler can request refreshes every sixty seconds. A worker reads a database snapshot and stores the result in Redis for one hundred and eighty seconds, including its generation time. This makes staleness visible and keeps the cache disposable. Redis is not the source of inventory truth. A worker or cache outage is reported explicitly. The live dashboard follows its own database-backed path. Service execution evidence is tracked separately from the implementation.","backend/app/tasks.py; backend/app/main.py; backend/app/reporting.py"))

    s=Scene(prs,11,"Scale the API while protecting correctness.","Concurrency and resilience")
    s.card(60,255,710,215,"Database coordination","PostgreSQL row locks serialize competing product changes. Stable lock ordering reduces deadlock risk.",TEAL)
    s.card(830,255,710,215,"Retry-aware writes","Request fingerprints distinguish an identical retry from a conflicting reuse of an idempotency key.",BLUE)
    s.card(60,510,710,215,"Independent replicas","API and frontend replicas can scale separately from workers. Shared durable state stays in PostgreSQL.",ORANGE)
    s.card(830,510,710,215,"Honest capacity boundary","SQLite tests exercise rules, not PostgreSQL locking semantics. Load and concurrent database testing remain required.",TEAL)
    s.note("Multiple replicas are an infrastructure configuration; production scalability requires measured capacity and failure tests.")
    records.append(s.finish("The design supports scaling without placing shared stock state in an application process. PostgreSQL row locks coordinate updates across replicas. Product locks are acquired in a stable order, reducing the risk of deadlocks when an order contains several products. Idempotency keys and request fingerprints protect retries. Frontend, API and worker workloads have distinct scaling responsibilities. There is an important verification boundary: SQLite-based tests do not validate PostgreSQL row locking. Concurrent PostgreSQL tests, load tests and failure recovery exercises are still needed before claiming a measured production scale.","backend/app/inventory.py; backend/app/orders.py; helm/stockpilot"))

    s=Scene(prs,12,"Turn a source change into a gated release.","Continuous integration and delivery")
    stages=[("SOURCE","Lint + unit tests",TEAL),("SECURITY","SAST + dependencies",BLUE),("IMAGES","Build + image scan",ORANGE),("DEPLOY","kind + Helm smoke",TEAL),("PROMOTE","GitOps image tag",BLUE)]
    for i,(title,body,c) in enumerate(stages):
        x=60+i*300
        s.card(x,300,280,240,title,body,c,f"0{i+1}")
        if i<4:s.line(x+282,420,x+296,420,c,3,True)
    s.rect(60,596,1480,128,PANEL2)
    s.text(90,623,"TRACEABILITY",21,ORANGE,True,300)
    s.text(388,618,"Commit SHA > container image > Helm value > deployed revision",27,INK,True,1100)
    s.text(388,661,"A workflow file is not a successful GitHub Actions run.",23,MUTED,width=1100)
    s.note("CI definitions are reviewable locally. Hosted execution and GHCR publication require repository/network access.")
    records.append(s.finish("The delivery workflow links source validation to deployment. It defines backend checks, a frontend build, source and dependency security gates, container image builds and vulnerability scanning. A temporary kind cluster provides a place to install the Helm chart and smoke test it. Promotion updates the desired image revision only after its prerequisites succeed. Commit SHA image tags connect a release to a specific source version. These are implementation details in the workflow. A successful hosted run, published image and deployment must each be demonstrated separately before they are reported as verified.",".github/workflows; scripts; gitops"))

    s=Scene(prs,13,"Kubernetes encodes operational expectations.","Runtime platform")
    s.card(60,255,470,380,"SERVE","Frontend + API Deployments\nClusterIP Services + Ingress\nStartup, readiness and liveness probes\nHPA + disruption budgets",TEAL)
    s.card(565,255,470,380,"PERSIST","PostgreSQL StatefulSet\nPersistent volume claim\nRedis for broker/cache\nMigration job before rollout",BLUE)
    s.card(1070,255,470,380,"CONSTRAIN","Non-root containers\nResource requests and limits\nNetwork isolation policies\nConfiguration + external secrets",ORANGE)
    s.text(65,677,"Readiness asks: can this replica safely receive traffic now?",30,TEAL,True,1450)
    s.note("A rendered chart describes intended resources. Running pods, persistence and failover need cluster evidence.")
    records.append(s.finish("The Helm chart expresses more than how to start a container. Deployments and services connect the frontend and API. Probes separate startup, process health and database readiness. Resource requests, limits, autoscaling and disruption budgets describe operational expectations. PostgreSQL uses persistent storage, while a migration job prepares the schema before the application rollout. Runtime security settings reduce container privileges. These controls are designed in configuration. Actual rollout behaviour, storage persistence, scaling and failover need a Kubernetes environment and captured execution evidence.","helm/stockpilot/templates; kubernetes; backend/app/main.py"))

    s=Scene(prs,14,"Security has both release and runtime boundaries.","DevSecOps")
    s.card(60,255,710,350,"BEFORE RELEASE","Source analysis\nDependency vulnerability checks\nGit history secret scanning\nContainer and infrastructure scans",TEAL)
    s.card(830,255,710,350,"DURING EXECUTION","Non-root workloads\nRestricted capabilities\nExplicit configuration and credentials\nNetwork and resource boundaries",BLUE)
    s.rect(60,649,1480,92,PANEL2)
    s.text(88,675,"CURRENT PRODUCT BOUNDARY: no sign-in or RBAC; keep demo write APIs private.",26,ORANGE,True,1420)
    s.note("A scan result is specific to a commit and vulnerability database. No passing scan is inferred from configuration.")
    records.append(s.finish("Security operates before release and during execution. The repository defines checks for source code, dependencies, secrets, container images and infrastructure. Runtime controls reduce privileges and make credentials and network boundaries explicit. These measures do not add user authentication by themselves. The current application has no sign in or role based permissions, so write APIs should remain private in a demo environment. A passing scan also applies to one source revision and vulnerability database. It should never be translated into a blanket claim that the platform is secure.",".github/workflows; security; backend/app/main.py; helm/stockpilot/templates"))

    s=Scene(prs,15,"Observe requests, then explain failures.","Monitoring and GitOps")
    s.card(60,255,710,350,"PROMETHEUS > GRAFANA","HTTP request counts\nRequest-duration histograms\nStatus labels and route labels\nDashboard and alert definitions",TEAL)
    s.card(830,255,710,350,"GIT > ARGO CD","Review desired state in Git\nReconcile the Helm release\nTrack the deployed image revision\nRecover from configuration drift",BLUE)
    s.rect(60,649,1480,92,PANEL2)
    s.text(88,676,"JSON request logs connect method, route, status and elapsed time.",28,INK,True,1420)
    s.note("Live Grafana graphs and Argo CD Healthy/Synced status require captured runtime evidence.")
    records.append(s.finish("The API exports Prometheus counters and request duration histograms, with method, route and status labels. Structured request logs include the elapsed time. The repository also contains monitoring configuration that connects metrics to dashboards and alerts. GitOps addresses a different concern: Argo CD compares the cluster with the desired Helm configuration in Git and reconciles drift. Monitoring explains what the system is doing, while GitOps manages what it should be running. Live graphs and a healthy synchronized application status require their own runtime evidence.","backend/app/main.py; monitoring; gitops"))

    s=Scene(prs,16,"Cloud infrastructure is explicit and reviewable.","Terraform / deployment boundary")
    s.rect(60,245,1480,460,PANEL)
    s.text(90,273,"AWS VPC",22,TEAL,True,1300)
    s.rect(100,337,650,200,PANEL2,10,BLUE);s.text(125,362,"PUBLIC SUBNETS",21,BLUE,True,600);s.text(125,407,"Default demo worker placement\nPublic IPs; NAT is optional",26,INK,width=590)
    s.rect(850,337,650,200,PANEL2,10,TEAL);s.text(875,362,"PRIVATE SUBNETS",21,TEAL,True,600);s.text(875,407,"Workers here with NAT enabled\nPrivate subnets remain defined",26,INK,width=590)
    s.text(100,585,"Plan > review > apply > verify > capture > destroy",32,INK,True,1370)
    s.pill(1010,647,"NO AWS DEPLOYMENT CLAIMED",ORANGE,480)
    s.note("AWS access is unavailable for this session. Definitions are separate from a real Terraform plan or apply.")
    records.append(s.finish("Terraform describes a possible AWS deployment with a virtual private cloud, public and private subnets, EKS workers and storage integration. Network access, node sizing and NAT choices should be reviewed before applying it. The user does not currently have AWS access, and this session does not claim a cloud deployment. Infrastructure definitions, a successful plan, an apply and a verified running application are different milestones. A complete cloud demonstration also includes teardown, so the presenter should capture the result and then remove resources that are no longer needed.","terraform; docs/operations-guide.md; docs/evidence.md"))

    s=Scene(prs,17,"Evidence follows execution, not ambition.","Verification register")
    evidence_path=ROOT/"docs"/"presentation"/"verification.json"
    evidence=json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    table=[("Application code","Implemented","Catalog, stock rules, orders, reports"),
           ("Backend verification",evidence.get("backend","See evidence register"),evidence.get("backend_detail","Latest captured results in docs/evidence.md")),
           ("Frontend verification",evidence.get("frontend","See evidence register"),evidence.get("frontend_detail","Build result captured separately")),
           ("Containers + cluster","Not executed here","Local Docker socket unavailable"),
           ("Browser recording","Not available here","Chromium sandbox process denied"),
           ("Hosted CI + AWS","Not claimed","External access required")]
    for i,(area,status,detail) in enumerate(table):
        y=240+i*79
        s.rect(60,y,1480,68,PANEL if i%2==0 else PANEL2,6)
        s.text(84,y+19,area,23,INK,True,385);s.text(491,y+19,status,23,TEAL if "passed" in status.lower() or status=="Implemented" else ORANGE,True,435);s.text(949,y+20,detail,21,MUTED,width=565)
    s.note("Read docs/evidence.md and the referenced logs for exact commands, scope and timestamps.")
    records.append(s.finish("This register separates implementation from execution. The application code and delivery configuration are present. The evidence guide records the exact local checks that completed, with their scope and logs. Local container deployment is blocked because the Docker socket is unavailable. Chromium startup is also denied by the current sandbox, so this recording uses explanatory slides rather than pretending to show a browser walkthrough. Hosted continuous integration, registry publication and AWS deployment are not claimed without successful execution. This boundary makes the submission reviewable and honest.","docs/evidence.md; docs/presentation/verification.json; demo/README.md"))

    s=Scene(prs,18,"A complete demo has a clear next action.","Presenter runbook / next verification")
    s.card(60,255,710,370,"PRODUCT WALKTHROUGH","1  Open dashboard and catalogue\n2  Receive and transfer stock\n3  Reserve, release and fulfil\n4  Order and receive a purchase\n5  Refresh a background report",TEAL)
    s.card(830,255,710,370,"PLATFORM WALKTHROUGH","1  Run backend and frontend checks\n2  Build containers and install Helm\n3  Verify persistence and recovery\n4  Capture monitoring and GitOps\n5  Plan/apply cloud only with access",BLUE)
    s.text(65,672,"Built to explain every stock change—and every release.",35,TEAL,True,1450)
    s.note("Use the runbook to demonstrate product workflows, delivery checks and operational recovery.")
    records.append(s.finish("For the live presentation, start with the dashboard and catalogue. Receive stock, transfer it, reserve units, then demonstrate release and fulfilment. Create a purchase order and receive it to close the procurement loop. Next, show the checks, container deployment, persistent data, monitoring and GitOps evidence. The remaining environment-dependent captures are listed in the runbook. Thank you for exploring how product rules and delivery engineering work together.","demo/RUNBOOK.md; docs/operations-guide.md"))

    prs.save(OUT/"StockPilot-Capstone.pptx")
    images=[Image.open(FRAMES/f"{i:02d}.png").convert("RGB") for i in range(1,19)]
    images[0].save(OUT/"StockPilot-Capstone.pdf",save_all=True,append_images=images[1:],resolution=144)
    for record in records:
        record["presenter_notes"] = record["narration"]
        record["narration"] = VIDEO_NARRATION.get(record["number"],record["narration"])
    (DEMO/"chapters.json").write_text(json.dumps(records,indent=2)+"\n")
    script=["# StockPilot narration\n", "Synthetic English voice; original explanatory diagrams. This is not a live browser or cloud recording.\n"]
    for r in records:script.append(f"## {r['number']:02d} — {r['title']}\n\n{r['narration']}\n\nSource: `{r['source']}`\n")
    (DEMO/"NARRATION.md").write_text("\n".join(script))
    print("Built 18-slide editable PPTX, matching PDF, slides and narration",flush=True)
    return records


def timestamp(seconds, srt=False):
    h=int(seconds)//3600;m=int(seconds)//60%60;s=int(seconds)%60;ms=int(round(seconds%1*1000))
    return f"{h:02}:{m:02}:{s:02}{',' if srt else '.'}{ms:03}"


def video(records):
    work=DEMO/".render"
    work.mkdir(exist_ok=True)
    concat=[];subtitles=[];chapters=[];elapsed=0;index=1
    neural=None
    model=os.getenv("STOCKPILOT_TTS_MODEL")
    voices=os.getenv("STOCKPILOT_TTS_VOICES")
    if model and voices:
        import kokoro_onnx
        import onnxruntime as runtime
        def cpu_session(path):
            options=runtime.SessionOptions()
            options.intra_op_num_threads=12
            options.inter_op_num_threads=1
            options.log_severity_level=3
            return runtime.InferenceSession(path,sess_options=options,providers=["CPUExecutionProvider"])
        kokoro_onnx.create_session=cpu_session
        neural=kokoro_onnx.Kokoro(model, voices)
        print("Narration engine: Kokoro ONNX, af_heart (generic synthetic voice)",flush=True)
    for rec in records:
        n=rec["number"];txt=work/f"{n:02d}.txt";wav=work/f"{n:02d}.wav";mp4=work/f"{n:02d}.mp4"
        narration_unchanged=txt.exists() and txt.read_text()==rec["narration"]
        txt.write_text(rec["narration"])
        if wav.exists() and narration_unchanged:
            print(f"Reusing completed narration {n:02d}",flush=True)
        elif neural is not None:
            import numpy as np
            spoken=rec["narration"]
            for before,after in [("StockPilot","Stock Pilot"),("FastAPI","Fast A P I"),("PostgreSQL","Postgres"),("SQLAlchemy","S Q L Alchemy"),("SQLite","S Q Lite"),("GitOps","Git Ops"),("DevOps","Dev Ops"),("DevSecOps","Dev Sec Ops"),("Argo CD","Argo C D"),("API","A P I"),("APIs","A P I's"),("SHA","sha"),("CI","C I"),("RBAC","R back"),("TypeScript","Type Script")]:
                spoken=spoken.replace(before,after)
            samples,rate=neural.create(spoken,voice="af_heart",speed=1.04,lang="en-us")
            with wave.open(str(wav),"wb") as audio:
                audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate)
                audio.writeframes((np.clip(samples,-1,1)*32767).astype(np.int16).tobytes())
        else:
            subprocess.run(["espeak-ng","-v","en-us","-s","166","-p","46","-a","155","-f",str(txt),"-w",str(wav)],check=True)
        with wave.open(str(wav)) as audio:duration=audio.getnframes()/audio.getframerate()+1.0
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-framerate","10","-i",str(ROOT/rec["image"]),"-i",str(wav),"-c:v","libx264","-preset","ultrafast","-tune","stillimage","-crf","22","-pix_fmt","yuv420p","-vf","scale=1600:900","-c:a","aac","-b:a","128k","-af","apad=pad_dur=1","-t",f"{duration:.3f}","-threads","2",str(mp4)],check=True)
        concat.append(f"file '{mp4.resolve()}'")
        chapters.append(f"{timestamp(elapsed)[:-4]}  {n:02d}  {rec['title']}")
        rec["start_seconds"]=round(elapsed,3);rec["duration_seconds"]=round(duration,3)
        sentences=rec["narration"].split(". ")
        words=sum(len(sentence.split()) for sentence in sentences)
        current=elapsed
        for sentence in sentences:
            part=(duration-1.0)*len(sentence.split())/words
            subtitles.append(f"{index}\n{timestamp(current,True)} --> {timestamp(current+part,True)}\n"+"\n".join(textwrap.wrap(sentence.rstrip(".")+".",100))+"\n")
            current+=part;index+=1
        elapsed+=duration
        print(f"Encoded chapter {n:02d}: {duration:.1f}s",flush=True)
    (work/"concat.txt").write_text("\n".join(concat)+"\n")
    (DEMO/"StockPilot-Capstone.srt").write_text("\n".join(subtitles))
    (DEMO/"CHAPTERS.md").write_text("# Video chapters\n\nDuration: "+timestamp(elapsed)[:-4]+"\n\n```text\n"+"\n".join(chapters)+"\n```\n")
    (DEMO/"chapters.json").write_text(json.dumps(records,indent=2)+"\n")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(work/"concat.txt"),"-i",str(DEMO/"StockPilot-Capstone.srt"),"-map","0:v","-map","0:a","-map","1:0","-c:v","copy","-c:a","aac","-b:a","128k","-ar","48000","-af","loudnorm=I=-16:TP=-1.5:LRA=11","-c:s","mov_text","-metadata:s:s:0","language=eng","-metadata","title=StockPilot: Inventory, engineered for operations","-metadata","artist=Vimal Kumar Yadav","-movflags","+faststart",str(DEMO/"StockPilot-Capstone-Narrated.mp4")],check=True)
    print(f"Built narrated MP4: {elapsed/60:.1f} minutes",flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--video",action="store_true");args=parser.parse_args()
    result=build()
    if args.video:video(result)
