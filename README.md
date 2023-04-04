# Wunderbar
A cli tool to import anki cards.

## UID
```latex
A-Za-z0-9
24 \cdot 2 + 10 = 58
```

1.3 * (10 ^ 7) = 50% chance of duplicate

## Neovim integration (the good stuff)

### Snippets
Luasnip configuration. I sadly don't know any other snippet engines.
```lua
-- Generate a unique string
local function uid(len)
  local uid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890"
  local rt = ""
  for _ = 1, len do
    local rand_int = math.random(1, #uid_chars)
    local rand_char = uid_chars:sub(rand_int, rand_int)
    rt = rt .. rand_char
  end
  return rt
end

-- Snippet
ls.s("new_card", fmt(
  [[
  #+begin_src toml
  [{}.{}]
  front = "{}"
  back = "{}"
  tags = ["{}"]
  #+end_src{}
  ]], {
      ls.choice_node(1, {ls.text_node("basic"), ls.text_node("cloze"), ls.text_node("type"), ls.text_node("reversed"), ls.text_node("reversed_optional")}),
      ls.function_node(function() return uid(8) end),
      ls.insert_node(2), ls.insert_node(3), ls.insert_node(4), ls.insert_node(0),
    }
  )
)
```
### User command
Adds `Anki` as an user command when in org files.
```lua
-- Command Anki that does it real good
local anki_augroup = vim.api.nvim_create_augroup("anki", {clear = true})
vim.api.nvim_create_autocmd("FileType", {
  pattern = "org",
  group = anki_augroup,
  desc = "Add user command to add anki card",
  callback = function()
    vim.api.nvim_create_user_command("Anki",
      function(args)
        local filename = vim.api.nvim_buf_get_name(0)
        if args["args"] == "" then
          os.execute("Wunderbar.py --force --file " .. filename)
        else
          os.execute("Wunderbar.py --force --file " .. filename .. "--deck " .. args["args"])
        end
      end,
      {nargs = "?", complete = function()
        return {"deutsch", "school", "wunderbar"}
      end, desc = "Add buffer toml cards to anki deck"}
    )
  end
})
```

## TODO
- Add markdown support
- Tags based on git branch?
- Custom css
- Write usage
- Write install
- Write dependencies
- Write AUR package
- Write AUR Table of content
