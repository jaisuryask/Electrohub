"""Support assistant: error codes -> FAQ -> project guides -> grounded AI -> support ticket.

Order of attempts for every message:
  1. greeting / thanks                      -> friendly reply
  2. error code or error name (404, EL-1001) -> explanation from the ErrorCode table
  3. FAQ match (TF-IDF over the FAQ table)   -> the stored FAQ answer
  4. project guide question                  -> grounded answer about that project
  5. AI model grounded ONLY in FAQ/error/project context (answers CANNOT_ANSWER if not covered)
  6. otherwise                               -> a support Ticket is created (SQL)
"""
import math
import re
from collections import Counter

from . import ai
from .models import FAQ, ErrorCode, Ticket

FAQ_MIN = 0.30       # minimum cosine similarity to answer straight from an FAQ
PROJECT_MIN = 20     # minimum project-search score (0-100) to answer from a project guide
GREETING = re.compile(r"^\s*(hi|hello|hey|yo|thanks|thank you|thx|ok|okay|good (morning|afternoon|evening))\b[\s!.?]*$", re.I)
CODE_RE = re.compile(r"\b(EL-\d{4}|[1-5]\d{2})\b", re.I)
CODE_HINT = re.compile(r"error|code|status|http|page|server|getting|got|mean|why|what is", re.I)

GROUNDED = (
    "You are the ElectroLab support assistant. Answer ONLY from the CONTEXT below (FAQs, error codes, project guides). "
    "Be concise (under 120 words). If the context does not contain the answer, reply with exactly: CANNOT_ANSWER"
)


def _rank(query, docs):
    """docs: [(obj, text)] -> [(cosine, obj)] best first."""
    q = Counter(ai.tokens(query))
    if not q or not docs:
        return []
    counts = [Counter(ai.tokens(t)) for _, t in docs]
    df = Counter()
    for c in counts:
        df.update(c.keys())
    n = len(docs)
    idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}

    def vec(c):
        return {t: (1 + math.log(f)) * idf.get(t, 1) for t, f in c.items()}

    qv = vec(q)
    qn = math.sqrt(sum(x * x for x in qv.values())) or 1
    out = []
    for (obj, _), c in zip(docs, counts):
        dv = vec(c)
        dn = math.sqrt(sum(x * x for x in dv.values())) or 1
        out.append((sum(w * dv.get(t, 0) for t, w in qv.items()) / (qn * dn), obj))
    return sorted(out, key=lambda x: -x[0])


def faq_matches(message):
    docs = [(f, f"{f.question} {f.question} {f.question} {f.keywords} {f.keywords} {f.answer}") for f in FAQ.objects.all()]
    return _rank(message, docs)


def explain_error(message):
    """Return a formatted explanation when the message is about a known error code, else None."""
    found = []
    for raw in CODE_RE.findall(message):
        ec = ErrorCode.objects.filter(code__iexact=raw).first()
        if ec and ec not in found:
            found.append(ec)
    if found and not (CODE_HINT.search(message) or len(message.split()) <= 3):
        found = []
    if not found:
        low = message.lower()
        found = [ec for ec in ErrorCode.objects.all() if len(ec.title) > 6 and ec.title.lower() in low][:1]
    if not found:
        return None
    return "\n\n".join(
        f"**{ec.code} — {ec.title}**\n{ec.meaning}\n**How to fix:** {ec.fix}" for ec in found[:2])


def _create_ticket(message, session, page):
    t = Ticket.objects.create(question=message, session_id=(session or "")[:64], page=(page or "")[:200], source="chat")
    return t.ref


def respond(message, project=None, session="", history=None, page=""):
    """Returns dict(answer, source, engine, ticket, related)."""
    msg = (message or "").strip()[:600]
    base = {"engine": "local", "ticket": None, "related": []}

    if GREETING.match(msg):
        return {**base, "source": "greeting", "answer":
                "Hi! I'm the ElectroLab assistant. Ask me a question, paste an error code like **404**, or ask about any project."}

    explained = explain_error(msg)
    if explained:
        return {**base, "source": "error-code", "answer": explained}

    ranked = faq_matches(msg)
    if ranked and ranked[0][0] >= FAQ_MIN:
        f = ranked[0][1]
        return {**base, "source": "faq", "answer": f"**{f.question}**\n{f.answer}"}

    hits = [] if project else ai.search(msg, 3)
    strong = bool(project) or (bool(hits) and hits[0][0] >= PROJECT_MIN)
    related = [project] if project else [p for _, p in hits]

    # Grounded AI call: FAQ + error codes + project context only
    text, provider = None, "local"
    if ai.llm_available():
        ctx = ["FAQS:"] + [f"Q: {f.question}\nA: {f.answer}" for _, f in ranked[:4]]
        ctx += ["ERROR CODES:"] + [f"{e.code} {e.title}: {e.meaning} Fix: {e.fix}" for e in ErrorCode.objects.all()]
        if project:
            ctx.append(ai.project_context(project))
        elif hits and hits[0][0] >= 15:
            ctx += [ai.project_context(p, with_code=False) for _, p in hits[:2]]
        msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])[-4:]
                if h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str)]
        msgs.append({"role": "user", "content": "CONTEXT:\n" + "\n".join(ctx) + "\n\nQUESTION: " + msg})
        text, provider = ai.call_llm(GROUNDED, msgs, 400)
        if text and "CANNOT_ANSWER" in text:
            text = None
        elif text:
            return {**base, "source": "ai", "engine": provider, "answer": text,
                    "related": [] if project else _links(related if strong else [])}

    if strong:
        local = ai.local_answer(msg, project, related, strict=True)
        if not local and not project and related:
            local = f"This looks related: **{related[0].title}** - {related[0].summary}"
        if local:
            note = "\n\n_EL-2001: the AI model was unavailable, so the built-in engine answered._" if ai.llm_available() else ""
            return {**base, "source": "project", "answer": local + note, "related": [] if project else _links(related)}

    ref = _create_ticket(msg, session, page)
    return {**base, "source": "ticket", "ticket": ref, "answer":
            f"I couldn't find a reliable answer to that, so I created support ticket **{ref}**. "
            "Add your email below if you'd like a reply, or track it on the Support page."}


def _links(projects):
    return [{"title": p.title, "url": p.get_absolute_url()} for p in projects]
