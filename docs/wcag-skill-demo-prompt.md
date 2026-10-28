# Accessible HTML generation

Build the requested page with these WCAG-informed rules. Keep the requested
content and functionality. Return only the complete HTML document, with inline
CSS and any necessary JavaScript. No external assets, tools, reports, or claims
of accessibility conformance.

- Start with `<!doctype html>`, `<html lang="en">` (or the content language),
  a meaningful `<title>`, charset, and viewport metadata.
- Use one `<main>` and one descriptive `<h1>`. Nest section headings logically.
  Use semantic header, navigation, lists, and footer where appropriate. Give
  repeated navigation landmarks distinct names. Add a working skip link when
  navigation precedes the main content.
- Use native links for navigation and buttons for actions. Every control and
  link needs a concise, meaningful accessible name; avoid empty or ambiguous
  links. Give icon-only buttons text or an `aria-label`. Do not use clickable
  divs, positive tabindex, or redundant/conflicting ARIA roles.
- Give each input a visible `<label for="...">` matching its unique `id`.
  Use suitable input types and autocomplete tokens. Group related options in
  `<fieldset><legend>`. Do not use placeholders as labels. Identify required
  fields in text and with `required`.
- Explain errors in text, connect help/errors using `aria-describedby`, and
  set `aria-invalid` when invalid. Preserve valid entries. Announce submission
  feedback through a status region. Do not rely on color alone.
- Give informative images meaningful `alt`; use `alt=""` for decorative ones.
  Use real text instead of images of text. Use captions and header cells with
  appropriate `scope` for data tables, never tables for layout.
- Use dark text on a solid light background or another high-contrast palette.
  Target at least 7:1 for normal text and 4.5:1 for large text. Keep borders,
  controls, and meaningful graphics at least 3:1 against adjacent colors.
- Keep keyboard order logical and focus visible, with a clear outline. Do not
  hide focus or cover focused controls with sticky content. Make targets at
  least 44 by 44 CSS pixels where practical. Allow zoom and mobile reflow.
- Prefer native checkbox, radio, select, and `<details><summary>` controls.
  If custom interaction is needed, support keyboard activation and synchronize
  visible changes with accessible states such as `aria-expanded` or
  `aria-pressed`. Never put focusable elements inside hidden content.
- Avoid flashing, autoplay, unnecessary animation, and automatic navigation.
  Respect `prefers-reduced-motion`. Keep the page simple enough to complete
  within the requested output budget; remove decoration before required labels,
  semantics, keyboard behavior, or closing markup.