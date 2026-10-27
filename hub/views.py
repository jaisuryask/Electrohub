import io
import json
import zipfile

from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from . import ai
from .diagram import wiring_svg
from .models import AIQuery, Category, CodeFile, Project


def _log(kind, prompt, engine):
    AIQuery.objects.create(kind=kind, prompt=prompt[:1000], engine=engine)


def _body(request):
    try:
        return json.loads(request.body or b"{}")
    except ValueError:
        return {}


# ------------------------------------------------------------------ pages
def home(request):
    qs = Project.objects.select_related("category")
    return render(request, "hub/home.html", {
        "featured": qs.filter(featured=True)[:3],
        "latest": qs.order_by("-created")[:6],
        "categories": Category.objects.all(),
        "stats": {"projects": qs.count(), "videos": qs.exclude(youtube_id="").count(),
                  "files": CodeFile.objects.count()},
    })


def project_list(request):
    qs = Project.objects.select_related("category")
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    diff = request.GET.get("difficulty", "")
    board = request.GET.get("board", "")
    scores = {}
    if cat:
        qs = qs.filter(category__slug=cat)
    if diff:
        qs = qs.filter(difficulty=diff)
    if board:
        qs = qs.filter(board__icontains=board)
    projects = list(qs)
    if q:  # AI semantic search ranks results; plain match is the safety net
        ranked = ai.search(q, 50)
        scores = {p.pk: s for s, p in ranked}
        keep = [p for p in projects if p.pk in scores]
        if not keep:
            keep = [p for p in projects if q.lower() in (p.title + p.summary + p.tags).lower()]
        projects = sorted(keep, key=lambda p: -scores.get(p.pk, 0))
        for p in projects:
            p.score = scores.get(p.pk)
    return render(request, "hub/list.html", {
        "projects": projects, "scores": scores, "q": q, "cat": cat, "diff": diff, "board": board,
        "categories": Category.objects.all(),
        "boards": sorted({b for b in Project.objects.values_list("board", flat=True)}),
    })


def project_detail(request, slug):
    p = get_object_or_404(Project.objects.select_related("category"), slug=slug)
    Project.objects.filter(pk=p.pk).update(views=F("views") + 1)
    conns = list(p.connections.all())
    related = [r for _, r in ai.search(p.title + " " + p.tags, 5) if r.pk != p.pk][:3]
    return render(request, "hub/detail.html", {
        "p": p, "components": p.components.all(), "connections": conns,
        "diagram": mark_safe(wiring_svg(conns)), "code_files": p.code_files.all(),
        "steps": p.steps.all(), "related": related,
        "total_parts": sum(c.quantity for c in p.components.all()),
    })


def ai_lab(request):
    return render(request, "hub/ailab.html", {"projects": Project.objects.all()})


# ------------------------------------------------------------------ downloads
def download_code(request, pk):
    f = get_object_or_404(CodeFile, pk=pk)
    r = HttpResponse(f.content, content_type="text/plain; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{f.filename}"'
    return r


def download_bundle(request, slug):
    p = get_object_or_404(Project, slug=slug)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        readme = [f"# {p.title}", "", p.summary, "", p.description, "", "## Parts"]
        readme += [f"- {c.quantity}x {c.name}" for c in p.components.all()]
        readme += ["", "## Wiring"]
        readme += [f"- {c.from_part} {c.from_pin} -> {c.to_part} {c.to_pin}" for c in p.connections.all()]
        readme += ["", "## Steps"]
        readme += [f"{i}. {s.title} - {s.body}" for i, s in enumerate(p.steps.all(), 1)]
        if p.safety_note:
            readme += ["", "SAFETY: " + p.safety_note]
        z.writestr(f"{p.slug}/README.md", "\n".join(readme))
        for f in p.code_files.all():
            folder = f.filename.rsplit(".", 1)[0] if f.filename.endswith(".ino") else ""
            z.writestr(f"{p.slug}/{folder + '/' if folder else ''}{f.filename}", f.content)
    r = HttpResponse(buf.getvalue(), content_type="application/zip")
    r["Content-Disposition"] = f'attachment; filename="{p.slug}.zip"'
    return r


# ------------------------------------------------------------------ AI API
@require_POST
def api_chat(request):
    d = _body(request)
    msg = (d.get("message") or "").strip()
    if not msg:
        return JsonResponse({"error": "Empty message"}, status=400)
    project = Project.objects.filter(slug=d.get("project", "")).first()
    answer, engine, related = ai.ask(msg, project, d.get("history"))
    _log("chat", msg, engine)
    return JsonResponse({"answer": answer, "engine": engine,
                         "related": [{"title": r.title, "url": r.get_absolute_url()} for r in related if not project]})


@require_POST
def api_recommend(request):
    d = _body(request)
    owned = (d.get("parts") or "").strip()
    if not owned:
        return JsonResponse({"error": "List the parts you own"}, status=400)
    _log("recommend", owned, "local")
    return JsonResponse({"results": [{
        "title": r["project"].title, "url": r["project"].get_absolute_url(), "score": r["score"],
        "have": r["have"], "missing": r["missing"], "thumb": r["project"].thumbnail,
        "board": r["project"].board} for r in ai.recommend(owned)]})


@require_POST
def api_troubleshoot(request):
    d = _body(request)
    problem = (d.get("problem") or "").strip()
    if not problem:
        return JsonResponse({"error": "Describe the problem"}, status=400)
    project = Project.objects.filter(slug=d.get("project", "")).first()
    res = ai.troubleshoot(problem, project)
    _log("troubleshoot", problem, res["engine"])
    return JsonResponse(res)


@require_POST
def api_explain(request, pk):
    f = get_object_or_404(CodeFile.objects.select_related("project"), pk=pk)
    res = ai.explain_code(f)
    _log("explain", f.filename, res["engine"])
    return JsonResponse(res)


def api_search(request):
    q = request.GET.get("q", "")
    return JsonResponse({"results": [{"title": p.title, "url": p.get_absolute_url(), "score": s,
                                      "board": p.board, "summary": p.summary} for s, p in ai.search(q, 6)]})


def api_projects(request):
    """Public JSON API: GET /api/projects/"""
    data = [{"title": p.title, "slug": p.slug, "board": p.board, "category": p.category.name,
             "difficulty": p.difficulty, "summary": p.summary, "tags": p.tag_list,
             "youtube_id": p.youtube_id, "url": p.get_absolute_url()}
            for p in Project.objects.select_related("category")]
    return JsonResponse({"count": len(data), "projects": data})
