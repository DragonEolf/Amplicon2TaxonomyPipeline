from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
except ImportError as exc:  # pragma: no cover - friendly runtime error
    raise SystemExit(
        "This report generator needs reportlab.\n"
        "Install it with: python3 -m pip install reportlab"
    ) from exc


RANKS = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
DEFAULT_DB_PRIORITY = ["SILVA", "RDP", "Greengenes2", "UNITE"]
BRAND_BLUE = colors.HexColor("#123D6A")
BRAND_CYAN = colors.HexColor("#18A4C7")
BRAND_GREEN = colors.HexColor("#68B545")
BRAND_GRAY = colors.HexColor("#5E6A71")
LIGHT_BLUE = colors.HexColor("#EAF6FA")
LIGHT_GRAY = colors.HexColor("#F3F5F7")
DARK = colors.HexColor("#1D252C")
PIE_MIN_PERCENT = 3.5
PIE_MAX_SLICES = 8
PIE_COLORS = [
    colors.HexColor("#0072B2"),
    colors.HexColor("#009E73"),
    colors.HexColor("#E69F00"),
    colors.HexColor("#CC79A7"),
    colors.HexColor("#56B4E9"),
    colors.HexColor("#D55E00"),
    colors.HexColor("#6A3D9A"),
    colors.HexColor("#8C8C2A"),
    colors.HexColor("#4E79A7"),
    colors.HexColor("#59A14F"),
    colors.HexColor("#B07AA1"),
    colors.HexColor("#9C755F"),
]
OTHER_COLOR = colors.HexColor("#B8C0C7")
UNCLASSIFIED_COLOR = colors.HexColor("#6F7780")
KNOWN_TAXON_COLORS = {
    "Archaea": colors.HexColor("#6A3D9A"),
    "Bacteria": BRAND_GREEN,
    "Eukaryota": BRAND_CYAN,
    "Fungi": colors.HexColor("#9C755F"),
    "Metazoa": colors.HexColor("#4E79A7"),
    "Viridiplantae": colors.HexColor("#59A14F"),
}


def main() -> None:
    args = parse_args()
    generate_report_from_csv(
        args.csv,
        output=args.output,
        sample=args.sample,
        database=args.database,
        min_bootstrap=args.min_bootstrap,
        title=args.title,
        matches_csv=args.matches_csv,
    )


def generate_report_from_csv(
    csv_path: Path,
    output: Path | None = None,
    sample: str | None = None,
    database: str = "SILVA",
    min_bootstrap: float = 50.0,
    title: str = "16S Metagenomics Report",
    matches_csv: Path | None = None,
) -> Path:
    rows = read_rows(csv_path)
    records = collapse_asv_records(rows, database=database, min_bootstrap=min_bootstrap)
    if not records:
        raise SystemExit("No ASV records found in the CSV.")

    sample_id = sample or infer_sample_id(records, csv_path)
    output = output or csv_path.with_suffix(".genepath_report.pdf")
    report = build_report_data(records)
    matches = read_matches(matches_csv) if matches_csv else []
    draw_report(output, sample_id, report, title, matches=matches)
    print(f"Wrote {output}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a GenePath-branded microbiome taxonomy PDF from taxonomy_long.csv."
    )
    parser.add_argument("csv", type=Path, help="Input taxonomy_long.csv")
    parser.add_argument("-o", "--output", type=Path, help="Output PDF path")
    parser.add_argument("--sample", help="Sample name shown on the report")
    parser.add_argument(
        "--database",
        default="SILVA",
        help="Taxonomy source: SILVA, RDP, Greengenes2, UNITE, consensus, or first. Default: SILVA",
    )
    parser.add_argument(
        "--min-bootstrap",
        type=float,
        default=50.0,
        help="Minimum bootstrap confidence to report a taxonomic rank. Lower ranks are blanked after the first failed rank. Default: 50",
    )
    parser.add_argument("--title", default="16S Metagenomics Report", help="Report title")
    parser.add_argument("--matches-csv", type=Path, help="Optional closest_matches.csv from the classifier")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("rt", newline="") as handle:
        return list(csv.DictReader(handle))


def read_matches(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("rt", newline="") as handle:
        return list(csv.DictReader(handle))


def collapse_asv_records(rows: list[dict[str, str]], database: str, min_bootstrap: float) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("asv_id", "")].append(row)

    records = []
    for asv_id, asv_rows in grouped.items():
        chosen = choose_taxonomy_row(asv_rows, database)
        reads = int(float(chosen.get("reads") or 0))
        lineage = lineage_from_row(chosen, database, min_bootstrap)
        records.append(
            {
                "asv_id": asv_id,
                "reads": reads,
                "sequence": chosen.get("sequence", ""),
                "job_id": chosen.get("job_id", ""),
                "marker": chosen.get("marker", ""),
                "database": chosen.get("database", ""),
                "lineage": lineage,
            }
        )
    return records


def choose_taxonomy_row(rows: list[dict[str, str]], database: str) -> dict[str, str]:
    if database.lower() in {"consensus", "first"}:
        for db in DEFAULT_DB_PRIORITY:
            for row in rows:
                if row.get("database") == db:
                    return row
        return rows[0]

    for row in rows:
        if row.get("database", "").lower() == database.lower():
            return row
    return rows[0]


def lineage_from_row(row: dict[str, str], database: str, min_bootstrap: float) -> dict[str, str]:
    if database.lower() == "consensus":
        consensus = row.get("consensus_taxonomy", "").strip()
        if consensus:
            parts = [clean_taxon(part) for part in consensus.split(";")]
            return {rank: parts[i] if i < len(parts) else "" for i, rank in enumerate(RANKS)}

    lineage = {}
    still_classified = True
    for rank in RANKS:
        taxon, bootstrap = split_taxon_bootstrap(row.get(rank, ""))
        if not still_classified or not taxon:
            lineage[rank] = ""
            still_classified = False
            continue
        if bootstrap is not None and bootstrap < min_bootstrap:
            lineage[rank] = ""
            still_classified = False
            continue
        lineage[rank] = taxon
    return lineage


def clean_taxon(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"\s+\(\d+(\.\d+)?\)$", "", value)
    value = value.strip("; ")
    return value


def split_taxon_bootstrap(value: str) -> tuple[str, float | None]:
    value = (value or "").strip()
    match = re.match(r"^(.*?)\s+\((\d+(?:\.\d+)?)\)$", value)
    if match:
        return match.group(1).strip(), float(match.group(2))
    return clean_taxon(value), None


def infer_sample_id(records: list[dict[str, object]], csv_path: Path) -> str:
    job_id = str(records[0].get("job_id") or "")
    if job_id:
        return job_id
    return csv_path.stem


def build_report_data(records: list[dict[str, object]]) -> dict[str, object]:
    total_reads = sum(int(record["reads"]) for record in records)
    asv_count = len(records)
    classified_by_rank = {}
    top_by_rank = {}
    all_by_rank = {}
    category_counts = {}

    for rank in RANKS:
        counts: dict[str, int] = defaultdict(int)
        classified_reads = 0
        for record in records:
            reads = int(record["reads"])
            taxon = str(record["lineage"].get(rank, ""))  # type: ignore[index]
            if taxon:
                counts[taxon] += reads
                classified_reads += reads

        unclassified = max(total_reads - classified_reads, 0)
        rows = sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))
        all_by_rank[rank] = rows
        top_by_rank[rank] = rows[:8]
        category_counts[rank] = len(counts)
        classified_by_rank[rank] = {
            "reads": classified_reads,
            "percent": percent(classified_reads, total_reads),
            "unclassified": unclassified,
        }

    return {
        "total_reads": total_reads,
        "asv_count": asv_count,
        "classified_by_rank": classified_by_rank,
        "top_by_rank": top_by_rank,
        "all_by_rank": all_by_rank,
        "category_counts": category_counts,
    }


def percent(part: int, whole: int) -> float:
    return (part / whole * 100.0) if whole else 0.0


def draw_report(
    output: Path,
    sample_id: str,
    report: dict[str, object],
    title: str,
    matches: list[dict[str, str]] | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=letter)

    draw_cover(c, sample_id, title)
    draw_summary_page(c, sample_id, report, title)
    next_page = 3
    if matches:
        draw_match_evidence_page(c, matches, title, next_page)
        next_page += 1
    draw_kingdom_page(c, report, title, next_page)
    for rank in RANKS[1:]:
        draw_rank_page(c, report, rank, title, next_page)
    c.save()


def draw_cover(c: canvas.Canvas, sample_id: str, title: str) -> None:
    w, h = letter
    c.setFillColor(BRAND_BLUE)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(BRAND_CYAN)
    c.rect(0, h - 1.15 * inch, w, 0.12 * inch, fill=1, stroke=0)
    c.setFillColor(BRAND_GREEN)
    c.rect(0, h - 1.02 * inch, w, 0.08 * inch, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(0.8 * inch, h - 2.1 * inch, title)
    c.setFont("Helvetica", 15)
    c.drawString(0.8 * inch, h - 2.6 * inch, f"Sample: {sample_id}")
    c.setFont("Helvetica", 11)
    c.drawString(0.8 * inch, h - 3.0 * inch, f"Report Date: {now_utc()}")

    draw_logo(c, 0.8 * inch, 0.95 * inch, large=True)
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.white)
    c.drawRightString(w - 0.8 * inch, 0.9 * inch, "Generated from taxonomy_long.csv")
    c.showPage()


def draw_summary_page(c: canvas.Canvas, sample_id: str, report: dict[str, object], title: str) -> None:
    header(c, title, 2)
    y = 700
    section_title(c, "Sample Configuration", y)
    y -= 28
    key_values(
        c,
        [
            ("Sample ID", sample_id),
            ("Input Type", "taxonomy_long.csv"),
            ("Report Source", "GenePath ASV Taxonomy Pipeline"),
        ],
        72,
        y,
    )

    y -= 100
    section_title(c, "Sample Information", y)
    y -= 36
    total_reads = int(report["total_reads"])
    asv_count = int(report["asv_count"])
    summary_rows = [
        ["Total Reads", "ASVs", "Report Mode"],
        [fmt_int(total_reads), fmt_int(asv_count), "Taxonomy summary"],
    ]
    draw_table(c, summary_rows, 72, y, [140, 100, 180], row_h=26, header_fill=BRAND_BLUE)

    y -= 105
    section_title(c, "Classification Statistics", y)
    y -= 26
    stats = [["Taxonomic Level", "Reads Classified", "% Total Reads"]]
    classified = report["classified_by_rank"]  # type: ignore[assignment]
    for rank in RANKS:
        item = classified[rank]
        stats.append([rank.title(), fmt_int(item["reads"]), f"{item['percent']:.2f} %"])
    draw_table(c, stats, 72, y, [160, 135, 130], row_h=22, header_fill=BRAND_BLUE)
    footer(c, 2)
    c.showPage()


def draw_kingdom_page(c: canvas.Canvas, report: dict[str, object], title: str, page: int = 3) -> None:
    header(c, title, page)
    section_title(c, "Classification Results by Taxonomic Level", 700)
    c.setFont("Helvetica", 10)
    c.setFillColor(DARK)
    c.drawString(72, 675, "Tables show the highest 8 taxonomic classifications at each level.")
    c.drawString(72, 660, "Charts show dominant classifications; smaller and tail categories are grouped as Other.")
    draw_rank_body(c, report, "kingdom", 620)
    footer(c, page)
    c.showPage()


def draw_match_evidence_page(c: canvas.Canvas, matches: list[dict[str, str]], title: str, page: int) -> None:
    header(c, title, page)
    section_title(c, "Nearest Reference Evidence", 700)
    c.setFont("Helvetica", 10)
    c.setFillColor(DARK)
    c.drawString(72, 675, "Top-ranked reference matches provide identity evidence for ASV-level calls.")

    best_by_asv = {}
    for match in matches:
        if match.get("rank") == "1" and match.get("asv_id") not in best_by_asv:
            best_by_asv[match.get("asv_id", "")] = match

    table_rows = [["ASV", "Database", "Identity", "Species", "Reference"]]
    ordered = sorted(
        best_by_asv.values(),
        key=lambda row: (-float(row.get("identity") or 0), row.get("asv_id", "")),
    )
    for match in ordered[:18]:
        table_rows.append(
            [
                match.get("asv_id", ""),
                match.get("database", ""),
                f"{float(match.get('identity') or 0):.2f} %",
                match.get("species", ""),
                match.get("reference_id", ""),
            ]
        )

    draw_table(c, table_rows, 72, 635, [80, 82, 72, 155, 100], row_h=23, header_fill=BRAND_BLUE)
    c.setFont("Helvetica", 8.5)
    c.setFillColor(BRAND_GRAY)
    c.drawString(72, 84, "Full top-5 evidence is available in closest_matches.csv.")
    footer(c, page)
    c.showPage()


def draw_rank_page(c: canvas.Canvas, report: dict[str, object], rank: str, title: str, page_offset: int = 3) -> None:
    page = RANKS.index(rank) + page_offset
    header(c, title, page)
    draw_rank_body(c, report, rank, 690)
    footer(c, page)
    c.showPage()


def draw_rank_body(c: canvas.Canvas, report: dict[str, object], rank: str, y: float) -> None:
    total_reads = int(report["total_reads"])
    top_by_rank = report["top_by_rank"]  # type: ignore[assignment]
    all_by_rank = report["all_by_rank"]  # type: ignore[assignment]
    classified_by_rank = report["classified_by_rank"]  # type: ignore[assignment]
    category_counts = report["category_counts"]  # type: ignore[assignment]
    unclassified = classified_by_rank[rank]["unclassified"]

    section_title(c, f"Top {rank.title()} Classification Results", y)
    y -= 30
    table_rows = [["Classification", "Number of Reads", "% Total Reads"]]
    if unclassified:
        table_rows.append([f"Unclassified at {rank.title()} level", fmt_int(unclassified), f"{percent(unclassified, total_reads):.2f} %"])
    for taxon, reads in top_by_rank[rank]:
        table_rows.append([taxon, fmt_int(reads), f"{percent(reads, total_reads):.2f} %"])
    table_rows = table_rows[:9]
    draw_table(c, table_rows, 72, y, [265, 120, 105], row_h=24, header_fill=BRAND_BLUE)

    table_bottom = y - (len(table_rows) * 24)
    chart_items = list(all_by_rank[rank])
    if unclassified:
        chart_items.append(("Unclassified", unclassified))
    chart_y = max(185, table_bottom - 95)
    draw_pie(c, chart_items, total_reads, 155, chart_y, 58)

    note_y = min(chart_y - 82, 145)
    c.setFont("Helvetica", 9)
    c.setFillColor(DARK)
    c.drawString(
        72,
        note_y,
        f"Total {rank.title()}-level taxonomic categories identified: {category_counts[rank]}. "
        f"This table shows the top {min(8, len(top_by_rank[rank]))} classifications.",
    )
    c.drawString(72, note_y - 15, f'Note: "Other" groups taxa below {PIE_MIN_PERCENT:.2f}% abundance plus any tail categories beyond the legend limit.')


def header(c: canvas.Canvas, title: str, page: int) -> None:
    w, h = letter
    c.setFillColor(colors.white)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(BRAND_BLUE)
    c.rect(0, h - 0.62 * inch, w, 0.62 * inch, fill=1, stroke=0)
    c.setFillColor(BRAND_CYAN)
    c.rect(0, h - 0.69 * inch, w, 0.07 * inch, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, h - 0.42 * inch, title)
    draw_logo(c, w - 158, h - 0.49 * inch)


def footer(c: canvas.Canvas, page: int) -> None:
    w, _ = letter
    c.setStrokeColor(LIGHT_GRAY)
    c.line(72, 48, w - 72, 48)
    c.setFillColor(BRAND_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(72, 34, "GenePath Metagenomics Report")
    c.drawCentredString(w / 2, 34, "Generated from ASV taxonomy results")
    c.drawRightString(w - 72, 34, f"Page {page}")


def section_title(c: canvas.Canvas, text: str, y: float) -> None:
    c.setFillColor(BRAND_BLUE)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, text)
    c.setStrokeColor(BRAND_CYAN)
    c.setLineWidth(1.2)
    c.line(72, y - 5, 72 + min(310, stringWidth(text, "Helvetica-Bold", 14) + 28), y - 5)


def key_values(c: canvas.Canvas, items: list[tuple[str, str]], x: float, y: float) -> None:
    c.setFont("Helvetica", 10)
    for label, value in items:
        c.setFillColor(BRAND_GRAY)
        c.drawString(x, y, f"{label}:")
        c.setFillColor(DARK)
        c.drawString(x + 115, y, value[:72])
        y -= 18


def draw_table(
    c: canvas.Canvas,
    rows: list[list[str]],
    x: float,
    y: float,
    widths: list[float],
    row_h: float,
    header_fill,
) -> None:
    for r, row in enumerate(rows):
        fill = header_fill if r == 0 else (LIGHT_BLUE if r % 2 else colors.white)
        text_color = colors.white if r == 0 else DARK
        c.setFillColor(fill)
        c.rect(x, y - row_h, sum(widths), row_h, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#D8DEE3"))
        c.rect(x, y - row_h, sum(widths), row_h, fill=0, stroke=1)
        cx = x
        c.setFont("Helvetica-Bold" if r == 0 else "Helvetica", 8.8 if r else 9)
        c.setFillColor(text_color)
        for i, value in enumerate(row):
            c.drawString(cx + 6, y - row_h + 7, fit_text(str(value), widths[i] - 12, c._fontname, c._fontsize))
            cx += widths[i]
        y -= row_h


def prepare_pie_slices(items: list[tuple[str, int]], total: int) -> list[tuple[str, int]]:
    if total <= 0:
        return []

    merged: dict[str, int] = defaultdict(int)
    for name, value in items:
        if value <= 0:
            continue
        label = name.strip() or "Unclassified"
        merged[label] += value

    unclassified = merged.pop("Unclassified", 0)
    taxa = sorted(merged.items(), key=lambda item: (-item[1], item[0].casefold()))
    above_threshold = [(name, value) for name, value in taxa if percent(value, total) >= PIE_MIN_PERCENT]
    needs_other = len(above_threshold) < len(taxa)
    special_slots = 1 if unclassified else 0

    if len(above_threshold) > PIE_MAX_SLICES - special_slots:
        needs_other = True

    other_value = 0
    if needs_other:
        visible_taxa_count = max(0, PIE_MAX_SLICES - special_slots - 1)
        visible_taxa = above_threshold[:visible_taxa_count]
        visible_names = {name for name, _ in visible_taxa}
        other_value = sum(value for name, value in taxa if name not in visible_names)
    else:
        visible_taxa = above_threshold[: max(0, PIE_MAX_SLICES - special_slots)]

    slices = list(visible_taxa)
    if other_value:
        slices.append(("Other", other_value))
    if unclassified:
        slices.append(("Unclassified", unclassified))
    return slices[:PIE_MAX_SLICES]


def stable_palette_index(name: str) -> int:
    digest = hashlib.sha256(name.casefold().encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") % len(PIE_COLORS)


def pie_slice_color(name: str, used_palette_indexes: set[int]):
    if name == "Unclassified":
        return UNCLASSIFIED_COLOR
    if name == "Other":
        return OTHER_COLOR
    if name in KNOWN_TAXON_COLORS:
        return KNOWN_TAXON_COLORS[name]

    start = stable_palette_index(name)
    for offset in range(len(PIE_COLORS)):
        palette_index = (start + offset) % len(PIE_COLORS)
        if palette_index not in used_palette_indexes:
            used_palette_indexes.add(palette_index)
            return PIE_COLORS[palette_index]
    return PIE_COLORS[start]


def draw_pie(c: canvas.Canvas, items: list[tuple[str, int]], total: int, x: float, y: float, radius: float) -> None:
    slices = prepare_pie_slices(items, total)
    slice_total = sum(value for _, value in slices)
    if slice_total <= 0:
        return

    start = 90
    legend_x = x + radius + 42
    legend_y = y + radius - 4
    used_palette_indexes: set[int] = set()
    for idx, (name, value) in enumerate(slices):
        extent = 360 * value / slice_total
        c.setFillColor(pie_slice_color(name, used_palette_indexes))
        c.wedge(x - radius, y - radius, x + radius, y + radius, start, extent, fill=1, stroke=0)
        start += extent
        c.rect(legend_x, legend_y - idx * 15, 8, 8, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7.8)
        c.drawString(legend_x + 14, legend_y - idx * 15, fit_text(f"{name} ({percent(value, total):.1f}%)", 300, "Helvetica", 7.8))
    c.setStrokeColor(colors.white)
    c.setLineWidth(1)
    c.circle(x, y, radius, stroke=1, fill=0)


def draw_logo(c: canvas.Canvas, x: float, y: float, large: bool = False) -> None:
    size = 18 if not large else 34
    c.setFillColor(BRAND_GREEN)
    c.circle(x + size * 0.45, y + size * 0.38, size * 0.34, fill=1, stroke=0)
    c.setFillColor(BRAND_CYAN)
    c.circle(x + size * 0.82, y + size * 0.60, size * 0.23, fill=1, stroke=0)
    c.setFillColor(colors.white if large else BRAND_BLUE)
    c.setFont("Helvetica-Bold", 17 if large else 11)
    c.drawString(x + size * 1.25, y + size * 0.18, "GenePath")


def fit_text(text: str, width: float, font: str, size: float) -> str:
    if stringWidth(text, font, size) <= width:
        return text
    ellipsis = "..."
    while text and stringWidth(text + ellipsis, font, size) > width:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


def fmt_int(value: int) -> str:
    return f"{value:,}"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


if __name__ == "__main__":
    main()
