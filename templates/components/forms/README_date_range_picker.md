# Date Range Picker Component

A reusable date range picker component with navigation controls and customizable callbacks.

## Usage

### Basic Usage
```django
{% include "components/forms/date_range_picker.html" with id="my_range_picker" %}
```

### Advanced Usage
```django
{% include "components/forms/date_range_picker.html" with 
    id="dashboard_range" 
    label="📅 Time Period" 
    placeholder="Select date range..." 
    container_class="col-md-6"
    show_navigation=True
    callback_function="loadDashboardData"
    initial_range="Dec 15, 2024 to Dec 21, 2024"
%}
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | string | **required** | Unique identifier for the input field |
| `label` | string | "📅 Date Range" | Display label for the component |
| `placeholder` | string | "Select date range..." | Placeholder text for input |
| `container_class` | string | "col-md-6" | CSS class for container div |
| `show_navigation` | boolean | True | Whether to show prev/next buttons |
| `callback_function` | string | null | JavaScript function name to call on change |
| `initial_range` | string | null | Initial date range value (auto-sets to current week if not provided) |

## JavaScript API

The component provides several JavaScript functions for interaction:

### Core Functions
- `initializeDateRangePicker(id, options)` - Initialize a picker instance
- `getDateRangeValue(id)` - Get current value
- `setDateRangeValue(id, value)` - Set value programmatically
- `adjustDateRange(id, days)` - Adjust by number of days

### Utility Functions
- `getCurrentWeekRange()` - Get current week range string
- `getWeekRange(date)` - Get week range for specific date
- `parseDateRange(dateString)` - Parse range string to dates

## Migration Example

### Before (inline code):
```html
<div class="col-md-6">
    <label class="form-label fw-bold mb-2">📅 Time Period</label>
    <div class="d-flex align-items-center gap-2">
        <button class="btn btn-outline-secondary btn-sm" id="prev-week">
            <i class="fas fa-chevron-left"></i>
        </button>
        <input class="form-control datetimepicker" id="dashboard_range" type="text" 
               placeholder="Select date range..."
               data-options='{"mode":"range","dateFormat":"M j, Y","disableMobile":true,"position":"below","predefinedRanges":["this_week", "last_week", "this_month", "last_month"]}'/>
        <button class="btn btn-outline-secondary btn-sm" id="next-week">
            <i class="fas fa-chevron-right"></i>
        </button>
    </div>
</div>
```

### After (component):
```django
{% include "components/forms/date_range_picker.html" with 
    id="dashboard_range" 
    label="📅 Time Period" 
    callback_function="loadDashboardData"
%}
```

## Features

- ✅ **Responsive Design** - Works on all screen sizes
- ✅ **Navigation Controls** - Previous/Next buttons with week navigation
- ✅ **Customizable Callbacks** - Trigger functions on value change
- ✅ **Auto-initialization** - Sets to current week by default
- ✅ **Flatpickr Integration** - Uses existing flatpickr styling and functionality
- ✅ **Multiple Instances** - Support multiple pickers on same page
- ✅ **Predefined Ranges** - This week, last week, this month, last month options

## CSS Classes

The component uses these CSS classes for styling:
- `form-label fw-bold mb-2` - Label styling
- `d-flex align-items-center gap-2` - Navigation container
- `btn btn-outline-secondary btn-sm` - Navigation buttons
- `form-control datetimepicker` - Input field
- `fas fa-chevron-left/right` - Icons

## Dependencies

- Bootstrap 5+ (for styling)
- FontAwesome (for icons)
- Flatpickr (for date picker functionality)
- jQuery (for event handling)
