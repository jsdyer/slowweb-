"""Account for completed HTTP responses in a single Chromium page network session."""
from urllib.parse import urlsplit


def in_domain(host, domain):
    return host == domain or host.endswith("."+domain)


class Network:
    def __init__(self):
        self.active = {}
        self.hosts = set()
        self.started = self.finished = self.failed = self.encoded = 0

    def request(self,event):
        url=event["request"]["url"]
        key=event["requestId"]
        redirect=event.get("redirectResponse")
        if redirect and key in self.active:
            self.encoded += max(0,int(redirect.get("encodedDataLength",0)))
            self.finished += 1
            self.active.pop(key)
        parsed=urlsplit(url)
        if parsed.scheme not in ("https","http") or not parsed.hostname:
            return
        self.hosts.add(parsed.hostname)
        self.active[key]=url
        self.started += 1

    def complete(self,event):
        if self.active.pop(event["requestId"],None) is not None:
            self.finished+=1
            self.encoded+=max(0,int(event["encodedDataLength"]))

    def failure(self,event):
        if self.active.pop(event["requestId"],None) is not None:
            self.failed+=1

    def result(self,domain,subframes):
        return {"encoded_bytes":self.encoded,"requests":self.started,"finished":self.finished,
                "failed":self.failed,"pending":len(self.active),"subframes":subframes,
                "outside_hosts":sorted(h for h in self.hosts if not in_domain(h,domain)),
                "all_observed_responses_finished":self.finished>0 and not self.failed and not self.active and not subframes}
