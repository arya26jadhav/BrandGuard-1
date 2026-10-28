# Known Issues and Limits (Member 3)

## 1. Alerts only cover checked posts
Fact alerts reach a post only if a check run has linked it to the fact. A published post that was never checked gets no alert.
Planned fix after the demo: scan published posts for the fact's text.

## 2. Logo matching uses perceptual hashing (pHash)
pHash detects similar overall shape, not exact design. It cannot reliably catch distorted, rotated, cropped, or recoloured logos.
Planned upgrade: OpenCLIP visual similarity.

## 3. Text checks are not in the image validator
Unsupported-claim and missing-disclaimer checks are not implemented in `image_validator.py`. They belong to the rules engine.

## 4. Logo self-comparison proves only that the function runs
The approved logo compared with itself returns distance 0. This shows the code path works, not that variants are detected.

## 5. Integration test needs a reachable database
`test_integration_alerts_against_db` skips when pytest cannot connect to Postgres. Run it on a machine with the database reachable before the demo.

## 6. Development database security
The local Postgres `pg_hba.conf` contains `host all all 0.0.0.0/0 trust`, which allows login without a password from any host. Restore `scram-sha-256` or remove the line before any demo or deployment.

## 7. Starlette test warning
`TestClient` shows a DeprecationWarning about `anyio.abc.BlockingPortal`. It comes from upstream and is harmless.