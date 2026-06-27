from app.core.pagination import ListParams, Page, SortDirection


def test_list_params_calculates_offset() -> None:
    params = ListParams(page=3, page_size=25, direction=SortDirection.DESC)

    assert params.offset == 50


def test_page_has_expected_contract() -> None:
    params = ListParams(page=2, page_size=10)

    page = Page[str].create(["item"], 11, params)

    assert page.model_dump() == {
        "items": ["item"],
        "total": 11,
        "page": 2,
        "page_size": 10,
    }
