#!/usr/bin/env python3
"""Reading-experience metadata for the Technical Lab (idempotent).

    python3 scripts/lab_meta.py           # rewrite lab/*.html and lab/*/*.html in place
    python3 scripts/lab_meta.py --check   # report what would change, write nothing

For every article (lab/<category>/<slug>.html) it maintains:
  - a byline under the <h1>: author, published date, updated date (only for
    articles listed in UPDATED) and reading time (~230 words per minute)
  - the standard reference-architecture note under the lead
  - an author box, related Lab articles and an Insights companion before the
    article navigation
  - TechArticle + BreadcrumbList JSON-LD (real dates only)
  - heading levels without skips (h2 -> h4 becomes h2 -> h3)
  - the link to assets/css/lab.css
For every category index (lab/<category>.html) it refreshes the reading time and
date of each listed article, adds a "Further reading" list of official
documentation, and links lab.css.

Everything it inserts sits between <!-- lab-meta:... --> markers or in elements
with lab-* classes, so running it again replaces rather than duplicates.
"""
import glob
import html
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://www.wbadawi.info"
WPM = 230
CSS_VERSION = "20261127"
PERSON = {"@id": f"{SITE}/#person", "@type": "Person", "name": "Waleed Albadawi"}

NOTE = ("Reference architecture with illustrative code &mdash; not a description of any "
        "specific organisation&rsquo;s production systems.")
AUTHOR_SENTENCE = ("Waleed Albadawi is an enterprise technology and transformation executive in "
                   "regulated banking who connects business strategy with engineering execution, "
                   "turning fragmented technology delivery into governed, resilient, reusable "
                   "institutional capability.")

# Articles whose content was materially corrected, and when. Only these show "Updated".
_FIX_DATE = "2026-11-27"
UPDATED = {p: _FIX_DATE for p in """
api-gateway/aws-api-gateway api-gateway/graphql-federation api-gateway/ibm-api-connect
api-gateway/kong-and-envoy api-gateway/rate-limiting-and-throttling
api-security/api-waf-and-owasp api-security/fapi-2-open-banking api-security/oauth-and-mtls
api-security/open-banking-consent-management api-security/service-mesh-mtls-at-scale
api-security/vault-pki-and-cert-manager
data-streaming/flink-on-openshift-checkpointing data-streaming/kafka-streams-and-flink
data-streaming/ksqldb-and-flink-sql data-streaming/real-time-fraud-detection
data-streaming/schema-registry-and-data-contracts data-streaming/stateful-stream-processing
data-sync/conflict-resolution-multi-master data-sync/cross-region-replication
data-sync/debezium-and-outbox data-sync/event-driven-data-mesh data-sync/idempotent-consumer-exactly-once
devops/gitops-for-cloud-pak-for-integration devops/internal-developer-platform devops/multi-cluster-gitops
devops/observability-pipeline-architecture devops/progressive-delivery-flagger-argo-rollouts
devops/vault-secrets-management
distributed-caching/cache-invalidation-via-cdc distributed-caching/distributed-session-management
distributed-caching/hazelcast-imdg-in-process-state distributed-caching/near-cache-and-read-replicas
distributed-caching/redis-cluster
event-driven/asyncapi-kafka-contracts event-driven/dead-letter-queue-and-replay event-driven/kafka-and-mq
event-driven/saga-patterns-distributed-transactions event-driven/strimzi-on-private-ocp
field-playbooks/timeouts-and-unknown-outcomes
integration-patterns/api-composition-and-bff integration-patterns/apache-camel-cloud-native
integration-patterns/circuit-breaker-and-bulkhead integration-patterns/hold-and-release-payments
integration-patterns/ibm-ace integration-patterns/idempotency-keys integration-patterns/iso-20022-transformation
integration-patterns/scatter-gather-aggregation
legacy-integration/anti-corruption-layer-core-banking legacy-integration/legacy-message-apis-and-simulators
legacy-integration/soap-to-rest-modernisation
""".split()}

# Last material content change for articles not in UPDATED (git history: the Lab was
# generalised on 27 Nov 2026). Articles absent from both use their published date.
REVISED = {p: "2026-11-27" for p in """
api-security/fapi-2-conformance-testing data-sync/reconciliation-pipelines-for-regulators
devops/tekton-and-argocd distributed-caching/multi-tier-caching-strategies
event-driven/event-sourcing-and-cqrs event-driven/obligation-ledger-pattern
field-playbooks/changing-a-live-api field-playbooks/onboarding-consumers-in-days
field-playbooks/slow-integration-triage integration-patterns/canonical-data-model
""".split()}

# h1 corrections: two articles carried the category name as their title
H1_FIX = {
    "devops/internal-developer-platform":
        "Internal Developer Platform for Integration Teams: Backstage, Golden Paths &amp; Scaffolders",
    "devops/tekton-and-argocd": "DevOps &amp; Platform Engineering: Tekton &amp; ArgoCD",
}

# Related Lab articles (2-3) and the Insights companion, keyed by category/slug
RELATED = {
    "api-gateway/aws-api-gateway": ["api-gateway/kong-and-envoy", "api-gateway/rate-limiting-and-throttling", "api-security/oauth-and-mtls"],
    "api-gateway/graphql-federation": ["integration-patterns/api-composition-and-bff", "api-gateway/rate-limiting-and-throttling", "api-gateway/kong-and-envoy"],
    "api-gateway/ibm-api-connect": ["api-gateway/kong-and-envoy", "api-gateway/rate-limiting-and-throttling", "legacy-integration/soap-to-rest-modernisation"],
    "api-gateway/kong-and-envoy": ["api-gateway/ibm-api-connect", "api-gateway/rate-limiting-and-throttling", "api-security/service-mesh-mtls-at-scale"],
    "api-gateway/rate-limiting-and-throttling": ["api-gateway/kong-and-envoy", "api-security/api-waf-and-owasp", "api-gateway/aws-api-gateway"],
    "api-security/api-waf-and-owasp": ["api-gateway/rate-limiting-and-throttling", "api-security/fapi-2-open-banking", "api-security/oauth-and-mtls"],
    "api-security/fapi-2-conformance-testing": ["api-security/fapi-2-open-banking", "api-security/open-banking-consent-management", "api-security/oauth-and-mtls"],
    "api-security/fapi-2-open-banking": ["api-security/fapi-2-conformance-testing", "api-security/open-banking-consent-management", "api-security/vault-pki-and-cert-manager"],
    "api-security/oauth-and-mtls": ["api-security/fapi-2-open-banking", "api-security/service-mesh-mtls-at-scale", "api-security/vault-pki-and-cert-manager"],
    "api-security/open-banking-consent-management": ["api-security/fapi-2-open-banking", "integration-patterns/scatter-gather-aggregation", "api-security/fapi-2-conformance-testing"],
    "api-security/service-mesh-mtls-at-scale": ["api-security/vault-pki-and-cert-manager", "api-security/oauth-and-mtls", "devops/observability-pipeline-architecture"],
    "api-security/vault-pki-and-cert-manager": ["devops/vault-secrets-management", "api-security/service-mesh-mtls-at-scale", "api-security/oauth-and-mtls"],
    "data-streaming/flink-on-openshift-checkpointing": ["data-streaming/stateful-stream-processing", "data-streaming/real-time-fraud-detection", "data-streaming/kafka-streams-and-flink"],
    "data-streaming/kafka-streams-and-flink": ["data-streaming/stateful-stream-processing", "data-streaming/ksqldb-and-flink-sql", "event-driven/kafka-and-mq"],
    "data-streaming/ksqldb-and-flink-sql": ["data-streaming/kafka-streams-and-flink", "data-streaming/schema-registry-and-data-contracts", "data-streaming/real-time-fraud-detection"],
    "data-streaming/real-time-fraud-detection": ["data-streaming/stateful-stream-processing", "data-streaming/flink-on-openshift-checkpointing", "distributed-caching/multi-tier-caching-strategies"],
    "data-streaming/schema-registry-and-data-contracts": ["event-driven/asyncapi-kafka-contracts", "data-sync/event-driven-data-mesh", "data-streaming/ksqldb-and-flink-sql"],
    "data-streaming/stateful-stream-processing": ["data-streaming/flink-on-openshift-checkpointing", "data-streaming/kafka-streams-and-flink", "data-streaming/real-time-fraud-detection"],
    "data-sync/conflict-resolution-multi-master": ["data-sync/cross-region-replication", "data-sync/reconciliation-pipelines-for-regulators", "event-driven/saga-patterns-distributed-transactions"],
    "data-sync/cross-region-replication": ["data-sync/conflict-resolution-multi-master", "event-driven/strimzi-on-private-ocp", "data-sync/reconciliation-pipelines-for-regulators"],
    "data-sync/debezium-and-outbox": ["data-sync/idempotent-consumer-exactly-once", "distributed-caching/cache-invalidation-via-cdc", "data-sync/reconciliation-pipelines-for-regulators"],
    "data-sync/event-driven-data-mesh": ["data-streaming/schema-registry-and-data-contracts", "event-driven/asyncapi-kafka-contracts", "data-sync/debezium-and-outbox"],
    "data-sync/idempotent-consumer-exactly-once": ["integration-patterns/idempotency-keys", "data-sync/debezium-and-outbox", "event-driven/dead-letter-queue-and-replay"],
    "data-sync/reconciliation-pipelines-for-regulators": ["data-sync/debezium-and-outbox", "data-sync/idempotent-consumer-exactly-once", "event-driven/event-sourcing-and-cqrs"],
    "devops/gitops-for-cloud-pak-for-integration": ["devops/tekton-and-argocd", "devops/multi-cluster-gitops", "devops/progressive-delivery-flagger-argo-rollouts"],
    "devops/internal-developer-platform": ["devops/gitops-for-cloud-pak-for-integration", "devops/tekton-and-argocd", "field-playbooks/onboarding-consumers-in-days"],
    "devops/multi-cluster-gitops": ["devops/gitops-for-cloud-pak-for-integration", "devops/progressive-delivery-flagger-argo-rollouts", "devops/tekton-and-argocd"],
    "devops/observability-pipeline-architecture": ["field-playbooks/slow-integration-triage", "field-playbooks/first-30-minutes-of-an-incident", "devops/progressive-delivery-flagger-argo-rollouts"],
    "devops/progressive-delivery-flagger-argo-rollouts": ["devops/multi-cluster-gitops", "devops/observability-pipeline-architecture", "field-playbooks/changing-a-live-api"],
    "devops/tekton-and-argocd": ["devops/gitops-for-cloud-pak-for-integration", "devops/vault-secrets-management", "devops/multi-cluster-gitops"],
    "devops/vault-secrets-management": ["api-security/vault-pki-and-cert-manager", "devops/tekton-and-argocd", "api-security/service-mesh-mtls-at-scale"],
    "distributed-caching/cache-invalidation-via-cdc": ["data-sync/debezium-and-outbox", "distributed-caching/multi-tier-caching-strategies", "distributed-caching/near-cache-and-read-replicas"],
    "distributed-caching/distributed-session-management": ["distributed-caching/redis-cluster", "distributed-caching/hazelcast-imdg-in-process-state", "api-security/oauth-and-mtls"],
    "distributed-caching/hazelcast-imdg-in-process-state": ["distributed-caching/near-cache-and-read-replicas", "distributed-caching/redis-cluster", "distributed-caching/multi-tier-caching-strategies"],
    "distributed-caching/multi-tier-caching-strategies": ["distributed-caching/near-cache-and-read-replicas", "distributed-caching/cache-invalidation-via-cdc", "distributed-caching/redis-cluster"],
    "distributed-caching/near-cache-and-read-replicas": ["distributed-caching/multi-tier-caching-strategies", "distributed-caching/hazelcast-imdg-in-process-state", "distributed-caching/redis-cluster"],
    "distributed-caching/redis-cluster": ["distributed-caching/multi-tier-caching-strategies", "distributed-caching/distributed-session-management", "distributed-caching/near-cache-and-read-replicas"],
    "event-driven/asyncapi-kafka-contracts": ["data-streaming/schema-registry-and-data-contracts", "event-driven/kafka-and-mq", "data-sync/event-driven-data-mesh"],
    "event-driven/dead-letter-queue-and-replay": ["data-sync/idempotent-consumer-exactly-once", "event-driven/kafka-and-mq", "field-playbooks/first-30-minutes-of-an-incident"],
    "event-driven/event-sourcing-and-cqrs": ["event-driven/saga-patterns-distributed-transactions", "event-driven/obligation-ledger-pattern", "data-sync/reconciliation-pipelines-for-regulators"],
    "event-driven/kafka-and-mq": ["event-driven/strimzi-on-private-ocp", "event-driven/dead-letter-queue-and-replay", "event-driven/asyncapi-kafka-contracts"],
    "event-driven/obligation-ledger-pattern": ["integration-patterns/hold-and-release-payments", "event-driven/event-sourcing-and-cqrs", "event-driven/saga-patterns-distributed-transactions"],
    "event-driven/saga-patterns-distributed-transactions": ["event-driven/event-sourcing-and-cqrs", "integration-patterns/hold-and-release-payments", "field-playbooks/timeouts-and-unknown-outcomes"],
    "event-driven/strimzi-on-private-ocp": ["event-driven/kafka-and-mq", "data-sync/cross-region-replication", "devops/gitops-for-cloud-pak-for-integration"],
    "field-playbooks/changing-a-live-api": ["field-playbooks/onboarding-consumers-in-days", "event-driven/asyncapi-kafka-contracts", "devops/progressive-delivery-flagger-argo-rollouts"],
    "field-playbooks/first-30-minutes-of-an-incident": ["field-playbooks/slow-integration-triage", "field-playbooks/timeouts-and-unknown-outcomes", "devops/observability-pipeline-architecture"],
    "field-playbooks/onboarding-consumers-in-days": ["field-playbooks/changing-a-live-api", "legacy-integration/legacy-message-apis-and-simulators", "devops/internal-developer-platform"],
    "field-playbooks/slow-integration-triage": ["field-playbooks/first-30-minutes-of-an-incident", "integration-patterns/circuit-breaker-and-bulkhead", "devops/observability-pipeline-architecture"],
    "field-playbooks/timeouts-and-unknown-outcomes": ["integration-patterns/idempotency-keys", "integration-patterns/hold-and-release-payments", "field-playbooks/slow-integration-triage"],
    "integration-patterns/apache-camel-cloud-native": ["integration-patterns/ibm-ace", "integration-patterns/iso-20022-transformation", "integration-patterns/canonical-data-model"],
    "integration-patterns/api-composition-and-bff": ["integration-patterns/scatter-gather-aggregation", "integration-patterns/circuit-breaker-and-bulkhead", "api-gateway/graphql-federation"],
    "integration-patterns/canonical-data-model": ["integration-patterns/iso-20022-transformation", "legacy-integration/anti-corruption-layer-core-banking", "integration-patterns/ibm-ace"],
    "integration-patterns/circuit-breaker-and-bulkhead": ["integration-patterns/scatter-gather-aggregation", "field-playbooks/timeouts-and-unknown-outcomes", "integration-patterns/idempotency-keys"],
    "integration-patterns/hold-and-release-payments": ["event-driven/obligation-ledger-pattern", "integration-patterns/idempotency-keys", "field-playbooks/timeouts-and-unknown-outcomes"],
    "integration-patterns/ibm-ace": ["integration-patterns/apache-camel-cloud-native", "integration-patterns/canonical-data-model", "devops/gitops-for-cloud-pak-for-integration"],
    "integration-patterns/idempotency-keys": ["data-sync/idempotent-consumer-exactly-once", "field-playbooks/timeouts-and-unknown-outcomes", "integration-patterns/hold-and-release-payments"],
    "integration-patterns/iso-20022-transformation": ["integration-patterns/canonical-data-model", "integration-patterns/apache-camel-cloud-native", "data-streaming/schema-registry-and-data-contracts"],
    "integration-patterns/scatter-gather-aggregation": ["integration-patterns/api-composition-and-bff", "integration-patterns/circuit-breaker-and-bulkhead", "api-security/open-banking-consent-management"],
    "legacy-integration/anti-corruption-layer-core-banking": ["legacy-integration/legacy-message-apis-and-simulators", "integration-patterns/canonical-data-model", "legacy-integration/soap-to-rest-modernisation"],
    "legacy-integration/legacy-message-apis-and-simulators": ["legacy-integration/anti-corruption-layer-core-banking", "field-playbooks/onboarding-consumers-in-days", "legacy-integration/soap-to-rest-modernisation"],
    "legacy-integration/soap-to-rest-modernisation": ["legacy-integration/anti-corruption-layer-core-banking", "api-gateway/ibm-api-connect", "legacy-integration/legacy-message-apis-and-simulators"],
}

# Insights companions (blog/<slug>.html). Most of these already link to the Lab article.
INSIGHTS = {
    "legacy-integration/anti-corruption-layer-core-banking": "anti-corruption-layer-decision",
    "integration-patterns/apache-camel-cloud-native": "apache-camel-enterprise-integration",
    "integration-patterns/api-composition-and-bff": "api-composition-decision",
    "api-security/api-waf-and-owasp": "api-waf-decision",
    "event-driven/asyncapi-kafka-contracts": "asyncapi-event-contracts-decision",
    "devops/gitops-for-cloud-pak-for-integration": "audit-ready-releases-decision",
    "devops/tekton-and-argocd": "audit-ready-releases-decision",
    "api-gateway/aws-api-gateway": "aws-api-gateway-regulated-workloads",
    "distributed-caching/cache-invalidation-via-cdc": "cache-invalidation-decision",
    "integration-patterns/canonical-data-model": "canonical-data-model-decision",
    "integration-patterns/circuit-breaker-and-bulkhead": "circuit-breaker-decision",
    "data-sync/conflict-resolution-multi-master": "conflict-resolution-decision",
    "legacy-integration/legacy-message-apis-and-simulators": "core-banking-as-a-product",
    "data-sync/cross-region-replication": "cross-region-data-replication-decision",
    "event-driven/dead-letter-queue-and-replay": "dead-letter-queue-decision",
    "distributed-caching/distributed-session-management": "distributed-session-decision",
    "data-sync/event-driven-data-mesh": "event-driven-data-mesh-decision",
    "event-driven/event-sourcing-and-cqrs": "event-sourcing-cqrs-payments-decision",
    "api-security/fapi-2-open-banking": "fapi-2-decision",
    "api-security/oauth-and-mtls": "fapi-2-decision",
    "data-streaming/flink-on-openshift-checkpointing": "flink-on-openshift-decision",
    "api-gateway/graphql-federation": "graphql-federation-decision",
    "distributed-caching/hazelcast-imdg-in-process-state": "hazelcast-in-process-caching-decision",
    "data-sync/idempotent-consumer-exactly-once": "idempotent-consumer-decision",
    "integration-patterns/idempotency-keys": "idempotent-consumer-decision",
    "field-playbooks/timeouts-and-unknown-outcomes": "idempotent-consumer-decision",
    "integration-patterns/iso-20022-transformation": "iso-20022-migration-decision",
    "event-driven/obligation-ledger-pattern": "live-code-is-the-spec",
    "devops/multi-cluster-gitops": "multi-cluster-gitops-decision",
    "distributed-caching/multi-tier-caching-strategies": "multi-tier-caching-decision",
    "distributed-caching/redis-cluster": "multi-tier-caching-decision",
    "distributed-caching/near-cache-and-read-replicas": "near-cache-read-replicas-decision",
    "devops/observability-pipeline-architecture": "observability-pipeline-decision",
    "api-security/fapi-2-conformance-testing": "open-banking-conformance-decision",
    "api-security/open-banking-consent-management": "open-banking-consent-architecture",
    "api-gateway/kong-and-envoy": "open-source-gateway-decision",
    "api-gateway/ibm-api-connect": "open-source-gateway-decision",
    "integration-patterns/hold-and-release-payments": "payment-rail-migration-decision",
    "devops/internal-developer-platform": "platform-idp-for-integration-leaders",
    "devops/progressive-delivery-flagger-argo-rollouts": "progressive-delivery-decision",
    "api-gateway/rate-limiting-and-throttling": "rate-limiting-decision",
    "data-streaming/real-time-fraud-detection": "real-time-fraud-detection-decision",
    "data-sync/reconciliation-pipelines-for-regulators": "reconciliation-pipelines-decision",
    "event-driven/saga-patterns-distributed-transactions": "saga-patterns-distributed-transactions-decision",
    "integration-patterns/scatter-gather-aggregation": "scatter-gather-decision",
    "data-streaming/schema-registry-and-data-contracts": "schema-registry-decision",
    "api-security/service-mesh-mtls-at-scale": "service-mesh-mtls-decision",
    "legacy-integration/soap-to-rest-modernisation": "soap-to-rest-decision",
    "data-streaming/stateful-stream-processing": "stateful-stream-processing-decision",
    "data-streaming/kafka-streams-and-flink": "stateful-stream-processing-decision",
    "data-streaming/ksqldb-and-flink-sql": "stream-analytics-data-decisions",
    "api-security/vault-pki-and-cert-manager": "vault-pki-cert-lifecycle-decision",
    "devops/vault-secrets-management": "vault-secrets-decision",
    "field-playbooks/first-30-minutes-of-an-incident": "platform-resilience-organizational-discipline",
}

# Official documentation per category index (well-known, stable URLs only)
FURTHER = {
    "api-gateway": [
        ("https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html", "Amazon API Gateway Developer Guide"),
        ("https://docs.konghq.com/", "Kong Gateway documentation"),
        ("https://www.envoyproxy.io/docs/envoy/latest/", "Envoy proxy documentation"),
        ("https://www.ibm.com/docs/en/api-connect", "IBM API Connect documentation"),
        ("https://www.apollographql.com/docs/federation/", "Apollo Federation documentation"),
        ("https://datatracker.ietf.org/doc/html/rfc6585", "RFC 6585 &mdash; HTTP 429 Too Many Requests"),
    ],
    "api-security": [
        ("https://datatracker.ietf.org/doc/html/rfc6749", "RFC 6749 &mdash; The OAuth 2.0 Authorization Framework"),
        ("https://datatracker.ietf.org/doc/html/rfc9700", "RFC 9700 &mdash; Best Current Practice for OAuth 2.0 Security"),
        ("https://openid.net/specs/fapi-2_0-security-profile.html", "OpenID Foundation &mdash; FAPI 2.0 Security Profile"),
        ("https://datatracker.ietf.org/doc/html/rfc8705", "RFC 8705 &mdash; OAuth 2.0 Mutual-TLS and Certificate-Bound Access Tokens"),
        ("https://datatracker.ietf.org/doc/html/rfc9449", "RFC 9449 &mdash; OAuth 2.0 Demonstrating Proof of Possession (DPoP)"),
        ("https://datatracker.ietf.org/doc/html/rfc9126", "RFC 9126 &mdash; OAuth 2.0 Pushed Authorization Requests"),
        ("https://owasp.org/API-Security/", "OWASP API Security Project (API Security Top 10)"),
        ("https://eur-lex.europa.eu/eli/reg_del/2018/389/oj", "Commission Delegated Regulation (EU) 2018/389 &mdash; PSD2 RTS on SCA and secure communication"),
        ("https://developer.hashicorp.com/vault/docs/secrets/pki", "HashiCorp Vault &mdash; PKI secrets engine"),
        ("https://istio.io/latest/docs/concepts/security/", "Istio &mdash; security concepts"),
    ],
    "data-streaming": [
        ("https://kafka.apache.org/documentation/", "Apache Kafka documentation"),
        ("https://kafka.apache.org/documentation/streams/", "Kafka Streams documentation"),
        ("https://nightlies.apache.org/flink/flink-docs-stable/", "Apache Flink documentation"),
        ("https://nightlies.apache.org/flink/flink-kubernetes-operator-docs-stable/", "Flink Kubernetes Operator documentation"),
        ("https://docs.ksqldb.io/", "ksqlDB documentation"),
        ("https://docs.confluent.io/platform/current/schema-registry/index.html", "Confluent Schema Registry documentation"),
        ("https://avro.apache.org/docs/", "Apache Avro specification and documentation"),
    ],
    "data-sync": [
        ("https://debezium.io/documentation/", "Debezium documentation"),
        ("https://kafka.apache.org/documentation/#georeplication", "Apache Kafka &mdash; geo-replication with MirrorMaker 2"),
        ("https://www.postgresql.org/docs/current/warm-standby.html", "PostgreSQL &mdash; log-shipping and streaming replication"),
        ("https://patroni.readthedocs.io/", "Patroni documentation"),
        ("https://www.ibm.com/docs/en/db2", "IBM Db2 documentation (HADR)"),
        ("https://www.cockroachlabs.com/docs/", "CockroachDB documentation"),
    ],
    "devops": [
        ("https://argo-cd.readthedocs.io/", "Argo CD documentation"),
        ("https://argoproj.github.io/argo-rollouts/", "Argo Rollouts documentation"),
        ("https://docs.flagger.app/", "Flagger documentation"),
        ("https://tekton.dev/docs/", "Tekton documentation"),
        ("https://backstage.io/docs/", "Backstage documentation"),
        ("https://opentelemetry.io/docs/collector/", "OpenTelemetry Collector documentation"),
        ("https://developer.hashicorp.com/vault/docs", "HashiCorp Vault documentation"),
        ("https://www.ibm.com/docs/en/app-connect", "IBM App Connect documentation"),
    ],
    "distributed-caching": [
        ("https://redis.io/docs/latest/", "Redis documentation"),
        ("https://docs.hazelcast.com/", "Hazelcast documentation"),
        ("https://github.com/ben-manes/caffeine/wiki", "Caffeine cache wiki"),
        ("https://docs.spring.io/spring-session/reference/", "Spring Session reference"),
        ("https://debezium.io/documentation/", "Debezium documentation"),
    ],
    "event-driven": [
        ("https://kafka.apache.org/documentation/", "Apache Kafka documentation"),
        ("https://www.ibm.com/docs/en/ibm-mq", "IBM MQ documentation"),
        ("https://strimzi.io/documentation/", "Strimzi documentation"),
        ("https://www.asyncapi.com/docs/reference/specification/v3.0.0", "AsyncAPI 3.0.0 specification"),
        ("https://docs.axoniq.io/", "Axon Framework documentation"),
        ("https://www.enterpriseintegrationpatterns.com/", "Enterprise Integration Patterns (Hohpe &amp; Woolf)"),
    ],
    "field-playbooks": [
        ("https://www.rfc-editor.org/rfc/rfc9110", "RFC 9110 &mdash; HTTP Semantics (status codes, Retry-After)"),
        ("https://datatracker.ietf.org/doc/html/rfc9457", "RFC 9457 &mdash; Problem Details for HTTP APIs"),
        ("https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/", "IETF draft &mdash; the Idempotency-Key HTTP header"),
        ("https://spec.openapis.org/oas/latest.html", "OpenAPI Specification"),
        ("https://opentelemetry.io/docs/", "OpenTelemetry documentation"),
        ("https://sre.google/sre-book/table-of-contents/", "Google &mdash; Site Reliability Engineering (incident response chapters)"),
    ],
    "integration-patterns": [
        ("https://www.ibm.com/docs/en/app-connect", "IBM App Connect Enterprise documentation"),
        ("https://camel.apache.org/docs/", "Apache Camel documentation"),
        ("https://resilience4j.readme.io/docs", "Resilience4j documentation"),
        ("https://www.iso20022.org/", "ISO 20022 &mdash; message definitions and catalogue"),
        ("https://www.swift.com/standards/iso-20022", "Swift &mdash; ISO 20022 programme and CBPR+"),
        ("https://www.enterpriseintegrationpatterns.com/", "Enterprise Integration Patterns (Hohpe &amp; Woolf)"),
    ],
    "legacy-integration": [
        ("https://www.ibm.com/docs/en/app-connect", "IBM App Connect Enterprise documentation"),
        ("https://www.ibm.com/docs/en/ibm-mq", "IBM MQ documentation"),
        ("https://daffodil.apache.org/", "Apache Daffodil (DFDL for fixed-length and binary formats)"),
        ("https://www.w3.org/TR/soap12/", "W3C &mdash; SOAP 1.2 specification"),
        ("https://spec.openapis.org/oas/latest.html", "OpenAPI Specification"),
        ("https://datatracker.ietf.org/doc/html/rfc9457", "RFC 9457 &mdash; Problem Details for HTTP APIs"),
    ],
}

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
SHORT = {m[:3]: i + 1 for i, m in enumerate(MONTHS)}


def long_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def parse_date(text):
    text = html.unescape(text).strip()
    m = re.match(r"([A-Z][a-z]{2})[a-z]* (\d{1,2}), (\d{4})", text)      # "Nov 14, 2026"
    if m:
        return date(int(m.group(3)), SHORT[m.group(1)], int(m.group(2))).isoformat()
    m = re.match(r"(\d{1,2}) ([A-Z][a-z]+) (\d{4})", text)               # "14 November 2026"
    if m:
        return date(int(m.group(3)), SHORT[m.group(2)[:3]], int(m.group(1))).isoformat()
    raise ValueError(f"unparsed date {text!r}")


def plain(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def h1_of(text):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- word count

def body_words(text):
    m = re.search(r'<article class="lab-article__body">(.*?)(?:<!-- lab-meta:end-matter -->|<nav class="article-nav")', text, re.S)
    body = m.group(1) if m else ""
    body = re.sub(r"<!-- lab-meta:start -->.*?<!-- lab-meta:end -->", " ", body, flags=re.S)
    body = re.sub(r"<svg.*?</svg>", " ", body, flags=re.S)
    body = re.sub(r'<div class="article-meta">.*?</div>', " ", body, flags=re.S)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’._/-]*", plain(body))
    lead = re.search(r'<p class="lead">(.*?)</p>', text, re.S)
    n = len(words) + (len(plain(lead.group(1)).split()) if lead else 0)
    return n


def minutes(words):
    return max(1, round(words / WPM))


# ---------------------------------------------------------------- articles

def article_info(path):
    text = read(path)
    key = path[len("lab/"):-len(".html")]
    cat = key.split("/")[0]
    cat_text = read(f"lab/{cat}.html")
    m = re.search(r'<strong>Published:</strong>\s*([^<]+)</span>', text) or \
        re.search(r'<time class="lab-byline__published" datetime="([0-9-]+)"', text)
    published = m.group(1) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", m.group(1).strip()) else parse_date(m.group(1))
    title = H1_FIX.get(key) or h1_of(text)
    return {
        "path": path, "key": key, "cat": cat, "cat_name": h1_of(cat_text),
        "title": title, "published": published,
        "updated": UPDATED.get(key),
        "modified": UPDATED.get(key) or REVISED.get(key) or published,
        "words": body_words(text),
    }


def byline_html(info):
    parts = ['<span>By <a href="../../about.html" rel="author">Waleed Albadawi</a></span>',
             f'<span>Published <time class="lab-byline__published" datetime="{info["published"]}">{long_date(info["published"])}</time></span>']
    if info["updated"]:
        parts.append(f'<span>Updated <time datetime="{info["updated"]}">{long_date(info["updated"])}</time></span>')
    parts.append(f'<span>{minutes(info["words"])} min read</span>')
    return ('<div class="lab-byline">\n            ' + '\n            '.join(parts) + '\n          </div>')


def end_matter(info, infos):
    rel_items = []
    for target in RELATED.get(info["key"], []):
        t = infos[target]
        href = os.path.relpath(f"lab/{target}.html", os.path.dirname(info["path"]))
        rel_items.append(
            f'<li><a class="lab-related__link" href="{href}"><span class="lab-related__kicker">Lab &middot; {t["cat_name"]}</span>'
            f'<span class="lab-related__name">{t["title"]}</span></a></li>')
    slug = INSIGHTS.get(info["key"])
    if slug and os.path.exists(os.path.join(ROOT, f"blog/{slug}.html")):
        btitle = h1_of(read(f"blog/{slug}.html"))
        btitle = re.sub(r"<[^>]+>", "", btitle)
        rel_items.append(
            f'<li><a class="lab-related__link lab-related__link--insights" href="../../blog/{slug}.html"><span class="lab-related__kicker">Insights &middot; the leadership decision</span>'
            f'<span class="lab-related__name">{btitle}</span></a></li>')
    items = "\n              ".join(rel_items)
    return f'''<!-- lab-meta:start -->
          <aside class="lab-author" aria-label="About the author">
            <p class="lab-author__label">About the author</p>
            <p class="lab-author__text">{AUTHOR_SENTENCE}</p>
            <p class="lab-author__more"><a href="../../about.html">More about Waleed &rarr;</a></p>
          </aside>

          <aside class="lab-related" aria-label="Related reading">
            <h2 class="lab-related__heading">Related reading</h2>
            <ul class="lab-related__list">
              {items}
            </ul>
          </aside>
          <!-- lab-meta:end -->
          '''


def jsonld_scripts(info, text):
    old = None
    for m in re.finditer(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', text, re.S):
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("@type") == "TechArticle":
            old = obj
    old = old or {}
    canonical = f'{SITE}/{info["path"]}'
    desc = old.get("description") or ""
    if not desc:
        m = re.search(r'<meta name="description" content="([^"]*)"', text)
        desc = m.group(1) if m else ""
    img = old.get("image")
    if not img:
        m = re.search(r'<meta property="og:image" content="([^"]*)"', text)
        img = m.group(1) if m else f"{SITE}/assets/img/og-image.png"
    art = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": plain(info["title"]),
        "description": html.unescape(desc),
        "image": img,
        "datePublished": info["published"],
        "dateModified": info["modified"],
        "author": PERSON,
        "publisher": PERSON,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "url": canonical,
        "inLanguage": "en",
        "wordCount": info["words"],
        "isPartOf": {"@type": "CollectionPage", "name": f'{plain(info["cat_name"])} — Technical Lab',
                     "url": f'{SITE}/lab/{info["cat"]}.html'},
        "proficiencyLevel": old.get("proficiencyLevel", "Expert"),
    }
    if old.get("audience"):
        art["audience"] = old["audience"]
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Technical Lab", "item": f"{SITE}/technical.html"},
            {"@type": "ListItem", "position": 3, "name": plain(info["cat_name"]), "item": f'{SITE}/lab/{info["cat"]}.html'},
            {"@type": "ListItem", "position": 4, "name": plain(info["title"]), "item": canonical},
        ],
    }

    def block(obj):
        body = json.dumps(obj, ensure_ascii=False, indent=2)
        body = "\n".join("  " + ln for ln in body.splitlines())
        return f'  <script type="application/ld+json">\n{body}\n  </script>'
    return block(art) + "\n" + block(crumbs)


def fix_headings(main):
    """Remove skipped heading levels: a heading is never more than one level below
    its parent (h2 followed by h4 becomes h2 > h3). Step-list titles are siblings,
    so they are first given one common level."""
    def unify(m):
        block = m.group(0)
        levels = [int(x) for x in re.findall(r"<li>\s*<h([1-6])", block)]
        if not levels:
            return block
        lvl = min(levels)
        return re.sub(r"(<li>\s*)<h[1-6]([^>]*)>(.*?)</h[1-6]>",
                      lambda mm: f"{mm.group(1)}<h{lvl}{mm.group(2)}>{mm.group(3)}</h{lvl}>", block, flags=re.S)
    main = re.sub(r'<ol class="step-list">.*?</ol>', unify, main, flags=re.S)

    out, pos, stack, open_levels = [], 0, [], []   # stack of (source level, new level)
    for m in re.finditer(r"<(/?)h([1-6])\b([^>]*)>", main):
        out.append(main[pos:m.start()])
        closing, lvl, attrs = m.group(1), int(m.group(2)), m.group(3)
        if not closing:
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            new = min(lvl, stack[-1][1] + 1) if stack else lvl
            stack.append((lvl, new))
            open_levels.append(new)
            out.append(f"<h{new}{attrs}>")
        else:
            out.append(f"</h{open_levels.pop() if open_levels else lvl}>")
        pos = m.end()
    out.append(main[pos:])
    return "".join(out)


def link_css(text, prefix):
    tag = f'<link rel="stylesheet" href="{prefix}assets/css/lab.css?v={CSS_VERSION}">'
    if "assets/css/lab.css" in text:
        return text
    return re.sub(r'(<link rel="stylesheet" href="[^"]*assets/css/style\.css[^"]*">)', r"\1\n  " + tag, text, count=1)


def process_article(info, infos):
    path = info["path"]
    text = orig = read(path)
    key = info["key"]

    # h1 fix
    if key in H1_FIX:
        text = re.sub(r"<h1>.*?</h1>", f"<h1>{H1_FIX[key]}</h1>", text, count=1, flags=re.S)

    # byline under the h1
    text = re.sub(r'\s*<div class="lab-byline">.*?</div>', "", text, flags=re.S)
    text = re.sub(r"(<h1>.*?</h1>)", lambda m: m.group(1) + "\n          " + byline_html(info), text, count=1, flags=re.S)

    # note under the lead
    text = re.sub(r'\s*<p class="lab-disclaimer">.*?</p>', "", text, flags=re.S)
    text = re.sub(r'(<p class="lead">.*?</p>)', lambda m: m.group(1) + f'\n          <p class="lab-disclaimer">{NOTE}</p>',
                  text, count=1, flags=re.S)

    # article-meta strip keeps stack/audience; date, time and author live in the byline
    def trim_meta(m):
        block = m.group(0)
        block = re.sub(r'\s*<span class="article-meta__item"><strong>(?:Read|Published|Updated|Author):</strong>.*?</span>(?=\s*(?:<span|</div>))',
                       "", block, flags=re.S)
        return block
    text = re.sub(r'<div class="article-meta">.*?</div>', trim_meta, text, count=1, flags=re.S)

    # end matter: author box + related reading, before the article navigation
    text = re.sub(r"<!-- lab-meta:start -->.*?<!-- lab-meta:end -->\s*", "", text, flags=re.S)
    text = text.replace('<nav class="article-nav">', end_matter(info, infos) + '<nav class="article-nav">', 1)

    # headings without skipped levels (inside <main> only)
    i, j = text.find("<main"), text.find("</main>")
    text = text[:i] + fix_headings(text[i:j]) + text[j:]

    # JSON-LD: replace TechArticle/BreadcrumbList blocks
    def drop(m):
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            return m.group(0)
        return "" if isinstance(obj, dict) and obj.get("@type") in ("TechArticle", "BreadcrumbList") else m.group(0)
    scripts = jsonld_scripts(info, text)
    text = re.sub(r'\s*<script type="application/ld\+json">\s*(.*?)\s*</script>', drop, text, flags=re.S)
    text = text.replace("</head>", scripts + "\n</head>", 1)

    text = link_css(text, "../../")
    return text, orig


def process_category(cat, infos):
    path = f"lab/{cat}.html"
    text = orig = read(path)

    def refresh(m):
        item = m.group(0)
        href = re.search(r'href="([^"]+)"', item).group(1)
        key = f"{cat}/{href.split('/')[-1][:-5]}" if "/" in href else None
        info = infos.get(key)
        if not info:
            return item
        item = re.sub(r'(<span class="article-list__date-pub">)[^<]*(</span>)',
                      lambda mm: mm.group(1) + long_date(info["published"]) + mm.group(2), item)
        item = re.sub(r"<span>~?\d+ min read</span>", f'<span>{minutes(info["words"])} min read</span>', item)
        if key in H1_FIX:
            pass
        return item
    text = re.sub(r'<a href="[^"]+" class="article-list__item">.*?</a>', refresh, text, flags=re.S)

    links = "\n".join(
        f'            <li><a href="{u}">{label}</a></li>' for u, label in FURTHER.get(cat, []))
    section = f'''<!-- lab-meta:further -->
  <section class="lab-further" aria-labelledby="further-reading">
    <div class="container container--narrow">
      <h2 id="further-reading">Further reading</h2>
      <p class="lab-further__intro">Official documentation and specifications behind the articles above. The articles are reference architectures with illustrative code; these sources are authoritative.</p>
      <ul class="lab-further__list">
{links}
      </ul>
    </div>
  </section>
  <!-- /lab-meta:further -->'''
    text = re.sub(r"\s*<!-- lab-meta:further -->.*?<!-- /lab-meta:further -->", "", text, flags=re.S)
    text = re.sub(r"\s*</main>", lambda m: "\n\n  " + section + "\n\n  </main>", text, count=1)
    text = link_css(text, "../")
    return text, orig


def main():
    check = "--check" in sys.argv
    os.chdir(ROOT)
    paths = sorted(glob.glob("lab/*/*.html"))
    infos = {}
    for p in paths:
        info = article_info(p)
        infos[info["key"]] = info
    missing = [k for k in infos if k not in RELATED]
    if missing:
        print("no RELATED entry:", ", ".join(missing))
    changed = 0
    for info in infos.values():
        new, old = process_article(info, infos)
        if new != old:
            changed += 1
            if not check:
                open(info["path"], "w", encoding="utf-8").write(new)
    for cat in sorted({i["cat"] for i in infos.values()}):
        new, old = process_category(cat, infos)
        if new != old:
            changed += 1
            if not check:
                open(f"lab/{cat}.html", "w", encoding="utf-8").write(new)
    print(("would update" if check else "updated"), changed, "files")


if __name__ == "__main__":
    main()
