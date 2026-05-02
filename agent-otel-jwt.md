# Agent JWT Monitoring Pattern

This document describes the JWT-authenticated monitoring pattern for Elasticsearch when using Elastic Agent as the EDOT runtime and an EDOT gateway as the forwarder to the monitoring cluster.

## What Is Supported

Elastic Agent 9.2+ embeds the EDOT Collector runtime and can collect Elasticsearch monitoring data through the Elasticsearch integration. The supported collection path for Elasticsearch monitoring remains:

1. Elastic Agent runs on or near the Elasticsearch source cluster.
2. The `elasticsearch/metrics` integration collects Stack Monitoring data.
3. The `filestream` input collects Elasticsearch server logs.
4. The Agent forwards data to the EDOT gateway or directly to Elasticsearch, depending on the mode.
5. The EDOT gateway writes to the monitoring Elasticsearch cluster.

Relevant Elastic docs:

- [Elastic Agent as an OpenTelemetry Collector](https://www.elastic.co/docs/reference/fleet/elastic-agent-as-otel-collector)
- [Collecting monitoring data with Elastic Agent](https://www.elastic.co/guide/en/elasticsearch/reference/current/configuring-elastic-agent.html)
- [Configuring monitoring data streams created by Elastic Agent](https://www.elastic.co/guide/en/elasticsearch/reference/current/config-monitoring-data-streams-elastic-agent.html)

## JWT Reality Check

Elasticsearch can trust JWT bearer tokens through a JWT realm.

The important constraint is that the current Elastic Agent Elasticsearch output and Elasticsearch monitoring integration do not expose JWT as a first-class source-cluster authentication method. Elastic Agent output authentication is documented for:

- basic auth
- API key auth
- PKI certificates
- Kerberos

That means JWT is not the direct auth method inside the stock `elasticsearch/metrics` input path in this repo.

There is a second constraint in this lab: the JWT realm itself is not enabled on the current basic license. When the overlay is applied on a basic-license cluster, Elasticsearch starts but auto-disables the JWT realm and rejects JWT requests. To validate this flow end to end you need a trial or commercial license that permits JWT realms.

Relevant docs:

- [JWT authentication in Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/jwt-auth-realm.html)
- [Elastic Agent Elasticsearch output authentication](https://www.elastic.co/docs/reference/fleet/elasticsearch-output)
- [EDOT Collector authentication methods](https://www.elastic.co/docs/reference/edot-collector/config/authentication-methods)

## Recommended JWT Flow

Use JWT as the authentication boundary at the source cluster, then terminate or exchange the token before the collector talks to Elasticsearch.

Recommended flow:

1. A client or auth proxy obtains a JWT from your identity provider.
2. Elasticsearch trusts that JWT through a configured JWT realm.
3. A small auth shim or proxy exchanges or validates the JWT and calls Elasticsearch on behalf of the monitoring integration.
4. Elastic Agent still performs the Elasticsearch metrics collection using its supported Elasticsearch integration settings.
5. Elastic Agent exports to the EDOT gateway.
6. The gateway writes to the monitoring cluster.

This keeps JWT as the identity layer while preserving the Elastic-supported monitoring transport path.

## Example Kubernetes Shape

The JWT path is best treated as a separate configuration overlay rather than a new default mode.

This repo now includes a temporary test harness for that overlay:

```bash
make jwt-test-up
make jwt-test
make jwt-test-down
```

Those commands:

- apply a JWT realm overlay to `elasticsearch-main`
- create the matching role and role mapping for a signed test principal
- mint and validate a JWT against the source cluster
- remove the JWT-specific resources again during cleanup

The scripts intentionally fail fast if the source cluster reports a basic license, because the JWT realm is automatically disabled there.

Source cluster JWT realm example:

```yaml
xpack.security.authc.realms.jwt.jwt1:
  order: 3
  token_type: access_token
  client_authentication.type: shared_secret
  allowed_issuer: "https://idp.example.com/jwt/"
  allowed_audiences: ["es-monitoring"]
  allowed_signature_algorithms: [RS256]
  pkc_jwkset_path: jwt/jwkset.json
  claims.principal: sub
```

Agent collection example:

```yaml
inputs:
  - id: elasticsearch-stack-monitoring
    type: elasticsearch/metrics
    use_output: default
    data_stream.namespace: main
    streams:
      - metricsets: ["cluster_stats"]
        data_stream.dataset: elasticsearch.stack_monitoring.cluster_stats
        period: 60s
        hosts: ["${MAIN_ELASTICSEARCH_URL}"]
        ssl.certificate_authorities: ["/etc/elastic-agent/certs/ca.crt"]
```

Gateway export example:

```yaml
exporters:
  elasticsearch/monitoring:
    endpoint: ${env:MONITORING_ELASTICSEARCH_URL}
    api_key: ${env:MONITORING_ELASTICSEARCH_API_KEY}
    mapping:
      mode: otel
```

For Kubernetes, keep the API key in a Secret and mount it as an environment variable or file. Do not hardcode it in the manifest.

The live test harness in this repo uses a JWT realm overlay on the source cluster, but the supported Agent collection path still uses the Elastic Agent integration and ships onward using the configured Elasticsearch output or EDOT gateway transport.

## Scaling Guidance

These recommendations are based on how Elasticsearch collectors behave and on Elastic's monitoring guidance. They are practical defaults, not a hard requirement.

- Use `scope: cluster` unless you explicitly need per-node collection.
- Keep one Agent per source cluster for normal deployments.
- Use separate `data_stream.namespace` values when you monitor multiple clusters so the streams do not collide.
- Prefer a 60s interval for `cluster_stats`.
- Use 30s to 60s for `node_stats` and `index` on medium clusters.
- Use 60s for `shard` and `index_recovery` when shard counts are high.
- Keep 10s intervals for small labs or short troubleshooting sessions only.
- If you switch to `scope: node`, remember that every Elasticsearch node needs an Agent and the elected master does more work.

Elastic docs note that the collection work is serialized and that collector failures can show up when the elected master is overloaded or the cluster has many indices or shards. That is the main reason to slow the interval down as the cluster grows.

Relevant docs:

- [Collectors](https://www.elastic.co/guide/en/elasticsearch/reference/current/es-monitoring-collectors.html/)
- [Collecting monitoring data with Elastic Agent](https://www.elastic.co/guide/en/elasticsearch/reference/current/configuring-elastic-agent.html)
- [Scale Elastic Agent on Kubernetes](https://www.elastic.co/guide/en/fleet/current/scaling-on-kubernetes.html)

## Source Cluster Load

The highest-cost collectors are the ones that fan out across indices or shards:

- `cluster_stats` is generally the lightest.
- `node_stats` adds JVM, GC, file descriptors, and thread-pool detail.
- `index` and `shard` scale with cluster cardinality.
- `index_recovery` is useful but should stay at a lower rate unless you are actively troubleshooting recovery.

Best-practice starting point:

- `cluster_stats`: `60s`
- `node_stats`: `30s` or `60s`
- `index`: `60s`
- `shard`: `60s`
- `index_recovery`: `60s`

If the cluster is small, you can tighten these to `10s` for lab work. If the cluster is large, move them up before you scale out another collector.

## Multiple Elasticsearch Sources

This repo does not implement multi-source fan-in, but the operating model is straightforward:

- one Agent policy per source cluster, or
- one Agent deployment per source cluster, or
- one input block per source cluster with a distinct namespace

Keep the namespaces separate and avoid sharing the same stream names across clusters. That keeps dashboards simple and prevents collisions in the monitoring cluster.

## Summary

JWT is a valid Elasticsearch authentication mechanism.

In this repo, the supported place to use it is at the source-cluster boundary, before the Agent's Elasticsearch monitoring integration reaches Elasticsearch. The Agent still ships data to the EDOT gateway and the monitoring cluster using the supported Elastic transport path.
