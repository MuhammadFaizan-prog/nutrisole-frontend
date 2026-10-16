"""Pakistan Bureau of Statistics weekly SPI: national-weekly-average fallback (used only when the Lahore
retail list and AMIS are stale or missing). Source: https://www.pbs.gov.pk/price-statistics/ (weekly SPI
report + annexure). G4 ships the interface only: the annexure parser is not implemented, so this source
always returns no rows and the app shows no SPI price (never a guessed one)."""
URL = "https://www.pbs.gov.pk/price-statistics/"


def fetch() -> dict:
    return dict(source="PBS weekly SPI (national weekly average)", source_url=URL, price_type="national weekly average",
                list_date=None, rows=[], status="not_implemented_g4")
