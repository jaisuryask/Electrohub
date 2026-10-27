import io
import json
import os
import time
import zipfile

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connection
from django.db.models import F
from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from . import ai, assistant, integrations, mongo
from .diagram import wiring_svg
from .middleware import STARTED, stats
from .models import FAQ, AIQuery, Category, CodeFile, ErrorCode, Project, Ticket


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
        "video": integrations.youtube_meta(p.youtube_id, p.video_credit),
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
    session = str(d.get("session", ""))[:64]
    res = assistant.respond(msg, project, session, d.get("history"), page=str(d.get("page", "")))
    _log("chat", msg, res["engine"])
    log_id, store = mongo.insert("chat_logs", {
        "session": session, "page": str(d.get("page", ""))[:200], "project": project.slug if project else "",
        "question": msg, "answer": res["answer"], "source": res["source"], "engine": res["engine"],
        "ticket": res["ticket"]})
    return JsonResponse({**res, "log_id": log_id, "store": store})


@require_POST
def api_feedback(request):
    d = _body(request)
    rating = d.get("rating")
    if rating not in ("up", "down"):
        return JsonResponse({"error": "rating must be 'up' or 'down'", "code": "400"}, status=400)
    log_id = str(d.get("log_id", ""))[:40]
    fields = {"rating": rating, "comment": str(d.get("comment", ""))[:500]}
    _, store = mongo.insert("feedback", {"log_id": log_id, "session": str(d.get("session", ""))[:64], **fields})
    mongo.update_feedback(log_id, fields)
    return JsonResponse({"ok": True, "store": store})


@require_POST
def api_ticket_email(request):
    d = _body(request)
    ref = str(d.get("ref", "")).upper().replace("ELT-", "")
    try:
        validate_email(d.get("email", ""))
        ticket = Ticket.objects.get(pk=int(ref))
    except (ValidationError, ValueError, Ticket.DoesNotExist):
        return JsonResponse({"error": "Enter a valid email and ticket reference.", "code": "400"}, status=400)
    ticket.email = d["email"]
    ticket.save(update_fields=["email"])
    return JsonResponse({"ok": True})


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


# ------------------------------------------------------------------ FAQ / errors / support / health
def faq_page(request):
    groups = {}
    for f in FAQ.objects.all():
        groups.setdefault(f.category, []).append(f)
    return render(request, "hub/faq.html", {"groups": groups, "total": FAQ.objects.count()})


def errors_page(request):
    return render(request, "hub/errors.html", {"codes": ErrorCode.objects.all()})


def support_page(request):
    ctx = {}
    if request.method == "POST":
        question = request.POST.get("question", "").strip()[:2000]
        email = request.POST.get("email", "").strip()
        if len(question) < 10:
            ctx["error"] = "Please describe the problem in at least 10 characters."
        else:
            try:
                if email:
                    validate_email(email)
                t = Ticket.objects.create(question=question, email=email, source="form")
                ctx["created"] = t.ref
            except ValidationError:
                ctx["error"] = "That email address doesn't look valid."
    ref = request.GET.get("ref", "").strip().upper()
    if ref:
        try:
            ctx["found"] = Ticket.objects.get(pk=int(ref.replace("ELT-", "")))
        except (ValueError, Ticket.DoesNotExist):
            ctx["notfound"] = ref
    return render(request, "hub/support.html", ctx)


def health(request):
    """Health check: SQL, MongoDB, AI providers, third-party API, request counters. 503 if SQL is down."""
    sql = {"ok": True, "detail": ""}
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        sql["detail"] = f"{FAQ.objects.count()} FAQs, {Project.objects.count()} projects, {Ticket.objects.count()} tickets"
    except Exception as exc:
        sql = {"ok": False, "detail": type(exc).__name__}
    mg = mongo.ping()
    providers = [n for n, k in (("groq", "GROQ_API_KEY"), ("gemini", "GEMINI_API_KEY")) if os.environ.get(k)] + ["pollinations"]
    data = {
        "status": "ok" if sql["ok"] and mg["ok"] else ("down" if not sql["ok"] else "degraded"),
        "uptime_seconds": int(time.time() - STARTED),
        "checks": {
            "sql": sql, "mongodb": mg,
            "ai_providers": {"ok": True, "detail": ", ".join(providers) + " (+ built-in fallback)"},
            "youtube_oembed": {"ok": not integrations.status["last"].startswith("fallback"),
                               "detail": integrations.status["last"] + f" (timeout {integrations.TIMEOUT}s)"},
        },
        "requests": {k: stats[k] for k in ("total", "2xx", "3xx", "4xx", "5xx")},
    }
    code = 200 if sql["ok"] else 503
    if request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", ""):
        return JsonResponse(data, status=code)
    return render(request, "hub/health.html", {"d": data, "recent": list(stats["recent"])}, status=code)


# ------------------------------------------------------------------ custom error pages
def _error_page(request, status, template, **extra):
    try:
        return render(request, template, {"code": str(status), **extra}, status=status)
    except Exception:
        return HttpResponseServerError(
            "<h1>%d</h1><p>Something went wrong. <a href='/'>Home</a> · <a href='/support/'>Support</a></p>" % status)


def error_404(request, exception=None):
    ec = ErrorCode.objects.filter(code="EL-1001" if request.path.startswith("/projects/") else "404").first()
    return _error_page(request, 404, "hub/404.html", ec=ec, path=request.path[:120])


def error_500(request):
    return _error_page(request, 500, "hub/500.html", path=request.path[:120])


def error_403(request, exception=None):
    return _error_page(request, 403, "hub/404.html", ec=ErrorCode.objects.filter(code="403").first(), path=request.path[:120])


def error_400(request, exception=None):
    return _error_page(request, 400, "hub/404.html", ec=ErrorCode.objects.filter(code="400").first(), path=request.path[:120])
