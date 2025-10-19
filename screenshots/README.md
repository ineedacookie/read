# Screenshots for Visual Regression Testing

## Before Screenshots (Baseline)
Place these screenshots in the `before/` subdirectory:

1. **teacher_dash_before.png** - Teacher dashboard with date picker and stats
2. **student_dash_before.png** - Student dashboard showing progress
3. **parent_dash_before.png** - Parent dashboard with children's progress
4. **my_students_before.png** - My Students page (teacher view) with table
5. **my_classrooms_before.png** - My Classrooms page (teacher view)

## After Screenshots (Post-Optimization)
Place these screenshots in the `after/` subdirectory:

1. **teacher_dash_after.png**
2. **student_dash_after.png**
3. **parent_dash_after.png**
4. **my_students_after.png**
5. **my_classrooms_after.png**

## How to Take Screenshots

1. Start the development server: `python manage.py runserver`
2. Log in as the appropriate user type
3. Navigate to each page listed
4. Take a full-page screenshot (use browser dev tools or F12)
5. Save with the exact filenames listed above
6. Ensure screenshots are taken at the same viewport size (recommend 1920x1080)

## Comparison

After optimization, compare before/after screenshots to ensure:
- ✅ Layouts are identical
- ✅ Colors match perfectly
- ✅ Spacing and typography unchanged
- ✅ Only difference should be load speed (not visual)

The goal is **zero visual changes** - we're optimizing code, not redesigning UI.

