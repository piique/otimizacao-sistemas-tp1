-- Substitui glifos sem cobertura em Latin Modern por equivalentes presentes
-- na fonte DejaVu Sans, para a geracao do PDF.
function Str(el)
  local t = el.text
  t = t:gsub("\u{2714}", "\u{2713}")  -- ✔ -> ✓
  t = t:gsub("\u{2718}", "\u{2717}")  -- ✘ -> ✗
  if t ~= el.text then
    return pandoc.Str(t)
  end
end
