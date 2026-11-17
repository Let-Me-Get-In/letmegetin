"""The AccesLibre export split the address in two and carries a building id."""

from __future__ import annotations

from pathlib import Path

from letmegetin.application.places.import_acceslibre import iter_acceslibre_rows

_HEADER = "id;nom;numero;voie;commune;code_postal;latitude;longitude;categorie;rnb_id;siret\n"


def _rows(tmp_path: Path, body: str) -> list:
    path = tmp_path / "acceslibre.csv"
    path.write_text(_HEADER + body, encoding="utf-8")
    return list(iter_acceslibre_rows(path))


def test_number_and_street_make_the_address(tmp_path: Path) -> None:
    [row] = _rows(
        tmp_path,
        "test-1;Mairie Test;12;Rue des Tests;Testville;99001;45.1;5.1;Mairie;ABCD1234EF56;"
        "12345678900012\n",
    )

    assert row.address == "12 Rue des Tests"
    assert row.address_number == "12"
    assert row.address_street == "Rue des Tests"
    assert row.rnb_id == "ABCD1234EF56"
    assert row.siret == "12345678900012"


def test_street_without_number_is_kept_alone(tmp_path: Path) -> None:
    [row] = _rows(
        tmp_path,
        "test-2;Mairie Test;;Rue des Tests;Testville;99001;45.1;5.1;Mairie;;\n",
    )

    assert row.address == "Rue des Tests"
    assert row.address_number is None


def test_no_address_part_means_no_address(tmp_path: Path) -> None:
    [row] = _rows(tmp_path, "test-3;Lieu Test;;;;99001;45.1;5.1;Mairie;;\n")

    assert row.address is None
    assert row.rnb_id is None
    assert row.siret is None
