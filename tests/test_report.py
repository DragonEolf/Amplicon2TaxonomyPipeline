from __future__ import annotations

import pytest

pytest.importorskip("reportlab")

from generate_genepath_report import build_report_data, draw_pie, prepare_pie_slices


class RecordingCanvas:
    def __init__(self):
        self.wedges = []

    def setFillColor(self, color):
        pass

    def wedge(self, x1, y1, x2, y2, start, extent, fill=1, stroke=0):
        self.wedges.append((start, extent))

    def rect(self, x, y, width, height, fill=1, stroke=0):
        pass

    def setFont(self, font, size):
        pass

    def drawString(self, x, y, text):
        pass

    def setStrokeColor(self, color):
        pass

    def setLineWidth(self, width):
        pass

    def circle(self, x, y, radius, stroke=1, fill=0):
        pass


def test_report_keeps_full_rank_counts_for_pie():
    records = [
        {"reads": 40, "lineage": {"phylum": "Firmicutes"}},
        {"reads": 20, "lineage": {"phylum": "Proteobacteria"}},
        {"reads": 10, "lineage": {"phylum": "Actinobacteria"}},
        {"reads": 5, "lineage": {"phylum": "Bacteroidota"}},
        {"reads": 4, "lineage": {"phylum": "Cyanobacteria"}},
        {"reads": 3, "lineage": {"phylum": "Planctomycetota"}},
        {"reads": 2, "lineage": {"phylum": "Verrucomicrobiota"}},
        {"reads": 1, "lineage": {"phylum": "Acidobacteriota"}},
        {"reads": 1, "lineage": {"phylum": "Chloroflexi"}},
        {"reads": 1, "lineage": {"phylum": "Myxococcota"}},
        {"reads": 13, "lineage": {"phylum": ""}},
    ]

    report = build_report_data(records)

    assert sum(value for _, value in report["all_by_rank"]["phylum"]) == 87
    assert report["classified_by_rank"]["phylum"]["unclassified"] == 13


def test_prepare_pie_slices_groups_tail_without_losing_reads():
    items = [
        ("Firmicutes", 40),
        ("Proteobacteria", 20),
        ("Actinobacteria", 10),
        ("Bacteroidota", 5),
        ("Cyanobacteria", 4),
        ("Planctomycetota", 3),
        ("Verrucomicrobiota", 2),
        ("Acidobacteriota", 1),
        ("Chloroflexi", 1),
        ("Myxococcota", 1),
        ("Unclassified", 13),
    ]

    slices = prepare_pie_slices(items, 100)

    assert slices == [
        ("Firmicutes", 40),
        ("Proteobacteria", 20),
        ("Actinobacteria", 10),
        ("Bacteroidota", 5),
        ("Cyanobacteria", 4),
        ("Other", 8),
        ("Unclassified", 13),
    ]
    assert sum(value for _, value in slices) == 100


def test_prepare_pie_slices_uses_stable_tie_order():
    slices = prepare_pie_slices([("Beta", 10), ("Alpha", 10), ("Gamma", 10)], 30)

    assert slices == [("Alpha", 10), ("Beta", 10), ("Gamma", 10)]


def test_draw_pie_passes_extent_not_end_angle_to_reportlab():
    canvas = RecordingCanvas()

    draw_pie(canvas, [("Alpha", 50), ("Beta", 25), ("Unclassified", 25)], 100, 100, 100, 25)

    assert canvas.wedges == [(90, 180), (270, 90), (360, 90)]
