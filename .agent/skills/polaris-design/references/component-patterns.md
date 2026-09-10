# Polaris Component Patterns

Common component patterns following Shopify Polaris design principles.

## Cards

### Basic Card
```css
.polaris-card {
  background: var(--p-color-bg-surface);
  border-radius: var(--p-border-radius-200);
  padding: var(--p-space-400);
  box-shadow: var(--p-shadow-200);
}

.polaris-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--p-space-400);
}

.polaris-card__title {
  font-size: var(--p-font-size-300);
  font-weight: var(--p-font-weight-semibold);
  color: var(--p-color-text);
}

.polaris-card__section {
  padding: var(--p-space-400) 0;
  border-top: var(--p-border-width-1) solid var(--p-color-border);
}
```

## Buttons

### Button Variants
```css
.polaris-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--p-space-100);
  font-family: var(--p-font-family-sans);
  font-size: var(--p-font-size-200);
  font-weight: var(--p-font-weight-medium);
  line-height: 1;
  padding: var(--p-space-200) var(--p-space-400);
  border: none;
  border-radius: var(--p-border-radius-100);
  cursor: pointer;
  transition: background var(--p-motion-duration-150) var(--p-motion-ease);
}

/* Primary */
.polaris-button--primary {
  background: var(--p-color-bg-fill-brand);
  color: #ffffff;
}
.polaris-button--primary:hover {
  background: #006e52;
}

/* Secondary */
.polaris-button--secondary {
  background: var(--p-color-bg-surface);
  color: var(--p-color-text);
  border: var(--p-border-width-1) solid var(--p-color-border);
}
.polaris-button--secondary:hover {
  background: var(--p-color-bg-surface-hover);
}

/* Critical */
.polaris-button--critical {
  background: var(--p-color-bg-fill-critical);
  color: #ffffff;
}

/* Plain (link-style) */
.polaris-button--plain {
  background: transparent;
  color: var(--p-color-text-brand);
  padding: 0;
}
.polaris-button--plain:hover {
  text-decoration: underline;
}

/* Disabled state */
.polaris-button:disabled {
  background: var(--p-color-bg-surface);
  color: var(--p-color-text-disabled);
  cursor: not-allowed;
}
```

## Form Inputs

### Text Input
```css
.polaris-input {
  width: 100%;
  font-family: var(--p-font-family-sans);
  font-size: var(--p-font-size-200);
  padding: var(--p-space-200) var(--p-space-300);
  border: var(--p-border-width-1) solid var(--p-color-border);
  border-radius: var(--p-border-radius-100);
  background: var(--p-color-bg);
  color: var(--p-color-text);
  transition: border-color var(--p-motion-duration-150) var(--p-motion-ease);
}

.polaris-input:hover {
  border-color: var(--p-color-border-hover);
}

.polaris-input:focus {
  outline: none;
  border-color: var(--p-color-bg-fill-brand);
  box-shadow: 0 0 0 1px var(--p-color-bg-fill-brand);
}

.polaris-input::placeholder {
  color: var(--p-color-text-secondary);
}

.polaris-input:disabled {
  background: var(--p-color-bg-surface);
  color: var(--p-color-text-disabled);
  cursor: not-allowed;
}

/* Error state */
.polaris-input--error {
  border-color: var(--p-color-bg-fill-critical);
}
.polaris-input--error:focus {
  box-shadow: 0 0 0 1px var(--p-color-bg-fill-critical);
}
```

### Label
```css
.polaris-label {
  display: block;
  font-size: var(--p-font-size-200);
  font-weight: var(--p-font-weight-medium);
  color: var(--p-color-text);
  margin-bottom: var(--p-space-100);
}

.polaris-label--required::after {
  content: '*';
  color: var(--p-color-bg-fill-critical);
  margin-left: var(--p-space-050);
}
```

### Select
```css
.polaris-select {
  width: 100%;
  font-family: var(--p-font-family-sans);
  font-size: var(--p-font-size-200);
  padding: var(--p-space-200) var(--p-space-300);
  padding-right: var(--p-space-800);
  border: var(--p-border-width-1) solid var(--p-color-border);
  border-radius: var(--p-border-radius-100);
  background: var(--p-color-bg) url("data:image/svg+xml,...") no-repeat right var(--p-space-300) center;
  appearance: none;
  cursor: pointer;
}
```

## Data Tables

### Basic Table
```css
.polaris-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--p-font-family-sans);
  font-size: var(--p-font-size-200);
}

.polaris-table th {
  text-align: left;
  font-weight: var(--p-font-weight-semibold);
  font-size: var(--p-font-size-75);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-color-text-secondary);
  padding: var(--p-space-300) var(--p-space-400);
  border-bottom: var(--p-border-width-1) solid var(--p-color-border);
  background: var(--p-color-bg-surface-secondary);
}

.polaris-table td {
  padding: var(--p-space-300) var(--p-space-400);
  border-bottom: var(--p-border-width-1) solid var(--p-color-border);
  color: var(--p-color-text);
}

.polaris-table tr:hover {
  background: var(--p-color-bg-surface-hover);
}

/* Numeric columns */
.polaris-table--numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Compact variant */
.polaris-table--compact th,
.polaris-table--compact td {
  padding: var(--p-space-200) var(--p-space-300);
  font-size: var(--p-font-size-100);
}
```

## Navigation

### Sidebar Navigation
```css
.polaris-nav {
  width: 240px;
  background: var(--p-color-bg-surface);
  padding: var(--p-space-400);
}

.polaris-nav__section {
  margin-bottom: var(--p-space-400);
}

.polaris-nav__title {
  font-size: var(--p-font-size-75);
  font-weight: var(--p-font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--p-color-text-secondary);
  padding: var(--p-space-200) var(--p-space-300);
}

.polaris-nav__item {
  display: flex;
  align-items: center;
  gap: var(--p-space-200);
  padding: var(--p-space-200) var(--p-space-300);
  border-radius: var(--p-border-radius-100);
  color: var(--p-color-text);
  text-decoration: none;
  transition: background var(--p-motion-duration-150) var(--p-motion-ease);
}

.polaris-nav__item:hover {
  background: var(--p-color-bg-surface-hover);
}

.polaris-nav__item--active {
  background: var(--p-color-bg-surface-active);
  font-weight: var(--p-font-weight-medium);
}
```

## Badges & Tags

### Badge
```css
.polaris-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--p-space-050) var(--p-space-200);
  font-size: var(--p-font-size-75);
  font-weight: var(--p-font-weight-medium);
  border-radius: var(--p-border-radius-full);
}

.polaris-badge--success {
  background: #d4edda;
  color: #1a6d4f;
}

.polaris-badge--critical {
  background: #fce4e4;
  color: #d72c0d;
}

.polaris-badge--warning {
  background: #fff3cd;
  color: #8a6116;
}

.polaris-badge--info {
  background: #e0f0ff;
  color: #0066cc;
}
```

## Page Layout

### Page Container
```css
.polaris-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--p-space-600);
}

.polaris-page__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--p-space-600);
}

.polaris-page__title {
  font-size: var(--p-font-size-500);
  font-weight: var(--p-font-weight-bold);
  color: var(--p-color-text);
}

.polaris-page__actions {
  display: flex;
  gap: var(--p-space-200);
}
```

### Grid Layout
```css
.polaris-grid {
  display: grid;
  gap: var(--p-space-400);
}

.polaris-grid--2 {
  grid-template-columns: repeat(2, 1fr);
}

.polaris-grid--3 {
  grid-template-columns: repeat(3, 1fr);
}

.polaris-grid--4 {
  grid-template-columns: repeat(4, 1fr);
}

@media (max-width: 768px) {
  .polaris-grid--2,
  .polaris-grid--3,
  .polaris-grid--4 {
    grid-template-columns: 1fr;
  }
}
```

## Empty State

```css
.polaris-empty-state {
  text-align: center;
  padding: var(--p-space-1000);
}

.polaris-empty-state__icon {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--p-space-400);
  color: var(--p-color-text-secondary);
}

.polaris-empty-state__heading {
  font-size: var(--p-font-size-400);
  font-weight: var(--p-font-weight-semibold);
  margin-bottom: var(--p-space-200);
}

.polaris-empty-state__content {
  color: var(--p-color-text-secondary);
  margin-bottom: var(--p-space-400);
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}
```
