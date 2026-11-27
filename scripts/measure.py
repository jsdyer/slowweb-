"""Make one bounded observation per configured public page in a fresh JS-off Chromium context."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

from playwright.async_api import async_playwright, Error as BrowserError

from network import Network, in_domain

ROOT = Path(__file__).resolve().parents[1]


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")


async def observe(browser,subject):
    context=await browser.new_context(java_script_enabled=False,service_workers="block",viewport={"width":390,"height":844},locale="en-CA",timezone_id="UTC")
    page=await context.new_page()
    session=await context.new_cdp_session(page)
    network=Network()
    await session.send("Network.enable")
    await session.send("Network.setCacheDisabled",{"cacheDisabled":True})
    session.on("Network.requestWillBeSent",network.request)
    session.on("Network.loadingFinished",network.complete)
    session.on("Network.loadingFailed",network.failure)
    evidence=[]
    status=None
    outcome="unavailable"
    note=""
    try:
        reply=await page.goto(subject["url"],wait_until="domcontentloaded",timeout=25000)
        if reply:
            status=reply.status
        try:
            await page.wait_for_load_state("load",timeout=10000)
        except BrowserError:
            note="The load event did not arrive within the observation window."
        await page.wait_for_timeout(1200)
        host=urlsplit(page.url).hostname or ""
        if status is None or status >= 400:
            note=f"HTTP {status} from the page." if status else "No HTTP document response."
        elif not in_domain(host,subject["domain"]):
            note="The page redirected outside its configured publisher domain."
        else:
            action = subject.get("action")
            if action:
                control = page.locator(action["select"])
                available = await control.count() == 1 and await control.is_visible() and await control.is_enabled()
                if available:
                    await control.select_option(action["value"],timeout=2000)
                evidence.append({"label":"Layer selector available and operable","found":available})
            for criterion in subject["checks"]:
                nodes=page.locator(criterion.get("selector","body")).filter(visible=True)
                texts=await nodes.all_inner_texts()
                pattern=re.compile(criterion["text"],re.I)
                match=next((hit for text in texts if (hit:=pattern.search(" ".join(text.split())))),None)
                item={"label":criterion["label"],"found":bool(match)}
                if match and criterion.get("show_match"):
                    item["observed_text"]=match.group()[:90]
                evidence.append(item)
            outcome="completed" if all(item["found"] for item in evidence) else "not-demonstrated"
    except BrowserError as exc:
        reason=re.search(r"net::[A-Z_]+",str(exc))
        note=reason.group() if reason else "The public page did not finish navigation within the observation window."
    result={"id":subject["id"],"observed_at":utc(),"url":subject["url"],"domain":subject["domain"],
            "name":subject["name"],"task":subject["task"],"outcome":outcome,"http_status":status,"note":note,
            "checks":evidence,"network":network.result(subject["domain"],max(0,len(page.frames)-1))}
    await context.close()
    return result


async def collect():
    subjects=json.loads((ROOT/"config/subjects.json").read_text())
    if not subjects or len(subjects)>30 or len({s["id"] for s in subjects})!=len(subjects):
        raise ValueError("Expected 1–30 distinct, configured public subjects")
    for s in subjects:
        url=urlsplit(s["url"])
        if url.scheme!="https" or not url.hostname or url.username or url.password or not in_domain(url.hostname,s["domain"]) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",s["id"]) or not s["checks"]:
            raise ValueError(f"Invalid configured subject {s['id']}")
    at=utc()
    opts={"executable_path":os.getenv("CHROMIUM_PATH")}
    if proxy:=os.getenv("SLOWWEB_PROXY"):
        opts["proxy"]={"server":proxy}
    if pins:=os.getenv("SLOWWEB_TRUSTED_SPKI"):
        opts["args"]=["--ignore-certificate-errors-spki-list="+pins]
    async with async_playwright() as api:
        browser=await api.chromium.launch(**opts)
        version=browser.version
        limit=asyncio.Semaphore(3)
        async def run(s):
            async with limit:
                result=await observe(browser,s)
                print(s["id"],result["outcome"],result["network"]["encoded_bytes"],flush=True)
                return result
        results=await asyncio.gather(*(run(s) for s in subjects))
        await browser.close()
    if not any(row["outcome"]!="unavailable" for row in results):
        raise ValueError("All documents were unavailable; retained the previous edition.")
    captured=utc()
    edition={"started_at":at,"checked_at":captured,"method":1,"browser":"Chromium "+version,
             "access_path":"Managed HTTPS proxy" if opts.get("proxy") else "Direct runner connection",
             "results":results}
    folder=ROOT/"data/editions"
    folder.mkdir(parents=True,exist_ok=True)
    name=at.replace("-","").replace(":","")+".json"
    dest=folder/name
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=folder,suffix=".part",delete=False) as fp:
        temp=Path(fp.name)
        try:
            json.dump(edition,fp,ensure_ascii=False,indent=2)
            fp.write("\n")
            fp.flush()
            os.link(temp,dest)
        finally:
            temp.unlink(missing_ok=True)
    return edition


if __name__=="__main__":
    asyncio.run(collect())
