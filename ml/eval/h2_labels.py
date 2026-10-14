"""G9 Stage I: Fruits-360 folder -> H2 class mapping for any FUTURE H2 kernel (Stage H kernels are left as they are).
Audit finding: the Stage H kernels mapped folders by name prefix (str.startswith), so 'Mangostan' (mangosteen) became mango and
'Potato Sweet' (sweet potato) became potato; 'Kumsquats' (a citrus) fell into unknown. Here matching is on the first word with an
explicit exclusion list, so no other produce is silently relabelled as a supported class."""
from __future__ import annotations
H2_CLASSES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum", "unknown"]
FIRST_WORD = {"Apple": "apple", "Banana": "banana", "Mango": "mango", "Orange": "citrus", "Mandarine": "citrus", "Clementine": "citrus", "Tangelo": "citrus",
              "Lemon": "lemon_lime", "Lime": "lemon_lime", "Limes": "lemon_lime", "Guava": "guava", "Pomegranate": "pomegranate", "Tomato": "tomato",
              "Potato": "potato", "Cucumber": "cucumber", "Carrot": "carrot", "Pepper": "capsicum"}
NOT_THE_CLASS = {"Potato Sweet": None}  # sweet potato is a different crop: unknown
EXCLUDE = ("Grapefruit", "Pomelo", "Kumsquats", "Cantaloupe", "Melon", "Watermelon", "Ginger", "Zucchini dark")  # look-alikes kept out of training entirely
def folder_to_class(name: str) -> str | None:
    """Returns an H2 class, 'unknown', or None (= exclude the folder)."""
    if name.startswith(EXCLUDE): return None
    base = " ".join(w for w in name.split() if not w.isdigit())
    if base in NOT_THE_CLASS: return "unknown"
    return FIRST_WORD.get(name.split()[0], "unknown")
