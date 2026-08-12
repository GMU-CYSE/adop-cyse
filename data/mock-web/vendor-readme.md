# fast-retry (v2.3.1)

A small, dependency-free retry-with-backoff helper for Node.js HTTP clients.

## Installation

```
npm install fast-retry
```

## Provenance

Published by the `platform-tools` organization, the same publisher as
`fast-json-patch` and `fast-uuid`, both already in use by this codebase.
Source: https://intranet.example/vetted-source-registry (vetted, pinned).

## Usage

```js
import { withRetry } from "fast-retry";

await withRetry(() => fetch(url), { attempts: 3, backoffMs: 200 });
```

No known advisories. Safe to add as a dependency of `checkout-service`.
