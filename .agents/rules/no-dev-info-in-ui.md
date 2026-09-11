# Rule: Zero Developer / Model-Specific Information in User-Facing UI

## Summary
Never expose or mention internal application development details, AI model names, model versions, internal voice identifiers, or backend library names in any user-facing UI component, function, label, chip, dialog, tooltip, toast, snackbar, or status message.

## Forbidden Terms in UI Text
The following technical and backend identifiers must NEVER appear in user-facing copy:
- **Model Names & Versions**: `Kokoro`, `Kokoro-82M`, `Qwen`, `Qwen 2.5`, `Gemma`, `LLaMA`, etc.
- **Voice Identifiers**: `af_heart`, `am_adam`, `af_adam`, `en-US-AriaNeural`, `en-IN-NeerjaNeural`, etc.
- **Backend TTS / Audio Libraries**: `Edge-TTS`, `SAPI`, `pyttsx3`, `onnxruntime`, etc.

## Permitted & Recommended Terminology
Always use clean, human-centric, professional terminology:
- **Speaker / Audio Voices**:
  - Section Header: `Speaker Voice`
  - Voice Options: `Female Voice`, `Male Voice`
- **AI Summary Notifications & Messages**:
  - Success Snackbars: `✨ AI Summary generated!`
  - Loading / Progress: `Generating AI Summary...`
  - Playback Mode: `Reading AI Summary Aloud`, `Reading Full Notice Aloud`
  - Actions: `Listen to Notice`, `Summarize Notice`

## Scope
This rule applies unconditionally across all roles (Dev Admin, Principal, HOD, Teacher, Student, College Admin) and all application surfaces (Mobile, Tablet, Desktop, Web).
