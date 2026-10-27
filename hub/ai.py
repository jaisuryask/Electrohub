"""ElectroLab AI engine.

Two layers:
  * Local engine (always on): TF-IDF semantic search, parts-based recommender,
    rule-based troubleshooter, heuristic code explainer, retrieval-grounded Q&A.
  * Free LLM (server-side): chat / code explanation / troubleshooting are answered by a free model
    (Groq or Gemini free tier if a key is in .env, otherwise keyless Pollinations), grounded with the
    retrieved project context. If every provider fails, the local engine answers.
"""
import json
import math
import os
import re
import urllib.request
from collections import Counter

from django.conf import settings

from .models import Project

STOP = set(
    "a an the and or of to in on for with is are be it this that how do i my me can you what which "
    "from at as by use using make build project get want need".split()
)


def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if w in STOP or len(w) < 2:
            continue
        if len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        out.append(w)
    return out


# ---------------------------------------------------------------- index / search
def _doc_text(p):
    parts = [p.title] * 3 + [p.tags.replace(",", " ")] * 2 + [p.board, p.category.name, p.summary, p.description]
    parts += [c.name for c in p.components.all()]
    parts += [s.title + " " + s.body for s in p.steps.all()]
    parts += [c.description for c in p.code_files.all()]
    return " ".join(parts)


def _build_index():
    docs = []
    for p in Project.objects.select_related("category").prefetch_related("components", "steps", "code_files"):
        docs.append((p, Counter(tokens(_doc_text(p)))))
    n = len(docs) or 1
    df = Counter()
    for _, c in docs:
        df.update(c.keys())
    idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}
    vecs = []
    for p, c in docs:
        v = {t: (1 + math.log(f)) * idf[t] for t, f in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        vecs.append((p, v, norm))
    return vecs, idf


def search(query, limit=8):
    """Semantic-ish search: TF-IDF cosine similarity over every project."""
    q = Counter(tokens(query))
    if not q:
        return []
    vecs, idf = _build_index()
    qv = {t: (1 + math.log(f)) * idf.get(t, 1) for t, f in q.items()}
    qn = math.sqrt(sum(x * x for x in qv.values())) or 1
    scored = []
    for p, v, n in vecs:
        dot = sum(w * v.get(t, 0) for t, w in qv.items())
        if dot > 0:
            scored.append((dot / (qn * n), p))
    scored.sort(key=lambda x: -x[0])
    return [(round(s * 100), p) for s, p in scored[:limit]]


# ---------------------------------------------------------------- recommender
ALIASES = {
    "uno": "arduino", "nano": "arduino", "esp32cam": "esp32-cam", "dht": "dht22", "dht11": "dht22",
    "hcsr04": "hc-sr04", "ultrasonic": "hc-sr04", "pico": "raspberry pi pico", "rpi": "raspberry pi pico",
    "led": "led", "pir": "pir", "moisture": "soil moisture", "buzzer": "buzzer", "pump": "pump",
}


def _norm_part(s):
    t = set(tokens(s.replace("-", " ")))
    return t


def recommend(owned_text):
    """Rank projects by how many of their parts the user already owns."""
    owned_items = [x.strip() for x in re.split(r"[,\n;]+", owned_text) if x.strip()]
    owned_tok = [_norm_part(x) | _norm_part(ALIASES.get(x.lower().replace(" ", ""), "")) for x in owned_items]
    results = []
    for p in Project.objects.select_related("category").prefetch_related("components"):
        have, missing = [], []
        for c in p.components.all():
            ct = _norm_part(c.name)
            hit = any(ct & o and (len(ct & o) / max(1, min(len(ct), len(o)))) >= 0.5 for o in owned_tok)
            (have if hit else missing).append(c.name)
        total = len(have) + len(missing)
        if total and have:
            results.append({
                "project": p, "have": have, "missing": missing,
                "score": round(100 * len(have) / total),
            })
    results.sort(key=lambda r: (-r["score"], r["project"].build_minutes))
    return results[:6]


# ---------------------------------------------------------------- LLM
# Provider chain (first available wins, each failure falls through to the next):
#   groq (GROQ_API_KEY, free tier) -> gemini (GEMINI_API_KEY, free tier)
#   -> pollinations (free, no key) -> local engine.
# Keys are read from the server environment / .env only; the browser talks to our /api/ai/* endpoints.
OPENAI_STYLE = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.0-flash"),
    "pollinations": ("https://text.pollinations.ai/openai", None, "POLLINATIONS_MODEL", "openai"),
}


def llm_available():
    return settings.AI_ENABLED


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json", "user-agent": "ElectroLab/1.0", **headers})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _call_openai_style(name, system, messages, max_tokens):
    url, key_env, model_env, default_model = OPENAI_STYLE[name]
    headers = {}
    if key_env:
        key = os.environ.get(key_env, "")
        if not key:
            raise RuntimeError("no key")
        headers["authorization"] = "Bearer " + key
    data = _post(url, {"model": os.environ.get(model_env, default_model), "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system}] + messages}, headers)
    return data["choices"][0]["message"]["content"].strip()


def call_llm(system, messages, max_tokens=700):
    """Returns (text, provider) or (None, "local") when every provider fails."""
    for name in ("groq", "gemini", "pollinations"):
        try:
            text = _call_openai_style(name, system, messages, max_tokens)
            if text:
                return text, name
        except Exception:
            continue
    return None, "local"


def project_context(p, with_code=True):
    lines = [f"PROJECT: {p.title} ({p.board}, {p.get_difficulty_display()}, ~{p.build_minutes} min, ~${p.cost_usd})",
             p.summary, p.description, "PARTS: " + "; ".join(f"{c.quantity}x {c.name}" for c in p.components.all()),
             "WIRING:"]
    lines += [f"  {c.from_part}.{c.from_pin} -> {c.to_part}.{c.to_pin} ({c.note})" for c in p.connections.all()]
    lines += ["STEPS:"] + [f"  {i}. {s.title}: {s.body}" for i, s in enumerate(p.steps.all(), 1)]
    if with_code:
        for f in p.code_files.all():
            lines.append(f"CODE {f.filename}:\n{f.content[:2500]}")
    if p.safety_note:
        lines.append("SAFETY: " + p.safety_note)
    return "\n".join(lines)


SYSTEM = (
    "You are ElectroLab AI, a friendly embedded-systems and IoT mentor on the ElectroLab website. "
    "Answer concisely (under 180 words) using the provided project context when relevant. "
    "Use short lists, mention exact pins, and warn about voltage/safety where it matters. "
    "If the context does not contain the answer, say so and give general best practice."
)


# ---------------------------------------------------------------- chat / Q&A
def ask(question, project=None, history=None):
    """Return (answer_text, engine, related_projects)."""
    if project:
        related = [project]
        context = project_context(project)
    else:
        hits = search(question, 3)
        related = [p for _, p in hits]
        context = "\n\n".join(project_context(p, with_code=False) for p in related) or "No matching projects."
    if llm_available():
        try:
            msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])[-6:]
                    if h.get("role") in ("user", "assistant")]
            msgs.append({"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"})
            text, provider = call_llm(SYSTEM, msgs)
            if text:
                return text, provider, related
        except Exception:
            pass
    return local_answer(question, project, related), "local", related


def local_answer(q, project, related):
    ql = q.lower()
    if not project and not related:
        return ("I couldn't find a matching project. Try describing sensors or boards, e.g. "
                "“temperature monitor with ESP32” — or use the Part-Finder in the AI Lab.")
    p = project or related[0]
    if re.search(r"\b(hi|hello|hey)\b", ql) and len(ql.split()) < 4:
        return "Hi! I'm the ElectroLab assistant. Ask me about wiring, parts, code or troubleshooting for any project."
    if re.search(r"wir|connect|pin|plug|attach", ql):
        rows = "\n".join(f"• {c.from_part} {c.from_pin} → {c.to_part} {c.to_pin}" + (f" ({c.note})" if c.note else "")
                         for c in p.connections.all())
        return f"Wiring for **{p.title}**:\n{rows}\n\nDouble-check the common ground before powering on."
    if re.search(r"part|component|need|buy|bom|cost|price|budget", ql):
        rows = "\n".join(f"• {c.quantity}× {c.name}" for c in p.components.all())
        return f"**{p.title}** needs:\n{rows}\n\nEstimated cost ≈ ${p.cost_usd}."
    if re.search(r"code|sketch|upload|library|flash|program", ql):
        files = ", ".join(f.filename for f in p.code_files.all())
        return (f"**{p.title}** includes: {files}. Open the Code tab to copy or download them, "
                "then use “Explain this code” for a line-by-line walkthrough.")
    if re.search(r"hard|easy|difficult|time|long|level|minute", ql):
        return f"**{p.title}** is {p.get_difficulty_display().lower()} level and takes about {p.build_minutes} minutes."
    if re.search(r"step|start|build|instruction|how (do|to|can)", ql):
        rows = "\n".join(f"{i}. {s.title}" for i, s in enumerate(p.steps.all(), 1))
        return f"Build steps for **{p.title}**:\n{rows}"
    if re.search(r"safe|danger|mains|volt", ql) and p.safety_note:
        return "⚠ " + p.safety_note
    if not project and len(related) > 1:
        names = "\n".join(f"• **{r.title}** — {r.summary}" for r in related)
        return f"These projects look relevant:\n{names}"
    return f"**{p.title}** — {p.summary}"


# ---------------------------------------------------------------- troubleshooter
KB = [
    (r"upload|flash|timed out|connect to|failed to|serial port|com\d|boot mode|a fatal error",
     "Upload / flashing problem",
     ["Pick the right board and COM port in the IDE (Tools menu).",
      "Use a data-capable USB cable, not a charge-only one.",
      "ESP32: hold the BOOT button while 'Connecting…' appears. ESP32-CAM: tie GPIO0 to GND while flashing, then reset.",
      "Close other programs using the serial port (Serial Monitor, PuTTY)."]),
    (r"nan|dht|temperature.*(wrong|zero|0)|humidity.*(wrong|zero|0)|sensor.*not (read|work)",
     "Sensor reads NaN / wrong values",
     ["Check the data pin is wired to the GPIO in your code and has a 10 kΩ pull-up to 3.3 V.",
      "Make sure the library matches the sensor type (DHT11 vs DHT22).",
      "Wait ≥2 s between DHT22 reads.", "Verify supply voltage — ESP32 sensors must run at 3.3 V."]),
    (r"wifi|wi-fi|ssid|ip address|cannot connect|not connect(ing)? to network|brownout",
     "Wi-Fi won't connect",
     ["ESP32 supports 2.4 GHz only — not 5 GHz.", "Re-check SSID/password (case-sensitive).",
      "Brownout? Use a stronger 5 V supply (≥500 mA, ≥1 A for ESP32-CAM) and add a 100–470 µF capacitor.",
      "Move closer to the router and print WiFi.status() for the failure code."]),
    (r"distance|ultrasonic|hc-sr04|echo|always 0|jump",
     "Ultrasonic distance unstable / zero",
     ["Trig → output pin, Echo → input pin — don't swap them.", "HC-SR04 needs 5 V and a common GND.",
      "Echo is 5 V: use a divider (1k/2k) when connecting to a 3.3 V board.",
      "Keep targets flat, hard and 2 cm–4 m away; average several readings."]),
    (r"relay|clicks|always on|inverted|reversed|active low",
     "Relay behaves inverted / clicks randomly",
     ["Most relay modules are ACTIVE-LOW: LOW = ON, HIGH = OFF.", "Power the relay's VCC from 5 V, share ground with the MCU.",
      "Use a flyback diode on bare relays, and a separate supply for pumps/motors.",
      "Never touch mains wiring — use a low-voltage load for testing."]),
    (r"camera|esp32.?cam|black|green|frame|init failed|0x105|0x20001",
     "ESP32-CAM won't initialise / bad image",
     ["Select 'AI Thinker ESP32-CAM' and enable PSRAM.", "Re-seat the camera ribbon (lift the latch, insert fully, close).",
      "Power from a solid 5 V 1 A source — USB-serial adapters often brown out.", "Lower frame size to QVGA/VGA if frames drop."]),
    (r"led.*(not|doesn't|no)|nothing happens|no light|dim",
     "LED doesn't light",
     ["LEDs are polarised: long leg (anode) to the resistor/pin, short leg to GND.", "Always use a 220–330 Ω series resistor.",
      "Confirm pinMode(pin, OUTPUT) / Pin(n, Pin.OUT) and the pin number in code."]),
    (r"reset|restart|reboot|watchdog|guru meditation|crash",
     "Board keeps resetting",
     ["Remove delay-free infinite loops that starve the watchdog — add delay(1)/yield().",
      "Check power: motors/pumps sharing the MCU supply cause brownouts.", "Read the serial crash log and decode it with the ESP exception decoder."]),
    (r"moisture|soil|plant|pump",
     "Soil sensor / pump issues",
     ["Calibrate: note ADC reading in dry air and in water, then set your threshold between.", "Capacitive sensors last longer than resistive ones.",
      "Power the pump through a relay/MOSFET with its own supply and common ground."]),
]


def troubleshoot(problem, project=None):
    pl = problem.lower()
    matches = [(t, tips) for pat, t, tips in KB if re.search(pat, pl)]
    answer_llm, provider = None, "local"
    if llm_available():
        try:
            ctx = project_context(project) if project else ""
            answer_llm, provider = call_llm(
                SYSTEM + " You are diagnosing a hardware/software fault: give likely causes ranked by probability, then a test for each.",
                [{"role": "user", "content": f"{ctx}\n\nPROBLEM: {problem}"}])
        except Exception:
            answer_llm = None
    if not matches:
        matches = [("General checklist", [
            "Re-check every wire against the Connections table — most faults are wiring.",
            "Verify power rails with a multimeter (3.3 V / 5 V) and a common ground.",
            "Print debug values to the Serial Monitor at 115200 baud.",
            "Test one component at a time with the smallest possible sketch."])]
    return {"matches": [{"title": t, "tips": tips} for t, tips in matches[:3]], "llm": answer_llm,
            "engine": provider if answer_llm else "local"}


# ---------------------------------------------------------------- code explainer
RULES = [
    (r"^\s*#include\s*[<\"](.+?)[>\"]", lambda m: f"Imports the **{m.group(1)}** library."),
    (r"^\s*import\s+(\w+)|^\s*from\s+(\w+)\s+import", lambda m: f"Imports the Python module **{m.group(1) or m.group(2)}**."),
    (r"^\s*#define\s+(\w+)\s+(\S+)", lambda m: f"Defines constant **{m.group(1)}** = {m.group(2)} (usually a pin number)."),
    (r"^\s*const\s+int\s+(\w+)\s*=\s*(\w+)", lambda m: f"Names pin/value **{m.group(1)}** = {m.group(2)}."),
    (r"void\s+setup\s*\(", lambda m: "`setup()` runs **once** at power-up — configure pins, serial and Wi-Fi here."),
    (r"void\s+loop\s*\(", lambda m: "`loop()` runs **forever** after setup — the main program."),
    (r"Serial\.begin\((\d+)\)", lambda m: f"Starts serial debugging at {m.group(1)} baud (match the Serial Monitor)."),
    (r"Serial\.print", lambda m: "Prints a value to the Serial Monitor for debugging."),
    (r"pinMode\((\w+),\s*(\w+)\)", lambda m: f"Sets pin **{m.group(1)}** as **{m.group(2)}**."),
    (r"digitalWrite\((\w+),\s*(\w+)\)", lambda m: f"Drives pin **{m.group(1)}** {m.group(2)} (HIGH = 3.3/5 V, LOW = 0 V)."),
    (r"digitalRead\((\w+)\)", lambda m: f"Reads the digital level on **{m.group(1)}**."),
    (r"analogRead\((\w+)\)", lambda m: f"Reads an analog voltage on **{m.group(1)}** (ADC value)."),
    (r"analogWrite\((\w+)", lambda m: f"Outputs a PWM signal on **{m.group(1)}**."),
    (r"pulseIn\(", lambda m: "Measures how long a pin stays HIGH — the echo time of the ultrasonic pulse."),
    (r"delayMicroseconds|delay\(", lambda m: "Pauses the program (non-blocking logic would use millis())."),
    (r"WiFi\.begin", lambda m: "Starts connecting to your Wi-Fi network."),
    (r"WiFi\.status", lambda m: "Checks the Wi-Fi connection state."),
    (r"WiFi\.localIP", lambda m: "Gets the IP address the board received — open it in a browser."),
    (r"server\.on\(", lambda m: "Registers a web route and the function that answers it."),
    (r"server\.handleClient|server\.begin", lambda m: "Runs/serves the built-in HTTP server."),
    (r"dht\.read(Temperature|Humidity)", lambda m: f"Reads {m.group(1).lower()} from the DHT sensor."),
    (r"esp_camera_init", lambda m: "Initialises the OV2640 camera with the pin map above."),
    (r"esp_camera_fb_get", lambda m: "Grabs a JPEG frame from the camera."),
    (r"httpd_", lambda m: "Uses the ESP-IDF HTTP server to stream MJPEG frames."),
    (r"machine\.Pin|Pin\((\d+),", lambda m: "Creates a GPIO pin object (MicroPython)."),
    (r"\.value\(", lambda m: "Reads or sets the pin level (1 = HIGH, 0 = LOW)."),
    (r"time\.sleep", lambda m: "Waits for the given number of seconds."),
    (r"PWM\(", lambda m: "Sets up PWM for smooth brightness/speed control."),
    (r"while\s+True|while\s*\(\s*true\s*\)", lambda m: "Infinite loop — keeps the program running."),
    (r"requests\.|urllib", lambda m: "Makes an HTTP request to the device/server."),
    (r"csv\.", lambda m: "Reads/writes CSV data."),
    (r"^\s*if\b|else\s+if", lambda m: "Decision — runs the block only when the condition is true."),
    (r"^\s*for\b", lambda m: "Loop — repeats the block."),
]


def explain_code(code_file):
    lines = code_file.content.splitlines()
    notes = []
    for i, line in enumerate(lines, 1):
        if not line.strip() or line.strip().startswith(("//", "#", "*", "/*")) and not line.strip().startswith("#include") and not line.strip().startswith("#define"):
            continue
        for pat, fn in RULES:
            m = re.search(pat, line)
            if m:
                notes.append({"line": i, "code": line.strip()[:90], "text": fn(m)})
                break
    summary = (f"{code_file.filename}: {code_file.description or 'program'}. "
               f"{len(lines)} lines, {len(notes)} annotated statements.")
    llm, provider = None, "local"
    if llm_available():
        try:
            llm, provider = call_llm(SYSTEM + " Explain the code for a beginner: purpose, how it works, key pins, and 2 improvement ideas.",
                                     [{"role": "user", "content": f"FILE {code_file.filename}\n{code_file.content[:6000]}"}], 800)
        except Exception:
            llm = None
    return {"summary": summary, "notes": notes[:60], "llm": llm, "engine": provider if llm else "local"}
