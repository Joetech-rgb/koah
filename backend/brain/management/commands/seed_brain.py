from __future__ import annotations

from django.core.management.base import BaseCommand

from brain.models import CompanyProfile, Product, SalesRule, Service


class Command(BaseCommand):
    """Seed the Brain app with KoahCloud's real business data.

    Idempotent: safe to re-run, uses get_or_create to avoid duplicates.
    """

    help = "Seed initial CompanyProfile, Services, Products, and SalesRules for KoahCloud."

    def handle(self, *args: object, **options: object) -> None:
        company, created = CompanyProfile.objects.get_or_create(
            name="KoahCloud",
            defaults={
                "description": (
                    "KoahCloud is a Ghana-based technology company offering website "
                    "design, POS systems, school management software, and AI-powered "
                    "business agents, alongside laptops and IT equipment supply."
                ),
                "email_tone": "friendly, direct, confident",
                "based_in": "Ghana",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"CompanyProfile {'created' if created else 'already existed'}: {company}")
        )

        services = [
            ("Website Design", "no website detected"),
            ("POS Systems", "retail or restaurant business with no visible point-of-sale system"),
            ("School Management Systems", "school or educational institution"),
            ("AI Business Agents", "manual or repetitive business processes visible"),
        ]
        for name, signal in services:
            _, created = Service.objects.get_or_create(
                company=company, name=name, defaults={"target_signal": signal}
            )
            self.stdout.write(f"  Service: {name} ({'created' if created else 'exists'})")

        products = [
            ("Laptops", "from $500"),
            ("IT Equipment", "custom quote on request"),
        ]
        for name, price_note in products:
            _, created = Product.objects.get_or_create(
                company=company, name=name, defaults={"price_note": price_note}
            )
            self.stdout.write(f"  Product: {name} ({'created' if created else 'exists'})")

        rules = [
            "Always mention laptops as an add-on regardless of the pitch angle.",
            "Introduce KoahCloud as a Ghana-based provider when the lead's country is not Ghana.",
        ]
        for rule_text in rules:
            _, created = SalesRule.objects.get_or_create(company=company, rule_text=rule_text)
            self.stdout.write(f"  SalesRule: {rule_text[:50]}... ({'created' if created else 'exists'})")

        self.stdout.write(self.style.SUCCESS("Seeding complete."))