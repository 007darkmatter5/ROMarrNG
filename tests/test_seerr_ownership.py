"""SeerrNG ownership has to recognize a ROM the catalog names differently."""

from __future__ import annotations

from types import SimpleNamespace

from romarr.app import (
    _seerr_library_lookup,
    _seerr_library_matches,
    _seerr_text_keys,
)
from romarr.libraries import Game
from romarr.store import SeerrRequest


def _keys(value: str) -> set[str]:
    return _seerr_text_keys(value)


def test_rom_filename_forms_share_a_key_with_the_catalog_title():
    catalog = _keys("The Legend of Zelda")
    assert catalog & _keys("Legend of Zelda, The (USA).nes")
    assert catalog & _keys("Legend of Zelda, The (USA) [!].nes")
    assert catalog & _keys("Legend_of_Zelda,_The")
    assert _keys("Zelda II: The Adventure of Link") & _keys(
        "Zelda_II__The_Adventure_of_Link")
    assert _keys("Super Mario World") & _keys("Super Mario World (USA).nkit.iso")
    assert not (catalog & _keys("The Legend of Zelda: The Minish Cap"))


def test_library_lookup_recognizes_a_no_intro_name(tmp_path):
    from romarr.app import ROMarr

    service = ROMarr({"ROMARR_DATA": str(tmp_path / "state.json")})
    service._library_cache = ([
        Game(id="zelda", name="Legend of Zelda, The (USA).nes",
             platform="Nintendo Entertainment System", platform_slug="nes"),
        Game(id="metroid", name="Super Metroid (USA) [!].sfc",
             platform="snes", platform_slug="snes"),
    ], 0, 0)
    service._library_partial = False
    titles = [
        {"title": "The Legend of Zelda", "platform": "nes"},
        {"title": "The Legend of Zelda: The Minish Cap", "platform": "nes"},
        {"title": "Zelda II: The Adventure of Link", "platform": "nes"},
    ]

    found = _seerr_library_lookup(service, titles)

    assert found["ready"] is True
    assert found["matches"] == [{"title": "The Legend of Zelda", "platform": "nes"}]


def test_saved_metadata_title_and_igdb_id_count_as_owned(tmp_path):
    from romarr.app import ROMarr

    service = ROMarr({"ROMARR_DATA": str(tmp_path / "state.json")})
    service.store.set_library_metadata("default", "hvc-zl", {
        "metadata_title": "The Legend of Zelda",
        "metadata_source": "IGDB",
        "provider_id": "1022",
        "metadata_status": "identified",
    })
    service._publish_library([
        Game(id="hvc-zl", name="HVC-ZL", platform="Nintendo Entertainment System",
             platform_slug="nes"),
    ], "", partial=False)

    by_title = _seerr_library_lookup(service, [
        {"title": "The Legend of Zelda", "platform": "nes"},
    ])
    by_id = _seerr_library_lookup(service, [
        {"title": "The Legend of Zelda", "platform": "nes", "igdbId": 1022},
    ])
    other_id = _seerr_library_lookup(service, [
        {"title": "Unrelated Catalog Title", "platform": "nes", "igdbId": 999},
    ])
    other_platform = _seerr_library_lookup(service, [
        {"title": "The Legend of Zelda", "platform": "snes", "igdbId": 1022},
    ])

    assert by_title["matches"] == [{"title": "The Legend of Zelda", "platform": "nes"}]
    assert by_id["matches"] == [{"title": "The Legend of Zelda", "platform": "nes"}]
    assert other_id["matches"] == []
    assert other_platform["matches"] == []
    stored = service.store.library_metadata("default", "hvc-zl")
    assert stored["provider_id"] == "1022"
    assert service.library_view().get("items", [])[0]["metadata_provider_id"] == "1022"


def test_a_rawg_id_is_not_treated_as_an_igdb_id(tmp_path):
    from romarr.app import ROMarr

    service = ROMarr({"ROMARR_DATA": str(tmp_path / "state.json")})
    service._library_cache = ([
        SimpleNamespace(name="HVC-ZL", platform="nes", platform_slug="nes",
                        metadata_title="", metadata_source="RAWG",
                        metadata_provider_id="1022"),
    ], 0, 0)
    service._library_partial = False

    found = _seerr_library_lookup(service, [
        {"title": "The Legend of Zelda", "platform": "nes", "igdbId": 1022},
    ])

    assert found["matches"] == []


def test_failed_import_still_hides_a_partial_library_copy(tmp_path):
    from romarr.app import ROMarr
    from romarr.store import QueueItem

    service = ROMarr({"ROMARR_DATA": str(tmp_path / "state.json")})
    service._library_cache = ([
        SimpleNamespace(name="Legend of Zelda, The (USA)", platform="nes",
                        platform_slug="nes", metadata_title="",
                        metadata_source="", metadata_provider_id=""),
    ], 0, 0)
    service._library_partial = False
    service.queue.append(QueueItem(
        "The Legend of Zelda", "nes", "Zelda.nes", 1, "import-failed"))
    titles = [{"title": "The Legend of Zelda", "platform": "nes", "igdbId": 1022}]

    assert _seerr_library_lookup(service, titles)["matches"] == []

    service.queue.append(QueueItem(
        "The Legend of Zelda", "nes", "Zelda.nes.retry", 1, "imported",
        imported_paths=[str(tmp_path / "missing")]))
    # The retry is not inside a library root, so only the scanned ROM counts.
    assert _seerr_library_lookup(service, titles)["matches"] == [
        {"title": "The Legend of Zelda", "platform": "nes"},
    ]


def test_request_matches_metadata_title_and_catalog_id(tmp_path):
    from romarr.app import ROMarr

    service = ROMarr({"ROMARR_DATA": str(tmp_path / "state.json")})
    service._library_cache = ([
        Game(id="hvc-zl", name="HVC-ZL", platform="nes", platform_slug="nes",
             metadata_title="The Legend of Zelda", metadata_source="IGDB",
             metadata_provider_id="1022"),
    ], 0, 0)

    by_title = _seerr_library_matches(
        service, SeerrRequest("ext", "The Legend of Zelda", "nes"))
    by_id = _seerr_library_matches(
        service, SeerrRequest(
            "ext", "Unrelated Catalog Title", "nes",
            catalog_provider="igdb", catalog_id=1022))
    missing = _seerr_library_matches(
        service, SeerrRequest("ext", "Unrelated Catalog Title", "nes"))

    assert [row["id"] for row in by_title] == ["hvc-zl"]
    assert [row["id"] for row in by_id] == ["hvc-zl"]
    assert missing == []
