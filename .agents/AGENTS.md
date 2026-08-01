# Workspace Rules for EchoSphere

## UI Consistency Rule Across User Roles
- UI improvements and design changes made to the Developer Administrator (`devadmin`) role's pages must automatically be applied to the pages of all other roles (Student, Teacher, Head of Department, College Admin, Principal).
- Note: This rule applies ONLY to UI/UX design, styling, and visual aesthetics — feature permissions and role capabilities must remain strictly enforced.

## Primary Target & Zero Overflow Guarantee
- **Primary Build Target**: Android (`flutter build apk --debug`) is the primary target for all builds, feature updates, and layout testing.
- **Zero Overflow Constraint**: All UI layouts, headers, stat cards, dialogs, chip rows, and text fields must use responsive constraints (`Expanded`, `Flexible`, `SingleChildScrollView`, `Wrap`) to guarantee zero layout overflow errors on all Android device screen sizes (from 320px compact mobile screens to large tablets).

