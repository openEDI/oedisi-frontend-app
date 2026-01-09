# UI Component Library

This document describes the reusable UI components available in the application.

## Button Component

**File**: `src/components/ui/Button.vue`

A versatile button component with multiple variants and sizes.

### Props
- `variant`: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link' (default: 'default')
- `size`: 'default' | 'sm' | 'lg' | 'icon' (default: 'default')
- `class`: Additional CSS classes to apply

### Usage
```vue
<Button>Click me</Button>
<Button variant="outline" size="lg">Large outline button</Button>
<Button variant="destructive">Delete</Button>
<Button variant="ghost" size="icon">
  <Home :size="20" />
</Button>
```

## Card Component

**File**: `src/components/ui/Card.vue`

A container component for content with optional header and footer sections.

### Slots
- `header`: Content for the header section
- `default`: Main content
- `footer`: Content for the footer section

### Props
- `class`: Additional CSS classes

### Usage
```vue
<Card>
  <template #header>
    <h2>Card Title</h2>
  </template>
  <p>Card content goes here</p>
  <template #footer>
    <Button>Action</Button>
  </template>
</Card>
```

## Dialog Component

**File**: `src/components/ui/Dialog.vue`

A modal dialog that appears on top of the page content.

### Props
- `open`: Boolean to control visibility (v-model)

### Emits
- `update:open`: Emitted when dialog should close

### Child Components
- `DialogHeader`: Container for header content
- `DialogTitle`: Title of the dialog
- `DialogDescription`: Description text
- `DialogFooter`: Container for action buttons

### Usage
```vue
<Dialog v-model:open="isOpen">
  <DialogHeader>
    <DialogTitle>Dialog Title</DialogTitle>
    <DialogDescription>Optional description</DialogDescription>
  </DialogHeader>
  <!-- Content -->
  <DialogFooter>
    <Button @click="isOpen = false">Cancel</Button>
    <Button>Save</Button>
  </DialogFooter>
</Dialog>
```

## Input Component

**File**: `src/components/ui/Input.vue`

A text input field with consistent styling.

### Props
- `class`: Additional CSS classes
- All standard HTML input attributes (type, placeholder, value, etc.)

### Usage
```vue
<Input 
  v-model="username" 
  type="text"
  placeholder="Enter username"
/>
```

## Textarea Component

**File**: `src/components/ui/Textarea.vue`

A multi-line text input for longer text content.

### Props
- `class`: Additional CSS classes
- All standard HTML textarea attributes

### Usage
```vue
<Textarea 
  v-model="description" 
  placeholder="Enter description"
  rows="4"
/>
```

## Label Component

**File**: `src/components/ui/Label.vue`

A form label for labeling inputs.

### Props
- `class`: Additional CSS classes

### Usage
```vue
<Label for="username">Username</Label>
<Input id="username" v-model="username" />
```

## Layout Components

### LeftSidebar
**File**: `src/components/LeftSidebar.vue`

Displays available components that can be dragged to the designer canvas.

### RightSidebar
**File**: `src/components/RightSidebar.vue`

Shows properties and configuration options for selected elements.

### DataVisualization
**File**: `src/components/DataVisualization.vue`

Component for visualizing simulation data and results.

## Styling

All components use Tailwind CSS with custom CSS variables defined in `src/styles/index.css`. The variables follow this pattern:

- `--color-primary`: Primary color
- `--color-secondary`: Secondary color
- `--color-destructive`: Destructive action color
- `--color-muted`: Muted/disabled state color
- `--color-background`: Page background
- `--color-foreground`: Text foreground
- And more...

Customize theme colors by modifying the CSS variables in the `:root` selector.

## Utility Functions

### cn() - Class Name Merge
**File**: `src/lib/utils.ts`

Merges Tailwind CSS classes intelligently, handling conflicts.

```typescript
import { cn } from '@/lib/utils'

// Usage
const buttonClass = cn(
  'px-4 py-2 rounded',
  'bg-blue-500',
  className // Override with custom class
)
```

## Component Variants

Components use `class-variance-authority` for managing variant styling. This allows for type-safe variant definitions:

```typescript
const buttonVariants = cva(
  'base styles...',
  {
    variants: {
      variant: {
        default: '...',
        outline: '...',
      },
      size: {
        default: '...',
        sm: '...',
      },
    },
  }
)
```

## Best Practices

1. **Accessibility**: All components support standard HTML attributes for accessibility
2. **Type Safety**: Full TypeScript support with proper prop interfaces
3. **Composition**: Components are composable and can be combined
4. **Styling**: Use Tailwind CSS classes for custom styling
5. **Slots**: Use slots for flexible content placement

## Adding New Components

To create a new component:

1. Create a new `.vue` file in `src/components/ui/`
2. Use the Composition API with `<script setup>`
3. Define props and emits with proper TypeScript types
4. Use Tailwind CSS for styling
5. Use the `cn()` utility for class merging

Example:
```vue
<template>
  <div :class="cn('base-styles', props.class)">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  class?: string
}

defineProps<Props>()
</script>
```
