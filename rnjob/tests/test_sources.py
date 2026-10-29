from rnjob.sources import _extract_candidates, source_links

def test_source_links_are_https_and_source_specific():
    links=source_links("React Native TypeScript","Delhi NCR, India")
    assert links["linkedin"].startswith("https://www.linkedin.com/")
    assert links["naukri"].startswith("https://www.naukri.com/")
    assert "React+Native" in links["indeed"]

def test_jsonld_jobposting_extraction():
    html='''<html><head><script type="application/ld+json">{"@context":"https://schema.org","@type":"JobPosting","title":"Senior React Native Engineer","datePosted":"2026-10-27","hiringOrganization":{"name":"Example Tech"},"jobLocation":{"address":{"addressLocality":"Gurugram","addressRegion":"Haryana"}},"description":"7+ years React Native and TypeScript"}</script></head></html>'''
    rows=_extract_candidates("linkedin",html,"https://www.linkedin.com/jobs/search/")
    assert rows and rows[0]["role"]=="Senior React Native Engineer"
    assert rows[0]["company"]=="Example Tech"