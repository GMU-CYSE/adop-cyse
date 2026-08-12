# Contributing

1. Open an issue before starting non-trivial work.
2. Keep patches scoped to one service.
3. All commits must pass SAST/DAST/SCA gates in the golden-path CI/CD
   pipeline before merge (see the project's platform documentation).
4. Do not commit secrets. Use `.env.example` as the template for local
   configuration; real values live in the secrets manager.
