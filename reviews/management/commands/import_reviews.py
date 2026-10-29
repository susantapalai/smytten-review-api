import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from reviews.models import Product, Review

REQUIRED = ["product", "brand", "username", "rating", "review"]


class Command(BaseCommand):
    help = "Clean a messy reviews CSV and load it into the database"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the CSV file")

    def handle(self, *args, **options):
        try:
            df = pd.read_csv(options["csv_path"], dtype=str)
        except FileNotFoundError:
            raise CommandError(f"File not found: {options['csv_path']}")

        df.columns = [c.strip().lower() for c in df.columns]
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise CommandError(f"Missing columns: {missing}")

        total = len(df)

        # 1. Trim whitespace; treat blank strings as missing
        for col in REQUIRED:
            df[col] = df[col].str.strip().replace("", pd.NA)

        # 2. Drop rows missing the essentials
        df = df.dropna(subset=["product", "review"])

        # 3. Normalise text fields
        df["product"] = df["product"].str.title()
        df["brand"] = df["brand"].fillna("Unknown").str.title()
        df["username"] = df["username"].fillna("anonymous").str.lower()
        df["review"] = df["review"].str.replace(r"\s+", " ", regex=True)

        # 4. Parse ratings ("4 stars" -> 4) and keep only 1-5
        extracted = df["rating"].str.extract(r"(\d+(?:\.\d+)?)")[0]
        df["rating"] = pd.to_numeric(extracted, errors="coerce").round()
        df = df[df["rating"].between(1, 5)]

        # 5. Remove duplicate reviews
        df["_key"] = df["review"].str.lower()
        df = df.drop_duplicates(subset=["product", "username", "_key"])

        # 6. Load into the database (safe to re-run)
        User = get_user_model()
        created = 0
        for row in df.itertuples():
            product, _ = Product.objects.get_or_create(
                name=row.product, defaults={"brand": row.brand}
            )
            user, made = User.objects.get_or_create(username=row.username)
            if made:
                user.set_unusable_password()
                user.save()
            _, is_new = Review.objects.get_or_create(
                product=product, user=user, text=row.review,
                defaults={"rating": int(row.rating)},
            )
            created += is_new

        self.stdout.write(self.style.SUCCESS(
            f"Read {total} rows, kept {len(df)} after cleaning "
            f"({total - len(df)} dropped), imported {created} new reviews."
        ))