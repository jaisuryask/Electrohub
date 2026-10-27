from django.core.management.base import BaseCommand

from hub import faq_data as fd
from hub import seed_data as sd
from hub.models import FAQ, Category, CodeFile, Component, Connection, ErrorCode, Project, Step


class Command(BaseCommand):
    help = "Load ElectroLab starter categories and projects (idempotent)."

    def handle(self, *args, **opts):
        cats = {}
        for slug, name, icon, blurb in sd.CATEGORIES:
            cats[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults=dict(name=name, icon=icon, blurb=blurb))
        for d in sd.PROJECTS:
            p, _ = Project.objects.update_or_create(slug=d["slug"], defaults=dict(
                title=d["title"], category=cats[d["category"]], board=d["board"], summary=d["summary"],
                description=d["description"], difficulty=d["difficulty"], build_minutes=d["build_minutes"],
                cost_usd=d["cost_usd"], tags=d["tags"], youtube_id=d["youtube_id"],
                video_credit=d.get("video_credit", ""), safety_note=d.get("safety_note", ""),
                featured=d.get("featured", False)))
            p.components.all().delete(); p.connections.all().delete()
            p.code_files.all().delete(); p.steps.all().delete()
            for n, q, note in d["components"]:
                Component.objects.create(project=p, name=n, quantity=q, note=note)
            for i, (fp, fpin, tp, tpin, col, note) in enumerate(d["connections"]):
                Connection.objects.create(project=p, order=i, from_part=fp, from_pin=fpin,
                                          to_part=tp, to_pin=tpin, wire_color=col, note=note)
            for i, (t, b) in enumerate(d["steps"]):
                Step.objects.create(project=p, order=i, title=t, body=b)
            for i, (fn, lang, desc, content) in enumerate(d["code"]):
                CodeFile.objects.create(project=p, order=i, filename=fn, language=lang,
                                        description=desc, content=content)
        for i, (cat, q, a, kw) in enumerate(fd.FAQS):
            FAQ.objects.update_or_create(question=q, defaults=dict(category=cat, answer=a, keywords=kw, order=i))
        for code, title, meaning, fix, status in fd.ERROR_CODES:
            ErrorCode.objects.update_or_create(code=code, defaults=dict(
                title=title, meaning=meaning, fix=fix, http_status=status))
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(sd.PROJECTS)} projects, {len(fd.FAQS)} FAQs, {len(fd.ERROR_CODES)} error codes."))
