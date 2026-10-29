import ipaddress,re,socket,unicodedata
from urllib.parse import urlparse
PATTERNS=[r"ignore\s+(all|any|the)\s+previous",r"ignore\s+previous\s+instructions",r"system\s+message",r"developer\s+message",r"reveal\s+(your|the)\s+prompt",r"execute\s+(this|the)\s+command",r"run\s+(this|the)\s+command",r"disregard\s+.*instructions"]
BAD_UNICODE={0x200B,0x200C,0x200D,0x202E,0x2060,0x2066,0x2067,0x2068,0x2069,0xFEFF}

def detect_prompt_injection(text):
    low=unicodedata.normalize("NFKC",text or "").lower(); return [p for p in PATTERNS if re.search(p,low)]

def hidden_unicode(text): return sorted({f"U+{ord(c):04X}" for c in text if ord(c) in BAD_UNICODE})

def integrity_flags(text):
    a=detect_prompt_injection(text); b=hidden_unicode(text)
    return {"prompt_injection_hits":a,"hidden_unicode":b,"safe":not a and not b}

def _is_bad_ip(ip):
    x=ipaddress.ip_address(ip)
    return x.is_private or x.is_loopback or x.is_link_local or x.is_reserved or x.is_multicast or x.is_unspecified

def validate_public_url(url):
    u=urlparse(url)
    if u.scheme not in {"http","https"} or not u.hostname: raise ValueError("Only public http(s) URLs are allowed")
    if u.username or u.password: raise ValueError("Credential-bearing URLs are not allowed")
    host=u.hostname.rstrip(".").lower()
    if host in {"localhost","localhost.localdomain"}: raise ValueError("Localhost is not allowed")
    try:
        if _is_bad_ip(host): raise ValueError("Private/reserved IP is not allowed")
    except ValueError as e:
        if "IP" in str(e): raise
        # Hostname: resolve and validate every address.
        try:
            infos=socket.getaddrinfo(host,None,proto=socket.IPPROTO_TCP)
            ips={x[4][0] for x in infos}
        except socket.gaierror as e: raise ValueError(f"DNS resolution failed: {host}") from e
        if not ips or any(_is_bad_ip(ip) for ip in ips): raise ValueError("Refusing private, loopback, link-local, reserved, multicast, or unspecified URL")
    return True

def sanitize_for_ai(text):
    text=unicodedata.normalize("NFKC",text or "")
    for cp in BAD_UNICODE: text=text.replace(chr(cp),"")
    return text