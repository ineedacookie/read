/*!
 * Reading Logs App - Minimal Theme JS
 * Optimized from 365KB bloated theme.js to essential functionality only
 * Senior Developer Optimized - Production Ready
 */

"use strict";

/* -------------------------------------------------------------------------- */
/*                                Core Utils                                  */
/* -------------------------------------------------------------------------- */

const docReady = (fn) => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn);
  } else {
    setTimeout(fn, 1);
  }
};

const getData = (el, data) => {
  try {
    return JSON.parse(el.dataset[camelize(data)]);
  } catch (e) {
    return el.dataset[camelize(data)];
  }
};

const camelize = (str) => {
  const text = str.replace(/[-_\s.]+(.)?/g, (_, c) => c ? c.toUpperCase() : '');
  return `${text.substr(0, 1).toLowerCase()}${text.substr(1)}`;
};

/* -------------------------------------------------------------------------- */
/*                             Color Functions                                */
/* -------------------------------------------------------------------------- */

const getColor = (name, dom = document.documentElement) => {
  return getComputedStyle(dom).getPropertyValue(`--falcon-${name}`).trim();
};

const hexToRgb = (hexValue) => {
  let hex = hexValue.indexOf('#') === 0 ? hexValue.substring(1) : hexValue;
  const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(
    hex.replace(shorthandRegex, (m, r, g, b) => r + r + g + g + b + b)
  );
  return result ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)] : null;
};

const rgbaColor = (color = '#fff', alpha = 0.5) => {
  return `rgba(${hexToRgb(color)}, ${alpha})`;
};

/* -------------------------------------------------------------------------- */
/*                            Essential UI Components                         */
/* -------------------------------------------------------------------------- */

// Tooltip initialization (minimal)
const tooltipInit = () => {
  const tooltipList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
};

// Popover initialization (minimal)
const popoverInit = () => {
  const popoverList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverList.map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
};

// Choices.js initialization for select elements
const choicesInit = () => {
  if (typeof Choices === 'undefined') {
    console.warn('Choices.js library not loaded - skipping dropdown enhancements');
    return;
  }
  
  const elements = document.querySelectorAll('.js-choice');
  elements.forEach(element => {
    try {
      const userOptions = getData(element, 'options');
      const choices = new Choices(element, {
        itemSelectText: '',
        ...userOptions
      });
    } catch (error) {
      console.warn('Failed to initialize Choices for element:', element, error);
    }
  });
};

// Flatpickr (date picker) initialization
const flatpickrInit = () => {
  if (typeof flatpickr === 'undefined') {
    console.warn('Flatpickr library not loaded - skipping date picker enhancements');
    return;
  }
  
  const elements = document.querySelectorAll('.datetimepicker');
  elements.forEach(element => {
    try {
      const userOptions = getData(element, 'options');
      flatpickr(element, {
        nextArrow: '<svg width="14" height="11" viewBox="0 0 14 11"><path d="m1 6 4 4 4-4"/></svg>',
        prevArrow: '<svg width="14" height="11" viewBox="0 0 14 11"><path d="m9 1-4 4 4 4"/></svg>',
        ...userOptions
      });
    } catch (error) {
      console.warn('Failed to initialize Flatpickr for element:', element, error);
    }
  });
};

// ECharts responsive handling
const echartResponsiveInit = () => {
  const elements = document.querySelectorAll('[data-echart-responsive="true"]');
  
  const resizeHandler = () => {
    elements.forEach(element => {
      const chart = window.echarts?.getInstanceByDom(element);
      if (chart) {
        chart.resize();
      }
    });
  };

  window.addEventListener('resize', resizeHandler);
  
  // Initial resize after a short delay
  setTimeout(resizeHandler, 100);
};

// Progress bar animation
const progressAnimationToggle = () => {
  const elements = document.querySelectorAll('[data-progress-animation]');
  elements.forEach(element => {
    const progress = element.querySelector('.progress-bar');
    if (progress) {
      const width = progress.style.width;
      progress.style.width = '0%';
      setTimeout(() => {
        progress.style.width = width;
      }, 300);
    }
  });
};

// Navbar vertical collapsed handler
const handleNavbarVerticalCollapsed = () => {
  const navbarVertical = document.querySelector('.navbar-vertical');
  if (navbarVertical) {
    const navbarVerticalCollapse = navbarVertical.querySelector('.navbar-collapse');
    if (navbarVerticalCollapse) {
      navbarVerticalCollapse.addEventListener('show.bs.collapse', () => {
        navbarVertical.classList.add('navbar-vertical-collapsed-show');
      });
      navbarVerticalCollapse.addEventListener('hidden.bs.collapse', () => {
        navbarVertical.classList.remove('navbar-vertical-collapsed-show');
      });
    }
  }
};

// Dark mode detector and handler
const detectorInit = () => {
  const detector = document.querySelector('.theme-control-toggle');
  if (detector) {
    detector.addEventListener('click', (e) => {
      const input = e.currentTarget.querySelector('input');
      if (input.checked) {
        document.documentElement.classList.add('dark');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('theme', 'light');
      }
    });
  }

  // Set initial theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark');
    const toggle = document.querySelector('.theme-control-toggle input');
    if (toggle) toggle.checked = true;
  }
};

// Navbar top drop shadow
const navbarTopDropShadow = () => {
  const navbarTop = document.querySelector('.navbar-top');
  if (navbarTop) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 0) {
        navbarTop.classList.add('navbar-top-shadow');
      } else {
        navbarTop.classList.remove('navbar-top-shadow');
      }
    });
  }
};

/* -------------------------------------------------------------------------- */
/*                            Reading Logs Specific                          */
/* -------------------------------------------------------------------------- */

// Enhanced table functionality for reading logs
const tableEnhancements = () => {
  // Auto-refresh functionality
  const autoRefreshToggle = document.querySelector('[data-auto-refresh]');
  if (autoRefreshToggle) {
    let refreshInterval;
    
    autoRefreshToggle.addEventListener('change', function() {
      if (this.checked) {
        refreshInterval = setInterval(() => {
          location.reload();
        }, 30000); // 30 seconds
      } else {
        clearInterval(refreshInterval);
      }
    });
  }

  // Enhanced row highlighting
  const tableRows = document.querySelectorAll('tbody tr[data-log-id]');
  tableRows.forEach(row => {
    row.addEventListener('mouseenter', function() {
      this.classList.add('table-row-highlight');
    });
    row.addEventListener('mouseleave', function() {
      this.classList.remove('table-row-highlight');
    });
  });
};

// Form validation enhancements
const formValidationInit = () => {
  const forms = document.querySelectorAll('.needs-validation');
  forms.forEach(form => {
    form.addEventListener('submit', function(event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });
};

// Reading progress animations
const progressCardAnimations = () => {
  const cards = document.querySelectorAll('.progress-card');
  
  // Intersection Observer for scroll animations
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate-in');
      }
    });
  }, { threshold: 0.1 });

  cards.forEach(card => observer.observe(card));
};

/* -------------------------------------------------------------------------- */
/*                           Minimal Error Handling                          */
/* -------------------------------------------------------------------------- */

// Global error handler for better UX
window.addEventListener('error', (e) => {
  console.error('Theme Error:', e.error);
  // Don't show errors to users unless in development
  if (window.location.hostname === 'localhost') {
    console.warn('Theme.js Error:', e.filename, e.lineno, e.error);
  }
});

/* -------------------------------------------------------------------------- */
/*                            Theme Initialization                           */
/* -------------------------------------------------------------------------- */

// Initialize core features
docReady(() => {
  detectorInit();
  handleNavbarVerticalCollapsed();
  navbarTopDropShadow();
  tooltipInit();
  popoverInit();
  choicesInit();
  flatpickrInit();
  echartResponsiveInit();
  progressAnimationToggle();
  tableEnhancements();
  formValidationInit();
  progressCardAnimations();
});

// Performance monitoring
if (window.performance && window.performance.mark) {
  window.performance.mark('theme-minimal-loaded');
}

/* -------------------------------------------------------------------------- */
/*                              Export for modules                           */
/* -------------------------------------------------------------------------- */

// Make utilities available globally for backward compatibility
window.Reading = {
  docReady,
  getData,
  getColor,
  hexToRgb,
  rgbaColor,
  tooltipInit,
  popoverInit,
  choicesInit,
  flatpickrInit
};

console.log('📚 Reading Logs Theme Minimal loaded successfully!');
