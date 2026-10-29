"""Seeded generator for the synthetic document set.

    uv run python -m data.generate

Writes data/docs/<doc_id>.pdf|.png and data/truth/<doc_id>.json, plus
data/manifest.json. Every name, company, address, policy number, SSN and amount
is invented. SSNs start with 000, which the SSA never issues.

Three document types (invoice, w2, loss_run), 10 of each. Some documents are
deliberately hard: rasterized "scans" with rotation and noise (no text layer),
two-page documents, a missing required field, and documents whose printed
numbers do not add up. The ground truth is what is PRINTED on the page, so an
extractor that faithfully reads a wrong total is correct; it is the rules'
job to send that document to review. `expected_review` records that intent.

Each truth field also stores the page and the exact printed text it came
from. The offline scripted model uses that text as its citation, and a test
checks that every truth citation is found by the citation checker.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
TRUTH = ROOT / "truth"
SEED = 20261029
FOOTER = "SYNTHETIC TEST DOCUMENT - all names, companies and numbers are fictional."
W, H = letter

VENDORS = [
    ("Brightwater Industrial Supply LLC", "4410 Kestrel Mill Rd, Dunmore Falls, OH 44720"),
    ("Halvorsen Tool & Die Inc.", "88 Quarrystone Pkwy, Elkbridge, PA 17602"),
    ("Copperline Office Products", "1207 Wrenfield Ave, Marlow Heights, IL 60917"),
    ("Marrow Creek Electrical Supply", "350 Tannery Row, Fenwick Bay, WI 53088"),
    ("Ostrander Fasteners Inc.", "19 Old Forge Ln, Ridley Pines, MI 48177"),
    ("Pinegate Janitorial Supply Co.", "702 Saltmarsh Dr, Corvan, NC 27519"),
]
CUSTOMERS = [
    ("Fenwick Hollow Bakery Inc.", "61 Larch St, Amberley, OH 44611"),
    ("Larkspur Dental Group", "2300 Meadowgate Blvd, Suite 4, Calder, IN 46320"),
    ("Quarry Lane Builders LLC", "915 Quarry Lane, Westhollow, PA 17544"),
    ("Ashgrove Veterinary Clinic", "48 Birchmoor Rd, Tessaly, MI 48402"),
    ("Sundial Print Works", "377 Gable Ct, Norrow, WI 53210"),
]
PRODUCTS = [
    ("Nitrile gloves, box of 100", 8.75), ("Shop towels, case of 12 rolls", 31.40),
    ("Hex bolt 3/8 x 2 in, box of 50", 14.20), ("Safety glasses, clear lens", 4.95),
    ("Copy paper, 10-ream case", 52.00), ("LED tube lamp 4 ft", 11.60),
    ("Cable ties 8 in, bag of 500", 18.30), ("Floor cleaner concentrate 1 gal", 23.85),
    ("Toner cartridge, black", 89.00), ("Extension cord 25 ft 12 AWG", 37.50),
    ("Packing tape 2 in, case of 36", 64.80), ("Work gloves, leather palm", 9.40),
    ("Stretch wrap 18 in x 1500 ft", 27.95), ("Wire nuts assorted, jar", 12.15),
    ("Trash liners 55 gal, case", 41.25), ("Machine screw kit", 19.99),
]
EMPLOYERS = [
    ("Tamberlane Freight Systems Inc.", "4419 Corvid Way, Elkbridge, PA 17602"),
    ("Glasswing Pediatrics PLLC", "800 Holloway Sq, Calder, IN 46320"),
    ("Redfern Mills Bakery Co.", "12 Granary Rd, Amberley, OH 44611"),
    ("Northmere Software Labs LLC", "2700 Lakeview Ter, Norrow, WI 53210"),
    ("Hollis & Vane Landscaping", "95 Fieldstone Dr, Corvan, NC 27519"),
]
FIRST = ["Dana", "Ravi", "Marisol", "Theo", "Imani", "Calvin", "Priya", "Oskar", "Lena",
         "Jonah", "Wren", "Tomasz"]
LAST = ["Whitcombe", "Okafor", "Lindqvist", "Ferreira", "Haddad", "Brennan", "Sato", "Mbeki",
        "Castellano", "Varga", "Prewitt", "Aldana"]
CARRIERS = [
    ("Granite Harbor Mutual Insurance Co.", "GHM"),
    ("Bluefen Casualty Company", "BFC"),
    ("Northlight Specialty Insurance", "NLS"),
]
LOSS_DESCRIPTIONS = [
    "Slip on wet floor, wrist sprain", "Lifting strain, lower back", "Laceration, box cutter",
    "Forklift contact, foot", "Repetitive motion, shoulder", "Fall from ladder, knee",
    "Vehicle backing, rear bumper", "Water damage, stock room", "Customer trip, parking lot",
    "Burn, fryer splash", "Eye irritation, chemical", "Pinch point, conveyor",
]


# ---------------------------------------------------------------- helpers

def money(x: float) -> str:
    return f"${x:,.2f}"


def plain(x: float) -> str:
    return f"{x:,.2f}"


def us_date(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def long_date(d: date) -> str:
    return d.strftime("%B %-d, %Y")


def r2(x: float) -> float:
    return round(x + 1e-9, 2)


class Doc:
    """Collects ground truth while the page is drawn."""

    def __init__(self, doc_id: str, doc_type: str, path: Path):
        self.doc_id, self.doc_type = doc_id, doc_type
        self.c = canvas.Canvas(str(path), pagesize=letter, invariant=1)  # byte-reproducible
        self.c.setTitle(f"Synthetic {doc_type} {doc_id}")
        self.page = 1
        self.fields: dict[str, dict] = {}
        self.items: list[dict] = []

    def text(self, x, y, s, size=10, bold=False, right=False):
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        (self.c.drawRightString if right else self.c.drawString)(x, y, s)

    def field(self, name, value, text):
        self.fields[name] = {"value": value, "page": self.page, "text": text}

    def missing(self, name):
        self.fields[name] = {"value": None, "page": None, "text": None}

    def footer(self, total_pages):
        self.text(40, 30, FOOTER, size=7)
        self.text(W - 40, 30, f"Page {self.page} of {total_pages}", size=7, right=True)

    def new_page(self, total_pages):
        self.footer(total_pages)
        self.c.showPage()
        self.page += 1

    def save(self, total_pages):
        self.footer(total_pages)
        self.c.save()


# ---------------------------------------------------------------- invoices

def make_invoice(rng: random.Random, doc_id: str, path: Path, variant: str, layout: str) -> Doc:
    d = Doc(doc_id, "invoice", path)
    vendor, vaddr = rng.choice(VENDORS)
    customer, caddr = rng.choice(CUSTOMERS)
    n_items = 26 if variant == "two_page" else rng.randint(3, 7)
    picks = [rng.choice(PRODUCTS) for _ in range(n_items)]
    items = []
    for desc, price in picks:
        qty = rng.randint(1, 24)
        items.append((desc, qty, price, r2(qty * price)))
    subtotal = r2(sum(i[3] for i in items))
    rate = rng.choice([0.0575, 0.0625, 0.07])
    tax = r2(subtotal * rate)
    total = r2(subtotal + tax)
    printed_total = r2(total + rng.choice([90.00, 125.50, 18.00])) if variant == "total_mismatch" \
        else total
    inv_date = date(2026, rng.randint(1, 9), rng.randint(1, 28))
    net = rng.choice([15, 30, 45])
    due = inv_date + timedelta(days=net)
    number = (f"INV-{rng.randint(20000, 29999)}" if layout == "A"
              else f"B{rng.randint(100000, 999999)}")
    po = f"PO-{rng.randint(4000, 9999)}"
    fmt = us_date if layout == "A" else long_date
    pages = 2 if variant == "two_page" else 1

    # header
    d.text(40, H - 60, vendor, size=15, bold=True)
    d.field("vendor_name", vendor, vendor)
    d.text(40, H - 76, vaddr, size=9)
    d.text(W - 40, H - 60, "INVOICE" if layout == "A" else "BILL", size=18, bold=True, right=True)
    label_x, val_x, y = 360, W - 40, H - 100
    rows = [
        ("Invoice No.:" if layout == "A" else "Bill Number:", "invoice_number", number, number),
        ("Invoice Date:" if layout == "A" else "Date Issued:", "invoice_date", inv_date,
         fmt(inv_date)),
        ("Due Date:" if layout == "A" else "Payment Due:", "due_date", due, fmt(due)),
        ("Terms:", "payment_terms", f"Net {net}", f"Net {net}"),
        ("PO Number:" if layout == "A" else "Customer PO:", "po_number", po, po),
    ]
    for label, name, value, shown in rows:
        if variant == "missing_field" and name == "invoice_date":
            d.missing(name)
            continue
        d.text(label_x, y, label, size=9, bold=True)
        d.text(val_x, y, shown, size=9, right=True)
        d.field(name, value.isoformat() if isinstance(value, date) else value, f"{label} {shown}")
        y -= 14
    d.text(40, H - 110, "Bill To:" if layout == "A" else "Customer:", size=9, bold=True)
    d.text(40, H - 124, customer, size=10)
    d.field("customer_name", customer, customer)
    d.text(40, H - 137, caddr, size=9)

    # line items
    cols = (40, 360, 450, W - 40)
    head = ("Description", "Qty", "Unit Price", "Amount") if layout == "A" else \
        ("Item", "Quantity", "Rate", "Line Total")

    def header_row(y):
        d.text(cols[0], y, head[0], size=9, bold=True)
        d.text(cols[1] + 30, y, head[1], size=9, bold=True, right=True)
        d.text(cols[2] + 60, y, head[2], size=9, bold=True, right=True)
        d.text(cols[3], y, head[3], size=9, bold=True, right=True)
        d.c.line(40, y - 4, W - 40, y - 4)

    y = H - 200
    header_row(y)
    y -= 18
    for i, (desc, qty, price, amount) in enumerate(items):
        if variant == "two_page" and i == 18:
            d.text(W - 40, y - 6, "Continued on next page", size=8, right=True)
            d.new_page(pages)
            y = H - 60
            d.text(40, y, f"{vendor} - {number} (continued)", size=10, bold=True)
            y -= 30
            header_row(y)
            y -= 18
        cells = (desc, str(qty), plain(price), plain(amount))
        d.text(cols[0], y, cells[0], size=9)
        d.text(cols[1] + 30, y, cells[1], size=9, right=True)
        d.text(cols[2] + 60, y, cells[2], size=9, right=True)
        d.text(cols[3], y, cells[3], size=9, right=True)
        d.items.append({"description": desc, "quantity": qty, "unit_price": price,
                        "amount": amount, "page": d.page, "text": " ".join(cells)})
        y -= 15

    # totals
    y -= 10
    d.c.line(360, y + 8, W - 40, y + 8)
    for label, name, value in (
        ("Subtotal", "subtotal", subtotal),
        (f"Sales Tax ({rate * 100:.2f}%)", "tax", tax),
        ("Total Due" if layout == "A" else "Amount Due", "total", printed_total),
    ):
        d.text(360, y, label, size=10, bold=(name == "total"))
        d.text(W - 40, y, money(value), size=10, bold=(name == "total"), right=True)
        d.field(name, value, f"{label} {money(value)}")
        y -= 16
    d.text(40, 90, f"Please remit to {vendor}, {vaddr}.", size=8)
    d.text(40, 78, f"Reference invoice {number} with your payment.", size=8)
    d.save(pages)
    d.pages = pages
    return d


# ---------------------------------------------------------------- W-2

def mask_ssn(ssn: str) -> str:
    return "XXX-XX-" + ssn[-4:]


def make_w2(rng: random.Random, doc_id: str, path: Path, variant: str) -> Doc:
    d = Doc(doc_id, "w2", path)
    employer, eaddr = rng.choice(EMPLOYERS)
    first, last = rng.choice(FIRST), rng.choice(LAST)
    ssn = f"000-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}"
    ein = f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}"
    gross = r2(rng.uniform(38000, 142000))
    pretax_401k = r2(gross * rng.choice([0.0, 0.03, 0.05, 0.06]))
    box1 = r2(gross - pretax_401k)
    box3 = box5 = gross
    box2 = r2(box1 * rng.uniform(0.08, 0.17))
    box4 = r2(box3 * 0.062)
    box6 = r2(box5 * 0.0145)
    if variant == "ss_tax_mismatch":
        box4 = r2(box4 + 400.00)

    d.text(40, H - 50, "Form W-2  Wage and Tax Statement", size=14, bold=True)
    d.text(W - 40, H - 50, "2025", size=18, bold=True, right=True)
    d.field("tax_year", 2025, "2025")
    d.text(40, H - 64, "Copy B - To Be Filed With Employee's FEDERAL Tax Return "
           "(synthetic sample, not an IRS form)", size=8)

    def box(x, y, w, h, label, value, name=None, truth_value=None, size=10):
        d.c.rect(x, y, w, h)
        d.text(x + 4, y + h - 10, label, size=7)
        if value is not None:
            d.text(x + 6, y + 8, value, size=size)
        if name:
            if value is None:
                d.missing(name)
            elif name == "employee_ssn":  # truth never holds the full number, even as a citation
                d.field(name, truth_value, truth_value)
            else:
                d.field(name, truth_value if truth_value is not None else value, value)

    top = H - 140
    box(40, top, 260, 50, "a  Employee's social security number", ssn, "employee_ssn",
        mask_ssn(ssn))
    box(300, top, 270, 50, "b  Employer identification number (EIN)",
        None if variant == "missing_field" else ein, "employer_ein")
    box(40, top - 90, 260, 90, "c  Employer's name, address, and ZIP code", None)
    d.text(46, top - 30, employer, size=10)
    d.field("employer_name", employer, employer)
    d.text(46, top - 44, eaddr, size=8)
    box(40, top - 150, 260, 60, "e  Employee's first name and initial    Last name", None)
    d.text(46, top - 120, f"{first} {last}", size=11)
    d.field("employee_name", f"{first} {last}", f"{first} {last}")
    d.text(46, top - 134, f"{rng.randint(10, 999)} {rng.choice(LAST)} St, Calder, IN 46320",
           size=8)
    amounts = [
        ("1  Wages, tips, other compensation", "wages", box1),
        ("2  Federal income tax withheld", "federal_income_tax_withheld", box2),
        ("3  Social security wages", "social_security_wages", box3),
        ("4  Social security tax withheld", "social_security_tax_withheld", box4),
        ("5  Medicare wages and tips", "medicare_wages", box5),
        ("6  Medicare tax withheld", "medicare_tax_withheld", box6),
    ]
    for i, (label, name, value) in enumerate(amounts):
        col, row = i % 2, i // 2
        box(300 + col * 135, top - 50 - row * 50, 135, 50, label, plain(value), name, value)
    box(40, top - 210, 260, 50, "12a  See instructions for box 12",
        f"D  {plain(pretax_401k)}" if pretax_401k else "")
    d.text(40, 120, "Department of the Treasury - Internal Revenue Service (form layout imitated "
           "for testing only)", size=7)
    d.save(1)
    d.pages = 1
    return d


# ---------------------------------------------------------------- loss runs

def make_loss_run(rng: random.Random, doc_id: str, path: Path, variant: str, layout: str) -> Doc:
    d = Doc(doc_id, "loss_run", path)
    carrier, prefix = rng.choice(CARRIERS)
    insured, _ = rng.choice(CUSTOMERS + EMPLOYERS)
    lob = rng.choice(["Workers Compensation", "General Liability", "Commercial Auto"])
    lob_code = {"Workers Compensation": "WC", "General Liability": "GL",
                "Commercial Auto": "CA"}[lob]
    start = date(2024, rng.choice([1, 4, 7, 10]), 1)
    end = date(start.year + 1, start.month, 1)
    valuation = date(2026, 9, 30)
    policy = f"{prefix}-{lob_code}-{start.year}-{rng.randint(100000, 999999)}"
    n = {"two_page": 34, "no_claims": 0}.get(variant, rng.randint(3, 8))
    claims = []
    for _ in range(n):
        dol = start + timedelta(days=rng.randint(3, 360))
        closed = rng.random() < 0.55
        paid = r2(rng.uniform(250, 48000))
        reserved = 0.0 if closed else r2(rng.uniform(500, 30000))
        claims.append({"claim_number": f"{prefix}{start.year % 100}-{rng.randint(10000, 99999)}",
                       "date_of_loss": dol, "status": "closed" if closed else "open",
                       "paid": paid, "reserved": reserved, "incurred": r2(paid + reserved),
                       "description": rng.choice(LOSS_DESCRIPTIONS)})
    claims.sort(key=lambda c: c["date_of_loss"])
    if variant == "date_out_of_period":
        claims[1]["date_of_loss"] = end + timedelta(days=rng.randint(20, 80))
    tot_paid = r2(sum(c["paid"] for c in claims))
    tot_res = r2(sum(c["reserved"] for c in claims))
    tot_inc = r2(sum(c["incurred"] for c in claims))
    if variant == "total_mismatch":
        tot_inc = r2(tot_inc + 5000.00)
    fmt = us_date if layout == "A" else (lambda x: x.isoformat())
    pages = 2 if variant == "two_page" else 1

    d.text(40, H - 55, carrier, size=15, bold=True)
    d.field("carrier_name", carrier, carrier)
    d.text(W - 40, H - 55, "LOSS RUN REPORT" if layout == "A" else "Claims Experience Summary",
           size=12, bold=True, right=True)
    y = H - 90
    period = f"{fmt(start)} - {fmt(end)}" if layout == "A" else f"{fmt(start)} to {fmt(end)}"
    for label, name, value, shown in (
        ("Named Insured:", "insured_name", insured, insured),
        ("Policy Number:", "policy_number", policy, policy),
        ("Line of Business:", None, lob, lob),
        ("Policy Period:", "policy_period", None, period),
        ("Valuation Date:", "valuation_date", valuation.isoformat(), fmt(valuation)),
    ):
        d.text(40, y, label, size=9, bold=True)
        d.text(150, y, shown, size=9)
        if name == "policy_period":
            d.field("policy_period_start", start.isoformat(), f"{label} {shown}")
            d.field("policy_period_end", end.isoformat(), f"{label} {shown}")
        elif name:
            d.field(name, value, f"{label} {shown}")
        y -= 14

    cols = [(40, "Claim No.", False), (118, "Loss Date", False), (190, "Description", False),
            (385, "Status", False), (470, "Paid", True), (522, "Reserve", True),
            (W - 40, "Incurred", True)]
    if layout == "B":
        cols[3] = (385, "Open/Closed", False)
        cols[5] = (522, "Outstanding", True)

    def header_row(y):
        for x, label, right in cols:
            d.text(x, y, label, size=8, bold=True, right=right)
        d.c.line(40, y - 4, W - 40, y - 4)

    y -= 20
    header_row(y)
    y -= 16
    if not claims:
        d.text(40, y, "No claims reported for this policy period.", size=9)
        y -= 16
    for k, cl in enumerate(claims):
        if variant == "two_page" and k == 26:
            d.new_page(pages)
            y = H - 60
            d.text(40, y, f"{carrier} - Policy {policy} (continued)", size=10, bold=True)
            y -= 28
            header_row(y)
            y -= 16
        status = cl["status"].title() if layout == "A" else cl["status"].upper()
        cells = (cl["claim_number"], fmt(cl["date_of_loss"]), cl["description"], status,
                 plain(cl["paid"]), plain(cl["reserved"]), plain(cl["incurred"]))
        for (x, _, right), s in zip(cols, cells, strict=True):
            d.text(x, y, s, size=8, right=right)
        d.items.append({"claim_number": cl["claim_number"],
                        "date_of_loss": cl["date_of_loss"].isoformat(), "status": cl["status"],
                        "paid": cl["paid"], "reserved": cl["reserved"],
                        "incurred": cl["incurred"], "page": d.page, "text": " ".join(cells)})
        y -= 14
    y -= 6
    d.c.line(40, y + 10, W - 40, y + 10)
    d.text(40, y, f"Totals ({len(claims)} claims)", size=8, bold=True)
    for (x, _, _), value in zip(cols[4:], (tot_paid, tot_res, tot_inc), strict=True):
        d.text(x, y, plain(value), size=8, bold=True, right=True)
    totals_text = (f"Totals ({len(claims)} claims) "
                   f"{plain(tot_paid)} {plain(tot_res)} {plain(tot_inc)}")
    d.field("total_paid", tot_paid, totals_text)
    d.field("total_reserved", tot_res, totals_text)
    d.field("total_incurred", tot_inc, totals_text)
    d.text(40, 60, f"Valued as of {fmt(valuation)}. Reserves are estimates and may change.", size=7)
    d.save(pages)
    d.pages = pages
    return d


# ---------------------------------------------------------------- scans

def rasterize(pdf: Path, out: Path, rng: random.Random, as_pdf: bool) -> None:
    """Render page 1 to an image, rotate slightly, add speckle noise and blur."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "130", "-gray", "-png", "-f", "1", "-l", "1",
                        str(pdf), f"{tmp}/p"], check=True)
        img = Image.open(next(Path(tmp).glob("p*.png"))).convert("L")
    img = img.rotate(rng.uniform(-2.2, 2.2), resample=Image.BICUBIC, expand=True, fillcolor=255)
    px = img.load()
    for _ in range(img.width * img.height // 120):
        x, y = rng.randrange(img.width), rng.randrange(img.height)
        px[x, y] = rng.randint(0, 120) if rng.random() < 0.5 else 255
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    if as_pdf:
        img.save(out, "PDF", resolution=130)
    else:
        img.save(out, "PNG", optimize=True)


# ---------------------------------------------------------------- plan

PLAN = [
    # doc_id, type, variant, layout
    ("inv-01", "invoice", "standard", "A"), ("inv-02", "invoice", "standard", "B"),
    ("inv-03", "invoice", "standard", "A"), ("inv-04", "invoice", "standard", "B"),
    ("inv-05", "invoice", "two_page", "A"), ("inv-06", "invoice", "total_mismatch", "B"),
    ("inv-07", "invoice", "missing_field", "A"), ("inv-08", "invoice", "scanned_png", "B"),
    ("inv-09", "invoice", "scanned_pdf", "A"), ("inv-10", "invoice", "standard", "B"),
    ("w2-01", "w2", "standard", "A"), ("w2-02", "w2", "standard", "A"),
    ("w2-03", "w2", "standard", "A"), ("w2-04", "w2", "standard", "A"),
    ("w2-05", "w2", "missing_field", "A"), ("w2-06", "w2", "ss_tax_mismatch", "A"),
    ("w2-07", "w2", "scanned_png", "A"), ("w2-08", "w2", "scanned_pdf", "A"),
    ("w2-09", "w2", "standard", "A"), ("w2-10", "w2", "standard", "A"),
    ("lr-01", "loss_run", "standard", "A"), ("lr-02", "loss_run", "standard", "B"),
    ("lr-03", "loss_run", "standard", "A"), ("lr-04", "loss_run", "two_page", "B"),
    ("lr-05", "loss_run", "total_mismatch", "A"), ("lr-06", "loss_run", "date_out_of_period", "B"),
    ("lr-07", "loss_run", "no_claims", "A"), ("lr-08", "loss_run", "scanned_png", "B"),
    ("lr-09", "loss_run", "scanned_pdf", "A"), ("lr-10", "loss_run", "standard", "B"),
]
# Why each hard case should land in review. Standard, two-page and no-claims documents
# have no expected reason, so a review route there is a false alarm.
EXPECTED_REASON = {
    "total_mismatch": "rule_failed", "ss_tax_mismatch": "rule_failed",
    "date_out_of_period": "rule_failed", "missing_field": "missing_required",
    "scanned_png": "no_text_layer", "scanned_pdf": "no_text_layer",
}


def generate(out_root: Path = ROOT) -> list[dict]:
    docs_dir, truth_dir = out_root / "docs", out_root / "truth"
    for p in (docs_dir, truth_dir):
        shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True)
    rng = random.Random(SEED)
    manifest = []
    for doc_id, doc_type, variant, layout in PLAN:
        scanned = variant.startswith("scanned")
        base_variant = "standard" if scanned else variant
        pdf = docs_dir / f"{doc_id}.pdf"
        if doc_type == "invoice":
            d = make_invoice(rng, doc_id, pdf, base_variant, layout)
        elif doc_type == "w2":
            d = make_w2(rng, doc_id, pdf, base_variant)
        else:
            d = make_loss_run(rng, doc_id, pdf, base_variant, layout)
        file = pdf
        if variant == "scanned_png":
            file = docs_dir / f"{doc_id}.png"
            rasterize(pdf, file, rng, as_pdf=False)
            pdf.unlink()
        elif variant == "scanned_pdf":
            scan = docs_dir / f"{doc_id}-scan.pdf"
            rasterize(pdf, scan, rng, as_pdf=True)
            pdf.unlink()
            file = docs_dir / f"{doc_id}.pdf"
            scan.rename(file)
        item_key = {"invoice": "line_items", "loss_run": "claims"}.get(doc_type)
        truth = {
            "doc_id": doc_id, "doc_type": doc_type, "file": f"docs/{file.name}",
            "media_type": "image/png" if file.suffix == ".png" else "application/pdf",
            "pages": d.pages, "variant": variant, "layout": layout,
            "expected_review": variant in EXPECTED_REASON,
            "expected_reason": EXPECTED_REASON.get(variant),
            "fields": d.fields,
        }
        if item_key:
            truth[item_key] = d.items
        (truth_dir / f"{doc_id}.json").write_text(json.dumps(truth, indent=2) + "\n")
        manifest.append({k: truth[k] for k in ("doc_id", "doc_type", "file", "variant",
                                                "expected_review")})
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    m = generate()
    print(f"wrote {len(m)} documents to {DOCS}")
