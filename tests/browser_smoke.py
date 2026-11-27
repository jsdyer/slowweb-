"""Test the built Slow Web directory, estimates and usable JS-off interface under a project prefix."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass


def main():
    shots=ROOT/"browser-checks"
    shots.mkdir(exist_ok=True)
    status=json.loads((ROOT/"dist/data/status.json").read_text())
    with tempfile.TemporaryDirectory() as temporary:
        (Path(temporary)/"slowweb").symlink_to(ROOT/"dist",target_is_directory=True)
        (Path(temporary)/"assets").mkdir()
        (Path(temporary)/"assets/tool-metrics.js").write_text("")
        server=ThreadingHTTPServer(("127.0.0.1",0),partial(QuietHandler,directory=temporary))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        url=f"http://127.0.0.1:{server.server_port}/slowweb/"
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
                page=browser.new_page(viewport={"width":1280,"height":900})
                errors=[]
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.goto(url)
                expect(page.locator("tbody tr")).to_have_count(status["page_count"])
                expect(page.locator("#controls")).to_be_visible()
                expect(page.locator(".spot")).to_contain_text("Alderney ferry")
                page.screenshot(path=str(shots/"desktop.png"))
                page.get_by_label("Collection",exact=True).select_option("Community networks")
                community={s["id"] for s in json.loads((ROOT/"config/subjects.json").read_text()) if s["group"]=="Community networks"}
                edition=json.loads(max((ROOT/"data/editions").glob("*.json")).read_text())
                expect(page.locator("tbody tr:visible")).to_have_count(sum(row["id"] in community for row in edition["results"]))
                page.get_by_label("Collection",exact=True).select_option("")
                page.get_by_label("Task outcome").select_option("not-demonstrated")
                expect(page.locator("tbody tr:visible")).to_have_count(sum(1 for r in json.loads(max((ROOT/"data/editions").glob("*.json")).read_text())["results"] if r["outcome"]=="not-demonstrated"))
                page.get_by_label("Task outcome").select_option("")
                page.get_by_label("Assumed line rate").select_option("14.4")
                expect(page.locator("#rate-label")).to_have_text("14.4")
                metric=page.locator('td[data-encoded]').first
                if encoded:=metric.get_attribute("data-encoded"):
                    assert metric.text_content() == page.evaluate('async ([b,r]) => (await import("./model.mjs")).transferEstimate(b,r)',[encoded,"14.4"])
                page.set_viewport_size({"width":390,"height":844})
                page.goto(url)
                expect(page.locator(".spot")).to_be_visible()
                box=page.get_by_role("link",name="Read the browser receipt").bounding_box()
                assert box and box["y"]>=0 and box["y"]+box["height"]<844
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(shots/"mobile.png"))
                page.get_by_role("link",name="Read the browser receipt").click()
                expect(page.get_by_role("heading",level=1)).to_have_text("Alderney ferry departures")
                assert page.locator("link[rel=canonical]").get_attribute("href")=="https://coolcode.ca/slowweb/records/alderney-ferry/"
                history=page.locator('a[href^="visits/"]').first
                history.click()
                expect(page.locator("main")).to_contain_text("What the visit found")
                expect(page.locator("main")).to_contain_text("Network observations")
                json_url=page.get_by_role("link",name="Download the dated JSON receipt").get_attribute("href")
                assert page.request.get(page.evaluate("(href) => new URL(href,location.href).href",json_url)).ok
                static=browser.new_page(java_script_enabled=False,viewport={"width":390,"height":844})
                static.goto(url)
                expect(static.locator("#controls")).to_be_hidden()
                expect(static.locator("tbody tr")).to_have_count(status["page_count"])
                static.get_by_role("link",name="Browse results",exact=True).click()
                static.get_by_role("link",name="Halifax Time Lens map controls",exact=True).click()
                expect(static.get_by_role("heading",level=1)).to_have_text("Halifax Time Lens map controls")
                static.get_by_role("link",name="Compare the static Dartmouth ferry photograph task").click()
                expect(static.locator("main")).to_contain_text("Dartmouth ferry landing photographs")
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    print("Passed project subpath, filters, observable rate changes, dated JSON links, 390px and JavaScript-off reading.")


if __name__=="__main__":
    main()
