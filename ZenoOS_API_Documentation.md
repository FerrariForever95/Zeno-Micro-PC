# Zeno OS — API Documentation

> Generated directly from the provided Zeno OS source tree. Only functionality
> present in the source is documented; no undocumented or assumed behavior has
> been added. Per request, `Home/APPS/Files.py` and `bin/banner/banner.py` are
> excluded from this reference.

---

## Table of Contents

1. [Module Overview](#module-overview)
2. [Dependencies](#dependencies)
3. [Public API Reference](#public-api-reference)
   - [3.1 Native C Modules](#31-native-c-modules)
     - [`moclcd` (modlcd.c)](#moclcd-modlcdc)
     - [`zfs` (zfs_lfs.h / zfs_lfs.c)](#zfs-zfs_lfsh--zfs_lfsc)
   - [3.2 `Graphics.py`](#32-graphicspy)
   - [3.3 `Services.py`](#33-servicespy)
   - [3.4 `pwrmanagement.py`](#34-pwrmanagementpy)
   - [3.5 `ZenCMD.py` (interactive shell)](#35-zencmdpy-interactive-shell)
   - [3.6 `recovery.py`](#36-recoverypy)
   - [3.7 `Home/OS/` boot scripts](#37-homeos-boot-scripts)
   - [3.8 `Home/TOOLS/zenpath.py`](#38-hometoolszenpathpy)
   - [3.9 `lcd.py`](#39-lcdpy)
   - [3.10 `pystone_lowmem.py`](#310-pystone_lowmempy)
   - [3.11 `Home/APPS/` bundled applications](#311-homeapps-bundled-applications)
4. [Usage Examples](#usage-examples)
5. [Notes and Limitations](#notes-and-limitations)

---

## Module Overview

**Zeno OS** is a MicroPython-based operating system targeting an **ESP32-S3**
handheld device with an ILI9488-class parallel (8080 8-bit) LCD panel and
resistive/capacitive touch input. The codebase is layered as follows:

| Layer | File(s) | Responsibility |
|---|---|---|
| Native drivers | `modlcd.c`, `zfs_lfs.c` / `zfs_lfs.h` | C-level MicroPython modules: `moclcd` (LCD panel I/O over ESP-IDF's `esp_lcd` i80 bus) and `zfs` (a private LittleFS2 filesystem on its own flash partition). |
| Graphics/UI toolkit | `Graphics.py` | Pure-Python widget library (buttons, sliders, dialogs, virtual keyboard, HTML-lite renderer, screen transitions) built on top of `moclcd`. |
| System services | `Services.py` | The OS "kernel services" layer: process scheduling, user accounts & permissions, a permissioned virtual file system facade, logging, disk/SD management, boot configuration, networking, Git-based package distribution, Bluetooth, IoT device control. |
| Power service | `pwrmanagement.py` | CPU frequency/power-tier scaling service, independent of the process scheduler. |
| Shell | `ZenCMD.py` (current, v3.81) and `recovery.py` (bundled snapshot, v2.2.0) | A POSIX-shell-like command line interface with piping (`|`), statement chaining (`;`), aliases, a permission ("Super Mode") gate, and a dependency-free `Recovery` utility for rebuilding the OS from GitHub even when the rest of the OS is broken. |
| Boot / home screen | `Home/OS/kernel.py`, `Home/OS/kernel1.py`, `Home/OS/safe.py` | Alternate/successive versions of the graphical home-screen boot sequence (app grid, power dialog, task manager). These use different, non-interchangeable UI object APIs (see [Notes](#notes-and-limitations)). |
| Tools | `Home/TOOLS/zenpath.py` | A minimal line-based remote patch agent for editing on-device files over stdin/stdout. |
| Bring-up scripts | `lcd.py` | A raw, hand-written bring-up/test script for the ILI9488 panel (predates `moclcd`). |
| Benchmark | `pystone_lowmem.py` | A low-memory MicroPython port of the classic Pystone CPU benchmark. |
| Applications | `Home/APPS/*.py` | Bundled end-user apps: `Browser.py`, `Settings.py`, `ZenStore.py`, `Paint.py`, `Creeper.py`, `do.py`, and the `SETTINGS/` sub-screens `display.py` and `wifi.py`. |

All application and boot-script code assumes a global `zeno` module (referred
to throughout the source as `zeno.py`) that exposes shared, boot-time state
such as `zeno.ui`, `zeno.net`, `zeno.tsk`, `zeno.user`, `zeno.password`,
`zeno.ssid`, `zeno.wifi_password`, `zeno.gitsecret`, `zeno.wallpaper`,
`zeno.boot_cap`, and `zeno.authorized`. `zeno.py` itself is not included in
the provided source (it is generated at recovery time — see
[`Recovery.ZENO_TEMPLATE`](#recovery-recoverypy--zencmdpy)), so its exact
runtime shape is inferred from usage rather than documented as source.

---

## Dependencies

**Native / firmware:**
- MicroPython (ESP32-S3 port), ESP-IDF v5.5.x
- `esp_lcd_panel_io`, `esp_lcd_panel_vendor`, `esp_heap_caps`, `driver/ledc` (backlight PWM)
- LittleFS2 (`lfs2.h` / `lfs2_util.h`) for the private `zfs` partition
- `extmod/font_petme128_8x8` (the same 8×8 font MicroPython's `framebuf.text()` uses)

**MicroPython built-in / stdlib modules used across the codebase:**
`machine`, `time`, `os`, `sys`, `gc`, `uio`, `json`, `hashlib`, `ucryptolib`,
`network`, `usocket`, `ssl`, `ntptime`, `micropython`, `ubluetooth`,
`_thread` (optional), `urandom` (or `random` fallback), `uio`

**Third-party / vendor libraries referenced by `Services.py`:**
- `urequests` (HTTP client)
- `firmware` module providing `DS3231` (RTC) and `SDCard` drivers
- `sinricpro` (`SinricPro`, `sinricpro.devices.sinricpro_switch.SinricProSwitch`) for `IoTManager`

**Internal, cross-referencing modules:**
- `moclcd` — native LCD driver, required by `Graphics.py`
- `zfs` — native private filesystem, required by `Services.py` (`zeno.py`'s persisted data lives here)
- `Graphics.py` — required by `Home/OS/kernel.py` and all `Home/APPS/*` apps
- `Services.py` — required by `ZenCMD.py`, `pwrmanagement.py` (optional `Logger`), and several apps (`Browser.py`, `ZenStore.py`)
- `zeno` (generated at recovery time) — required by nearly every application and boot script for shared runtime state

---

## Public API Reference

### 3.1 Native C Modules

#### `moclcd` (modlcd.c)

A MicroPython C extension module implementing an 8080 8-bit parallel LCD
driver on top of ESP-IDF's `esp_lcd` i80 bus API. Fixed pin mapping:

| Signal | GPIO |
|---|---|
| RST | 12 |
| RS (DC) | 13 |
| WR | 14 |
| RD | 41 |
| Backlight (BL) | 38 |
| D0–D7 | 16, 15, 11, 10, 9, 4, 18, 17 |

All drawing primitives clip silently to the panel bounds except where noted.

| Function | Parameters | Returns | Exceptions | Description |
|---|---|---|---|---|
| `moclcd.init(pclk=10_000_000, width=480, height=320, madctl=0x28)` | `pclk` (int, pixel clock Hz), `width`, `height` (int), `madctl` (int, MADCTL register value) | `None` | `OSError` if the underlying `esp_lcd` bus/IO setup fails | Initializes the i80 bus and panel IO. Defaults to landscape 480×320; pass `width=320, height=480, madctl=0x48` for portrait. |
| `moclcd.reset()` | none | `None` | `OSError` (via `require_init`) if called before `init()` | Performs the ILI9488 hardware reset sequence. |
| `moclcd.panel_init()` | none | `None` | `OSError` if not initialized | Runs the full known-good ILI9488 init command sequence (SWRESET, SLEEPOUT, COLMOD, MADCTL, DISPLAY ON, address window). |
| `moclcd.backlight(on)` | `on` (bool) | `None` | — | Digital backlight on/off. Drives PWM duty to max/0 instead if `backlight_init()` was previously called. |
| `moclcd.backlight_init(freq_hz=5000, resolution_bits=8)` | `freq_hz` (int), `resolution_bits` (int) | `None` | — | Sets up an LEDC PWM channel on the backlight pin for dimmable brightness. |
| `moclcd.backlight_set(level)` | `level` (float, 0.0–1.0) | `None` | Requires `backlight_init()` to have been called first | Sets backlight brightness as a fraction of full duty. |
| `moclcd.cmd(cmd, params=None)` | `cmd` (int), `params` (bytes-like, optional) | `None` | `OSError` if not initialized | Raw passthrough: sends a command byte with optional parameter bytes. |
| `moclcd.data(buf)` | `buf` (bytes-like) | `None` | `OSError` if not initialized | Raw passthrough: sends a raw data buffer. |
| `moclcd.fill_rect(x, y, w, h, color)` | `x, y, w, h` (int), `color` (int, RGB565) | `None` | `ValueError` if the rectangle is out of panel bounds | Fills a solid rectangle via a chunked, DMA-pipelined pixel stream (`FILL_CHUNK_PIXELS` = 2048 pixels/chunk). |
| `moclcd.fill_screen(color)` | `color` (int, RGB565) | `None` | Same as `fill_rect` | Fills the entire panel. |
| `moclcd.blit(x, y, w, h, buf)` | `x, y, w, h` (int), `buf` (bytes-like, raw RGB565, MSB first) | `None` | Raises if out of bounds (per module header) | Streams a raw RGB565 pixel buffer directly to the panel. |
| `moclcd.draw_pixel(x, y, color)` | `x, y` (int), `color` (int) | `None` | none (clips silently) | Draws a single pixel; off-panel coordinates are silently dropped. |
| `moclcd.draw_line(x0, y0, x1, y1, color)` | ints | `None` | none (clips silently) | Draws a line. Horizontal/vertical lines use the fast DMA fill path; diagonals use a pixel-by-pixel Bresenham walk. |
| `moclcd.draw_rect(x, y, w, h, color)` | ints | `None` | none (clips silently) | Draws a rectangle **outline** (four 1px edges). Use `fill_rect` for a solid rectangle. |
| `moclcd.draw_circle(x0, y0, r, color)` | ints | `None` | none (clips silently) | Draws a circle outline using the midpoint circle algorithm with 8-way symmetry. |
| `moclcd.fill_circle(x0, y0, r, color)` | ints | `None` | none (clips silently) | Draws a filled circle via vertical DMA-filled spans (same technique as Adafruit_GFX), cheaper than plotting pixel-by-pixel. |
| `moclcd.draw_text8x8(x, y, text, fg, bg=None)` | `x, y` (int), `text` (str), `fg` (int), `bg` (int, optional) | `None` | — | Renders text using the native `font_petme128_8x8` glyph table via the DMA path. Omitting `bg` renders a **transparent** background (only foreground pixels are touched). |
| `moclcd.draw_bmp(path, x, y, w=0, h=0, max_w=0, max_h=0)` | `path` (str), `x, y` (int), `w, h` (int, target size), `max_w, max_h` (int, clamp) | `None` | — | Loads and draws an uncompressed 24-bit BMP directly from the ESP-IDF VFS in C, as a single DMA transfer. No palette or RLE BMP support. Clips to the panel rather than raising or skipping. |

**Module state constants (internal, not exposed to Python):** panel width/height default to 480×320, MADCTL defaults to `0x28` (landscape). `FILL_CHUNK_PIXELS = 2048` (4 KB DMA chunks); `LCD_CMD_CASET/PASET/RAMWR/RAMWRC` are the underlying ILI9488 command bytes used internally.

#### `zfs` (zfs_lfs.h / zfs_lfs.c)

A private LittleFS2 filesystem mounted on its own flash **partition**
(never mounted into the MicroPython VFS, never visible via `os.listdir()` or
`open()`). Accessed only through `import zfs`. All functions are thread-safe
via an internal FreeRTOS mutex.

**Error codes (`zfs_err_t`)**

| Constant | Value | Meaning |
|---|---|---|
| `ZFS_OK` | 0 | Success |
| `ZFS_ERR_NOT_MOUNTED` | -1 | Filesystem not mounted |
| `ZFS_ERR_ALREADY_MNT` | -2 | Already mounted |
| `ZFS_ERR_NO_PART` | -3 | Backing partition not found |
| `ZFS_ERR_LFS` | -4 | Underlying LittleFS2 error |
| `ZFS_ERR_IO` | -5 | I/O error |
| `ZFS_ERR_INVAL` | -6 | Invalid argument |
| `ZFS_ERR_NOENT` | -7 | No such file/directory |
| `ZFS_ERR_EXIST` | -8 | Already exists |
| `ZFS_ERR_NOMEM` | -9 | Out of memory |
| `ZFS_ERR_NOTDIR` | -10 | Not a directory |
| `ZFS_ERR_ISDIR` | -11 | Is a directory |
| `ZFS_ERR_NOTEMPTY` | -12 | Directory not empty |
| `ZFS_ERR_NAMETOOLONG` | -13 | Name exceeds `ZFS_NAME_MAX` (255) |

**Data structures**

| Type | Fields | Purpose |
|---|---|---|
| `zfs_info_t` | `block_size`, `block_count`, `blocks_used` (uint32), `partition_offset`, `partition_size` (uint32), `mounted` (bool) | Returned by `zfs_lfs_info()`. |
| `zfs_dirent_t` | `name[256]` (char), `type` (uint8, `LFS2_TYPE_REG`/`LFS2_TYPE_DIR`), `size` (uint32, 0 for directories) | Passed to the `listdir` callback per entry. |
| `zfs_listdir_cb_t` | `int (*)(const zfs_dirent_t *entry, void *userdata)` | Callback type for `zfs_lfs_listdir`; return non-zero to stop iteration early. |

**Functions**

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `zfs_lfs_mount(void)` | — | `zfs_err_t` | Mounts the `zfs` partition (locates it by label, builds the LittleFS2 config, mounts). |
| `zfs_lfs_umount(void)` | — | `zfs_err_t` | Unmounts the filesystem. |
| `zfs_lfs_format(void)` | — | `zfs_err_t` | Formats the partition. |
| `zfs_lfs_info(zfs_info_t *out)` | `out` (output struct pointer) | `zfs_err_t` | Fills in block/partition/mount statistics. |
| `zfs_lfs_write(const char *path, const uint8_t *data, size_t len)` | path, buffer, length | `zfs_err_t` | Writes (creates/overwrites) a file. |
| `zfs_lfs_read(const char *path, uint8_t **out_data, size_t *out_len)` | path, output buffer pointer, output length pointer | `zfs_err_t` | Reads an entire file into a newly allocated buffer. |
| `zfs_lfs_delete(const char *path)` | path | `zfs_err_t` | Deletes a file or (empty) directory. |
| `zfs_lfs_exists(const char *path, bool *out)` | path, output flag | `zfs_err_t` | Checks whether a path exists. |
| `zfs_lfs_rename(const char *oldpath, const char *newpath)` | old/new paths | `zfs_err_t` | Renames/moves an entry. |
| `zfs_lfs_mkdir(const char *path)` | path | `zfs_err_t` | Creates a directory. |
| `zfs_lfs_rmdir(const char *path)` | path | `zfs_err_t` | Removes a directory. |
| `zfs_lfs_listdir(const char *path, zfs_listdir_cb_t cb, void *userdata)` | path, callback, user data pointer | `zfs_err_t` | Iterates directory entries, invoking `cb` once per entry. |
| `zfs_lfs_strerror(zfs_err_t err)` | error code | `const char *` | Returns a human-readable string for an error code. |

Internally, file I/O uses `lfs2_file_opencfg()` (MicroPython's LittleFS2 build
has no `lfs2_file_open()`), with per-file cache buffers sized `ZFS_CACHE_SIZE`
supplied by the caller; a FreeRTOS mutex (`s_zfs.lock`) guards all state and
is lazily created on first use.

---

### 3.2 `Graphics.py`

A pure-Python UI/graphics toolkit built directly on `moclcd`. Defaults to
**landscape** 480×320. Call `init_display()` once at boot.

```python
import zeno_gfx as gfx
gfx.init_display()                 # landscape 480x320
gfx.set_touch_handler(my_touch.read)
```

#### Module-level constants

| Constant | Value | Description |
|---|---|---|
| `WIDTH` | `480` | Current panel width (updated by `init_display()`). |
| `HEIGHT` | `320` | Current panel height (updated by `init_display()`). |
| `WHITE`, `BLACK`, `GRAY`, `DARK_GRAY`, `LIGHT_GRAY` | RGB565 ints | Common colors, derived via `color565()`. |
| `active_screen` | `UIScreen` or `None` | The most recently `.start()`-ed `UIScreen`. |
| `background` | RGB565 int, default `BLACK` | Module-wide default background color; override via `set_background()`. |

#### Module-level functions

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `init_display(pclk=10_000_000, width=480, height=320, madctl=0x28)` | see `moclcd.init` | `None` | Brings the panel up (backlight off → `moclcd.init` → backlight on → `moclcd.reset` → `moclcd.panel_init`) and syncs `WIDTH`/`HEIGHT`. |
| `brightness(value)` | `value` (float 0.0–1.0) | `None` | Sets backlight brightness via `moclcd.backlight_set`. |
| `color565(r, g, b)` | `r, g, b` (int 0–255) | `int` (RGB565) | Packs 8-bit RGB into an RGB565 value. |
| `set_background(color)` | `color` (int) | `None` | Sets the module-wide default background used by `clear()` and text rendering. |
| `log_error(msg)` / `log_warn(msg)` | `msg` (str) | `None` | Prints a tagged `[UI ERROR]` / `[UI WARN]` message. |
| `set_touch_handler(fn)` | `fn` (callable returning `(x, y)` or `None`) | `None` | Registers the touch driver callback used by `get_touch()`. |
| `get_touch()` | none | `(x, y)` or `None` | Returns the current touch point via the registered handler, or `None` if none registered/no touch. |
| `fill_rect(x, y, w, h, color)` | ints | `None` | Safe fill: clips to panel bounds instead of raising (unlike `moclcd.fill_rect`). No-ops if the clipped rectangle is empty. |
| `fill_screen(color)` | `color` (int) | `None` | Fills the whole panel. |
| `clear(color=None)` | `color` (int, optional) | `None` | Fills the whole panel with `color` or the module `background`. |
| `draw_hline(x, y, w, color)` / `draw_vline(x, y, h, color)` | ints | `None` | Draw a 1px horizontal/vertical line via `fill_rect`. |
| `blit(x, y, w, h, buf)` | ints, `buf` (bytes-like) | `None` | Safe blit: silently skipped if it doesn't fully fit on the panel. |
| `draw_text8x8(x, y, text, fg, bg=None)` | `x, y` (int), `text` (str), `fg` (int), `bg` (int, optional) | `None` | Wraps `moclcd.draw_text8x8`. `bg=None` produces a truly transparent glyph (no scratch buffer needed); an explicit color erases the full 8×8 cell. No-op for empty `text`. |
| `draw_bmp(path, x, y, w=None, h=None, max_w=None, max_h=None)` | `path` (str), ints | `None` | Wraps `moclcd.draw_bmp`. Uncompressed 24-bit BMP only; clipped rather than skipped if partially off-screen. |
| `window_close_animation(duration=0.4, fps=60, color=None, ease=True)` | see params | `None` | Shrinks the screen to a point (reverse of `window_open_animation`), used as a screen-close transition. |
| `window_open_animation(duration=0.4, fps=60, color=None, ease=True)` | see params | `None` | Expands the screen from a point outward, used as a screen-open transition. |

#### `UIButton`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, label, color=color565(0,0,255), text_color=WHITE, margin=5, action=None)` | Rectangular label button. |
| `draw()` | — | Draws the button (falls back to a red error box and logs on exception). |
| `get_touch()` | — | Returns `True`/`False` for whether touch is inside the button (± `margin`); invokes `action()` if inside. |

#### `UIText`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, text, fg=WHITE, bg=None)` | Static text label. |
| `draw()` | — | Renders text at `(x, y)`. |

#### `UIBMPButton`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, bmp, *, bmp_pressed=None, margin=5, action=None)` | Bitmap-image button with optional pressed-state image. |
| `draw()` | — | Draws `bmp_pressed` while pressed (if provided), else `bmp`. |
| `get_touch()` | — | Tracks pressed state and fires `action()` while touched inside bounds. |

#### `UIScreen`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(fg=WHITE, background=None, on_exit=None, taskbarcolor=color565(50,50,50), taskbar_text=None, taskbar_text_color=WHITE, taskbar_height=35, *args, **kwargs)` | Base screen/container: manages background, a taskbar with a close ("X") box, and exit callback. |
| `layer(x, y, width, height, color)` | ints | Draws a filled rectangle "layer" on the screen. |
| `openscreen()` / `closescreen()` | — | Runs the open/close window animation using this screen's background. |
| `start()` | — | Full screen bring-up: open animation, background draw, taskbar with close box, sets `active_screen`. |
| `taskbar(taskbarcolor, taskbar_text, taskbar_text_color, taskbar_height=35)` | — | (Re)draws the taskbar with new parameters. |
| `draw_gradient(color1, color2, angle=0, block_size=1)` | `color1, color2` (int), `angle` (0/45/90/135/180/270), `block_size` (int) | Renders a linear or diagonal gamma-corrected gradient with slight per-band dithering noise. |
| `start_withoutexit()` | — | Like `start()` but without the close box (implementation continues past the shown excerpt). |
| `check()` | — | Polls the close-box touch region; likely triggers `on_exit`. |

#### `UITextBoxView`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, text=None, fg=WHITE, bg=BLACK, padding=4)` | Scrollable multi-line text viewer. |
| `set_text(text)` | `text` (str) | Replaces displayed text and resets scroll. |
| `draw()` | — | Renders the currently visible lines, honoring vertical scroll offset (`scroll_px`). |
| `handle_touch()` | — | Implements vertical drag-to-scroll. |

#### `DialogBox`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(*, title="Dialog", message="", btn_yes="Yes", btn_no="No", on_yes=None, on_no=None, on_exit=None)` | Modal Yes/No dialog with a close box. |
| `show()` | — | Draws the dialog and blocks in a touch-polling loop until Yes/No/exit is pressed; returns `"yes"`, `"no"`, or `None`. |

#### `UIToggleSwitch`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w=50, h=26, state=False, on_color=color565(0,180,0), off_color=color565(120,120,120), knob=WHITE, action=None)` | An iOS-style toggle switch. |
| `draw()` | — | Renders the pill-shaped switch and knob. |
| `handle_touch()` | — | Flips `state` on tap inside bounds; calls `action(state)`. |

#### `UISlider`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, min_v=0, max_v=100, value=0, track=color565(80,80,80), fill=color565(0,150,255), knob=WHITE, action=None)` | Linear slider, fixed height 10px. |
| `draw()` | — | Draws track, fill, and knob. |
| `handle_touch()` | — | Updates `value` based on touch X position; calls `action(value)`. |

#### `UIPanel`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, title=None, bg=None, border=None, title_fg=None, title_bg=None)` | A bordered container panel with optional title text. |
| `draw()` | — | Draws background, border, and title. |
| `open(steps=8, delay_ms=1)` | ints | Animates the panel growing from a point to full size. |

#### `UIProgressBar`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h=12, value=0, bg=color565(50,50,50), fg=color565(0,200,0))` | Horizontal progress bar, `value` in 0–100. |
| `set(val)` | `val` (int) | Clamps to 0–100 and redraws. |
| `draw()` | — | Renders background and filled portion. |

#### `UIStatusIndicator`

| Member | Signature | Description |
|---|---|---|
| Class constants | `OK = 0`, `WARN = 1`, `ERR = 2` | Status states. |
| `__init__` | `(x, y, r=6, state=0)` | Small colored status dot. |
| `draw()` | — | Green/orange/red circle depending on `state`. |

#### `UIToast`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(text, duration=2)` | Transient bottom-of-screen notification. |
| `show()` | — | Draws the toast, sleeps `duration` seconds, then clears the screen. |

#### `UIListView`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, items, item_h=24, bg=color565(20,20,20), fg=WHITE, sel=color565(0,120,255), text_x=6, highlight=False, action=None)` | Scrollable, tappable list of text items. |
| `draw()` | — | Renders the visible window of `items`, honoring `scroll`. |
| `handle_touch()` | — | Drag-to-scroll plus tap-to-select (distinguishes drag vs. tap via a 6px move threshold); calls `action(idx, items[idx])` on selection. |

#### `UIInputTextBox`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, keyboard, fg, bg, padding=4, blink_ms=500)` | A single-line text field bound to a `VirtualKeyboard` instance, with a blinking caret. |
| `draw(force=False)` | `force` (bool) | Redraws only when the buffer changed or the caret blink toggled (unless `force=True`). |
| `handle_touch()` | — | Opens the bound keyboard when tapped. |

#### `UIIconButton`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, label, bg=color565(60,60,60), fg=WHITE, action=None)` | Text-labeled rectangular icon button. |
| `draw()` / `handle_touch()` | — | Standard button behavior with a small `time.sleep(0.15)` debounce after firing. |

#### `UICheckBox`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, label, checked=False, action=None)` | An 18×18 checkbox with adjacent label. |
| `draw()` / `handle_touch()` | — | Draws a checkmark when checked; toggles on tap. |

#### `UIRadioGroup`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, options, selected=0, action=None)` | Vertical group of radio buttons. |
| `draw()` / `handle_touch()` | — | Highlights the selected option; calls `action(i, options[i])` on selection. |

#### `UITabBar`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, h, tabs, active=0, action=None)` | Horizontal tab bar, tabs sized `w / len(tabs)`. |
| `draw()` / `handle_touch()` | — | Switches `active` tab on tap; calls `action(idx, tabs[idx])`. |

#### `UIStepper`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, value=0, step=1, action=None)` | A "−  value  +" numeric stepper, fixed 80×24 size. |
| `draw()` / `handle_touch()` | — | Increments/decrements `value` by `step`; calls `action(value)`. |

#### `UIDivider`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, color=color565(100,100,100))` | A horizontal divider line. |
| `draw()` | — | Draws the line. |

#### `UIScreenAnimator`

Vertical offset controller for screen transitions. **Contains no redraw
logic itself** — callers read `.offset_y` each frame and apply it.

| Member | Signature | Description |
|---|---|---|
| `__init__` | `()` | Initializes idle state (`offset_y = 0`). |
| `open(duration=220)` | ms | Animates from offset 30 → 0 (ease-out cubic). |
| `close(duration=160)` | ms | Animates from offset 0 → 30 (ease-in cubic). |
| `boot(duration=400)` | ms | Animates from offset 50 → 0 (ease-out cubic). |
| `update()` | — | Advances the animation; returns `True` while running, `False` once complete. |

#### `VirtualKeyboard`

An on-screen QWERTY/symbol keyboard with a fixed **touch-calibrated**
key layout (`calibrated_keys`, tuned for a specific screen
resolution/orientation — see [Notes](#notes-and-limitations)).

| Member | Signature | Description |
|---|---|---|
| Class constants | `TOUCH_RADIUS = 12`, `DEBOUNCE_MS = 200` | Touch-hit tolerance and repeat-press debounce. |
| `calibrated_keys` | `list[dict]` | Per-key `{'key': str, 'x': int, 'y': int}` calibration table for both ABC and symbol layouts. |
| `__init__` | `(width=None, height=120, text_color=None, key_color=None, border_color=None, bg_color=None, ok_action=None)` | Builds the keyboard docked at the bottom of the screen. |
| `close()` / `open()` | — | Hides/shows the keyboard. |
| `get_buffer(clear=False)` | `clear` (bool) | Returns the current typed buffer; optionally clears it. |
| `clear_buffer()` | — | Empties the buffer. |
| `check_touch()` | — | Processes a touch event against the current key layout, appending to `buffer` or invoking `ok_action`. |

#### `VKTouchCalibrator`

Interactive calibration tool for `VirtualKeyboard`; **must be re-run** after
changing screen resolution/orientation.

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(vk, samples_per_key=5)` | `vk` — a `VirtualKeyboard` instance to calibrate. |
| `run()` | — | Walks both the ABC and symbol/123 layouts, prompting the user to tap each unique key `samples_per_key` times, averages the touch coordinates, prints a ready-to-paste `calibrated_keys` block, and returns the computed list. |

#### `HTML`

A minimal HTML-subset renderer (recognizes `h1`, `p`, `br`, closing tags) that
displays plain text word-wrapped inside a `UIScreen`.

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(title="HTML")` | Sets up a titled screen and default `body`/`p`/`h1` styles. |
| `open(path)` | `path` (str) | Reads, clears, and parses/renders the file at `path`. |

#### `IOSSlider`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(x, y, w, min_v=0, max_v=100, value=0, track_border=color565(40,40,40), track_fill=color565(90,90,90), knob=color565(220,220,220), action=None)` | An iOS-style slider with a draggable rounded knob. |
| `draw()` / `handle_touch()` | — | Drag-only interaction (must start the drag on the knob itself); calls `action(value)` on move. |

---

### 3.3 `Services.py`

The system service layer. Imports several hardware/vendor modules
(`machine`, `network`, `ubluetooth`, `zfs`, `zeno`, `firmware.DS3231`,
`firmware.SDCard`, `sinricpro`) at module load time, and mounts the `zfs`
partition if not already mounted.

#### Module-level constants

| Constant | Value | Description |
|---|---|---|
| `SD_SCK, SD_MOSI, SD_MISO, SD_CS` | `40, 6, 5, 7` | SD card SPI pin assignment. |
| `LOGS_DIR` | `"/LOGS"` | Default logs directory. |
| `SYS_DIR` | `"/.sys"` | Hidden mirror directory backing `FileManager`'s metadata. |
| `PROGRAM_EXT`, `TEXT_EXT`, `BITMAP_EXT`, `IMAGE_EXT`, `AUDIO_EXT`, `VIDEO_EXT`, `JSON_EXT`, `ARCHIVE_EXT` | tuples of extensions | File type classification used by `FileManager`. |
| `EXECUTABLE_EXT`, `ROOT_OWNED_EXT` | tuples | `(".py", ".mpy")` / `(".py", ".mpy", ".zsh")` — files auto-executable / root-owned by default. |
| `PERM_FULL, PERM_READ, PERM_READWRITE, PERM_NONE, PERM_READEXEC, PERM_WRITEEXEC, PERM_WRITE, PERM_EXEC` | `0..7` | The 8-value Unix-like permission enum used by `FileManager`. |
| `READ_PERMS, WRITE_PERMS, EXEC_PERMS, VALID_PERMS` | sets | Groupings of the permission constants above. |
| `PID_TYPE_KERNEL/USER/THREAD/DAEMON/NETWORK/RESERVED` | `1,2,3,4,5,9` | PID "thousands place" type classification used by `Scheduler`. |
| `NEW, READY, RUNNING, BLOCKED, ZOMBIE, DEAD` | strings | `Process` state machine values. |
| `SIGTERM, SIGKILL, SIGSTOP, SIGCONT` | `15, 9, 19, 18` | Signal numbers understood by `Scheduler.kill()`. |
| `MODE_LOOP, MODE_PERIODIC, MODE_ONCE, MODE_THREAD` | strings | `Scheduler.spawn()` task modes. |
| `NICE_MIN, NICE_MAX` | `-20, 19` | Valid priority ("nice") range. |

#### `CPU`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(model="ESP32-S3N16R8")` | Prints the model string; tracks `usage_pct`. |
| `report_frame(busy_us, idle_us)` | ints | Scheduler tap: updates `usage_pct` from a single frame's busy/idle time. **Must not block.** |
| `usage()` | — | Returns last-reported CPU usage percentage (int). |
| `reboot()` | — | `machine.reset()` after a short delay. |
| `shutdown()` | — | `machine.deepsleep()` after a short delay. |
| `sleep_ms(ms)` | int | `machine.lightsleep(ms)`. |
| `set_freq(hz)` / `get_freq()` | int / — | Set/get CPU frequency via `machine.freq()`. |
| `reset_cause()` / `wake_reason()` | — | Wrap `machine.reset_cause()` / `machine.wake_reason()`. |
| `panic(reason=None)` | str | Prints `[CPU PANIC]` and resets the device. |
| `chip_temp()` | — | Returns `esp.raw_temperature()` or `None` if unavailable. |

#### `dewrapper`

A tiny static-method text wrapper over the `zfs` module.

| Member | Signature | Description |
|---|---|---|
| `read(path)` | str | Returns `zfs.read(path)` decoded as UTF-8. |
| `write(path, text)` | str, str | Encodes `text` as UTF-8 and calls `zfs.write`. |
| `lines(path)` | str | Returns non-blank, stripped lines of a file. |
| `records(path)` | str | Returns each line split on the `"###"` delimiter. |

#### Exceptions

`PermissionError`, `FileNotFoundError`, `FileExistsError`,
`NotADirectoryError` — plain `Exception` subclasses used throughout
`FileManager` (shadow the built-in names of the same purpose).

#### `SystemPrivilege`

A context-manager gate that lets trusted kernel code perform root-gated
operations independent of interactive Super Mode state. **Not a hard
security boundary** (single interpreter, no process isolation).

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(token, reason="system operation")` | Raises `PermissionError` if `token` doesn't match the internal `_SYSTEM_TOKEN`. |
| `__enter__` / `__exit__` | — | Increments/decrements a class-level active-depth counter. |
| `active()` *(classmethod)* | — | Returns `True` if any `SystemPrivilege` context is currently active. |

#### `usermanager`

Manages the single on-device user account, persisted (encrypted-adjacent, in
plaintext JSON) under `OS/users/userinfo.json` on the `zfs` partition.

| Method | Parameters | Returns | Exceptions | Description |
|---|---|---|---|---|
| `userinfo()` | — | `dict` (without password) | — | Public read of the stored user record. |
| `removeuser(name)` | `name` (str) | — | — | Deletes the user record if `name` matches the current root-flagged user; otherwise prints an error. |
| `is_session_root()` | — | `bool` | — | The only check permission logic should call: true if elevated this session, or inside a `SystemPrivilege` block. |
| `elevate(user, password)` | str, str | — | — | Verifies credentials; on success, sets session-root and (once) persists `root: True`. |
| `delevate(user, password)` | str, str | — | — | Verifies credentials and clears session-root. |
| `isrooted(user)` | str | `bool` | — | True only if `user` matches the account **and** is elevated this session. |
| `change_password(user, old_password, new_password)` | str×3 | `bool` | — | Requires the current password; updates the stored password. |
| `change_username(user, password, new_username)` | str×3 | `bool` | — | Requires the current password; updates the stored username (note: reverts on next `zeno.user` resync unless `zeno.py` is also updated). |
| `rebuild(system_token=None)` | token | `bool` | `PermissionError` if token invalid; `ProcessError` if write verification fails | Recreates `userinfo.json` from scratch using `zeno.user`/`zeno.password`. |
| `current_user()` | — | str | — | Public, unprivileged accessor for the current username. |

#### `FileManager`

A permissioned virtual-filesystem facade over MicroPython's `os` module.
Apps must go through this rather than touching `os`/`open()` directly.
Metadata (owner/permission/type/size) for each directory is mirrored as JSON
under `/.sys/...`.

| Method | Parameters | Returns | Exceptions | Description |
|---|---|---|---|---|
| `exists(path)` | str | `bool` | — | Whether a path exists. |
| `metadata(path)` | str | `dict` (`owner`, `permission`, `type`, `size`) | `FileNotFoundError` | Returns stored/scanned metadata for a path. |
| `listdir(path="/", show_hidden=False)` | str, bool | `list[str]` (sorted) | `FileNotFoundError`, `NotADirectoryError` | Lists a directory, syncing the metadata cache to the real filesystem contents. Requires read permission. |
| `create(path, content="", owner=None, permission=None)` | str, str, str, int | `bool` | `FileNotFoundError` (parent missing), `FileExistsError`, `ValueError` (bad permission) | Creates a new file with content. |
| `mkdir(path, owner=None, permission=None)` | str, str, int | `bool` | same as `create`, plus `FileExistsError("root already exists")` for `"/"` | Creates a new directory (and its metadata mirror). |
| `delete(path)` | str | `bool` | `PermissionError` (root), `FileNotFoundError` | Recursively deletes a file or directory, including its metadata/mirror files. |
| `rename(path, new_name)` | str, str | `bool` | `ValueError` (would change directory), `FileNotFoundError`, `FileExistsError` | Renames within the same parent directory. |
| `move(src, dst)` | str, str | `bool` | `FileNotFoundError`, `FileExistsError` | Moves an entry to a different directory (delegates to `rename` if same parent). |
| `copy(src, dst)` | str, str | `bool` | `FileNotFoundError`, `FileExistsError` | Recursively copies a file or directory tree, preserving owner/permission. |
| `chmod(path, permission)` | str, int | `bool` | `ValueError`, `PermissionError` (root cannot be chmod'd), `PermissionError` (not owner/root) | Sets an entry's permission bits. |
| `chown(path, new_owner)` | str, str | `bool` | `PermissionError` (root path, or caller not root) | Changes an entry's owner. |
| `refresh_tree(path="/", system_token=None)` | str, token | `int` (entries refreshed) | `PermissionError` (not root, unless valid `system_token`) | Rebuilds the metadata tree recursively from the real filesystem. |
| `open(path, mode="r")` | str, str | `int` (file descriptor) | `FileNotFoundError`, permission errors | Opens a file, auto-creating it for write modes if missing; tracks descriptors in an internal table. |
| `read(fd, size=-1)` / `write(fd, data)` / `close(fd)` | int, ... | data / count / `bool` | `ValueError` (bad fd) | Standard descriptor-based I/O over the internal handle table. |

#### `Logger`

| Member | Signature | Description |
|---|---|---|
| `LEVELS` | `{0: "ERROR", 1: "WARNING", 2: "DEBUG"}` | Log level names. |
| `__init__` | `(log_file_user="/LOGS/systemlog.txt", boot=False)` | Opens an I2C `DS3231` RTC; creates the log file; if `boot=True`, writes a `[BOOT_START]` marker. |
| `log(level, message, source="GENERAL")` | int, str, str | Writes a formatted `[SRC:...] [LEVEL] message` line. |
| `error(message, source="GENERAL")` / `warning(...)` / `debug(...)` | str, str | Convenience wrappers around `log()`. |
| `boot_complete()` | — | Marks the end of a boot sequence in the log. |
| `viewlogs(lines=None)` | int, optional | Prints log lines since the most recent `[BOOT_START]` marker, optionally limited to the last `lines`. |
| `clear_logs()` | — | Truncates the log file. |

#### `Disk`

SD card controller (SPI-attached) for mass storage.

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(mount_point="/MemDisk")` | — | Configures the SPI bus and CS pin for the SD card. |
| `check(retries=5, delay=0.2)` | int, float | `bool` | Polls whether the mount point is accessible, retrying with a delay. |
| `begin()` | — | `bool` | Initializes the `SDCard` object and mounts it; falls back to `check()` if mount raises but the path still resolves. |
| `unmount()` | — | `bool` | Unmounts the SD card. |
| `format(filesystem=os.VfsFat)` | filesystem class | `bool` | Unmounts, formats via the given VFS class, and re-mounts. Requires the SD object to already be initialized. |
| `info(path=None)` | str, optional | `None` (prints) | Prints total/free space for the given path (or the mount point). |

#### `BootConfig`

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | — | — | Loads (or creates with defaults) `/LOGS/bootcfg.json`. Defaults: `BOOT_MODE="NORMAL"`, `OPT_LEVEL=0`, `WIFI_AUTOCONNECT=True`, `SHOW_UI=True`, `KERNEL_PATH="/SYSTEM32/Admin/ROM/kernel.py"`, `LOGGER_STATUS="ENABLED"`, `LOG_REPL="ENABLED"`, `MODE="PERFORMANCE"`. |
| `save()` | — | Writes the current config dict to disk. |
| `get(key, default=None)` | str | Returns a config value. |
| `set(key, value)` | str, any | Sets a config value and saves immediately. |
| `show()` | — | Prints all current config entries. |

`cfg_get(cfg, *keys)` — module-level helper: returns the first present key's
value from a dict given multiple candidate key names.

#### `Process` (Process Control Block)

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(pid, ppid, owner, name, func, mode, period, priority)` | Fixed-slot record holding scheduling state and runtime metrics (`avg_us`, `min_us`, `max_us`, `last_us`, `samples`). |
| `weight()` | — | Returns the scheduling weight for the process's `priority` (nice value), via `_weight()`. |
| `as_row()` | — | Formats a fixed-width table row for `ps`-style listing. |

#### `Scheduler`

A cooperative CFS-style ("Completely Fair Scheduler"-inspired) task
scheduler with optional real-thread ("thread mode") tasks, PID classification
by process type, and owner-based signal permission.

| Method | Parameters | Returns | Exceptions | Description |
|---|---|---|---|---|
| `__init__` | `(logger=None)` | — | — | Sets up the process table and loads persisted per-task timing stats from `/LOGS/proc_state.json`. |
| `spawn(name, func, *, mode=MODE_LOOP, period=0, priority=0, owner=None, expected_us=None, ptype=None)` | see params | `int` (PID) | `ValueError` (bad mode, or daemon-series without `MODE_THREAD`), `ProcessError` (`_thread` unavailable) | Registers a new process; daemon-series (`4xxx`) PIDs **must** use `MODE_THREAD`. |
| `kill(pid, sig=SIGTERM, system_token=None)` | int, int, token | `bool` | `PermissionDenied` (SIGKILL on a protected daemon; caller lacks permission) | Signals a process. `SIGKILL` on non-thread processes marks it a zombie immediately; `SIGTERM` sets a pending signal for cooperative shutdown. |
| `should_die(pid)` | int | `bool` | — | True if the process has a pending `SIGTERM`/`SIGKILL`. |
| `checkpoint(pid)` | int | — | Raises `SystemExit` if a termination signal is pending | Cooperative checkpoint a long-running task should call periodically. |
| `wait(pid, timeout_ms=None)` | int, int | exit code or `None` | — | Blocks (polling) until the process reaches `ZOMBIE`/`DEAD`, then reaps it. |
| `nice(pid, priority, system_token=None)` | int, int, token | `bool` | `ProcessError` (no such pid), `PermissionDenied` | Changes a process's priority, clamped to `NICE_MIN`/`NICE_MAX`. |
| `getpid()` | — | int or `None` | — | PID of the currently executing task. |
| `list()` | — | `list[int]` (all PIDs) | — | Prints a `ps`-style table and returns all PIDs. |
| `tick()` | — | `bool` | — | Runs one cooperative task per call, picking the lowest-`vruntime` runnable process (CFS-style). |
| `reap(pid)` | int | `bool` | — | Removes a `ZOMBIE` process from the table. |
| `start(frame_ms=16)` | int | — | — | Runs the scheduler main loop: ticks cooperative tasks within a frame budget, sleeps out any remaining idle time, reports frame stats to `CPU`, persists state. |
| `stop()` | — | — | Stops the main loop (sets `running = False`). |
| `killall(system_token=None)` | token | — | never raises | Best-effort `SIGTERM` to every non-daemon process (used on the boot-failure/reboot path). |
| `log_misuse(p, sig, reason)` | `Process`, int, str | — | — | Centralized logging point for every rejected/blocked signal attempt. |

**Exceptions:** `ProcessError(Exception)`, `PermissionDenied(ProcessError)`.

#### `system`

Low-level system control: RAM/security housekeeping and a background
"guardian" daemon.

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(opt_level=0, debug=False)` | — | Creates a `Logger` and `BootConfig`. |
| `restart()` | — | — | `machine.reset()`. |
| `optlevel(level)` | int | — | Sets `micropython.opt_level(level)`. |
| `info()` | — | — (prints) | Prints version, CPU, RAM, unique ID, and disk stats. |
| `memconfig(percent=25)` | int | — | Runs `gc.collect()` and sets a GC threshold as a percentage of currently free memory. |
| `force_mem()` | — | — | Forces a garbage collection, logging the memory reclaimed. |
| `mem_usage()` | — | — (prints) | Prints total/used/free memory with percentages. |
| `perf_test()` | — | — | Runs the Pystone CPU benchmark, a RAM allocation test, and a flash write/read test, logging timings. |
| `mode(m)` | str (`PERF`/`BAL`/`SAVE`/etc.) | — | Sets a named performance mode, updates optimization level, and reboots. |
| `ram_guard(warn_pct=80, crit_pct=92)` | int, int | `float` (used %) | Threshold-gated: only collects/logs when usage crosses `warn_pct`, escalates message at `crit_pct`. |
| `security_scan()` | — | `list[str]` (findings) | Checks kernel auth flags, `/.sys` presence, and process-count sanity; logs any findings. |
| `checkup(mem_warn_pct=80, mem_crit_pct=92)` | ints | `dict` (`mem_used_pct`, `security_findings`) | Combines `ram_guard()` + `security_scan()`. |
| `start_guardian(sched, interval_ms=10_000)` | `Scheduler`, int | `int` (PID) | Spawns a root-owned, thread-mode daemon that periodically calls `checkup()`. |
| `firmware_update()` | — | — | Backs up `firmware.py` (and a "stable" copy), then reboots. |
| `boot_update()` | — | — | Backs up `boot.py`, then reboots. |

#### `Network`

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(ssid=None, password=None, timeout=15)` | — | Defaults SSID/password from `zeno.ssid`/`zeno.wifi_password`. |
| `connect()` | — | `bool` | Connects Wi-Fi (station mode), polling status until connected, a fatal status, or `timeout` seconds elapse. |
| `scan()` | — | list of scan results (also printed) | Wi-Fi network scan. |
| `disconnect()` | — | — | Disconnects and deactivates the interface. |
| `isconnected()` | — | `bool` | Wraps `wlan.isconnected()`. |
| `ifconfig()` | — | tuple | Wraps `wlan.ifconfig()`. |

#### `downloadhelper`

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | — | — | Creates a `Logger`. |
| `download_file(url, save_dir="/", save_file=None)` | str, str, str | `str` (saved path) or `None` | Raw-socket HTTP/HTTPS GET download (normalizes the URL scheme, resolves DNS, opens a raw or SSL-wrapped socket, streams the body to disk in 512-byte chunks). Returns `None` on any failure (all failures are logged, not raised). |

#### `Git`

GitHub raw-content download/upload helper.

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(base_raw=None, default_branch="main")` | — | `base_raw` defaults to `https://raw.githubusercontent.com`; token comes from `zeno.gitsecret`. |
| `download_url(url, save_dir=None)` | str, str | `bool` | Parses a `github.com` or `raw.githubusercontent.com` URL and downloads it. |
| `download(user, repo, filename, branch=None, save_dir=None)` | str×3, str, str | `bool` | Downloads `filename` from `user/repo@branch` via the raw-content CDN. |
| `upload(user, repo, local_path, repo_path=None, branch=None, message="Upload from ESP32")` | strs | `bool` | Uploads/updates a file via the GitHub Contents API (base64-encodes content, fetches existing SHA if present, then PUTs). Requires `zeno.gitsecret`. |

#### `BluetoothManager`

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(device_name="Zeno Micro PC")` | — | Wraps `ubluetooth.BLE()`, starts inactive. |
| `on()` / `off()` | — | — | Activates/deactivates BLE and (on `on()`) starts advertising. |
| `search(duration=5)` | int | `list` of `(addr_type, addr, adv_type, rssi, adv_data)` | Performs a BLE scan for `duration` seconds. |
| `connect(addr_type, addr)` | — | — | Initiates a GAP connection. |
| `disconnect()` | — | — | Disconnects the current connection. |
| `send_data(data)` | bytes/str | — | Sends a GATT notification if connected. |
| `get_data()` | — | `bytes` or `None` | Pops and returns any buffered received data. |

#### `AppInstaller`

Installs/uninstalls apps from the `Zeno-Micro-PC` GitHub repo's `APPS/` folder.

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | — | — | Fixed repo `FerrariForever95/Zeno-Micro-PC`, branch `main`, installs to `/SYSTEM32/APPS`. |
| `prompt_and_install()` | — | `bool` | Prompts for an app name via `input()`, then installs it. |
| `install(app_name)` | str | `bool` | Downloads `APPS/<app_name>.py` into the apps directory. |
| `uninstall(name)` | str | — | Removes `/SYSTEM32/APPS/<name>.py`. |
| `listapps()` | — | — (prints) | Prints installed `.py` app names. |

#### `Wiki`

A line-buffered Wikipedia summary/search reader (paginated `print`-based output).

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(lang="en", width=60, lines=10, out=print)` | — | `out` is the output sink (defaults to `print`, can be redirected e.g. to a UI text box). |
| `fetch(title, preview_dots=3)` | str, int | `None` (prints via `out`) | Fetches a page summary, word-wraps it to `width`, and prints an initial preview (stopping at `preview_dots` sentences or `lines` lines). |
| `next()` | — | `None` (prints) | Prints the next `lines`-sized page of the buffered article. |
| `search(query, n=5)` | str, int | `None` (prints) | Prints up to `n` matching page titles. |

#### `AppDB`

A tiny per-app JSON key-value store shared by all apps
(`/SYSTEM32/APPS/Data/appdb.json`).

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `set(app, key, value)` | str, str, any | — | Sets and persists a value under `app`/`key`. |
| `get(app, key, default=None)` | str, str, any | any | Retrieves a value. |
| `delete(app, key)` | str, str | — | Removes a key (and the app entry if now empty). |
| `clear(app)` | str | — | Removes all data for an app. |
| `dump()` | — | `dict` | Returns the entire store. |

#### `PackageManager`

GitHub-catalog-driven package installer, backed by `pkgtable.json` (remote
catalog) and `/pkglist.json` (local install record).

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(git=None, repo_user=None, repo_name=None)` | — | Defaults repo to `FerrariForever95/Zeno-Micro-PC`. Requires root/Super Mode for mutating operations. |
| `install(name, force=False)` | str, bool | `bool` | Resolves dependencies and required modules (auto-installing packages that provide missing modules), downloads, and records the package. Refuses to reinstall an already-installed package unless `force=True`. |
| `uninstall(name)` | str | `bool` | Refuses to remove packages flagged `core` or with an unsafe/empty `install_path`; recursively removes the install directory. |
| `reinstall(name)` | str | `bool` | Atomic uninstall + `install(name, force=True)` sharing one catalog fetch. |
| `update(name=None)` | str or `None` | `bool` | Updates one package, or all installed packages if `name` is `None`. |
| `run(name, *args)` | str, args | `bool` | Executes an installed package's file with `argv` set to `args`. |
| `info(name)` | str | dict/None (prints) | Prints installed + catalog metadata for a package. |
| `list()` | — | `list[str]` (prints too) | Lists installed package names/versions/authors. |
| `verify()` | — | `dict` (issues per package) | Checks that each installed package's file and required modules are present. |
| `check(module)` | str | — | Looks up whether a module name is provided by a known package (implementation continues past the shown excerpt). |

#### `Device`

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(device_id, name, obj, pin=None)` | Metadata record for one registered IoT device (`state` tracked locally, since SinricPro exposes no state getter). |
| `__repr__` | — | `<Device 'name' id=... state=ON/OFF>` |

#### `IoTManager`

Coordinates smart-home devices through **Sinric Pro**.

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(app_key, app_secret)` | — | Creates a `SinricPro()` client. |
| `add_switch(device_id, name, pin_number=None, custom_callback=None)` | str, str, int, callable | `SinricProSwitch` | Registers a switch device, optionally bound to a hardware `Pin`; wires a cloud power-state callback that also drives the pin and calls `custom_callback`. |
| `remove_device(identifier)` | str (ID or name) | `bool` | Unregisters a device. |
| `list_devices()` | — | `list[Device]` | All currently registered devices. |
| `on(identifier)` / `off(identifier)` | str | `bool` | Turns a device on/off by ID or friendly name. |
| `toggle(identifier)` | str | `bool` | Flips a device's last known (locally tracked) state. |
| `start()` | — | — | Connects the SinricPro client using `app_key`/`app_secret`. |
| `handle()` | — | — | Pumps the client's network loop; raises `AttributeError` with a detailed explanation if the installed SinricPro build has no public `handle()` method. |

---

### 3.4 `pwrmanagement.py`

A standalone CPU frequency/power-scaling service, independent of
`Services.Scheduler`. Frequency changes go through `machine.freq()`.

#### Module-level constants

| Constant | Description |
|---|---|
| `_PLATFORM_LEVELS` | Per-platform named frequency tiers in Hz, e.g. `esp32: {low: 80MHz, normal: 160MHz, high: 240MHz, turbo: 240MHz}`, `rp2: {low: 48MHz, normal: 125MHz, high: 200MHz, turbo: 250MHz}`. |
| `_LEVEL_ORDER` | `("low", "normal", "high", "turbo")` — ordering used to resolve the highest currently-requested tier. |

#### `PowerManagement`

| Method | Parameters | Returns | Description |
|---|---|---|---|
| `__init__` | `(logger=None)` | — | Builds the tier table for the detected platform (`sys.platform`); unknown platforms fall back to a single tier at the current frequency. |
| `help()` | — | — (prints) | Prints shell-style usage for the `power` module. |
| `status()` | — | `dict` (`platform`, `current_hz`, `requests`) | Prints and returns current frequency and active boost requests. |
| `levels_list()` | — | `dict` | Prints and returns available named tiers and their Hz values. |
| `set_level(level)` | str | `bool` | Pins the CPU to a tier immediately, **ignoring** active boost requests (manual/debug use — prefer `boost()`/`release()`). |
| `baseline_set(level)` | str | `bool` | Changes the idle/default tier that `release()` falls back to. |
| `boost(reason, level="high")` | str, str | `bool` | Reference-counted: requests a tier under `reason`; the highest requested tier across all reasons wins. |
| `release(reason)` | str | `bool` | Drops a boost request; falls back to the next-highest remaining request or the baseline. |
| `boosted(level="high", reason="context")` | str, str | `_BoostContext` | Context manager: `with power.boosted(): ...` boosts for the block's duration and always releases afterward. |
| `auto_scale(load_percent, reason="auto")` | float or `None` | — | Convenience: boosts to `"high"` at ≥70% load, `"normal"` at ≥40%, else releases. |

#### `_BoostContext`

Backing object for `PowerManagement.boosted()` (plain class, no `contextlib`
dependency).

| Member | Signature | Description |
|---|---|---|
| `__init__` | `(power, level, reason)` | — |
| `__enter__` | — | Calls `power.boost(reason, level)`. |
| `__exit__` | — | Calls `power.release(reason)`; never swallows exceptions. |

---

### 3.5 `ZenCMD.py` (interactive shell)

The current shell entry point, **ZenCMD version `"3.81"`** (`ZENOS_NAME =
"Zeno OS"`). Runs a REPL that parses statements separated by `;` and
pipelines separated by `|`.

#### `Recovery` (`recovery.py` / `ZenCMD.py`)

A dependency-free class embedded at the top of `ZenCMD.py`, intentionally
never importing anything from `/Services`, so it keeps working even if
`Services`, `PackageManager`, `Git`, `Network`, or `zeno.py` are missing or
corrupted. Uses only built-in MicroPython modules (`os`, `json`, `time`,
`urandom`, and guarded `network`/`urequests`).

| Member | Signature | Description |
|---|---|---|
| `PKGTABLE_URL` | `"https://raw.githubusercontent.com/FerrariForever95/Zeno-Micro-PC/main/pkgtable.json"` | Remote package catalog URL. |
| `PKGLIST_PATH` | `"/pkglist.json"` | Local install record path. |
| `ZENO_PATH` | `"/zeno.py"` | Path of the generated runtime-state module. |
| `ZENO_TEMPLATE` | str template | Template used to (re)generate `zeno.py` with `password`, `user`, `gitsecret`, `ssid`, `wifi_password` substituted in. |
| `__init__` | — | — | Resets in-memory credentials/results state. |
| `help()` | — | — (prints) | Shell-style usage line for the `recover` command. |
| `run()` | — | `bool` | Full recovery flow: reads existing Wi-Fi creds from `zeno.py` (or prompts if missing), connects Wi-Fi, downloads `pkgtable.json`, restores every package flagged `"core": true`, and — if `zeno.py` didn't already exist and nothing failed — writes a fresh one from `ZENO_TEMPLATE`. Returns `True` on full success. |

Private helpers (`_prompt_all`, `_prompt_wifi_only`, `_file_exists`,
`_read_zeno_wifi`, `_extract_assignment`, `_write_zeno_py`, `_connect_wifi`,
`_download_pkgtable`, `_http_get_text`, `_raw_url`, `_mkdirs`, `_full_path`,
`_write_and_verify`, `_file_is_healthy`, `_load_pkglist`, `_save_pkglist`,
`_restore_package`) implement this flow and are not intended as public API.

#### Version / configuration constants

| Constant | Value | Description |
|---|---|---|
| `ZENCMD_VERSION` | `"3.81"` | Shell version string (recovery.py's bundled copy reports `"2.2.0"`). |
| `ZENOS_NAME` | `"Zeno OS"` | OS name shown in the banner/prompt. |
| `PRIVILEGED_PREFIXES` | tuple of command words | Commands requiring **Super Mode**, matched as prefixes against the bare command/method name: `bootmgr`, `mount`, `umount`, `unmount`, `format`, `mkfs`, `shutdown`, `reboot`, `factory`, `removeuser`, `elevate`, `delevate`, `service`, `reload`, `reloadmodule`, `kernel`, `driver`, `pkg`, `install`, `remove`, `uninstall`, `reinstall`, `update`, `mountzfs`, `bootlog`. `recover` is deliberately **excluded** so it remains usable even when Super Mode itself is unavailable. |

#### Module registry

`_load_services()` builds `MODULES`, a `dict` of shell-enterable modules,
including only those that loaded successfully:

| Shell name | Backing class |
|---|---|
| `net` | `Services.Network` |
| `disk` | `Services.Disk` |
| `downserv` | `Services.downloadhelper` |
| `system` | `Services.system` |
| `log` | `Services.Logger` |
| `git` | `Services.Git` |
| `bootmgr` | `Services.BootConfig` |
| `bluetoothmgr` | `Services.BluetoothManager` |
| `pkg` | `Services.PackageManager` |
| `ps` | `Services.Scheduler` |
| `iot` | `Services.IoTManager` |

#### Built-in shell commands

`BUILTIN_HELP` documents every built-in; the most relevant are summarized
here (full text is shown verbatim by `help` / `help <cmd>`):

| Category | Commands |
|---|---|
| Navigation | `pwd`, `cd`, `ls` (`dir` alias), `tree`, `mkdir`, `rmdir`, `rm`, `cp`, `mv`, `touch` |
| File ops | `cat`, `head`, `tail`, `search` (`grep` alias), `echo`, `stat`, `file`, `find`, `which`, `whereis` |
| System | `whoami`, `id`, `hostname`, `date`, `time`, `uptime`, `version`, `df`, `du`, `free`, `memdebug`, `ps`, `kill`, `jobs`, `sync` |
| Environment | `env`, `export`, `alias`, `unalias`, `history`, `clear` (`cls` alias) |
| Zeno-specific | `super`, `unsuper`, `passwd`, `chusername`, `userdebug`, `whoisroot`, `modules`, `enter`, `leave`, `sysrun`, `pkgrun`, `service`, `services`, `reload`, `reloadmodule`, `mountzfs`, `bootlog`, `log`, `shutdown` *(Super)*, `reboot` *(Super)*, `factory` *(Super)* |
| Recovery | `recover` — always available, even with a broken `/Services` |
| Chaining | `;` (statement separator), `\|` (pipeline, e.g. `cat /LOGS/systemlog.txt \| search ERROR`) |

Built-in default aliases: `dir → ls`, `cls → clear`, `q → exit`, `grep →
search`.

#### Key module-level functions

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `_is_super()` | — | `bool` | Whether the current session is elevated (via `usermanager.isrooted`). |
| `_require_super(cmd_word)` | str | `bool` | Prints an "Access denied" message and returns `True` (meaning "skip") if `cmd_word` matches a privileged prefix and the session isn't elevated. |
| `_prompt()` | — | str | Builds the shell prompt string, reflecting current path, user, Super Mode, and active module. |
| `_normalize_path(path)` | str | str | Collapses `.`/`..`/repeated slashes into a clean absolute path (enables `cd ..`, `cat ../x.txt`, etc.). |
| `handle(raw)` | str | — | Top-level entry point: splits `raw` on `;`, logs each statement to history, and executes it (with `|` piping) via `_run_statement`. |
| `resolve_program(name, cwd)` / `run_python_file(path)` | str, str | — | Resolve and execute a `.py` program file. |
| `list_dir(path, long=False)` / `tree_dir(path, prefix="")` | str, bool | — | Directory listing helpers backing `ls`/`tree`. |

The module runs a `while True:` REPL at import time, printing the ZenCMD
banner, reading lines via `input(_prompt())`, and calling `handle(line)`,
catching `SystemExit` (clean exit), `KeyboardInterrupt` (prints `^C`), and
other exceptions (logged and printed, loop continues).

---

### 3.6 `recovery.py`

A **standalone snapshot** of the full `ZenCMD.py` shell (same `Recovery`
class and the entire command/shell implementation), reporting
`ZENCMD_VERSION = "2.2.0"`. It exists as a self-contained fallback copy — see
[Notes](#notes-and-limitations) for guidance on which file is authoritative.
Its public surface is identical to [§3.5](#35-zencmdpy-interactive-shell)
and is not repeated here.

---

### 3.7 `Home/OS/` boot scripts

Three successive/alternate versions of the graphical home-screen boot
sequence. **These are not reusable modules** — each is a top-level script
that runs its setup code and a `while True:` loop immediately on import/exec,
and each depends on a different, non-interchangeable UI object API (see
[Notes](#notes-and-limitations)).

#### `kernel.py`

Uses `zeno.ui` (an object exposing `.black`/`.white`/`.blue` colors,
`.tft`, `.on()`, `.fade_in()`, etc.) together with `Graphics.UIScreen` /
`UIText` / `UIButton` / `DialogBox` / `UIBMPButton` / `UITextBoxView` /
`color565`.

| Member | Signature | Description |
|---|---|---|
| `log(msg)` | str | Prints a `[SCHED]`-tagged debug line. |
| `Task` | `__init__(name, func, *, mode, period=0, expected_us=None)` | A lightweight task record (name/func/mode/period + timing metadata), distinct from `Services.Process`. |
| `TaskManager` | `__init__(cpu)` | A simple cooperative task runner (loop/periodic modes, boot-time queues with first/normal/last ordering, EWMA-smoothed timing stats persisted to `/LOGS/task_state.json`). |
| `TaskManager.run(name, func, *, mode, period=0, expected_us=None)` | — | `Task` | Registers a task; raises `ValueError` if `name` already exists. |
| `TaskManager.create_queue(qname)` / `queue_add(qname, task_name, *, position="normal")` | — | Builds named boot-sequencing queues. |
| `TaskManager.start()` | — | Runs boot queues to completion, then the frame-budgeted main loop (`loop`/`periodic` tasks), reporting frame stats to `CPU` and persisting state each frame. |
| `TaskManager.delete_task(name)` | str | `ValueError` if missing | Removes a task from all queues and the table. |
| `TaskManager.clean_memory()` / `memory_usage()` | — | `gc.collect()` / percentage of an assumed ~8 MB heap. |
| `CPU` | (duplicate of `Services.CPU`) | Same interface as `Services.CPU` (see §3.3). |
| `AppExit` | `Exception` | Raised by an app to signal "return to the home screen". |
| `launch_app(name)` | str | Executes `/SYSTEM32/APPS/<name>.py` in a fresh globals dict, catching `AppExit` (redraw home) and other exceptions (print traceback, redraw home). |
| `confirmed()` / `cancelled()` / `show_power()` | — | Power-dialog handlers: shutdown vs. cancel. |
| `redraw_home()` | — | Rebuilds the taskbar and the app-icon grid from `/SYSTEM32/APPS` + matching `LOGO/*.bmp` files. |
| `kernel_ui_task()` | — | Per-frame task: handles power-button/app-icon touches; triggers `clean_memory()` above a 5% memory-usage threshold. |
| `network_autoretry_task()` | — | Per-30s task: reconnects `zeno.net` if not connected and not already attempting to connect. |

#### `kernel1.py`

A refined variant of `kernel.py`. Requires a valid `zeno.boot_cap` integer
capability (consumed/cleared on load) and imports UI classes from a
`firmware` module rather than `Graphics` directly.

| Member | Signature | Description |
|---|---|---|
| `cleanup()` | — | Deinitializes the display/network, prunes `sys.modules` down to a fixed `KEEP` allow-list, and forces GC — used before a shutdown/reboot. |
| `AppExit` | `Exception` | Same purpose as in `kernel.py`. |
| `launch_app(name)` | str | Same behavior as `kernel.py`'s version, but calls `redraw_home()` unconditionally in `finally`. |
| `confirmed()` / `cancelled()` / `show_power()` | — | Power dialog handlers; `confirmed()` also calls `cleanup()` before `cpu.shutdown()`. |
| `redraw_home()` | — | Same app-grid rebuild as `kernel.py`. |

#### `safe.py`

The oldest variant: imports `HUIModule`, `UIScreen`, `UIText`, `UIButton`,
`DialogBox`, `TaskManager`, `CPU`, `Network` from `firmware`, and
`color565` from `ili9341`.

| Member | Signature | Description |
|---|---|---|
| `launch_app(app_name)` | str | Executes `/SYSTEM32/APPS/<app_name>.py`, then unconditionally raises `SystemExit`. |
| `power()` | — | Shows the power/restart dialog. |

The remainder of `safe.py` is a top-level script (not organized into
reusable functions) that builds the home screen, draws app icons, and runs
an infinite polling loop (`ui.get_touch()`, RTC-based taskbar clock,
throttled CPU usage sampling, `tsk.clean_memory()`).

---

### 3.8 `Home/TOOLS/zenpath.py`

A minimal, dependency-free line-protocol patch agent for editing on-device
files from a connected host over stdin/stdout.

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `apply_patch(path, start_line, delete_count, new_text)` | `path` (str), `start_line` (int, 1-based), `delete_count` (int), `new_text` (str) | `None` | Replaces `delete_count` lines starting at `start_line` with `new_text`, via a temp-file-then-rename write for safety. |
| `patch_loop()` | none | — (runs until `QUIT`) | Reads a simple line protocol from `sys.stdin`: `PATCH` → `FILE:<path>` → `REPLACE:<start>:<count>` → replacement lines terminated by `END`. Prints `OK` or `FAIL <error>` per patch, `BYE` on `QUIT`. Runs `gc.collect()` after each patch. |

Entry point: `if __name__ == "__main__": patch_loop()`.

---

### 3.9 `lcd.py`

A raw, hand-written bring-up/test script for the ILI9488 panel — **not**
the driver used by the rest of the OS (that role is filled by `moclcd`).
Configures GPIO pins directly and drives the 8080 bus by hand.

| Function | Parameters | Returns | Description |
|---|---|---|---|
| `write8(v)` | `v` (int, byte) | `None` | Bit-bangs one byte onto the 8-bit data bus (`D0`–`D7`) with a WR strobe. |
| `cmd(v)` | `v` (int) | `None` | Sends a command byte (`RS` low). |
| `data(v)` | `v` (int) | `None` | Sends a data byte (`RS` high). |

Pin assignment matches `moclcd`'s (RST=12, RS=13, WR=14, RD=41, backlight=38,
D0–D7 = 16,15,11,10,9,4,18,17). On import, the script performs a hardware
reset, the ILI9488 bring-up command sequence (SWRESET, SLEEPOUT, COLMOD
RGB565, MADCTL, DISPLAY ON, address window), and then fills the screen with
8 vertical color bars as a visual self-test.

---

### 3.10 `pystone_lowmem.py`

A MicroPython port of the classic Pystone 1.1 CPU benchmark, adapted for
low-memory devices (reduced allocation footprint vs. the original).

| Constant / Function | Signature | Returns | Description |
|---|---|---|---|
| `LOOPS` | `1000` | — | Default iteration count. |
| `pystones(loops=LOOPS)` | int | `float` (pystones/second) | Times `Proc0(loops)` and prints both the elapsed time and the resulting benchmark score. |
| `Proc0(loops)` | int | `(loops, loops)` | Internal benchmark body (string comparisons, arithmetic) run `loops` times. |
| `main(loops=LOOPS)` | int | — (prints) | Prints a banner and runs `pystones(loops)`. |

Entry point: `if __name__ == "__main__": main()`.

---

### 3.11 `Home/APPS/` bundled applications

All apps are top-level scripts, invoked via `exec()` by the home-screen
launcher (`launch_app()`), and expect the shared `zeno` module and `APP_EXIT`
(an `AppExit` exception class) to be present in their execution globals. Each
raises `APP_EXIT` from its `exit()`/`on_exit()` function to return to the
home screen.

#### `Browser.py`

A basic internet search app built on the DuckDuckGo Instant Answer API.

| Member | Signature | Description |
|---|---|---|
| `InternetBrowser` | `__init__(out=print)` | Search client; `out` is the output sink. |
| `InternetBrowser.search(query)` | str | Queries DuckDuckGo's Instant Answer API and prints (via `out`) the abstract/source and up to 5 related-topic snippets, or a "no instant answer found" message. Never raises — network errors are caught and printed. |
| `InternetBrowser.help()` | — | Prints module/method usage description. |
| `exit()` | — | Raises `APP_EXIT`. |
| `main()` | — | Builds the search screen (input box + virtual keyboard + Search button + scrollable result view) and runs the touch-polling main loop. |

Module-level layout/color constants: `BG_COLOR`, `TASKBAR_BG`, `SEARCH_BG`,
`CONTENT_BG`, `BUTTON_BG`, `TEXT_COLOR`, `SEARCH_X/Y/W/H`, `BTN_X/Y/W/H`,
`CONTENT_Y`.

#### `Settings.py`

A pure dispatcher screen that lists settings categories and `exec()`s the
corresponding sub-screen file in place.

| Member | Signature | Description |
|---|---|---|
| `SETTINGS_MAP` | `dict[str, str]` | Maps a display label to a sub-screen file path: `"Wi-Fi and Internet"`, `"Bluetooth"`, `"Display"`, `"Storage"`, `"System"`, `"About Device"` → `/SYSTEM32/APPS/SETTINGS/*.py`. |
| `exit()` | — | Raises `APP_EXIT`. |
| `open_setting(name)` | str | Looks up `name` in `SETTINGS_MAP` and `exec()`s that file; prints an error if the file is missing or fails to load. |
| `main()` | — | Draws a `UIListView` of settings categories; tapping an item calls `open_setting`. |

#### `ZenStore.py`

A minimal app store front-end: search (via on-screen keyboard) → Install /
Uninstall, backed by `Services.AppInstaller`.

| Member | Signature | Description |
|---|---|---|
| `APP_NAME, APP_AUTHOR, APP_VERSION` | `"ZenStore"`, `"Phoenix"`, `"1.0.0"` | App metadata constants. |
| `exit_to_kernel()` | — | Re-execs `/SYSTEM32/OS/kernel.py` to return to the home screen. |
| `confirmed()` / `cancelled()` | — | "No Internet" dialog handlers: connect and launch `Browser.py`, or disconnect. |
| `main(on_exit=exit_to_kernel)` | callable | Builds the store UI (header/content/footer panels, Install/Uninstall/Search buttons) and runs the main loop; wires the virtual keyboard's OK action to capture the typed app name, then calls `AppInstaller.install()`/`.uninstall()`. |

Layout constants: `CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H`.

#### `Paint.py`

A simple finger-paint canvas app with a fixed color palette and eraser.

| Member | Signature | Description |
|---|---|---|
| `APP_NAME` | `"Paint"` | App metadata constant. |
| `exit()` | — | Raises `APP_EXIT`. |
| `get_touch_fixed()` | — | Returns the current touch point adjusted by a fixed `TOUCH_X_OFFSET` (calibration correction), clamped to screen bounds. |
| `in_canvas(x, y)` | ints | `bool` | Whether a point is inside the drawing canvas region. |
| `redraw_palette()` | — | Redraws the color swatch buttons, highlighting the active color. |
| `select_color(c)` / `select_eraser()` | int / — | Sets the active drawing color / enables eraser mode. |
| `clear_canvas()` | — | Fills the canvas with the background color. |

Runs a top-level main loop drawing freehand lines between successive touch
points using `ui.tft.draw_line()`. Palette: black, white, red, green, blue,
yellow, orange, brown, gray (via `ui.<colorname>` constants).

#### `Creeper.py`

A static, auto-generated pixel-art demo screen (drawn entirely with
`screen.layer()` rectangle calls forming a Minecraft-Creeper-like face),
with an idle touch-polling loop and no interactive controls wired up.

| Member | Signature | Description |
|---|---|---|
| `APP_NAME, APP_AUTHOR, APP_VERSION` | `"App"`, `"Phoenix"`, `"1.0.0"` | App metadata constants. |
| `on_exit()` | — | Raises `APP_EXIT`. |
| `main()` | — | Draws the static pixel-art layers, then loops polling (empty) button/slider/toggle lists. |

#### `do.py`

An auto-generated demo screen ("Zeno UI Studio") showcasing a single
pre-configured `UIToggleSwitch`.

| Member | Signature | Description |
|---|---|---|
| `APP_NAME, APP_AUTHOR, APP_VERSION` | `"do*"`, `"User"`, `"1.0.0"` | App metadata constants. |
| `on_exit()` | — | Raises `APP_EXIT`. |
| `main()` | — | Draws a background panel, a text label, and one `UIToggleSwitch` (default `state=True`), then loops handling its touch. |

#### `Home/APPS/SETTINGS/display.py`

Brightness settings sub-screen (exec'd by `Settings.py`).

| Member | Signature | Description |
|---|---|---|
| `back_to_settings()` | — | Re-execs `Settings.py` to return to the settings list. |
| `on_brightness_change(value)` | int (0–100) | Converts the slider value to a 0.0–1.0 fraction and calls `zeno.ui.set_brightness()`. |

Builds a `UISlider` pre-populated from `zeno.ui.get_brightness()` and runs a
polling loop calling `screen.check()` / `brightness_slider.handle_touch()`.

#### `Home/APPS/SETTINGS/wifi.py`

Wi-Fi settings sub-screen (exec'd by `Settings.py`).

| Member | Signature | Description |
|---|---|---|
| `back_to_settings()` | — | Re-execs `Settings.py`. |
| `on_wifi_select(idx, name)` | int, str | Currently only prints the selection (password entry/connect flow is a stated future addition). |
| `toggle_wifi(state)` | bool | On enable: connects `zeno.net`, scans for networks, and populates the list view with found SSIDs; on disable: disconnects and clears the list. |

Builds a `UIToggleSwitch` (initial state from `zeno.net.on`) and a
`UIListView` of nearby networks, running a polling main loop.

---

## Usage Examples

**Bring up the display and draw a UI (via `Graphics.py` / `moclcd`):**

```python
import zeno_gfx as gfx  # Graphics.py

gfx.init_display()                    # 480x320 landscape
gfx.set_touch_handler(my_touch_driver.read)

gfx.fill_screen(gfx.BLACK)
gfx.draw_text8x8(10, 10, "Hello, Zeno!", gfx.WHITE)

btn = gfx.UIButton(20, 40, 120, 32, "Tap me", action=lambda: print("tapped"))
btn.draw()

while True:
    btn.get_touch()
```

**Using the native `moclcd` module directly:**

```python
import moclcd

moclcd.init(width=480, height=320, madctl=0x28)
moclcd.reset()
moclcd.panel_init()
moclcd.backlight_init()
moclcd.backlight_set(0.8)

moclcd.fill_screen(0xF800)          # solid red
moclcd.draw_circle(240, 160, 50, 0xFFFF)
moclcd.draw_text8x8(10, 10, "native draw", 0xFFFF)
```

**Filesystem access via `Services.FileManager`:**

```python
from Services import FileManager

fm = FileManager()
fm.mkdir("/Documents")
fm.create("/Documents/notes.txt", "hello from Zeno OS")
print(fm.listdir("/Documents"))
print(fm.metadata("/Documents/notes.txt"))
```

**Spawning and managing tasks via `Services.Scheduler`:**

```python
from Services import Scheduler, MODE_PERIODIC

sched = Scheduler()

def blink():
    print("tick")

pid = sched.spawn("blinker", blink, mode=MODE_PERIODIC, period=1000)
sched.start(frame_ms=16)   # runs forever; call sched.stop() from another task/thread to end
```

**Temporarily boosting CPU frequency during a heavy operation:**

```python
from pwrmanagement import PowerManagement

power = PowerManagement()
with power.boosted(level="high", reason="download"):
    do_expensive_network_operation()
# frequency automatically falls back afterward
```

**Installing a package from the shell:**

```
user/:$> super
user/:$# pkg install some-app
user/:$# pkg list
```

**Using `zenpath.py`'s patch protocol from a host script (conceptual):**

```
PATCH
FILE:/Home/APPS/do.py
REPLACE:8:1
APP_AUTHOR  = 'NewAuthor'
END
```//sent over the device's stdin while `patch_loop()` is running; the device replies `OK` or `FAIL <reason>`.

---

## Notes and Limitations

- **`recovery.py` vs. `ZenCMD.py`**: both files contain a nearly identical
  `Recovery` class and full shell implementation. `ZenCMD.py` reports
  `ZENCMD_VERSION = "3.81"` while the bundled `recovery.py` snapshot reports
  `"2.2.0"` — `recovery.py` appears to be an older, standalone fallback copy
  rather than a separate module with its own API surface.
- **Multiple, incompatible boot scripts**: `Home/OS/kernel.py`,
  `Home/OS/kernel1.py`, and `Home/OS/safe.py` are three different
  generations of the home-screen boot sequence. They are **not
  interchangeable**: `kernel.py`/`kernel1.py` assume a `zeno.ui` object with
  attributes like `.black`, `.white`, `.blue`, `.tft`, `.fade_in()`, while
  `safe.py` constructs its own `HUIModule` UI object directly. Neither
  matches the `Graphics.py` module-function style (`gfx.fill_rect(...)`)
  used by the bundled apps — callers should determine which boot script and
  UI convention is actually active on a given build before reusing code
  across them.
- **`VirtualKeyboard.calibrated_keys`** is a fixed touch-coordinate table
  tuned for a specific screen resolution/orientation. The source explicitly
  warns that after switching to landscape, `VKTouchCalibrator` must be
  re-run to regenerate valid coordinates before relying on touch input.
- **`SystemPrivilege`** (in `Services.py`) is explicitly documented in the
  source as *not* a hard security boundary — it is a single-interpreter,
  no-process-isolation seam between trusted and untrusted code paths, at the
  same trust tier as the rest of the permission model.
- **`IoTManager.handle()`** raises `AttributeError` by design on the
  currently installed SinricPro build, since it exposes no public `handle()`
  method — the source flags this as needing verification against the
  installed SinricPro API (`_process_publish_queue()` /
  `_process_received_queue()`, or an asyncio-driven loop).
- **Credentials handling**: `Recovery` and `ZenCMD`'s Wi-Fi/user setup
  prompts collect plaintext credentials via `input()` and store them only in
  RAM until written to the generated `zeno.py`; `Services.usermanager`
  stores the account password in plaintext JSON (`userinfo.json`) on the
  `zfs` partition.
- **Network operations do not raise on failure**: `downloadhelper.download_file`,
  `Git.download`/`upload`, and `Wiki.fetch`/`search` all catch and log/print
  errors internally, returning `None`/`False` rather than propagating
  exceptions — callers must check return values, not rely on exception
  handling.
- **`moclcd.fill_rect`/`.blit`** raise/require in-bounds input, while
  `moclcd.draw_line`/`draw_rect`/`draw_circle`/`fill_circle`/`draw_pixel`
  clip silently — this asymmetry is intentional per the module's own header
  comment and is preserved by `Graphics.py`'s safe wrappers (`fill_rect`,
  `blit`) which add their own clipping.
- **Excluded from this document**: `Home/APPS/Files.py` and
  `bin/banner/banner.py`, per request. `firmware.mpy` (pre-compiled bytecode)
  and `ili9488_reference.zip` (reference material) were not documented, as
  their contents are not readable Python/C source. The `Home/Downloads/`
  and `builder scipts to flash/` directories contain unrelated user data and
  shell build/flash tooling, respectively, and fall outside the scope of an
  API reference.
