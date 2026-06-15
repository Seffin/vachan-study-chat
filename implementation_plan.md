# Responsive Viewport & Layout Adjustments

The Vachan Study desktop layout is fully functional, but mobile and tablet layouts contain visual breakages. The sidebars (Scripture Navigator and scripture text Context) overlap or hide inappropriately, the header elements overflow, and the main page navigation tabs are completely missing on mobile viewports.

This plan details the visual, navigation, and breakpoint fixes to make the app fully responsive across mobile, tablet, and desktop screens.

## User Review Required

> [!IMPORTANT]
> **Mobile Navigation Drawer**:
> We will add a mobile hamburger menu drawer on the right side of the navbar (`Navbar.tsx`) for viewports below `md` (768px). This drawer will contain:
> 1. Navigation tabs (Study Room, My Notes, Groups, Dataset Viewer) which were previously hidden on mobile.
> 2. Gemini Token status details and the quota refill button.
> 3. User profile details.
>
> On the mobile header, the wide segmented Light/Dark theme switcher will be replaced by a single icon button to prevent header clutter. Do you approve this design choice?

## Proposed Changes

---

### [Component] Navigation Bar (`src/components/Navbar.tsx`)

Modify `Navbar.tsx` to handle responsive states gracefully, hiding wide desktop features and introducing a slide-out hamburger navigation menu on mobile.

#### [MODIFY] [Navbar.tsx](file:///h:/Seffin/Benjamin/Logos%20Bible%2520Study%2520Chatbot/src/components/Navbar.tsx)
- Add local state `const [menuOpen, setMenuOpen] = useState(false)` for the mobile drawer.
- Wrap desktop navigation links, token status pill, theme switcher, and profile dropdown in standard `hidden md:flex` / `hidden md:block` responsive visibility classes.
- Add a mobile Sun/Moon toggle button (`md:hidden`) that changes theme on click with a single icon tap.
- Add a hamburger icon button (`md:hidden`) to open the navigation drawer.
- Add a slide-out navigation panel (`AnimatePresence` + `motion.div`) aligned to `top-16` on mobile screens containing the collapsed tabs, quota progress, and profile link.

---

### [Component] Workspace (`src/components/Workspace.tsx`)

Adjust breakpoints and layout constraints inside the main multi-pane workspace to support tablet column configurations and resolve header/drawer squishing.

#### [MODIFY] [Workspace.tsx](file:///h:/Seffin/Benjamin/Logos%20Bible%2520Study%2520Chatbot/src/components/Workspace.tsx)
- **Breakpoints Realignment**:
  - Update Left Sidebar to hide on tablet viewports: change `md:flex` to `lg:flex`.
  - Update Left Menu toggle button in workspace header to show on tablet: change `md:hidden` to `lg:hidden`.
  - Realign Left Drawer and backdrop to toggle on tablet: change `md:hidden` to `lg:hidden`.
  - Realign Right Drawer and backdrop to toggle on tablet: change `md:hidden` to `lg:hidden`.
  - This ensures that on both mobile and tablet, sidebars slide out as drawers and do not squeeze the central chat interface.
- **Header Crowding**:
  - Hide "Study Assistant" text on mobile (`hidden sm:inline`) to prevent items overflowing or wrapping onto a second line.
- **Right Drawer Layout**:
  - Increase Right Drawer width on mobile/tablet from static `w-[320px]` to responsive `w-full max-w-[360px] sm:max-w-[380px]` to give content and controls more breathing room.
  - Import and use the Lucide `X` icon to close the Scripture Context drawer instead of the unintuitive `Eye` icon.
  - Reduce paddings and text sizes on drop-down selectors in the Right Drawer header to prevent layout breaks on small screen widths.

---

## Verification Plan

### Automated Verification
- Run Next.js linting and TypeScript checks to ensure no compile errors:
  ```bash
  npm run build
  ```

### Manual Verification
- Resize browser viewport to:
  - **Mobile (375x812)**: Open navigation menu, change theme, switch rooms, check workspace header spacing, open Navigator/Context drawers, and ensure they occupy full height without overflow.
  - **Tablet (768x1024)**: Open Navigator/Context drawers and verify they overlay cleanly.
  - **Desktop (1440x900)**: Verify sidebars remain docked and the desktop layout functions correctly.
