# Domain Model Notes

- `read/utils/model_mixins.py` now only exposes mixins used in production
  models. Unreferenced base classes (`BaseUserModel`, `BaseContentModel`,
  `BaseLogModel`, `MetricsMixin`, manager helpers) were removed to reduce noise.
- `BaseNamedContentModel` remains the single abstraction for classroom/reading
  group entities, consolidating school, naming, creator, and activity flags.
- Reading log models rely on per-model validation rather than inherited
  base-class behavior; imports were updated accordingly.

Future cleanups:

- Consider splitting mixins into a `read/core/models.py` package alongside shared
  validators and constraints.
- Evaluate soft-delete usage; if not required, migrate to hard deletes to save a
  field on `CustomUser`.

