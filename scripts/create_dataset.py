
import csv
import random
import re
from collections import Counter
from pathlib import Path

SEED = 42
N_SAMPLES = 10000
OUTPUT = Path("data/sample/construction_materials_large.csv")

rng = random.Random(SEED)

# Construction materials: English and Dutch
MATERIALS = {
    "Concrete": [
        "ready mix concrete",
        "reinforced concrete",
        "precast concrete panel",
        "concrete foundation block",
        "concrete slab",
        "concrete drainage pipe",
        "Portland cement",
        "cement mortar",
        "betonmortel",
        "gewapend beton",
        "prefab betonplaat",
        "betonblok",
        "cement",
        "betonnen vloerplaat",
    ],
    "Metals": [
        "reinforcement steel rebar",
        "galvanized steel beam",
        "structural steel column",
        "stainless steel plate",
        "aluminium facade profile",
        "copper pipe",
        "steel mesh",
        "steel sheet",
        "wapeningsstaal",
        "betonstaal",
        "verzinkte stalen balk",
        "RVS plaat",
        "aluminium profiel",
        "koperen buis",
    ],
    "Wood": [
        "spruce timber beam",
        "pine wooden battens",
        "oak flooring boards",
        "plywood sheets",
        "OSB construction board",
        "cross laminated timber",
        "MDF panel",
        "timber formwork",
        "vuren balk",
        "grenen latten",
        "multiplex plaat",
        "houten regel",
        "CLT paneel",
        "hardhouten plank",
    ],
    "Insulation": [
        "PIR insulation board",
        "EPS insulation panel",
        "XPS insulation board",
        "mineral wool",
        "rock wool insulation",
        "glass wool insulation",
        "thermal insulation sheet",
        "acoustic insulation panel",
        "PIR isolatieplaat",
        "EPS isolatie",
        "XPS plaat",
        "steenwol",
        "glaswol",
        "dakisolatie",
    ],
    "Glass": [
        "double glazed window",
        "triple glazing unit",
        "tempered safety glass",
        "laminated glass sheet",
        "clear float glass",
        "insulated glazing panel",
        "HR++ glazing",
        "glass facade panel",
        "dubbel glas",
        "driedubbel glas",
        "gehard veiligheidsglas",
        "gelaagd glas",
        "HR++ beglazing",
        "isolatieglas",
    ],
}

# Material-specific technical details
SPECS = {
    "Concrete": [
        "C20/25", "C25/30", "C30/37", "C35/45",
        "S3", "S4", "XC2", "XF1", "EN206",
    ],
    "Metals": [
        "B500B", "S235", "S355", "HEA200",
        "IPE160", "RVS316", "AISI304", "DX51D",
    ],
    "Wood": [
        "C18", "C24", "GL24h", "18mm",
        "22mm", "45x95mm", "45x145mm", "FSC",
    ],
    "Insulation": [
        "Rd 3.5", "Rd 4.5", "Rd 6.0",
        "lambda 0.022", "lambda 0.035",
        "80mm", "100mm", "120mm",
    ],
    "Glass": [
        "HR++", "HR+++", "4-15-4",
        "6-12-6", "Ug 1.1", "Ug 0.7",
        "8mm", "10mm",
    ],
}

UNITS = {
    "Concrete": ["m3", "m³", "kg", "ton", "st"],
    "Metals": ["kg", "ton", "m", "st", "pcs"],
    "Wood": ["m", "m2", "m²", "st", "pcs"],
    "Insulation": ["m2", "m²", "pak", "st", "pcs"],
    "Glass": ["m2", "m²", "st", "pcs"],
}

CONTEXT = [
    "project A12",
    "project N201",
    "bouwplaats Utrecht",
    "site Amsterdam",
    "renovation phase 2",
    "nieuwbouw fase 1",
    "levering week 35",
    "delivery batch 4",
    "order ref 2026",
    "warehouse stock",
]

PREFIXES = [
    "levering",
    "materiaal",
    "invoice line",
    "factuurregel",
    "artikel",
    "supply",
    "bestelling",
]

# Common abbreviations
ABBREVIATIONS = {
    "concrete": "conc.",
    "reinforced": "reinfrc.",
    "galvanized": "galv.",
    "stainless steel": "SS",
    "aluminium": "alu",
    "timber": "tmbr",
    "plywood": "plywd",
    "insulation": "insul.",
    "isolatieplaat": "isol.pl.",
    "laminated": "lam.",
    "double glazed": "dbl glazed",
    "veiligheidsglas": "veil.glas",
    "gewapend": "gew.",
    "verzinkte": "verz.",
}

def typo(word):
    """Introduce one simple character-level typo."""
    if len(word) < 5:
        return word

    operation = rng.choice(["delete", "swap", "duplicate"])

    i = rng.randrange(1, len(word) - 1)

    if operation == "delete":
        return word[:i] + word[i + 1:]

    if operation == "swap":
        chars = list(word)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return "".join(chars)

    return word[:i] + word[i] + word[i:]


def apply_typos(text):
    words = text.split()

    if not words:
        return text

    # Modify at most one word
    candidates = [
        i for i, word in enumerate(words)
        if len(word) >= 5 and word.isalpha()
    ]

    if candidates:
        i = rng.choice(candidates)
        words[i] = typo(words[i])

    return " ".join(words)


def apply_abbreviations(text):
    for original, short in ABBREVIATIONS.items():
        if rng.random() < 0.5:
            text = re.sub(
                re.escape(original),
                short,
                text,
                flags=re.IGNORECASE,
            )
    return text


def apply_case_noise(text):
    mode = rng.choice(["upper", "lower", "title", "normal"])

    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "title":
        return text.title()

    return text


def apply_spacing_noise(text):
    # Remove spaces around separators
    text = re.sub(r"\s*([,;/])\s*", r"\1", text)

    # Occasionally add extra whitespace
    if rng.random() < 0.5:
        text = text.replace(" ", "  ", 1)

    return text


def generate_description(category):
    material = rng.choice(MATERIALS[category])
    spec = rng.choice(SPECS[category])
    unit = rng.choice(UNITS[category])
    quantity = rng.randint(1, 150)
    context = rng.choice(CONTEXT)

    templates = [
        f"{material} {spec} {quantity} {unit}",
        f"{material}, {quantity} {unit}, {context}",
        f"{material} {spec} - {context}",
        f"{quantity} {unit} {material} {spec}",
        f"{rng.choice(PREFIXES)}: {material} {spec}",
        f"{material} ref {rng.randint(10000, 99999)}",
        f"{material} {quantity} {unit} {context}",
    ]

    text = rng.choice(templates)
    applied_noise = []

    if rng.random() < 0.35:
        text = apply_abbreviations(text)
        applied_noise.append("abbreviation")

    if rng.random() < 0.25:
        text = apply_typos(text)
        applied_noise.append("typo")

    if rng.random() < 0.35:
        text = apply_case_noise(text)
        applied_noise.append("case")

    if rng.random() < 0.20:
        text = apply_spacing_noise(text)
        applied_noise.append("spacing")

    if rng.random() < 0.20:
        text += f" PO-{rng.randint(100000, 999999)}"
        applied_noise.append("reference")

    if rng.random() < 0.15:
        text += f" EUR {rng.randint(10, 5000)}"
        applied_noise.append("price")

    if rng.random() < 0.10:
        text = text.replace(" ", "", 1)
        applied_noise.append("missing_space")

    return text, "|".join(applied_noise) or "none"


def generate_dataset(n_samples=N_SAMPLES):
    categories = list(MATERIALS)

    # Balanced allocation, including when n_samples
    # is not divisible by the number of categories
    counts = {
        category: n_samples // len(categories)
        for category in categories
    }

    for category in categories[:n_samples % len(categories)]:
        counts[category] += 1

    rows = []
    seen = set()

    for category, target_count in counts.items():
        attempts = 0

        while sum(row["category"] == category for row in rows) < target_count:
            attempts += 1

            if attempts > target_count * 100:
                raise RuntimeError(
                    f"Unable to generate enough unique rows for {category}"
                )

            description, noise = generate_description(category)

            # Avoid exact duplicate descriptions
            key = description.casefold()

            if key in seen:
                continue

            seen.add(key)

            rows.append({
                "description": description,
                "category": category,
                "noise_type": noise,
            })

    rng.shuffle(rows)
    return rows


def main():
    rows = generate_dataset()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["description", "category", "noise_type"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created: {OUTPUT}")
    print(f"Total rows: {len(rows)}")
    print("Category distribution:")

    for category, count in Counter(
        row["category"] for row in rows
    ).items():
        print(f"  {category}: {count}")

    print("\nExample descriptions:")
    for row in rows[:10]:
        print(f"  [{row['category']}] {row['description']}")


if __name__ == "__main__":
    main()
