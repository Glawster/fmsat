# ADR-001: Package the logging runtime with FMSAT

## Status

Accepted

## Context

FMSAT uses the semantic logging interface maintained by organiseMyProjects. During the
OMP v0.5 compliance work, application imports were changed from
`fmsat.core.logUtils` to `organiseMyProjects.logUtils` and the latter was added as an
application dependency.

That change conflicts with the deployment boundary. FMSAT must contain every runtime
module needed by its packaging and deployment engine; organiseMyProjects is a project
governance and development tool, not an FMSAT runtime dependency. The existing
`core/logUtils.py` identifies itself as a local deployment copy whose canonical source is
`Glawster/organiseMyProjects`.

OMP v0.5's shared-runtime guidance also says consuming projects must not introduce a
runtime dependency on organiseMyProjects. Its logging examples currently show direct
imports from that package, so the installed guidance is internally inconsistent on this
point.

## Decision Drivers

- Deployed FMSAT builds must be self-contained.
- Application startup and logging must not depend on a project-management package being
  installed in the target environment.
- Logging behaviour should remain aligned with the canonical organiseMyProjects
  implementation.
- Runtime imports must resolve from packages included by FMSAT's build configuration.

## Considered Options

1. Depend on and import `organiseMyProjects.logUtils` at runtime.
2. Package a synchronized logging module under `fmsat.core` and import it locally.
3. Add an `omp` runtime package immediately and migrate the existing local module into it.

## Decision Outcome

Use option 2. FMSAT imports logging from `fmsat.core.logUtils`, and
`organiseMyProjects` is not an application runtime dependency. The local module remains a
synchronized deployment copy of the canonical implementation.

An `omp` package migration may be considered separately if the OMP distribution process
provides an explicit synchronization and packaging mechanism. It is not required merely
to rename a working deployment boundary.

### Consequences

- Positive: packaged and deployed FMSAT installations remain self-contained.
- Positive: logging is available anywhere the `fmsat.core` package is available.
- Positive: organiseMyProjects can be upgraded or absent without changing the deployed
  application's dependency graph.
- Negative: canonical logging improvements must be synchronized deliberately into the
  local copy.
- Negative: agents must follow this ADR where the generic OMP logging example conflicts
  with the shared-runtime and deployment rules.

Synchronization is verified during OMP updates by comparing `core/logUtils.py` with the
installed `organiseMyProjects.logUtils` source. The files should remain identical; any
intentional divergence requires a superseding ADR.
