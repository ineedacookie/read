# Application & Authentication Overview

## Django Apps

- `users`: Handles authentication, registration, and user management. Relies on the
  custom user model for role-based permissions and school scoping.
- `reading_logs`: Owns core product behavior—logging activity, analytics,
  gamification, and related APIs.
- `read`: Project package that now focuses on core configuration (`settings`,
  `urls`) and shared helpers (to be further consolidated in later steps).

Grouping apps into `DJANGO_APPS`, `THIRD_PARTY_APPS`, and `LOCAL_APPS` in
`read/settings.py` clarifies ownership and makes it easier to spot redundant or
missing registrations.

## Custom User Model

`users.models.CustomUser` remains a requirement because it:

- Enforces role types (`teacher`, `student`, `parent`, `administrator`) used
  across permission checks and templates.
- Uses email as the login identifier.
- Tracks school membership and soft-deletion flags that underpin data isolation.

Authentication backends remain Django’s defaults—sufficient given the custom
model. Any future refactor should focus on trimming unused mixins and ensuring
school assignment is explicit (no automatic creation in `save()`).

## Next Steps

- Relocate shared helpers into a dedicated `read/core/` package and deprecate the
  existing `read/utils` namespace.
- Tighten the custom user lifecycle (e.g., validation preventing automatic
  school creation).
- Standardize permission checks across views using mixins or DRF viewsets.
- Continue trimming unused mixins and helper classes so only actively used
  abstractions remain in `read/utils/model_mixins.py`.


