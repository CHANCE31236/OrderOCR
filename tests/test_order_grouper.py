from src.business.order_grouper import group_orders
from src.ocr.schemas import PageExtraction


def make_page(order: str, page: int, total: int) -> PageExtraction:
    return PageExtraction(order_number=order, page_number=page, total_pages=total, rows=[], page_confidence=0.99)


def test_missing_middle_page_is_reported_and_blocks_export():
    pages = [make_page("Vs20260713-6", n, 6) for n in (1, 2, 4, 5, 6)]
    group = group_orders(pages)["Vs20260713-6"]
    assert group.missing_pages == [3]
    assert group.export_blocked


def test_pages_are_sorted():
    pages = [make_page("A-1", n, 3) for n in (3, 1, 2)]
    group = group_orders(pages)["A-1"]
    assert [p.page_number for p in group.pages] == [1, 2, 3]


def test_duplicate_page_is_reported():
    pages = [make_page("A-1", n, 2) for n in (1, 1, 2)]
    assert group_orders(pages)["A-1"].duplicate_pages == [1]


def test_similar_order_numbers_are_not_silently_separated():
    groups = group_orders([make_page("Vs20260713-6", 1, 1), make_page("Vs20260713-G", 1, 1)])
    assert groups["Vs20260713-6"].similar_order_warning == ["Vs20260713-G"]

