"""Build the explorer and permanent receipts offline from immutable browser observations."""
from collections import defaultdict
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from search_metadata import add_search_metadata

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://coolcode.ca/slowweb/"
OUTCOMES = {"completed":"Completed","not-demonstrated":"Not demonstrated","unavailable":"Unavailable"}
SPEEDS = (14.4,33.6,56,128,1000)
METHOD = """<h2>How the checks work</h2>
<p>Each visit starts in a fresh Chromium context with JavaScript disabled, the browser cache disabled, service workers blocked and a 390 × 844 viewport. The observer opens the configured public page, waits up to 25 seconds for the document, up to 10 more seconds for the load event, then waits 1.2 seconds. No scrolling or sign-in takes place. Visible text, links or a specified control determine the result for that task.</p>
<p>“Completed” means the listed evidence was visible and any specified control worked. “Not demonstrated” means the document loaded but one or more checks failed. “Unavailable” means the document could not be assessed. These observations describe the tested page, date and browser.</p>
<p>The byte count sums the encoded transfer lengths Chromium reports for finished HTTP(S) responses in the tab’s network session, including reported redirect responses. It excludes unreported bytes from failed or unfinished responses. A separate frame can have its own network session. Any child frame, failed request, pending request or missing document makes the count partial and suppresses the time estimate. The reader sees the HTTP result independently of task completion.</p>
<p>Outside hosts are observed request hostnames beyond the subject’s configured domain and its subdomains. They can serve public assets; their presence does not identify tracking or ownership. A managed proxy and server-side caches can change the returned representation and byte count.</p>
<p>Transfer estimates use encoded bytes × 8 ÷ (selected kilobits per second × 1,000). They omit connection setup, latency, retransmission, browser work and modem negotiation. The visits used modern Chromium. No dial-up connection, VCN access account, Windows XP system or period browser was tested.</p>"""


def e(value):
    return escape(str(value),quote=True)


def a(url,label,cls=None):
    style=' class="'+e(cls)+'"' if cls else ""
    return f'<a href="{e(url)}"{style}>{e(label)}</a>'


def pretty_time(stamp):
    return stamp.replace("T"," ").replace("Z"," UTC")


def pretty_rate(seconds):
    if seconds<10:
        return f"{seconds:.1f} s"
    if seconds<60:
        return f"{seconds:.0f} s"
    return f"{seconds/60:.1f} min"


def estimate(row,rate):
    n=row["network"]
    if row["outcome"]=="unavailable" or not n["all_observed_responses_finished"]:
        return "Unavailable"
    return pretty_rate(n["encoded_bytes"]*8/(rate*1000))


def amount(row):
    n=row["network"]
    if not n["finished"]:
        return "No finished response"
    suffix=" (partial)" if row["outcome"]=="unavailable" or not n["all_observed_responses_finished"] else ""
    return f'{n["encoded_bytes"]:,} B'+suffix


def badge(row):
    return f'<span class="outcome {e(row["outcome"])}">{e(OUTCOMES[row["outcome"]])}</span>'


def read_editions(root):
    editions=[]
    for file in sorted((root/"data/editions").glob("*.json")):
        d=json.loads(file.read_text())
        date=datetime.fromisoformat(d["started_at"])
        key=date.strftime("%Y%m%dT%H%M%SZ")
        if file.stem!=key or not d["results"]:
            raise ValueError(f"Edition date or results invalid: {file.name}")
        seen=set()
        for r in d["results"]:
            n=r["network"]
            if (r["id"] in seen or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",r["id"]) or r["outcome"] not in OUTCOMES
                or urlsplit(r["url"]).scheme!="https" or any(type(n[x])!=int or n[x]<0 for x in ["encoded_bytes","requests","finished","failed","pending","subframes"])
                or n["finished"]+n["failed"]+n["pending"]!=n["requests"]):
                raise ValueError(f"Invalid subject receipt in {file}")
            seen.add(r["id"])
        editions.append((key,d))
    if not editions:
        raise ValueError("No observed editions")
    return editions


def inspection(row, edition):
    n=row["network"]
    groups=["<h2>What the visit found</h2><ul class='checklist'>"]
    for check in row["checks"]:
        state="Found" if check["found"] else "Not found"
        evidence=" · "+e(check["observed_text"]) if check.get("observed_text") else ""
        groups.append(f'<li><strong>{state}</strong> {e(check["label"])}{evidence}</li>')
    groups.append("</ul>")
    if row["note"]:
        groups.append(f'<p>{e(row["note"])}</p>')
    groups.append(f'<p>Status {e(row["http_status"] or "unavailable")} · {e(edition["browser"])} · {e(edition.get("access_path","Not recorded"))}. {a(row["url"],"Open the observed page")}</p>')
    hosts=", ".join(e(x) for x in n["outside_hosts"]) or "None observed"
    groups.append(f'<h2>Network observations</h2><p><strong>{e(amount(row))}</strong> in reported finished responses. Requests observed: {n["requests"]} · Finished: {n["finished"]} · Failed: {n["failed"]} · Pending: {n["pending"]} · Child frames: {n["subframes"]}.</p><p>Hosts outside {e(row["domain"])} · {hosts}.</p>')
    if estimate(row,56)!="Unavailable":
        groups.append("<h2>Calculated transfer time</h2><p>Same measured bytes at different assumed line rates.</p><dl class='rates'>")
        groups.extend(f"<div><dt>{rate:g} kb/s</dt><dd>{estimate(row,rate)}</dd></div>" for rate in SPEEDS)
        groups.append("</dl>")
    else:
        groups.append("<p>A complete transfer estimate is unavailable for this observation.</p>")
    return "".join(groups)


def write(path,html):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(html,encoding="utf-8")


def save_page(out,route,title,description,body,tool,home=False):
    prefix="../"*route.count("/") or "./"
    nav=a(prefix,"Slow Web","brand")+a(prefix+"records/","Browse results")+a(prefix+"#methods","Method")
    head=f'<title>{e(title)} · Slow Web</title><meta name="description" content="{e(description)}">'
    if not home:
        head+=f'<link rel="canonical" href="{BASE}{route}"><meta property="og:title" content="{e(title)}"><meta property="og:url" content="{BASE}{route}">'
    script=f'<script src="{prefix}app.mjs" type="module"></script>' if home else ""
    footer=a("https://coolcode.ca/","CoolCode.ca")+" · "+a(tool["source"],"Source and methods")+" · "+a("https://coolcode.ca/report/?tool=slowweb","Report a correction")
    html=f"""<!doctype html><html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">{head}<link rel="stylesheet" href="{prefix}style.css"><link rel="icon" href="{prefix}favicon.svg">{script}<script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script></head>
<body data-tool-id="slowweb"><a class="skip" href="#main">Skip to results</a><header><nav>{nav}</nav></header><main id="main">{body}</main><footer>{footer}</footer></body></html>"""
    if home:
        html=add_search_metadata(html,tool,category="UtilitiesApplication")
    write(out/route/"index.html",html)


def build(root=ROOT):
    tool=json.loads((root/"tool.json").read_text())
    subjects={s["id"]:s for s in json.loads((root/"config/subjects.json").read_text())}
    editions=read_editions(root)
    recent_key,recent=editions[-1]
    rows=recent["results"]
    histories=defaultdict(list)
    for key,edition in editions:
        for row in edition["results"]:
            histories[row["id"]].append((key,edition,row))
    sitemap=ET.Element("urlset",xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        out=Path(tmp)/"site"
        shutil.copytree(root/"web",out)
        def record(path,title,description,body):
            save_page(out,path,title,description,body,tool)
            ET.SubElement(ET.SubElement(sitemap,"url"),"loc").text=BASE+path
        cards=[]
        for row in rows:
            sid=row["id"]
            group=subjects.get(sid,{}).get("group","Other")
            n=row["network"]
            bytes_value=n["encoded_bytes"] if estimate(row,56)!="Unavailable" else ""
            cards.append(f'''<tr data-group="{e(group)}" data-outcome="{e(row["outcome"])}"><th scope="row">{a("./records/"+sid+"/",row["name"])}<small>{e(row["task"])}</small></th>
<td>{badge(row)}</td><td>{e(amount(row))}</td><td data-encoded="{bytes_value}">{estimate(row,56)}</td></tr>''')
        feature=next((r for r in rows if r["id"]=="alderney-ferry"),rows[0])
        source_info=" · ".join(e(i["observed_text"]) for i in feature["checks"] if i.get("observed_text"))
        spotlight=f'''<section class="spot"><div><p class="subject">{e(feature["name"])}</p><h2>{e(feature["task"])}</h2>{badge(feature)} <span class="muted">with JavaScript off</span><p>{source_info}</p>
{a("./records/"+feature["id"]+"/","Read the browser receipt →")}</div><div class="measure"><strong>{e(amount(feature))}</strong><span>recorded response data</span><strong>{estimate(feature,56)}</strong><span>calculated at 56 kb/s</span></div></section>'''
        groups=sorted({subjects.get(row["id"],{}).get("group","Other") for row in rows})
        opts="".join(f'<option>{e(v)}</option>' for v in groups)
        speed_opts="".join(f'<option value="{v:g}"'+(" selected" if v==56 else "")+f'>{v:g} kb/s</option>' for v in SPEEDS)
        recent_time=pretty_time(recent["checked_at"])
        controls=f'''<div id="controls" hidden><label for="group">Collection</label><select id="group"><option value="">All collections</option>{opts}</select><label for="result">Task outcome</label><select id="result"><option value="">All outcomes</option>{''.join(f'<option value="{k}">{v}</option>' for k,v in OUTCOMES.items())}</select><label for="rate">Assumed line rate</label><select id="rate">{speed_opts}</select></div>'''
        home=f'''<div class="intro"><h1>Slow Web</h1><p>Can you finish an everyday task with JavaScript off? Read what a browser actually found, then see how long its response bytes would take at a chosen line rate.</p></div>{spotlight}
<section><h2>Compare the tasks</h2><p>{len(rows)} pages in the latest check · {e(recent_time)}</p>{controls}<p id="summary" role="status"></p><div class="table-scroll"><table><thead><tr><th>Page and task</th><th>JavaScript off</th><th>Observed bytes</th><th>Estimate at <span id="rate-label">56</span> kb/s</th></tr></thead><tbody>{''.join(cards)}</tbody></table></div><p>{a("./records/","Browse all task histories")} · {a("./data/editions/"+recent_key+".json","Download the latest receipt (JSON)")}</p></section>
<section id="methods">{METHOD}<p>The scheduled checks run Mondays at 10:17 UTC. {a("./data/status.json","See the last published check")}.</p></section>'''
        save_page(out,"","Website tasks tested with JavaScript off",tool["description"],home,tool,True)
        grouped=defaultdict(list)
        for sid,history in histories.items():
            key,edition,row=history[-1]
            subject=subjects.get(sid,{})
            grouped[subject.get("group","Previous subjects")].append((sid,row))
            linkback=a("../../","Compare all tasks")+" · "+a("../","Result directory")
            detail="<p>"+e(subject["note"])+"</p>" if subject.get("note") else ""
            links=""
            if sid=="alderney-ferry":
                links="<p>"+a("https://coolcode.ca/field-notes/reading-the-alderney-ferry-timetable/","Field note: reading the Alderney ferry timetable with JavaScript off")+".</p>"
            elif sid in ("chebucto-community-net","vancouver-community-network"):
                links="<p>"+a("https://coolcode.ca/freenet-echo/","Read the dated community network history in FreeNet Echo")+".</p>"
            elif sid=="halifax-map-layers" and "dartmouth-archive" in histories:
                links="<p>"+a("../dartmouth-archive/","Compare the static Dartmouth ferry photograph task")+".</p>"
            receipts=[]
            for ek,ed,ob in reversed(history):
                target="visits/"+ek.lower()+"/"
                receipts.append("<li>"+a(target,pretty_time(ob["observed_at"]))+" · "+e(OUTCOMES[ob["outcome"]])+" · "+e(amount(ob))+"</li>")
                observed=pretty_time(ob["observed_at"])
                desc=f'{ob["task"]} {OUTCOMES[ob["outcome"]]} with JavaScript disabled. Observed {observed}.'
                receipt=f'<p>{a("../../","← "+ob["name"]+" history")}</p><h1>{e(ob["name"])} · {e(observed)}</h1><p class="lead">{e(ob["task"])}</p>{badge(ob)}{inspection(ob,ed)}<p>{a("../../../../data/editions/"+ek+".json","Download the dated JSON receipt")} · {a("../../../../#methods","Measurement method")}</p>'
                record("records/"+sid+"/"+target,ob["name"]+" browser receipt, "+observed,desc,receipt)
            description=f'{row["task"]} Read dated browser checks, observed transfer bytes and the criteria for this task on {row["name"]}.'
            page=f'<p>{linkback}</p><h1>{e(row["name"])}</h1><p class="lead">{e(row["task"])}</p>{badge(row)} · {e(pretty_time(row["observed_at"]))}{detail}{inspection(row,edition)}{links}<h2>Dated visits</h2><ul>{"".join(receipts)}</ul><p>{a("../../#methods","Read the measurement method")}</p>'
            record("records/"+sid+"/",row["name"]+" with JavaScript off",description,page)
        contents=["<h1>Website tasks tested with JavaScript off</h1><p class='lead'>Choose a task to read the individual criteria, dated observations and transfer estimates.</p>"]
        for group,entries in sorted(grouped.items()):
            contents.append("<h2>"+e(group)+"</h2><ul>")
            for sid,row in entries:
                contents.append("<li>"+a("./"+sid+"/",row["name"])+" · "+e(row["task"])+"</li>")
            contents.append("</ul>")
        record("records/","Website task receipt directory","Browse dated JavaScript-disabled browser results across community networks, text-first websites and Halifax ferry information.","".join(contents))
        data=out/"data"
        shutil.copytree(root/"data/editions",data/"editions")
        status={"checked_at":recent["checked_at"],"page_count":len(rows),"edition_count":len(editions),"receipt_count":sum(len(x) for x in histories.values()),"sitemap_count":len(sitemap)}
        write(data/"status.json",json.dumps(status,indent=2)+"\n")
        ET.ElementTree(sitemap).write(out/"sitemap.xml",encoding="utf-8",xml_declaration=True)
        (out/".nojekyll").touch()
        dest=root/"dist"
        if dest.exists():shutil.rmtree(dest)
        os.replace(out,dest)
    print(f'Built {status["sitemap_count"]} permanent result URLs from {len(editions)} real editions.')


if __name__=="__main__":
    build()
