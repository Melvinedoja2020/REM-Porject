from django.conf import settings


DURATION_CHOICES = []
for days, meta in getattr(settings, "FEATURE_DURATION_CHOICES", {}).items():
    label = meta.get("label", f"{days} days")
    price = meta.get("price")
    if price is not None:
        DURATION_CHOICES.append((int(days), f"{label} — ₦{price:,}"))
    else:
        DURATION_CHOICES.append((int(days), label))
