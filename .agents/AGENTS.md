# Workspace Rules for EchoSphere

## UI Consistency Rule Across User Roles
- UI improvements and design changes made to the Developer Administrator (`devadmin`) role's pages must automatically be applied to the pages of all other roles (Student, Teacher, Head of Department, College Admin, Principal).
- Note: This rule applies ONLY to UI/UX design, styling, and visual aesthetics — feature permissions and role capabilities must remain strictly enforced.

## Primary Target & Zero Overflow Guarantee
- **Primary Build Target**: Android (`flutter build apk --debug`) is the primary target for all builds, feature updates, and layout testing.
- **Zero Overflow Constraint**: All UI layouts, headers, stat cards, dialogs, chip rows, and text fields must use responsive constraints (`Expanded`, `Flexible`, `SingleChildScrollView`, `Wrap`) to guarantee zero layout overflow errors on all Android device screen sizes (from 320px compact mobile screens to large tablets).

## Strict Prohibition of Developer / Model-Specific Info in User-Facing UI
- **Zero Internal / Technical Jargon in UI**: Never expose or mention application development-specific info, internal model names, model versions, voice IDs, or backend library names in any user-facing UI, label, button, chip, dialog, tooltip, toast, snackbar, or status message.
  - Prohibited technical terms in user-facing text include: `Kokoro`, `Qwen`, `Gemma`, `Edge-TTS`, `SAPI`, `pyttsx3`, `af_heart`, `am_adam`, `af_adam`, `en-US-AriaNeural`, or any other voice/model identifiers.
  - Use clean, user-centric, professional terminology instead:
    - Voice selection: "Speaker Voice" (header), "Female Voice" and "Male Voice" (options/chips).
    - Summarization: "AI Summary", "✨ AI Summary generated!", "Generating AI Summary...".
    - Audio playback: "Listen to Notice", "Reading AI Summary Aloud", "Reading Full Notice Aloud".
- This rule applies unconditionally to all future features, menus, dialogs, screens, and functions across the entire application.


