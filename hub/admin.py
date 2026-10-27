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


admin.site.register(models.Category)
admin.site.register(models.AIQuery)
