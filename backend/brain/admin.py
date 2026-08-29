from __future__ import annotations

from django.contrib import admin

from .models import (
    CompanyProfile,
    PortfolioItem,
    Product,
    ProposalTemplate,
    SalesRule,
    Service,
)


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class ProductInline(admin.TabularInline):
    model = Product
    extra = 1


class SalesRuleInline(admin.TabularInline):
    model = SalesRule
    extra = 1


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "based_in", "updated_at")
    search_fields = ("name",)
    inlines = [ServiceInline, ProductInline, SalesRuleInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "target_signal")
    list_filter = ("company",)
    search_fields = ("name", "target_signal")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "price_note")
    list_filter = ("company",)
    search_fields = ("name",)


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "created_at")
    list_filter = ("company",)


@admin.register(SalesRule)
class SalesRuleAdmin(admin.ModelAdmin):
    list_display = ("__str__", "company")
    list_filter = ("company",)


@admin.register(ProposalTemplate)
class ProposalTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "company")
    list_filter = ("company",)