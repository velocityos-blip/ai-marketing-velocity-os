"""Bounded, same-origin crawling of public HTTPS pages."""
from collections import deque
from html.parser import HTMLParser
import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from protego import Protego

import urllib3

AGENT = "VOSBot"
LIMIT = 384_000


def website(value):
    if not isinstance(value, str) or not value.strip() or len(value)>2048:
        raise ValueError("Enter a public HTTPS website.")
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    if parts.scheme!="https" or not parts.hostname or parts.username is not None or parts.password is not None or parts.port not in (None,443):
        raise ValueError("Enter a public HTTPS website on port 443.")
    host = parts.hostname.rstrip(".").encode("idna").decode().lower()
    if "." not in host or host.endswith((".local",".localhost",".internal")) or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for c in host):
        raise ValueError("Use a public website hostname.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Use a website hostname, not an IP address.")
    return urlunsplit(("https",host,parts.path or "/","",""))


def fetch(url):
    parts=urlsplit(url)
    host=parts.hostname
    addresses={item[4][0] for item in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(a).is_global or ipaddress.ip_address(a).is_multicast for a in addresses):
        raise ValueError("Website resolved outside the public network.")
    # Connect to the vetted address while validating the certificate for the hostname.
    addr=sorted(addresses,key=lambda a:(":" in a,a))[0]
    pool=urllib3.HTTPSConnectionPool(addr,443,server_hostname=host,assert_hostname=host,
        ssl_context=ssl.create_default_context(),timeout=urllib3.Timeout(connect=3,read=4))
    try:
        response=pool.urlopen("GET",parts.path or "/",headers={"Host":host,"User-Agent":AGENT+"/1.0","Accept-Encoding":"identity"},
                              redirect=False,retries=False,preload_content=False)
        try:
            raw=response.read(LIMIT+1,decode_content=False)
            return response.status,response.headers,raw[:LIMIT],len(raw)>LIMIT
        finally:
            response.close()
    finally:
        pool.close()


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.counts={"h1":0,"title":0,"img":0,"missing_alt":0}
        self.noindex=False

    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("h1","title","img"):
            self.counts[tag]+=1
        if tag=="img" and "alt" not in a:
            self.counts["missing_alt"]+=1
        if tag=="a" and a.get("href") and len(self.links)<100:
            self.links.append(a["href"])
        if tag=="meta" and (a.get("name") or "").lower()=="robots":
            self.noindex |= "noindex" in (a.get("content") or "").lower()


def crawl(start):
    origin="https://"+urlsplit(start).hostname
    report={"site":start,"pages":[],"skipped":0,"status":"complete","page_limit":6}
    try:
        status,headers,raw,truncated=fetch(origin+"/robots.txt")
        if status not in (404,410) and (status!=200 or truncated):
            raise ValueError("Robots rules unavailable.")
        robots=Protego.parse(raw.decode("utf-8","replace") if status==200 else "")
        delay=max(0.3,robots.crawl_delay(AGENT) or 0)
        rate=robots.request_rate(AGENT)
        if rate and rate.requests: delay=max(delay,rate.seconds/rate.requests)
        queue=deque([start])
        seen=set()
        deadline=time.monotonic()+32
        while queue and len(seen)<10 and len(report["pages"])<6:
            if time.monotonic()+delay>=deadline:
                report["status"]="time limit reached"
                break
            url=queue.popleft()
            if url in seen: continue
            seen.add(url)
            if not robots.can_fetch(url,AGENT):
                report["skipped"]+=1
                continue
            time.sleep(delay)
            status,headers,raw,truncated=fetch(url)
            if 300<=status<400:
                links=[headers.get("Location","")]
            elif status==200 and "html" in headers.get("Content-Type","").lower():
                p=Page()
                p.feed(raw.decode("utf-8","replace"))
                findings=[]
                if p.counts["missing_alt"]: findings.append(f'{p.counts["missing_alt"]} images missing alt attributes')
                if not truncated:
                    for tag in ("h1","title"):
                        if p.counts[tag]!=1: findings.append(f'{p.counts[tag]} {tag} elements')
                if p.noindex or "noindex" in headers.get("X-Robots-Tag","").lower(): findings.append("noindex directive")
                report["pages"].append(dict(url=url,status=status,partial=truncated,findings=findings))
                links=p.links
            else:
                report["pages"].append(dict(url=url,status=status,findings=["Non-HTML or unsuccessful response"]))
                links=[]
            for href in links:
                try:
                    dest=website(urljoin(url,href))
                except ValueError:
                    continue
                if dest.startswith(origin+"/") and dest not in seen and dest not in queue and len(queue)<50:
                    queue.append(dest)
        if not report["pages"]:report["status"]="no accessible HTML pages"
    except Exception:
        report["status"]="crawl incomplete; website or robots rules unavailable"
    return report
