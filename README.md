# Wunderbar
Anki, Orgmode, Neovim: simply wonderful.

## Install
My environment uses the following dependency versions: 
- python 3.10.10
- anki 2.1.61
- toml 0.10.2

Other versions should work as well, but are not tested.
I think python has to be >= 3.10, and anki >= 2.1.

```command
git clone "https://github.com/elicatza/wunderbar"
cd wunderbar
doas make install
```

## Uninstall
When in cloned directory run the following:
```command
doas make uninstall
cd ..
rm -rf wunderbar
```

## Usage
When in an orgmode file use this template:
```org
* Deutsch
  Normal orgfile
  #+begin_src toml
  [basic.wmPE0ceT] # Unique card identifier to avoid duplicate cards
  front = "Schon als Kind zeichnete und malte er gern."
  back = "Allerede som barn tegnet og malte han gjerne."
  tags = ["Deutsch"] # Optional
  #+end_src
```

There are more templates in [examples](./examples/cards.org).


I would recommend using a snippet engine to generate this template.
Luasnip example later.


Run `wunderbar.py -h` to see usage. Here are some examples:
```command
wunderbar.py --file myfile.org --deck [deck_name] --base [anki_base_dir]
wunderbar.py -F myfile.org -d [deck_name] --force
```

`wunderbar.py` will not write to deck without confirming changes with user.
This can be avoided using the --force falg, or -f for short.

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
          os.execute("wunderbar.py --force --file " .. filename)
        else
          os.execute("wunderbar.py --force --file " .. filename .. "--deck " .. args["args"])
        end
      end,
      {nargs = "?", complete = function()
        return {"deutsch", "school", "wunderbar"}
      end, desc = "Add buffer toml cards to anki deck"}
    )
  end
})
```

### Colored text
Highlight a word / sentence in visual mode.
Then click `<leader>am`, `<leader>an`, or `<leader>af` to color text.
This uses the same autogroup as in the **user command** section.

```lua
vim.api.nvim_create_autocmd("FileType", {
  pattern = "org",
  group = anki_augroup,
  desc = "Color me",
  callback = function()
    local function visual_surround_pre_suf(pre, suf)
      local _, rs, cs = unpack(vim.fn.getpos('v'))
      local _, re, ce = unpack(vim.fn.getpos('.'))
      if rs ~= re then
        -- Note: Does not work over multiple lines
        return nil
      end

      if cs > ce then
        vim.api.nvim_buf_set_text(0, rs - 1, cs, rs - 1, cs, { suf })
        vim.api.nvim_buf_set_text(0, re - 1, ce -1, re - 1, ce - 1, { pre })
      else
        vim.api.nvim_buf_set_text(0, re - 1, ce, re - 1, ce, { suf })
        vim.api.nvim_buf_set_text(0, rs - 1, cs - 1, rs - 1, cs - 1, { pre })
      end
    end

    vim.keymap.set("v", '<leader>af', function()
      visual_surround_pre_suf("<span style='color: rgb(247, 168, 184);'>", "</span>" )
    end, { noremap = true })
    vim.keymap.set("v", '<leader>an', function()
      visual_surround_pre_suf("<span style='color: rgb(169, 169, 169);'>", "</span>" )
    end, { noremap = true })
    vim.keymap.set("v", '<leader>am', function()
      visual_surround_pre_suf("<span style='color: rgb(85, 205, 252);'>", "</span>" )
    end, { noremap = true })
  end,
})
```

## TODO
- Add markdown support (also plain toml i guess)
- Tags based on git branch?
- Custom css
- Write AUR package
- Table of content
