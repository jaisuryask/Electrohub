from django.contrib import admin

from . import models


class ComponentInline(admin.TabularInline):
    model = models.Component
    extra = 0


class ConnectionInline(admin.TabularInline):
    model = models.Connection
    extra = 0


class CodeInline(admin.StackedInline):
    model = models.CodeFile
    extra = 0


class StepInline(admin.StackedInline):
    model = models.Step
    extra = 0


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "board", "difficulty", "featured", "views")
    list_filter = ("category", "difficulty", "featured")
    search_fields = ("title", "summary", "tags")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ComponentInline, ConnectionInline, CodeInline, StepInline]


@admin.register(models.FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order")
    list_filter = ("category",)
    search_fields = ("question", "answer", "keywords")


@admin.register(models.ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "http_status")


@admin.register(models.Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "email", "source", "status", "created")
    list_filter = ("status", "source")
    list_editable = ("status",)
    search_fields = ("question", "email")


admin.site.register(models.Category)
admin.site.register(models.AIQuery)
