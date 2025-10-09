import os, io, json, datetime as _dt
from typing import Any, Dict, List, Optional

from flask import Flask, request, render_template_string
from flask_cors import CORS
import requests
from PIL import Image

# -------- Gemini (google-generativeai) --------
import google.generativeai as genai

# =============== CONFIG (hard-coded key per your request) ===============
GOOGLE_API_KEY = "AIzaSyDTO982vSAI0BwYJk6-I_dBkj9tYTO1xrk"   # <-- your key
MODEL_NAME     = "gemini-2.0-flash"                     # change if you want, e.g., "gemini-2.0-flash"

# Always use the AI (no local fallback)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# ================== YOUR ANALYSIS LOGIC ==================
ALERT_THRESHOLD = "medium"
_SEV_ORDER = {"low":0, "medium":1, "high":2, "critical":3}

def _relaxed_json(s: str) -> dict:
    s = (s or "").strip()
    try:
        return json.loads(s)
    except Exception:
        l, r = s.find("{"), s.rfind("}")
        if l != -1 and r != -1 and r > l:
            try:
                return json.loads(s[l:r+1])
            except Exception:
                pass
    return {"raw": s}

def _bump(cur: str, nxt: str) -> str:
    return max(cur, nxt, key=lambda x: _SEV_ORDER.get(x, 0))

def _refine_situation(caption: str, objects: List[str], environment: List[str], proposed: str) -> str:
    c = (caption or "").lower()
    objs = {o.lower() for o in (objects or [])}
    envs = {e.lower() for e in (environment or [])}

    if any(k in c for k in ["police tape","crime scene tape","evidence marker","forensic","evidence bag","forensics","csi","chalk outline"]):
        return "crime scene investigation"

    if ({"teller","bank","counter","cashier"} & (objs | set(c.split()))) and \
       ({"mask","hoodie","gloves","gun","note","bag"} & (objs | set(c.split()))):
        return "robbery/hold-up in progress"

    if {"fire","smoke","flames"} & (objs | set(c.split())):
        return "fire emergency"

    if {"ambulance","paramedic","stretcher"} & objs:
        return "medical emergency"

    if {"police car","police"} & objs and any(k in c for k in ["pulled over","driver window","traffic stop"]):
        return "routine traffic stop"

    if {"tow truck","tow-truck"} & objs:
        return "vehicle towing"

    if any(k in c for k in ["accident","crash","collision"]) or {"damaged car","airbag"} & objs:
        return "accident/traffic collision"

    if ("crowd" in objs or "many people" in c) and ({"sign","banner","megaphone"} & (objs | set(c.split()))):
        return "protest/crowd control"

    if {"cone","barrier","hi-vis vest","helmet"} & objs or any(k in c for k in ["construction","maintenance","roadwork"]):
        return "construction/maintenance"

    if {"counter","cashier","checkout"} & (objs | set(c.split())) and not ({"gun","mask","hoodie","gloves"} & (objs | set(c.split()))):
        return "retail transaction"
    if "street" in envs and not ({"police","ambulance","fire truck","smoke","fire"} & objs):
        return "normal street scene"

    return proposed or "other"

def _rule_based_bump(caption: str, objects: List[str], environment: List[str], weather: List[str]):
    c = (caption or "").lower()
    objs = {o.lower() for o in (objects or [])}
    envs = {e.lower() for e in (environment or [])}
    wx   = {w.lower() for w in (weather or [])}
    sev, reasons = "low", []

    if {"gun","knife","weapon","explosion","fire","smoke","blood"} & objs or \
       any(k in c for k in ["gun","knife","weapon","explosion","fire","smoke","blood"]):
        return "critical", ["hazard (weapon/fire/smoke) detected (rule)"]

    if {"police","police officer","police officers","ambulance","fire truck","firetruck","tow truck","tow-truck"} & objs:
        sev = _bump(sev, "medium"); reasons.append("emergency/traffic intervention (rule)")
    if any(k in c for k in ["accident","crash","collision","crime scene","cordon","taped area","evacuate","investigation"]):
        sev = _bump(sev, "high"); reasons.append("incident indicated (rule)")

    if {"stormy","flood","snowy"} & wx:
        sev = _bump(sev, "high"); reasons.append("severe weather (rule)")
    elif {"rainy","foggy","hazy","night","overcast"} & wx:
        sev = _bump(sev, "medium"); reasons.append("low-visibility weather (rule)")

    if ("crowd" in objs or "many people" in c) and ({"car","bus","truck"} & objs or "traffic" in c or "street" in envs):
        sev = _bump(sev, "medium"); reasons.append("crowd near traffic (rule)")

    if any(k in c for k in ["construction","maintenance","roadwork"]) or {"barrier","cone"} & objs:
        sev = _bump(sev, "medium"); reasons.append("construction/maintenance activity (rule)")

    return sev, list(dict.fromkeys(reasons))

def _severity_bar(result: Dict[str, Any]) -> Dict[str, str]:
    sev = (result.get("severity") or "low").lower()
    abnormal = bool(result.get("is_abnormal"))
    triggered = bool(result.get("alert_triggered"))
    if triggered or abnormal or sev in ("high","critical"):
        return {"label": "Critical / High", "bg": "#ef4444"}
    if sev == "medium":
        return {"label": "Caution / Medium", "bg": "#f59e0b"}
    return {"label": "Normal / Low", "bg": "#22c55e"}

def analyze_image(image_url: Optional[str] = None,
                  image_file: Optional[bytes] = None,
                  mime_type: str = "image/jpeg",
                  min_words: int = 25) -> Dict[str, Any]:

    if image_url:
        rr = requests.get(image_url, timeout=30)
        rr.raise_for_status()
        img_bytes = rr.content
    else:
        img_bytes = image_file
    if not img_bytes:
        raise ValueError("No image provided")

    taxonomy = [
        "normal street scene","retail transaction","suspicious behavior","robbery/hold-up in progress",
        "routine traffic stop","vehicle towing","accident/traffic collision",
        "crime scene investigation","medical emergency","fire emergency",
        "protest/crowd control","construction/maintenance","other"
    ]
    env_hint = ["indoor","outdoor","street","office","park","residential","warehouse",
                "hospital","lab","kitchen","parking lot","school","shop","airport","train station","industrial"]
    weather_hint = ["sunny","cloudy","overcast","rainy","snowy","foggy","hazy","stormy","night","dusk","dawn"]

    prompt = (
        "You are a vision safety analyst. Look at the image and return STRICT JSON ONLY with keys:\n"
        '"caption": short string,\n'
        '"objects": 3–10 salient object nouns,\n'
        '"environment": 1–5 from ' + json.dumps(env_hint) + ',\n'
        '"weather": 0–3 from ' + json.dumps(weather_hint) + ',\n'
        '"situation_type": ONE of ' + json.dumps(taxonomy) + ".\n"
        "Only choose 'crime scene investigation' if POLICE TAPE, EVIDENCE MARKERS, FORENSIC SUITS, or EVIDENCE BAGGIES are visible.\n"
        "Choose 'robbery/hold-up in progress' if a masked/hooded/gloved person is interacting with a teller/cashier/counter, with implied threat (weapon or demand note or cash bag).\n"
        "Be conservative and pick the most direct match.\n"
        '"is_abnormal": boolean (true if alert-worthy; false if routine/normal),\n'
        '"severity": one of [\"low\",\"medium\",\"high\",\"critical\"],\n'
        '"reasons": 1–4 short phrases,\n'
        '"confidence": number 0..1 with two decimals,\n'
        '"explanation": a single paragraph of 25–60 words explaining what is happening and why it matters.\n'
        "No markdown, no extra words—JSON only."
    )

    resp = model.generate_content(
        [prompt, {"mime_type": mime_type, "data": img_bytes}],
        request_options={"timeout": 60},
        generation_config={"temperature": 0.1, "max_output_tokens": 420},
    )
    data = _relaxed_json(resp.text)

    caption = (data.get("caption") or "").strip()
    objects = [str(o).strip() for o in (data.get("objects") or []) if str(o).strip()][:10]
    environment = [str(e).strip() for e in (data.get("environment") or []) if str(e).strip()][:5]
    weather = [str(w).strip() for w in (data.get("weather") or []) if str(w).strip()][:3]
    situation_model = (data.get("situation_type") or "other").strip()
    is_abnormal = bool(data.get("is_abnormal", False))
    severity = (data.get("severity") or "low").strip().lower()
    reasons = [str(r).strip() for r in (data.get("reasons") or []) if str(r).strip()][:4]
    try:
        confidence = float(data.get("confidence", 0.70))
    except Exception:
        confidence = 0.70
    explanation = (data.get("explanation") or "").strip().replace("\n", " ")

    if len(explanation.split()) < min_words:
        resp2 = model.generate_content(
            [f"Rewrite to at least {min_words} words (<= 70), clear and specific, no markdown: {explanation}"],
            generation_config={"temperature": 0.1, "max_output_tokens": 200},
        )
        ex2 = (resp2.text or "").strip().replace("\n", " ")
        if len(ex2.split()) >= min_words:
            explanation = ex2

    situation = _refine_situation(caption, objects, environment, situation_model)
    sev_rule, rule_reasons = _rule_based_bump(caption, objects, environment, weather)
    if _SEV_ORDER.get(sev_rule,0) > _SEV_ORDER.get(severity,0):
        severity = sev_rule
        reasons = (reasons + rule_reasons)[:4]

    abnormal_situations = {
        "robbery/hold-up in progress","accident/traffic collision","fire emergency",
        "medical emergency","crime scene investigation","protest/crowd control"
    }
    is_abnormal = is_abnormal or (situation in abnormal_situations) or (severity in {"medium","high","critical"})

    trigger = _SEV_ORDER.get(severity,0) >= _SEV_ORDER.get(ALERT_THRESHOLD,1) or is_abnormal
    alert_reason = "severity-threshold" if _SEV_ORDER.get(severity,0) >= _SEV_ORDER.get(ALERT_THRESHOLD,1) else "abnormal-flag"

    return {
        "ts": _dt.datetime.utcnow().isoformat() + "Z",
        "caption": caption,
        "objects": objects,
        "environment": environment,
        "weather": weather,
        "situation": situation,
        "is_abnormal": bool(is_abnormal),
        "severity": severity,
        "reasons": reasons,
        "confidence": round(confidence, 2),
        "explanation": explanation,
        "alert_triggered": bool(trigger),
        "alert_trigger_reason": alert_reason
    }

# ================== FLASK UI ==================
app = Flask(__name__)
CORS(app)

TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>VigilantEye</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,'Helvetica Neue',Arial}
    .page{background:#0f172a;color:#e2e8f0;min-height:100vh;padding:24px}
    .row{display:flex;gap:24px;align-items:flex-start}
    .card{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:20px}
    .w50{width:50%}
    .btn{background:#3b82f6;border:none;color:white;padding:10px 16px;border-radius:8px;cursor:pointer}
    .ipt{width:100%;padding:10px;border-radius:8px;border:1px solid #374151;background:#0b1220;color:#e5e7eb}
    .hbar{height:40px;border-radius:10px;color:white;font-weight:600;display:flex;align-items:center;padding:0 12px}
    .lbl{color:#9ca3af;font-weight:600;margin-top:10px}
    img{max-width:100%;border-radius:10px;border:1px solid #334155}
    .tag{display:inline-block;background:#1f2937;color:#e5e7eb;border-radius:999px;padding:4px 10px;margin:2px 8px 2px 0}
    .small{color:#94a3b8;font-size:12px}
    .engine{position:fixed;top:14px;right:18px;color:#94a3b8}
  </style>
</head>
<body>
<div class="page">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px">
    <div style="width:10px;height:10px;background:#22c55e;border-radius:50%"></div>
    <h2 style="margin:0">VigilantEye</h2>
    <div class="engine">Engine: {{ engine }}</div>
  </div>

  <div class="row">
    <div class="card w50">
      <h3 style="margin-top:0">Analyze an image</h3>
      <form method="POST" enctype="multipart/form-data">
        <div class="lbl">Image URL</div>
        <input class="ipt" type="url" name="image_url" placeholder="https://..." value="{{ last_url or '' }}">
        <div class="lbl">Or upload a file</div>
        <input type="file" name="image_file" accept="image/*">
        <div style="margin-top:12px"><button class="btn" type="submit">Analyze</button></div>
      </form>
      {% if preview %}<div style="margin-top:16px"><img src="{{ preview }}" alt="preview"></div>{% endif %}
    </div>

    <div class="card w50">
      {% if error %}
        <div style="color:#fca5a5;white-space:pre-wrap">{{ error }}</div>
      {% elif result %}
        <div class="hbar" style="background: {{ bar.bg }}">{{ bar.label }}</div>

        <p><b>Caption:</b> {{ result.caption or '—' }}</p>
        <p><b>Situation:</b> {{ result.situation or '—' }}</p>
        <p><b>Severity:</b> {{ result.severity or '—' }}</p>
        <p><b>Abnormal:</b> {{ 'Yes' if result.is_abnormal else 'No' }}</p>

        <p><b>Objects:</b> {% if result.objects %}{% for o in result.objects %}<span class="tag">{{ o }}</span>{% endfor %}{% else %}—{% endif %}</p>
        <p><b>Environment:</b> {% if result.environment %}{% for e in result.environment %}<span class="tag">{{ e }}</span>{% endfor %}{% else %}—{% endif %}</p>

        <p><b>Reasons:</b> {% if result.reasons %}<ul>{% for r in result.reasons %}<li>{{ r }}</li>{% endfor %}</ul>{% else %}—{% endif %}</p>

        <p><b>Explanation:</b><br>{{ result.explanation or '—' }}</p>
        <p class="small">Confidence: {{ result.confidence }} • Alert: {{ 'Yes' if result.alert_triggered else 'No' }} ({{ result.alert_trigger_reason }})</p>
      {% else %}
        <div class="small">Waiting…</div>
      {% endif %}
    </div>
  </div>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    result = None
    preview = None
    last_url = None

    if request.method == "POST":
        image_url = (request.form.get("image_url") or "").strip()
        image_file = request.files.get("image_file")

        try:
            if image_file and image_file.filename:
                img_bytes = image_file.read()
                result = analyze_image(image_file=img_bytes, mime_type=image_file.mimetype or "image/jpeg")
                import base64
                preview = "data:%s;base64,%s" % (
                    image_file.mimetype or "image/jpeg",
                    base64.b64encode(img_bytes).decode("ascii"),
                )
            elif image_url:
                last_url = image_url
                result = analyze_image(image_url=image_url)
                preview = image_url
            else:
                error = "Please provide an image URL or upload a file."
        except Exception as ex:
            error = f"Failed: {ex}"

    bar = _severity_bar(result or {})
    return render_template_string(
        TEMPLATE,
        error=error, result=result, preview=preview, last_url=last_url,
        bar=bar, engine=MODEL_NAME
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2025, debug=True)
