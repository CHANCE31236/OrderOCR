from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from src.ocr.schemas import PageExtraction


@dataclass(slots=True)
class OrderGroup:
    order_number: str
    pages: list[PageExtraction] = field(default_factory=list)
    missing_pages: list[int] = field(default_factory=list)
    duplicate_pages: list[int] = field(default_factory=list)
    similar_order_warning: list[str] = field(default_factory=list)

    @property
    def export_blocked(self) -> bool:
        return bool(self.missing_pages or self.duplicate_pages or self.similar_order_warning)


def group_orders(pages: list[PageExtraction]) -> dict[str, OrderGroup]:
    groups: dict[str, OrderGroup] = {}
    for page in pages:
        groups.setdefault(page.order_number, OrderGroup(page.order_number)).pages.append(page)
    names = list(groups)
    for name, group in groups.items():
        group.pages.sort(key=lambda p: (p.page_number is None, p.page_number or 0))
        declared = [p.total_pages for p in group.pages if p.total_pages is not None]
        total = max(declared, default=0)
        actual = [p.page_number for p in group.pages if p.page_number is not None]
        group.missing_pages = sorted(set(range(1, total + 1)) - set(actual))
        group.duplicate_pages = sorted({n for n in actual if actual.count(n) > 1})
        for other in names:
            if other != name and SequenceMatcher(None, name.casefold(), other.casefold()).ratio() >= 0.88:
                group.similar_order_warning.append(other)
    return groups

