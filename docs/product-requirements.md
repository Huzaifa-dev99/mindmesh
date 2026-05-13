# MindMesh Product Requirements Specification

## 1. Objective

Improve MindMesh so it feels cleaner, easier to navigate, more visually distinctive, and more useful for personal knowledge retrieval. The updated experience should make chat retrieval feel lightweight, keep retrieved content out of the main answer unless requested, and make Library items easy to browse and preview.

## 2. Product Principles

- The chat is the primary user-facing intelligence surface.
- Retrieved content should support the answer, not overwhelm it.
- Notes and documents should feel like first-class knowledge objects.
- Navigation should stay minimal and predictable.
- Empty states should be honest and actionable.
- Design should feel modern, youthful, calm, and readable.

## 3. Scope

### In Scope

- Retrieved content reference behavior in chat.
- Sidebar cleanup.
- Updated color palette direction.
- Content Library list and preview behavior.
- Right-pane note organization by date.
- Architecture diagram and documentation.

### Out of Scope

- Full binary PDF/image OCR extraction.
- Multi-user team collaboration.
- Enterprise sharing and permissions.
- Full redesign of backend auth.

## 4. Retrieved Content Behavior

### Requirement

MindMesh should retrieve a maximum of 5 content references per chat response.

### Behavior

- Retrieval APIs should return only the top 5 most relevant results for chat citations.
- The assistant answer should not include full retrieved chunks by default.
- Retrieved content appears as small pill-style reference buttons below or inline with the assistant message.
- Each reference pill should show a short label:
  - Notes: note title
  - Documents: file name plus optional chunk/page marker
  - Web: source title or domain
- Clicking a reference opens the item in its source space:
  - Note reference opens the note preview/editor in the right pane.
  - Document reference opens document preview metadata in the right pane.
  - Web reference opens the external URL in a new browser tab.
- If a user asks "show the source", "show full context", or similar, the chat may expand the retrieved snippet.

### UX Details

- Reference pills should be compact, horizontally scrollable if needed, and keyboard-focusable.
- Hover/focus should reveal source type and relevance metadata where available.
- Citations should not interrupt message readability.
- If there are no relevant results, show no pills and let the assistant state the no-answer behavior.

### Acceptance Criteria

- Chat citations are capped at 5.
- Full retrieved chunks are not rendered in chat by default.
- Each citation is shown as a pill-style button.
- Clicking a note citation opens that note in the right pane.
- Clicking a document citation opens document metadata/preview in the right pane.
- Clicking a web citation opens the URL externally.
- Citation buttons are accessible by keyboard.

## 5. Sidebar Update

### Requirement

Remove the "New Note" button from the left sidebar.

### Behavior

- Left sidebar primary action remains "New Chat".
- Note creation should move to the Library or right-pane notes area.
- Sidebar navigation remains focused on:
  - Chats
  - Library
  - Chat history
  - Profile/settings/lock

### Acceptance Criteria

- "New Note" no longer appears in the left sidebar.
- Users can still create notes from the right pane or Library.
- Sidebar remains usable in expanded and collapsed states.

## 6. Visual Design Direction

### Design Goal

Refresh MindMesh with a modern, youthful, Gen Z-friendly palette while keeping the app calm, readable, and useful for long sessions.

### Recommended Palette

#### Dark Mode

- Background: `#0B0D12`
- Sidebar: `#11131A`
- Surface: `#181B24`
- Elevated Surface: `#202431`
- Primary: `#7C5CFF`
- Secondary: `#18C8A8`
- Accent: `#FF7AB6`
- Warning Accent: `#F8C14A`
- Text Primary: `#F7F7FB`
- Text Secondary: `#AEB4C2`
- Border: `#2A2F3D`

#### Light Mode

- Background: `#F8F7FF`
- Sidebar: `#FFFFFF`
- Surface: `#FFFFFF`
- Elevated Surface: `#F0EEFF`
- Primary: `#6848F5`
- Secondary: `#0FAF95`
- Accent: `#E84D93`
- Warning Accent: `#C88700`
- Text Primary: `#171923`
- Text Secondary: `#5B6272`
- Border: `#E3E0F4`

### Accessibility Notes

- Maintain WCAG AA contrast for text and buttons.
- Do not rely on color alone for source type.
- Use icons, labels, and tooltips for source distinctions.
- Keep focus states visible in both themes.

### Acceptance Criteria

- Theme variables define primary, secondary, accent, background, surface, text, and border colors.
- Both dark and light modes remain readable.
- Interactive elements have visible hover and focus states.
- No large blocks of low-contrast text.

## 7. Information Architecture

### Primary Navigation

- Chats
- Library

### Chat Area

- Conversation history.
- Assistant and user messages.
- Reference pills attached to assistant responses.
- Composer.

### Library

- Documents list.
- Notes list.
- Media references.
- Insights and activity.

### Right Pane

- Context preview.
- Note editor.
- Document preview.
- Grouped notes by date.

## 8. Content Library Requirements

### Requirement

The Content Library should display all documents and notes in one central area.

### Behavior

- Library shows sections or tabs for:
  - Notes
  - Documents
  - Media
  - Chats
- Notes and documents are listed by title/name.
- Clicking a note opens a preview in the right pane.
- Clicking a document opens a preview in the right pane.
- Preview screen includes:
  - Title
  - Type
  - Created date
  - Updated date where available
  - Source
  - Tags
  - Content snippet or document chunk summary
  - MinIO object path for documents

### Component Requirements

- `LibraryList`
- `LibraryItemRow`
- `RightPanePreview`
- `NotePreview`
- `DocumentPreview`
- `MetadataBadge`
- `ReferencePill`

### Acceptance Criteria

- Library displays both notes and documents.
- Clicking a note opens note preview in the right pane.
- Clicking a document opens document preview in the right pane.
- Preview metadata is visible and readable.
- Empty states explain how to add content.

## 9. Notes Organization

### Requirement

Notes in the right pane should be grouped by date, similar to chat history.

### Groups

- Today
- Yesterday
- Previous 7 Days
- Previous 30 Days
- Older

### Behavior

- Grouping uses `updated_at` when available, otherwise `created_at`.
- Groups with no notes are hidden.
- Notes inside each group are sorted newest first.
- Clicking a note opens preview or editor mode in the right pane.

### Acceptance Criteria

- Notes are grouped by the required date buckets.
- Empty groups are hidden.
- Notes sort newest first inside each group.
- Note click opens the selected note preview.

## 10. Data and State Requirements

### Chat State

- Active conversation ID.
- Messages.
- Citation/reference list per assistant message.
- Selected reference.
- Loading and error states.

### Library State

- Notes.
- Documents.
- Media references.
- Selected library item.
- Right-pane preview mode.
- Upload/import state.

### Settings State

- Theme.
- LLM provider.
- Tavily API key.
- Local lock/PIN state.

### Tag Input State

- Stored tags loaded from `GET /v1/knowledge/tags`.
- Current comma-separated tag draft.
- Active tag fragment after the last comma.
- Suggested stored tags filtered by the active fragment.

### Tag Input Behavior

- When a user types in a tag field, MindMesh suggests matching stored tags.
- Suggestions exclude tags already present in the field.
- Clicking a suggestion inserts it into the comma-separated list and keeps the field ready for another tag.
- Users can still type and save brand-new tags.

### Backend Requirements

- Chat endpoint should return no more than 5 citations.
- Citations should include:
  - `source_type`
  - `source_id`
  - `title`
  - `snippet`
  - `metadata`
- Document metadata must include `minio_object_path`.
- All retrieval must filter by `user_id`.

## 11. User Interaction Flows

### Chat Retrieval Flow

1. User sends query in chat.
2. Supervisor Agent receives query.
3. Supervisor routes to Notes, Documents, Web, or Direct response.
4. Subagent retrieves or searches content.
5. Supervisor returns final answer.
6. UI renders answer plus up to 5 reference pills.
7. User clicks a reference.
8. App opens corresponding item preview in the right pane or external URL.

### Library Preview Flow

1. User opens Library.
2. User selects a note or document.
3. Right pane opens preview.
4. User can inspect metadata and snippet.
5. For notes, user may switch to edit mode.

### Notes Grouping Flow

1. Right pane loads notes.
2. Notes are grouped by date bucket.
3. User selects a note.
4. Preview/editor opens in the right pane.

## 12. Acceptance Criteria Summary

- Retrieved chat citations are capped at 5.
- Retrieved content displays as reference pills only.
- Citation click opens the source preview/location.
- Left sidebar no longer has "New Note".
- Color palette is updated with accessible theme variables.
- Library lists all notes and documents.
- Note/document selection opens a right-pane preview.
- Right-pane notes are grouped by date buckets.
- Architecture docs are stored under `docs/`.
