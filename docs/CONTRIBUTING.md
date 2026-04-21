# Contributing

## i18n Policy

KiU v0.3 uses a simple language split:

- spec and API-facing docs: English canonical
- user guides and operational docs: bilingual or Chinese-first is acceptable when no English pair exists yet
- bundle content: controlled by each bundle's `manifest.language`

For new docs:

- add new normative specs in English first
- keep CLI examples portable (`python3`, not machine-local absolute paths)
- when a user-facing guide is expanded materially, prefer keeping an English canonical version and adding Chinese explanatory guidance where needed

## Validation Before Change

Before submitting changes, run:

```bash
python3 -m unittest tests/test_profile_resolver.py
python3 -m unittest tests/test_validator.py
python3 -m unittest tests/test_pipeline.py
python3 -m unittest tests/test_refiner.py
python3 scripts/validate_bundle.py bundles/poor-charlies-almanack-v0.1
```
