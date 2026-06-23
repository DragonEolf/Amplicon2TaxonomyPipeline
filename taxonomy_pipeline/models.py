from __future__ import annotations

from dataclasses import dataclass


RANKS = ("kingdom", "phylum", "class", "order", "family", "genus", "species")


@dataclass(frozen=True)
class Taxonomy:
    kingdom: str = ""
    phylum: str = ""
    class_name: str = ""
    order: str = ""
    family: str = ""
    genus: str = ""
    species: str = ""

    @classmethod
    def empty(cls) -> "Taxonomy":
        return cls()

    @classmethod
    def from_parts(cls, parts: list[str]) -> "Taxonomy":
        cleaned = [clean_taxon(part) for part in parts]
        padded = (cleaned + [""] * len(RANKS))[: len(RANKS)]
        return cls(
            kingdom=padded[0],
            phylum=padded[1],
            class_name=padded[2],
            order=padded[3],
            family=padded[4],
            genus=padded[5],
            species=padded[6],
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "kingdom": self.kingdom,
            "phylum": self.phylum,
            "class": self.class_name,
            "order": self.order,
            "family": self.family,
            "genus": self.genus,
            "species": self.species,
        }

    def lineage(self) -> str:
        values = [self.as_dict()[rank] for rank in RANKS]
        while values and not values[-1]:
            values.pop()
        return ";".join(values)


@dataclass(frozen=True)
class ASVRecord:
    asv_id: str
    sequence: str
    reads: int


@dataclass(frozen=True)
class Assignment:
    database: str
    taxonomy: Taxonomy
    match_type: str
    identity: float | None = None


def clean_taxon(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    prefixes = ("d__", "k__", "p__", "c__", "o__", "f__", "g__", "s__")
    if len(value) >= 3 and value[:3].lower() in prefixes:
        value = value[3:]
    return value.strip()
