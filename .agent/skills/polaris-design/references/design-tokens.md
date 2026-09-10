# Polaris Design Tokens

Complete reference for Shopify Polaris design tokens.

## Color Tokens

### Background Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--p-color-bg` | `#ffffff` | Page background |
| `--p-color-bg-surface` | `#f1f1f1` | Card/surface background |
| `--p-color-bg-surface-secondary` | `#f7f7f7` | Secondary surfaces |
| `--p-color-bg-surface-hover` | `#f0f0f0` | Hover state |
| `--p-color-bg-surface-active` | `#e8e8e8` | Active/pressed state |
| `--p-color-bg-surface-selected` | `#ededed` | Selected state |
| `--p-color-bg-inverse` | `#1a1a1a` | Dark backgrounds |

### Text Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--p-color-text` | `#1a1a1a` | Primary text |
| `--p-color-text-secondary` | `#616161` | Secondary/muted text |
| `--p-color-text-disabled` | `#8c8c8c` | Disabled text |
| `--p-color-text-inverse` | `#ffffff` | Text on dark bg |
| `--p-color-text-brand` | `#008060` | Brand/link text |

### Status Colors
| Role | Background | Text |
|------|------------|------|
| Success | `#008060` | `#1a6d4f` |
| Critical | `#d72c0d` | `#d72c0d` |
| Warning | `#ffc453` | `#8a6116` |
| Info | `#0070f3` | `#0066cc` |
| Highlight | `#5c6ac4` | `#5c6ac4` |

### Border Colors
| Token | Value |
|-------|-------|
| `--p-color-border` | `#e1e1e1` |
| `--p-color-border-secondary` | `#d1d1d1` |
| `--p-color-border-hover` | `#999999` |
| `--p-color-border-focus` | `#008060` |

## Spacing Tokens

Based on 4px base unit.

| Token | Value | Pixels |
|-------|-------|--------|
| `--p-space-050` | `0.125rem` | 2px |
| `--p-space-100` | `0.25rem` | 4px |
| `--p-space-150` | `0.375rem` | 6px |
| `--p-space-200` | `0.5rem` | 8px |
| `--p-space-300` | `0.75rem` | 12px |
| `--p-space-400` | `1rem` | 16px |
| `--p-space-500` | `1.25rem` | 20px |
| `--p-space-600` | `1.5rem` | 24px |
| `--p-space-800` | `2rem` | 32px |
| `--p-space-1000` | `2.5rem` | 40px |
| `--p-space-1200` | `3rem` | 48px |
| `--p-space-1600` | `4rem` | 64px |

## Typography Tokens

### Font Family
```css
--p-font-family-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--p-font-family-mono: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
```

### Font Sizes
| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| `--p-font-size-70` | `0.6875rem` | 11px | Caption small |
| `--p-font-size-75` | `0.75rem` | 12px | Caption |
| `--p-font-size-100` | `0.8125rem` | 13px | Body small |
| `--p-font-size-200` | `0.875rem` | 14px | Body (default) |
| `--p-font-size-300` | `1rem` | 16px | Body large |
| `--p-font-size-400` | `1.25rem` | 20px | Heading small |
| `--p-font-size-500` | `1.5rem` | 24px | Heading |
| `--p-font-size-600` | `1.75rem` | 28px | Heading large |
| `--p-font-size-700` | `2rem` | 32px | Display |

### Font Weights
| Token | Value | Usage |
|-------|-------|-------|
| `--p-font-weight-regular` | 400 | Body text |
| `--p-font-weight-medium` | 500 | Emphasis |
| `--p-font-weight-semibold` | 600 | Headings, labels |
| `--p-font-weight-bold` | 700 | Strong emphasis |

### Line Heights
| Token | Value | Usage |
|-------|-------|-------|
| `--p-font-line-height-1` | 1 | Single line |
| `--p-font-line-height-2` | 1.25 | Headings |
| `--p-font-line-height-3` | 1.5 | Body text |
| `--p-font-line-height-4` | 1.75 | Loose text |

## Border Tokens

### Border Radius
| Token | Value | Usage |
|-------|-------|-------|
| `--p-border-radius-050` | `0.125rem` | 2px - Subtle |
| `--p-border-radius-100` | `0.25rem` | 4px - Default |
| `--p-border-radius-200` | `0.5rem` | 8px - Cards |
| `--p-border-radius-300` | `0.75rem` | 12px - Modals |
| `--p-border-radius-400` | `1rem` | 16px - Large |
| `--p-border-radius-full` | `9999px` | Pills/circles |

### Border Width
| Token | Value |
|-------|-------|
| `--p-border-width-1` | `1px` |
| `--p-border-width-2` | `2px` |
| `--p-border-width-4` | `4px` |

## Shadow Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--p-shadow-100` | `0 1px 0 rgba(0,0,0,0.05)` | Subtle |
| `--p-shadow-200` | `0 1px 2px rgba(0,0,0,0.1)` | Cards |
| `--p-shadow-300` | `0 4px 6px -1px rgba(0,0,0,0.1)` | Dropdown |
| `--p-shadow-400` | `0 10px 15px -3px rgba(0,0,0,0.1)` | Modal |
| `--p-shadow-500` | `0 20px 25px -5px rgba(0,0,0,0.15)` | Popover |

## Motion Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--p-motion-duration-0` | `0ms` | Instant |
| `--p-motion-duration-50` | `50ms` | Micro |
| `--p-motion-duration-100` | `100ms` | Fast |
| `--p-motion-duration-150` | `150ms` | Default |
| `--p-motion-duration-200` | `200ms` | Moderate |
| `--p-motion-duration-300` | `300ms` | Slow |
| `--p-motion-duration-500` | `500ms` | Deliberate |
| `--p-motion-ease` | `cubic-bezier(0.25, 0.1, 0.25, 1)` | Standard |
| `--p-motion-ease-in` | `cubic-bezier(0.42, 0, 1, 1)` | Enter |
| `--p-motion-ease-out` | `cubic-bezier(0, 0, 0.58, 1)` | Exit |

## Z-Index Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `--p-z-1` | 100 | Base layer |
| `--p-z-2` | 400 | Overlay |
| `--p-z-3` | 510 | Modal |
| `--p-z-4` | 512 | Toast |
| `--p-z-5` | 513 | Tooltip |
