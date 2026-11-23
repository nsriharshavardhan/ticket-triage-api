"""FastAPI service: structured support-ticket triage."""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.triage import TicketIn, TicketTriageOut, triage

app = FastAPI(
    title="Ticket Triage API",
    description="Classifies SaaS support tickets into category, priority (P1-P3) and destination queue.",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/triage", response_model=TicketTriageOut)
def triage_ticket(ticket: TicketIn) -> TicketTriageOut:
    return triage(ticket)


DEMO_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ticket Triage API</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#1f2937}
 label{display:block;font-size:13px;color:#4b5563;margin-top:12px}
 input,select,textarea{width:100%;box-sizing:border-box;padding:9px;border:1px solid #d1d5db;border-radius:8px;font:inherit}
 textarea{height:110px} .row{display:flex;gap:12px} .row>div{flex:1}
 button{margin-top:14px;padding:10px 16px;border:0;border-radius:8px;background:#2563eb;color:#fff;cursor:pointer}
 button.ex{background:#eef2ff;color:#3730a3;padding:6px 10px;font-size:13px;margin-right:6px}
 .card{border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin-top:20px}
 .pill{display:inline-block;padding:3px 10px;border-radius:99px;font-weight:600;margin-right:6px}
 .P1{background:#fee2e2;color:#b91c1c}.P2{background:#fef3c7;color:#92400e}.P3{background:#dcfce7;color:#166534}
 .meta{font-size:12px;color:#6b7280}
</style></head><body>
<h1>Ticket Triage API</h1>
<p class="meta">Paste a support ticket to get its category, priority and destination queue as structured JSON.</p>
<div><button class="ex" data-ex="0">Enterprise outage</button><button class="ex" data-ex="1">Billing question</button><button class="ex" data-ex="2">Feature idea</button></div>
<form id="f">
 <div class="row"><div><label>Customer email</label><input id="email" type="email" required value="ops@bigcorp.com.au"></div>
 <div><label>Plan</label><select id="plan"><option>free</option><option selected>pro</option><option>enterprise</option></select></div></div>
 <label>Subject</label><input id="subject" required>
 <label>Body</label><textarea id="body" required></textarea>
 <button>Triage ticket</button>
</form>
<div id="out"></div>
<p class="meta"><a href="/docs">API docs</a></p>
<script>
const EX=[
 ["enterprise","Production down - API returning 500 for all users","Since 9am our whole team cannot log in and every request to the API returns 500. This is urgent, we are losing sales."],
 ["pro","Charged twice on this month's invoice","Hi, our credit card was double charged for the November subscription. Can you refund one of the payments?"],
 ["free","Suggestion: dark mode","It would be great if you could add a dark mode to the dashboard. Is it on the roadmap?"]];
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
document.querySelectorAll('.ex').forEach(b=>b.onclick=()=>{const e=EX[b.dataset.ex];$('plan').value=e[0];$('subject').value=e[1];$('body').value=e[2];});
$('f').onsubmit=async e=>{
  e.preventDefault();
  const r=await fetch('/triage',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({customer_email:$('email').value,plan:$('plan').value,subject:$('subject').value,body:$('body').value})});
  const d=await r.json();
  if(!r.ok){$('out').innerHTML=`<div class="card">Validation error: <pre>${esc(JSON.stringify(d.detail,null,1))}</pre></div>`;return;}
  $('out').innerHTML=`<div class="card"><span class="pill ${d.priority}">${d.priority}</span><b>${esc(d.category)}</b> → <code>${esc(d.assigned_queue)}</code>
   <p>${esc(d.reason)}</p><p class="meta">confidence ${d.confidence} · signals: ${d.signals.map(esc).join(', ')}</p>
   <details><summary class="meta">Raw JSON</summary><pre>${esc(JSON.stringify(d,null,2))}</pre></details></div>`;
};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo() -> str:
    return DEMO_HTML
