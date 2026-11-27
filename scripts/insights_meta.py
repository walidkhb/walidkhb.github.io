#!/usr/bin/env python3
"""Normalise the Insights articles and rebuild the curated Insights index.

    python3 scripts/insights_meta.py

For every article in blog/ (pages carrying a BlogPosting JSON-LD block) it:
  * turns the pseudo-headings (<p class="article-section">) into real <h2>s;
  * rebuilds the page header: breadcrumb, the unchanged <h1>, and one meta
    strip (author, published date, reading time at ~230 wpm);
  * replaces the old author bio with a short author box, a series note for
    Decision briefs, and 2-3 related articles chosen by topic;
  * rewrites the head JSON-LD as one BlogPosting plus one BreadcrumbList,
    using only the dates already published on the page;
  * links assets/css/insights.css.

It then regenerates the marked region of blog.html (flagship essays,
collections and the Decision briefs series) from the same data.

Idempotent: running it twice produces the same files. Titles, URLs, dates
and og images are read from the pages and never changed.
"""
import glob
import html
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.wbadawi.info'
WPM = 230
CSS_LINK = '<link rel="stylesheet" href="../assets/css/insights.css?v=20261127">'
PERSON = {"@id": SITE + "/#person", "@type": "Person", "name": "Waleed Albadawi"}
AUTHOR_SENTENCE = ('Waleed Albadawi is an enterprise technology and transformation executive in '
                   'regulated banking who connects business strategy with engineering execution, '
                   'turning fragmented technology delivery into governed, resilient, reusable '
                   'institutional capability.')

# Articles whose body text was materially edited (editorial and sensitivity
# review, 27 November 2026). dateModified is set only for these.
EDITED_ON = '2026-11-27'
EDITED = set('''
ai-without-infrastructure anti-corruption-layer-decision apache-camel-enterprise-integration
api-waf-decision asyncapi-event-contracts-decision aws-api-gateway-regulated-workloads
beyond-the-sla-managed-services cache-invalidation-decision canonical-data-model-decision
circuit-breaker-decision conflict-resolution-decision cross-region-data-replication-decision
dead-letter-queue-decision distributed-session-decision event-driven-data-mesh-decision
event-sourcing-cqrs-payments-decision fapi-2-decision flink-on-openshift-decision
graphql-federation-decision hazelcast-in-process-caching-decision idempotent-consumer-decision
iso-20022-migration-decision multi-cluster-gitops-decision near-cache-read-replicas-decision
observability-pipeline-decision open-banking-consent-architecture open-source-gateway-decision
platform-idp-for-integration-leaders portfolio-before-platform progressive-delivery-decision
rate-limiting-decision real-time-fraud-detection-decision reconciliation-pipelines-decision
saga-patterns-distributed-transactions-decision sama-open-banking-phase-2 scatter-gather-decision
schema-registry-decision service-mesh-mtls-decision soap-to-rest-decision
stateful-stream-processing-decision stream-analytics-data-decisions
vault-pki-cert-lifecycle-decision vault-secrets-decision why-digital-transformations-fail
'''.split())

COLLECTIONS = {
    'operating-models': {
        'name': 'Operating models & platform strategy',
        'desc': 'How technology organisations are structured, funded and sequenced so that delivery '
                'compounds: platforms over projects, the portfolio before the platform, and the '
                'organisation design that keeps architecture honest.',
    },
    'governance-resilience': {
        'name': 'Governance & resilience',
        'desc': 'Governance that speeds delivery up, sourcing that keeps design authority inside the '
                'bank, and resilience treated as an operating discipline rather than a diagram.',
    },
    'open-banking': {
        'name': 'Open Banking, payments & ecosystems',
        'desc': 'SAMA’s Open Banking framework and payment modernisation as strategy: what Phase 2 '
                'changes, why consent is a product decision, and the specification work that decides '
                'go-live.',
    },
    'ai-strategy': {
        'name': 'AI strategy & governance',
        'desc': 'Why banking AI stalls on data and integration foundations, and why automation only '
                'pays when the operating model is redesigned around it.',
    },
    'decision-briefs': {
        'name': 'Decision briefs',
        'desc': '',
    },
}

# slug -> (collection, tags)
A = {
    # Operating models & platform strategy
    'core-banking-as-a-product': ('operating-models', 'core operating-model platform apis legacy'),
    'live-code-is-the-spec': ('operating-models', 'legacy modernisation delivery-governance rules'),
    'architecture-not-a-plan': ('operating-models', 'delivery-governance portfolio operating-model'),
    'portfolio-before-platform': ('operating-models', 'portfolio modernisation operating-model'),
    'running-sixteen-domains-parallel': ('operating-models', 'portfolio delivery-governance operating-model'),
    'platform-mindset-build-capabilities': ('operating-models', 'platform operating-model funding'),
    'platform-idp-for-integration-leaders': ('operating-models', 'platform developer-platform operating-model'),
    'integration-leaders-real-job': ('operating-models', 'org-design operating-model governance'),
    'why-digital-transformations-fail': ('operating-models', 'org-design operating-model transformation'),
    # Governance & resilience
    'beyond-the-sla-managed-services': ('governance-resilience', 'sourcing governance vendors'),
    'governance-that-accelerates': ('governance-resilience', 'governance standards platform'),
    'platform-resilience-organizational-discipline': ('governance-resilience', 'resilience governance continuity'),
    'cloud-migration-regulated-banking': ('governance-resilience', 'cloud governance transformation'),
    # Open Banking, payments & ecosystems
    'open-banking-ksa-strategic-opportunity': ('open-banking', 'open-banking ecosystem strategy'),
    'sama-open-banking-phase-2': ('open-banking', 'open-banking ecosystem payments strategy'),
    'open-banking-consent-architecture': ('open-banking', 'open-banking consent platform'),
    'contract-before-code-payment-modernisation': ('open-banking', 'payments specifications delivery-governance'),
    # AI strategy & governance
    'ai-without-infrastructure': ('ai-strategy', 'ai data platform'),
    'automation-trap-banking-operations': ('ai-strategy', 'ai operating-model transformation'),
    # Decision briefs
    'payment-rail-migration-decision': ('decision-briefs', 'payments modernisation delivery'),
    'idempotent-consumer-decision': ('decision-briefs', 'payments messaging data-integrity'),
    'saga-patterns-distributed-transactions-decision': ('decision-briefs', 'payments data-integrity'),
    'event-sourcing-cqrs-payments-decision': ('decision-briefs', 'payments audit data'),
    'iso-20022-migration-decision': ('decision-briefs', 'payments specifications contracts'),
    'reconciliation-pipelines-decision': ('decision-briefs', 'data-integrity audit payments'),
    'real-time-fraud-detection-decision': ('decision-briefs', 'fraud streaming ai'),
    'dead-letter-queue-decision': ('decision-briefs', 'messaging payments resilience'),
    'open-banking-conformance-decision': ('decision-briefs', 'open-banking api-security audit'),
    'fapi-2-decision': ('decision-briefs', 'open-banking api-security consent'),
    'scatter-gather-decision': ('decision-briefs', 'open-banking apis core'),
    'api-composition-decision': ('decision-briefs', 'apis open-banking channels'),
    'rate-limiting-decision': ('decision-briefs', 'apis open-banking api-security'),
    'api-waf-decision': ('decision-briefs', 'api-security open-banking security'),
    'graphql-federation-decision': ('decision-briefs', 'apis governance channels'),
    'soap-to-rest-decision': ('decision-briefs', 'legacy apis modernisation'),
    'open-source-gateway-decision': ('decision-briefs', 'apis sourcing api-security'),
    'aws-api-gateway-regulated-workloads': ('decision-briefs', 'cloud apis api-security'),
    'anti-corruption-layer-decision': ('decision-briefs', 'core legacy contracts'),
    'canonical-data-model-decision': ('decision-briefs', 'contracts payments data'),
    'asyncapi-event-contracts-decision': ('decision-briefs', 'contracts streaming governance'),
    'schema-registry-decision': ('decision-briefs', 'contracts streaming data'),
    'event-driven-data-mesh-decision': ('decision-briefs', 'data contracts org-design'),
    'stream-analytics-data-decisions': ('decision-briefs', 'streaming data'),
    'stateful-stream-processing-decision': ('decision-briefs', 'streaming fraud'),
    'flink-on-openshift-decision': ('decision-briefs', 'streaming platform payments'),
    'apache-camel-enterprise-integration': ('decision-briefs', 'sourcing platform modernisation'),
    'circuit-breaker-decision': ('decision-briefs', 'resilience payments'),
    'conflict-resolution-decision': ('decision-briefs', 'resilience continuity data-integrity'),
    'cross-region-data-replication-decision': ('decision-briefs', 'continuity resilience'),
    'cache-invalidation-decision': ('decision-briefs', 'caching data-integrity'),
    'multi-tier-caching-decision': ('decision-briefs', 'caching resilience'),
    'near-cache-read-replicas-decision': ('decision-briefs', 'caching data-integrity'),
    'hazelcast-in-process-caching-decision': ('decision-briefs', 'caching platform'),
    'distributed-session-decision': ('decision-briefs', 'security channels caching'),
    'audit-ready-releases-decision': ('decision-briefs', 'delivery governance audit'),
    'progressive-delivery-decision': ('decision-briefs', 'delivery resilience'),
    'multi-cluster-gitops-decision': ('decision-briefs', 'delivery continuity platform'),
    'observability-pipeline-decision': ('decision-briefs', 'observability resilience platform'),
    'service-mesh-mtls-decision': ('decision-briefs', 'security platform'),
    'vault-secrets-decision': ('decision-briefs', 'security platform'),
    'vault-pki-cert-lifecycle-decision': ('decision-briefs', 'security audit'),
}

# Hand-picked related reading where topic overlap alone is weak.
RELATED_OVERRIDE = {
    'live-code-is-the-spec': ['payment-rail-migration-decision', 'core-banking-as-a-product', 'soap-to-rest-decision'],
    'core-banking-as-a-product': ['anti-corruption-layer-decision', 'live-code-is-the-spec', 'platform-mindset-build-capabilities'],
    'beyond-the-sla-managed-services': ['governance-that-accelerates', 'open-source-gateway-decision', 'platform-resilience-organizational-discipline'],
    'automation-trap-banking-operations': ['ai-without-infrastructure', 'why-digital-transformations-fail', 'real-time-fraud-detection-decision'],
    'ai-without-infrastructure': ['automation-trap-banking-operations', 'real-time-fraud-detection-decision', 'event-driven-data-mesh-decision'],
    'audit-ready-releases-decision': ['progressive-delivery-decision', 'multi-cluster-gitops-decision', 'governance-that-accelerates'],
    'open-banking-conformance-decision': ['fapi-2-decision', 'sama-open-banking-phase-2', 'open-banking-consent-architecture'],
    'payment-rail-migration-decision': ['contract-before-code-payment-modernisation', 'live-code-is-the-spec', 'idempotent-consumer-decision'],
    'open-banking-consent-architecture': ['sama-open-banking-phase-2', 'fapi-2-decision', 'open-banking-ksa-strategic-opportunity'],
    'integration-leaders-real-job': ['why-digital-transformations-fail', 'governance-that-accelerates', 'running-sixteen-domains-parallel'],
    'why-digital-transformations-fail': ['integration-leaders-real-job', 'automation-trap-banking-operations', 'platform-mindset-build-capabilities'],
    'cloud-migration-regulated-banking': ['beyond-the-sla-managed-services', 'cross-region-data-replication-decision', 'aws-api-gateway-regulated-workloads'],
    'platform-resilience-organizational-discipline': ['cross-region-data-replication-decision', 'observability-pipeline-decision', 'circuit-breaker-decision'],
}

FLAGSHIP = [
    ('core-banking-as-a-product',
     'Why the core becomes every project’s queue, and the operating-model shift — a catalogue, '
     'business APIs, a simulator and a named owner — that turns it into a product the whole bank builds on.'),
    ('live-code-is-the-spec',
     'Before rewriting legacy integration, recover the rules the running code actually enforces. A method '
     'for rule recovery, and the four decisions only leadership can make.'),
    ('payment-rail-migration-decision',
     'Moving payment schemes one at a time behind a fixed channel contract, with dark launches, agreed '
     'discrepancy thresholds and evidence — not the calendar — deciding each cutover.'),
    ('audit-ready-releases-decision',
     'What traceable delivery gives a board and an auditor, what it does not, and the four decisions that '
     'sit above engineering: freeze windows, merge rights, standards ownership and closing the manual path.'),
    ('open-banking-conformance-decision',
     'Treat conformance as a capability you operate, not a certificate you hold — and report sandbox, '
     'strict and certified results as the three different statements they are.'),
    ('beyond-the-sla-managed-services',
     'Why design authority, not the service level agreement, decides whether outsourcing reduces risk, '
     'and what to settle before the contract is signed.'),
    ('open-banking-consent-architecture',
     'Build consent as a platform or as a Phase 2 deliverable? The answer depends on a question leadership '
     'has to answer first: what is Open Banking for?'),
    ('automation-trap-banking-operations',
     'Why automating tasks rarely transforms operations, and what does: process-level design, a plan for '
     'freed capacity, a designed exception path and accountable ownership of automated decisions.'),
]

BRIEF_GROUPS = [
    ('Payments & money movement', [
        ('payment-rail-migration-decision', 'Payment rail migration', 'one scheme at a time, evidence before cutover'),
        ('idempotent-consumer-decision', 'Idempotent consumers', 'who owns duplicate-payment prevention'),
        ('saga-patterns-distributed-transactions-decision', 'Payment sagas', 'compensation authority and stuck-payment ownership'),
        ('event-sourcing-cqrs-payments-decision', 'Event sourcing', 'when an audit-grade ledger is worth its cost'),
        ('iso-20022-migration-decision', 'ISO 20022', 'purpose codes, coexistence and the testing mandate'),
        ('reconciliation-pipelines-decision', 'Reconciliation pipelines', 'proving the data arrived, not only that it was sent'),
        ('real-time-fraud-detection-decision', 'Real-time fraud detection', 'who sets the threshold and feeds the model'),
        ('dead-letter-queue-decision', 'Dead letter queues', 'what happens to the message nobody can process'),
    ]),
    ('Open Banking & APIs', [
        ('open-banking-conformance-decision', 'Open Banking conformance', 'a capability you operate, not a certificate'),
        ('fapi-2-decision', 'FAPI 2.0', 'the identity and consent decisions behind the profile'),
        ('scatter-gather-decision', 'Scatter-gather', 'what a partial result means to the customer'),
        ('api-composition-decision', 'Backend for frontend', 'who owns the shape of a channel’s API'),
        ('rate-limiting-decision', 'Rate limiting', 'limits as commercial terms with named owners'),
        ('api-waf-decision', 'API security', 'why OWASP API risks need design, not only a firewall'),
        ('graphql-federation-decision', 'GraphQL federation', 'subgraph ownership and breaking-change policy'),
        ('soap-to-rest-decision', 'SOAP to REST', 'wrap, rewrite or expose, and who owns the contract'),
        ('open-source-gateway-decision', 'Open-source gateway', 'a capability transfer, not a cost saving'),
        ('aws-api-gateway-regulated-workloads', 'Managed API gateway', 'shared responsibility in a regulated bank'),
    ]),
    ('Data, events & contracts', [
        ('anti-corruption-layer-decision', 'Anti-corruption layer', 'drawing and owning the boundary with the core'),
        ('canonical-data-model-decision', 'Canonical data model', 'one representation of a payment, one owner'),
        ('asyncapi-event-contracts-decision', 'Event contracts', 'contract-first channels with PDPL classification'),
        ('schema-registry-decision', 'Schema governance', 'a compatibility policy with teeth'),
        ('event-driven-data-mesh-decision', 'Data mesh', 'moving accountability, not only labels'),
        ('stream-analytics-data-decisions', 'SQL on streams', 'a persistent service you decide to own'),
        ('stateful-stream-processing-decision', 'Stateful stream processing', 'what exactly-once means to the business'),
        ('flink-on-openshift-decision', 'Flink as a platform', 'funding the team before the first job'),
        ('apache-camel-enterprise-integration', 'Open-source integration', 'a dual-track path, not rip-and-replace'),
    ]),
    ('Resilience & continuity', [
        ('circuit-breaker-decision', 'Circuit breakers', 'fallbacks are business commitments'),
        ('conflict-resolution-decision', 'Active-active writes', 'what a continuity attestation really promises'),
        ('cross-region-data-replication-decision', 'Cross-region replication', 'the topology you can actually operate'),
        ('cache-invalidation-decision', 'Cache invalidation', 'staleness as a signed-off policy'),
        ('multi-tier-caching-decision', 'Multi-tier caching', 'which data may be stale, and for how long'),
        ('near-cache-read-replicas-decision', 'Near-cache and replicas', 'caching as a risk architecture'),
        ('hazelcast-in-process-caching-decision', 'In-process caching', 'a rule for where state lives'),
        ('distributed-session-decision', 'Distributed sessions', 'timeouts and re-authentication as policy'),
    ]),
    ('Delivery, security & operations', [
        ('audit-ready-releases-decision', 'Audit-ready releases', 'the release as its own evidence'),
        ('progressive-delivery-decision', 'Progressive delivery', 'who owns the promotion gate'),
        ('multi-cluster-gitops-decision', 'Multi-cluster GitOps', 'deployment governance enforced by the system'),
        ('observability-pipeline-decision', 'Observability', 'telemetry funded and governed as infrastructure'),
        ('service-mesh-mtls-decision', 'Service mesh mTLS', 'committing to strict mode and holding it'),
        ('vault-secrets-decision', 'Secrets management', 'dynamic credentials and who runs the vault'),
        ('vault-pki-cert-lifecycle-decision', 'Certificate lifecycle', 'automated rotation as a pre-approved change'),
    ]),
]

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']

JSONLD_RE = re.compile(r'\s*<script type="application/ld\+json">.*?</script>', re.S)


def uk_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def esc(s):
    return html.escape(s, quote=True)


def text_of(fragment):
    t = re.sub(r'<(script|style|svg)\b.*?</\1>', ' ', fragment, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    return html.unescape(t)


def balanced_div_end(s, start):
    """Index just after the </div> closing the <div> that starts at `start`."""
    depth = 0
    for m in re.finditer(r'<div\b|</div>', s[start:]):
        depth += 1 if m.group(0) != '</div>' else -1
        if depth == 0:
            return start + m.end()
    raise ValueError('unbalanced div')


def load(slug):
    path = os.path.join(ROOT, 'blog', slug + '.html')
    s = open(path, encoding='utf-8').read()
    post = None
    for blob in re.findall(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', s, re.S):
        try:
            d = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if d.get('@type') == 'BlogPosting':
            post = d
            break
    if post is None:
        raise SystemExit('no BlogPosting in ' + slug)
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S).group(1).strip()
    desc = re.search(r'<meta name="description" content="(.*?)">', s, re.S)
    og = re.search(r'<meta property="og:image" content="(.*?)">', s)
    body_start = s.index('<div class="article-body')
    body = s[body_start:balanced_div_end(s, body_start)]
    words = len(text_of(body).split())
    return {
        'slug': slug, 'path': path, 'src': s, 'h1': h1,
        'headline': html.unescape(post.get('headline') or text_of(h1)).strip(),
        'published': post['datePublished'],
        'modified': EDITED_ON if slug in EDITED else post['datePublished'],
        'desc': html.unescape(desc.group(1)).strip() if desc else '',
        'image': og.group(1) if og else SITE + '/assets/img/og-image.png',
        'url': SITE + '/blog/' + slug + '.html',
        'words': words,
        'minutes': max(1, math.ceil(words / WPM)),
        'collection': A[slug][0],
        'tags': set(A[slug][1].split()),
    }


def related(art, arts):
    if art['slug'] in RELATED_OVERRIDE:
        return [arts[s] for s in RELATED_OVERRIDE[art['slug']]]
    flagship = {s for s, _ in FLAGSHIP}
    scored = []
    for other in arts.values():
        if other['slug'] == art['slug']:
            continue
        score = 2 * len(art['tags'] & other['tags'])
        if score == 0:
            continue
        if other['collection'] == art['collection']:
            score += 1
        if other['collection'] != 'decision-briefs':
            score += 0.5  # surface essays alongside briefs
        if other['slug'] in flagship:
            score += 0.5
        scored.append((score, other['published'], other['slug']))
    scored.sort(reverse=True)
    return [arts[s] for _, _, s in scored[:3]]


def label(art):
    return 'Decision brief' if art['collection'] == 'decision-briefs' else COLLECTIONS[art['collection']]['name']


def header_html(art):
    c = art['collection']
    return (
        '\n      <nav class="breadcrumb" aria-label="Breadcrumb"><a href="../blog.html">Insights</a>'
        '<span aria-hidden="true">/</span><a href="../blog.html#%s">%s</a></nav>\n'
        '      <h1 class="insights-title">%s</h1>\n'
        '      <div class="article-meta insights-meta">\n'
        '        <span class="article-meta__item">By <a href="../about.html" rel="author">Waleed Albadawi</a></span>\n'
        '        <span class="article-meta__item"><time datetime="%s">%s</time></span>\n'
        '        <span class="article-meta__item">%d min read</span>\n'
        '      </div>\n    ' % (c, esc(COLLECTIONS[c]['name']), art['h1'], art['published'],
                                uk_date(art['published']), art['minutes'])
    )


def end_html(art, arts):
    parts = ['\n\n        <!-- insights:end -->\n        <div class="insights-end">\n']
    if art['collection'] == 'decision-briefs':
        parts.append(
            '          <p class="insights-series-note">Part of the <a href="../blog.html#decision-briefs">'
            'Decision briefs</a> series: one architecture choice at a time, and the decisions that belong '
            'above it.</p>\n')
    parts.append(
        '          <aside class="insights-author" aria-label="About the author">\n'
        '            <p class="insights-author__text">%s</p>\n'
        '            <a class="insights-author__link" href="../about.html">About Waleed Albadawi &rarr;</a>\n'
        '          </aside>\n' % esc(AUTHOR_SENTENCE))
    rel = related(art, arts)
    parts.append('          <nav class="insights-related" aria-labelledby="related-heading">\n'
                 '            <h2 id="related-heading" class="insights-related__heading">Related insights</h2>\n'
                 '            <div class="insights-related__grid">\n')
    for r in rel:
        parts.append(
            '              <a class="thinking-card" href="%s.html">\n'
            '                <span class="thinking-card__topic">%s &middot; %d min read</span>\n'
            '                <span class="thinking-card__title">%s</span>\n'
            '              </a>\n' % (r['slug'], esc(label(r)), r['minutes'], r['h1']))
    parts.append('            </div>\n          </nav>\n        </div>\n        <!-- /insights:end -->')
    return ''.join(parts)


def jsonld(art):
    coll = COLLECTIONS[art['collection']]['name']
    post = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": art['headline'],
        "description": art['desc'],
        "image": art['image'],
        "datePublished": art['published'],
        "dateModified": art['modified'],
        "author": PERSON,
        "publisher": PERSON,
        "mainEntityOfPage": {"@type": "WebPage", "@id": art['url']},
        "url": art['url'],
        "isPartOf": {"@type": "Blog", "name": "Insights — Waleed Albadawi", "url": SITE + "/blog.html"},
        "articleSection": coll,
        "inLanguage": "en",
        "wordCount": art['words'],
        "timeRequired": "PT%dM" % art['minutes'],
    }
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Insights", "item": SITE + "/blog.html"},
            {"@type": "ListItem", "position": 3, "name": coll, "item": SITE + "/blog.html#" + art['collection']},
            {"@type": "ListItem", "position": 4, "name": art['headline'], "item": art['url']},
        ],
    }

    def block(d):
        txt = json.dumps(d, ensure_ascii=False, indent=2).replace('</', '<\\/')
        return '  <script type="application/ld+json">\n' + '\n'.join('  ' + l for l in txt.split('\n')) + '\n  </script>'
    return block(post) + '\n' + block(crumbs)


def rewrite(art, arts):
    s = art['src']
    # 1. Real section headings.
    s = re.sub(r'<p class="article-section"([^>]*)>(.*?)</p>', r'<h2 class="article-section"\1>\2</h2>', s, flags=re.S)
    # 2. Old author bio (h3, outdated copy) goes; the new author box replaces it.
    s = re.sub(r'\s*<!-- Author Bio -->\s*<section class="author-bio">.*?</section>', '', s, flags=re.S)
    s = re.sub(r'\s*<section class="author-bio">.*?</section>', '', s, flags=re.S)
    # 3. Page header.
    m = re.search(r'(<section class="page-header">\s*<div class="container">)(.*?)(</div>\s*</section>)', s, re.S)
    s = s[:m.start(2)] + header_html(art) + s[m.end(2):]
    # 4. End block after the article body.
    s = re.sub(r'\n*\s*<!-- insights:end -->.*?<!-- /insights:end -->', '', s, flags=re.S)
    start = s.index('<div class="article-body')
    end = balanced_div_end(s, start)
    s = s[:end] + end_html(art, arts) + s[end:]
    # 5. Head: JSON-LD, article dates, stylesheet.
    head_end = s.index('</head>')
    head, rest = s[:head_end], s[head_end:]
    head = JSONLD_RE.sub('', head)
    head = re.sub(r'\s*<!-- JSON-LD -->', '', head)
    head = re.sub(r'\s*<meta property="article:(published|modified)_time" content="[^"]*">', '', head)
    meta = '\n  <meta property="article:published_time" content="%s">' % art['published']
    if art['modified'] != art['published']:
        meta += '\n  <meta property="article:modified_time" content="%s">' % art['modified']
    head = head.replace('<meta property="og:type" content="article">',
                        '<meta property="og:type" content="article">' + meta, 1)
    if CSS_LINK not in head:
        last_style = head.rfind('</style>')
        anchor = last_style + len('</style>') if last_style != -1 else head.index('style.css') + head[head.index('style.css'):].index('>') + 1
        head = head[:anchor] + '\n  ' + CSS_LINK + head[anchor:]
    head = head.rstrip() + '\n' + jsonld(art) + '\n'
    s = head + rest
    return s


# ---------------------------------------------------------------- blog.html
def index_html(arts):
    out = ['<!-- insights:index (generated by scripts/insights_meta.py; edit the data there) -->\n']
    out.append(
        '  <section class="insights-section" id="flagship" aria-labelledby="flagship-heading">\n'
        '    <div class="container">\n'
        '      <span class="overline">Start here</span>\n'
        '      <h2 id="flagship-heading" class="insights-h2">Flagship essays</h2>\n'
        '      <p class="insights-intro">Eight pieces that set out how I approach the work: what the decision really is, '
        'who has to own it, and what the organisation needs for it to hold.</p>\n'
        '      <div class="grid grid--2 insights-flagship">\n')
    for slug, summary in FLAGSHIP:
        a = arts[slug]
        out.append(
            '        <a class="thinking-card" href="blog/%s.html">\n'
            '          <span class="thinking-card__topic">%s</span>\n'
            '          <span class="thinking-card__title">%s</span>\n'
            '          <span class="insights-card__summary">%s</span>\n'
            '          <span class="thinking-card__more">%s &middot; %d min read</span>\n'
            '        </a>\n' % (slug, esc(label(a)), a['h1'], esc(summary), uk_date(a['published']), a['minutes']))
    out.append('      </div>\n    </div>\n  </section>\n\n')

    out.append(
        '  <section class="insights-section section--alt" id="collections" aria-labelledby="collections-heading">\n'
        '    <div class="container">\n'
        '      <span class="overline">Collections</span>\n'
        '      <h2 id="collections-heading" class="insights-h2">Essays by theme</h2>\n'
        '      <div class="grid grid--2 insights-collections">\n')
    for cid in ('operating-models', 'governance-resilience', 'open-banking', 'ai-strategy'):
        items = sorted([a for a in arts.values() if a['collection'] == cid],
                       key=lambda a: (a['published'], a['slug']), reverse=True)
        out.append(
            '        <div class="domain-block insights-collection" id="%s">\n'
            '          <h3 class="domain-block__title">%s</h3>\n'
            '          <p class="domain-block__desc">%s</p>\n'
            '          <ul class="insights-list">\n' % (cid, esc(COLLECTIONS[cid]['name']), esc(COLLECTIONS[cid]['desc'])))
        for a in items:
            out.append(
                '            <li><a href="blog/%s.html">%s</a><span class="insights-list__meta">%s &middot; %d min</span></li>\n'
                % (a['slug'], a['h1'], uk_date(a['published']), a['minutes']))
        out.append('          </ul>\n        </div>\n')
    out.append('      </div>\n    </div>\n  </section>\n\n')

    n_briefs = sum(len(g[1]) for g in BRIEF_GROUPS)
    out.append(
        '  <section class="insights-section" id="decision-briefs" aria-labelledby="briefs-heading">\n'
        '    <div class="container">\n'
        '      <span class="overline">A series of %d</span>\n'
        '      <h2 id="briefs-heading" class="insights-h2">Decision briefs</h2>\n'
        '      <p class="insights-intro">Most architecture choices in a bank are settled in an engineering meeting. '
        'Each brief takes one of them &mdash; a caching strategy, a gateway, a replication topology &mdash; and asks '
        'what belongs above that meeting: who owns it, what risk the bank is accepting, what evidence a regulator '
        'will ask for, and what the team needs from leadership. The titles follow one formula on purpose: they '
        'name the pattern, then the decision it really is. Each brief links to a companion Lab article with the '
        'engineering detail.</p>\n'
        '      <ol class="insights-anatomy" aria-label="How every brief is structured">\n'
        '        <li><span class="insights-anatomy__step">1</span>The decision behind the pattern</li>\n'
        '        <li><span class="insights-anatomy__step">2</span>What the regulator will ask</li>\n'
        '        <li><span class="insights-anatomy__step">3</span>The trade-off the business owns</li>\n'
        '        <li><span class="insights-anatomy__step">4</span>What leadership must decide</li>\n'
        '      </ol>\n'
        '      <div class="insights-brief-groups">\n' % n_briefs)
    for gname, items in BRIEF_GROUPS:
        out.append(
            '        <div class="domain-block insights-brief-group">\n'
            '          <h3 class="domain-block__title">%s</h3>\n'
            '          <ul class="insights-briefs">\n' % esc(gname))
        for slug, short, line in items:
            a = arts[slug]
            out.append(
                '            <li><a href="blog/%s.html">%s</a><span class="insights-briefs__line">%s</span>'
                '<span class="insights-list__meta">%d min</span></li>\n' % (slug, esc(short), esc(line), a['minutes']))
        out.append('          </ul>\n        </div>\n')
    out.append('      </div>\n    </div>\n  </section>\n')
    out.append('  <!-- /insights:index -->')
    return ''.join(out)


def main():
    slugs = []
    for path in sorted(glob.glob(os.path.join(ROOT, 'blog', '*.html'))):
        if '"BlogPosting"' in open(path, encoding='utf-8').read():
            slugs.append(os.path.basename(path)[:-5])
    missing = set(slugs) - set(A)
    extra = set(A) - set(slugs)
    if missing or extra:
        raise SystemExit('collection map out of date: missing %s, unknown %s' % (sorted(missing), sorted(extra)))
    briefs = [s for _, g in BRIEF_GROUPS for s, _, _ in g]
    assert sorted(briefs) == sorted(s for s in A if A[s][0] == 'decision-briefs'), 'brief groups out of date'
    arts = {s: load(s) for s in slugs}
    changed = 0
    for art in arts.values():
        new = rewrite(art, arts)
        if new != art['src']:
            open(art['path'], 'w', encoding='utf-8').write(new)
            changed += 1
    blog = os.path.join(ROOT, 'blog.html')
    b = open(blog, encoding='utf-8').read()
    nb = re.sub(r'<!-- insights:index.*?<!-- /insights:index -->', lambda m: index_html(arts), b, count=1, flags=re.S)
    if nb != b:
        open(blog, 'w', encoding='utf-8').write(nb)
        changed += 1
    print('articles: %d, files updated: %d' % (len(arts), changed))


if __name__ == '__main__':
    main()
