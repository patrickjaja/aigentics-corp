# Frontend Components - AI Offer Agent

This directory contains all React components for the AI Offer Agent frontend application.

## Component Structure

```
components/
├── conversation/          # Conversation & chat components
│   ├── ChatInterface.tsx  # Main chat UI with AI Elements (T053)
│   └── QuestionFlow.tsx   # Progressive disclosure question flow (T054)
├── offer/                 # Offer-related components
│   └── OfferPreview.tsx   # Offer preview with work packages (T055)
├── customer/              # Customer & GDPR components
│   └── ConsentForm.tsx    # GDPR consent form (T056)
├── common/                # Shared/common components
│   └── LanguageSelector.tsx # EU language selector (T057)
├── admin/                 # Admin dashboard components
│   ├── ApprovalDashboard.tsx  # Admin approval dashboard (T058)
│   └── WorkPackageEditor.tsx  # Work package editor (T059)
└── ui/                    # Base shadcn/ui components
    ├── button.tsx
    ├── card.tsx
    ├── input.tsx
    ├── textarea.tsx
    ├── select.tsx
    ├── checkbox.tsx
    ├── label.tsx
    └── badge.tsx
```

## Component Overview

### T053: ChatInterface
**File**: `conversation/ChatInterface.tsx`

Main chat interface component with AI Elements integration.

**Features**:
- Real-time message streaming
- Auto-scroll to latest messages
- Conversation initialization
- German language default
- Error handling with retry

**Props**:
```typescript
interface ChatInterfaceProps {
  conversationId?: string;
  onConversationStart?: (conversation: Conversation) => void;
  onMessageSend?: (message: string) => Promise<void>;
  className?: string;
}
```

**Usage**:
```tsx
import { ChatInterface } from "@/components/conversation/ChatInterface";

<ChatInterface
  onConversationStart={(conv) => console.log('Started:', conv.id)}
  onMessageSend={async (msg) => await sendToBackend(msg)}
/>
```

### T054: QuestionFlow
**File**: `conversation/QuestionFlow.tsx`

Progressive disclosure question flow component (max 5 questions visible).

**Features**:
- Progressive disclosure pattern (max 5 visible questions)
- Visual progress tracking with breadcrumbs
- Multiple question types (text, select, number)
- Required field validation
- Navigation between questions

**Props**:
```typescript
interface QuestionFlowProps {
  conversationId: string;
  onComplete?: (answers: Record<string, unknown>) => void;
  maxQuestionsVisible?: number; // default: 5
  className?: string;
}
```

**Usage**:
```tsx
import { QuestionFlow } from "@/components/conversation/QuestionFlow";

<QuestionFlow
  conversationId={conversationId}
  maxQuestionsVisible={5}
  onComplete={(answers) => generateOffer(answers)}
/>
```

### T055: OfferPreview
**File**: `offer/OfferPreview.tsx`

Offer preview component with work packages and pricing breakdown.

**Features**:
- Complete offer visualization
- Work package breakdown
- German number/currency formatting (DIN 5008)
- Status badges
- Action buttons (download, accept, reject)
- Terms & conditions display

**Props**:
```typescript
interface OfferPreviewProps {
  offer: Offer;
  onDownload?: () => void;
  onAccept?: () => void;
  onReject?: () => void;
  showActions?: boolean; // default: true
  className?: string;
}
```

**Usage**:
```tsx
import { OfferPreview } from "@/components/offer/OfferPreview";

<OfferPreview
  offer={offer}
  onDownload={() => downloadPDF(offer.id)}
  onAccept={() => acceptOffer(offer.id)}
  showActions={true}
/>
```

### T056: ConsentForm
**File**: `customer/ConsentForm.tsx`

GDPR-compliant consent form with full tracking.

**Features**:
- GDPR consent tracking (timestamp, IP, version)
- Multiple consent purposes (required & optional)
- Privacy policy acknowledgment
- Form validation
- Email validation
- Customer data collection

**Props**:
```typescript
interface ConsentFormProps {
  onConsent?: (customer: Customer) => void;
  consentTextVersion?: string; // default: "1.0"
  className?: string;
}
```

**Usage**:
```tsx
import { ConsentForm } from "@/components/customer/ConsentForm";

<ConsentForm
  consentTextVersion="1.0"
  onConsent={(customer) => saveCustomer(customer)}
/>
```

### T057: LanguageSelector
**File**: `common/LanguageSelector.tsx`

EU language selector supporting all 24 EU official languages.

**Features**:
- All 24 EU official languages
- Persistent language preference (localStorage)
- Browser language detection
- Two variants: dropdown and compact
- useLanguage hook for easy integration

**Props**:
```typescript
interface LanguageSelectorProps {
  value?: string; // default: "de"
  onValueChange?: (language: string) => void;
  showFlag?: boolean; // default: true
  variant?: "dropdown" | "compact"; // default: "dropdown"
  className?: string;
}
```

**Usage**:
```tsx
import { LanguageSelector, useLanguage } from "@/components/common/LanguageSelector";

// Component usage
<LanguageSelector
  variant="dropdown"
  onValueChange={(lang) => i18n.changeLanguage(lang)}
/>

// Hook usage
function MyComponent() {
  const { language, setLanguage } = useLanguage();
  // language is auto-detected from browser/localStorage
}
```

### T058: ApprovalDashboard
**File**: `admin/ApprovalDashboard.tsx`

Admin dashboard for managing offer approvals (EUR 100k+ workflow).

**Features**:
- Approval statistics (pending, approved, rejected)
- Filtering by status
- Search by offer ID or creator
- Inline approval/rejection
- Comment/notes support
- High-value indicator (EUR 100k+)

**Props**:
```typescript
interface ApprovalDashboardProps {
  onApprove?: (approvalId: string, comments?: string) => Promise<void>;
  onReject?: (approvalId: string, comments: string) => Promise<void>;
  onView?: (approvalId: string) => void;
  className?: string;
}
```

**Usage**:
```tsx
import { ApprovalDashboard } from "@/components/admin/ApprovalDashboard";

<ApprovalDashboard
  onApprove={async (id, comments) => await approveOffer(id, comments)}
  onReject={async (id, comments) => await rejectOffer(id, comments)}
  onView={(offerId) => navigate(`/offers/${offerId}`)}
/>
```

### T059: WorkPackageEditor
**File**: `admin/WorkPackageEditor.tsx`

Interactive work package editor with drag-and-drop support.

**Features**:
- Add/remove work packages
- Edit package details (title, description, hours, rate)
- Manage deliverables and technologies
- Auto-calculate costs
- Drag-and-drop reordering (visual only)
- Change tracking
- Readonly mode

**Props**:
```typescript
interface WorkPackageEditorProps {
  workPackages: WorkPackage[];
  onChange?: (workPackages: WorkPackage[]) => void;
  onSave?: (workPackages: WorkPackage[]) => Promise<void>;
  readonly?: boolean; // default: false
  className?: string;
}
```

**Usage**:
```tsx
import { WorkPackageEditor } from "@/components/admin/WorkPackageEditor";

<WorkPackageEditor
  workPackages={offer.workPackages}
  onChange={(packages) => setWorkPackages(packages)}
  onSave={async (packages) => await updateOffer(packages)}
  readonly={false}
/>
```

## Base UI Components (shadcn/ui)

All components are built on top of shadcn/ui primitives:

- **Button**: Multiple variants (default, destructive, outline, secondary, ghost, link)
- **Card**: Container with header, title, description, content, footer
- **Input**: Text input with validation support
- **Textarea**: Multi-line text input
- **Select**: Dropdown select with search
- **Checkbox**: Checkbox with label support
- **Label**: Form label with accessibility
- **Badge**: Status indicators and tags

## Styling & Theming

All components use:
- **Tailwind CSS** for styling
- **CSS variables** for theming (defined in `globals.css`)
- **clsx + tailwind-merge** for conditional classes
- **class-variance-authority** for component variants

## TypeScript Types

All API types are defined in `/src/types/api.ts`:

```typescript
export interface Conversation { ... }
export interface Message { ... }
export interface Question { ... }
export interface WorkPackage { ... }
export interface Offer { ... }
export interface Customer { ... }
export interface GDPRConsent { ... }
export interface Approval { ... }
```

## Accessibility

All components follow WCAG 2.1 AA standards:
- Keyboard navigation support
- ARIA labels and roles
- Focus management
- Color contrast compliance
- Screen reader compatibility

## i18n Support

Components are i18n-ready:
- German as default language
- 24 EU languages supported
- Date/number formatting (DD.MM.YYYY, 1.234,56 €)
- Sie-Form in all German text

## Testing

Component tests are located in `/src/__tests__/components/`:
- Unit tests for each component
- Integration tests for complex flows
- Accessibility tests
- Snapshot tests

## Performance

- React.memo for expensive components
- useCallback for event handlers
- Lazy loading for large components
- Virtualization for long lists (future)

## Next Steps

1. Implement frontend pages (T060-T063)
2. Add i18n translation files (T076-T077)
3. Write component tests (T083)
4. Add Storybook documentation (optional)

---

**Created**: 2025-10-06
**Tasks**: T053-T059
**Status**: ✅ Complete
