# 01 — Cartridge Image, File System & Compression

## 1. LNX container

The image is a standard Lynx "LNX" file: a 64-byte header followed by the raw cartridge body.

| Offset | Size | Field | Value in this image |
|---|---|---|---|
| 0 | 4 | Magic | ASCII `LYNX` |
| 4 | 2 | Bank 0 page size (LE) | `0x0200` (512-byte pages) |
| 6 | 2 | Bank 1 page size (LE) | `0x0000` (no bank 1) |
| 8 | 2 | Format version (LE) | `1` |
| 10 | 32 | Cart name, NUL-padded | `chipchal.lnx` |
| 42 | 16 | Manufacturer, NUL-padded | `Atari` |
| 58 | 1 | Rotation | 0 (none) |
| 59 | 5 | Reserved | 0 |

Cartridge body: **131 072 bytes** (256 pages × 512 bytes). All "cart offsets" in these documents are relative to the start of the body (file offset 64).

An extractor should also accept a *headerless* 128 KiB body (detect by the absence of `LYNX` magic).

## 2. Cartridge addressing (background)

The Lynx reads the cartridge through a byte port with an auto-incrementing in-page counter and a separately latched page number. With 512-byte pages, the linear cart offset of a byte is simply `page × 512 + offset_in_page`, and sequential reads that run off the end of a page continue at offset 0 of the next page. **For the reimplementation this means the cartridge is just a flat 128 KiB byte array.**

## 3. Boot chain (informational — the reimplementation can ignore it)

| Cart range | Content | Notes |
|---|---|---|
| `0x0000–0x00FF` | Encrypted boot block 1 | First byte `0xFB` = 256−5 → five 51-byte blocks. Decrypted by the Lynx's internal boot ROM into a 250-byte stage-1 loader. |
| `0x0100–0x01FF` | Encrypted boot block 2 | Same scheme, a second 250-byte stage (generic Atari cartridge-checking loader). It hashes the cartridge and refuses to continue on mismatch. |
| `0x0200–0x075F` | **File directory** (plaintext) | See §4. |
| `0x0760–…` | File data | See §5. |

The boot stages load File 0 and File 1, then start File 1 (the game's own runtime loader), which loads File 2 (the main program) and starts it. Nothing in the boot blocks is needed to reimplement the game, and the directory and all file data are **not encrypted**.

## 4. File directory

Location: cart offset `0x0200`. **172 entries** (numbered 0–171), 8 bytes each:

| Byte | Meaning |
|---|---|
| 0 | Start page |
| 1–2 | Start offset within page (LE; 0–511) |
| 3 | Flags (always 0 in this cartridge; ignore) |
| 4–5 | Load address (LE). **Non-zero ⇒ file is stored uncompressed** and is copied verbatim to this address. **Zero ⇒ file is BPE-compressed** (§6); the caller chooses the load address. |
| 6–7 | Stored size in bytes (LE) — the number of cartridge bytes the file occupies (compressed size for compressed files). |

`start = page × 512 + offset`. Bytes after entry 171 are not directory entries.

**Validation rule for extractors:** for every compressed entry, the decompressor (§6) must consume exactly `stored size` bytes. This holds for all 170 compressed entries of a good image.

## 5. File roles

| File | Stored | Decoded size | Load address | Role |
|---|---|---|---|---|
| 0 | raw | 3 640 | `$A7C0` | **GFX0**: attract-mode palette (first 32 bytes) and attract/title sprite data (circuit-board background, etc.) |
| 1 | raw | 951 | `$18B7` | Runtime loader (file loading + decompression + IRQ dispatch). Not needed. |
| 2 | BPE | 29 577 | `$1C6E` | **MAIN** program. Also contains: tile & creature sprites and their control blocks, game palette, font, story text, UI text, sound-effect patches, many tables. |
| 3–15 | BPE | 313–2 426 | `$B600` | Music tracks 1–13 (in-level music; selection rule in §7) |
| 16 | BPE | 1 520 | `$B600` | Title / attract-mode music |
| 17 | BPE | 933 | `$B600` | Ending music |
| 18 | BPE | 5 781 | `$9000` | Title / attract-mode screen graphics (large Chip figure, title & credits pieces) |
| 19 | BPE | 5 222 | `$9000` | Ending scene 1 graphics (Chip and Melinda picture) |
| 20 | BPE | 2 154 | `$9000` | Ending scene 2 graphics (the prom picture) |
| 21 | BPE | 5 544 | `$C000` | Secret overlay program — a "Mandelbrot / Julia set explorer" — reachable only via the password `MAND` (doc 06 §9). Optional; not part of the game. |
| 22–171 | BPE | 1 or ~1 415–1 530 | `$0C00` | **Level files**: level *N* (1-based) is file `21 + N`, N = 1…150 (doc 02) |

Sizes, offsets and CRC-32 values of every decoded file are listed in doc 09.

## 6. BPE decompression (byte-pair encoding)

Every compressed file is a sequence of one or more **blocks**. Each block carries its own substitution table, so the table is discarded between blocks.

### 6.1 Block layout

| Field | Size | Meaning |
|---|---|---|
| `n` | 1 | Number of pair-table entries in this block (0–255) |
| `more` | 1 | Non-zero ⇒ another block follows this one; zero ⇒ last block |
| `count` | 2 (LE) | Number of **top-level tokens** in this block (not output bytes) |
| table | 3 × `n` | Entries numbered **1…n**, each `(symbol, left, right)` |
| tokens | `count` | Token bytes |

### 6.2 Expansion rule

A byte value can be bound to several table entries; later entries were created by later compression passes and may reuse earlier symbols. Expansion uses "the most recent definition that is older than the context":

- `expand(b, limit)`: let `e` be the **highest-numbered** entry with index `< limit` and `symbol == b`.
  - If no such entry exists, output byte `b` literally.
  - Otherwise output `expand(left[e], e)` followed by `expand(right[e], e)`.
- Each top-level token `t` is expanded with `expand(t, ∞)` (i.e. any entry 1…n may apply).

Pseudocode (fresh, for illustration):

```
decode(stream):
    out = []
    loop:
        n, more, count = read_u8(), read_u8(), read_u16le()
        sym, L, R = arrays indexed 1..n read as triples
        repeat count times:
            push expansion of read_u8() with limit = n+1 onto out
        if more == 0: break
    return out

expansion(b, limit):
    e = max { i : 1 <= i < limit and sym[i] == b }   (none → literal)
    if none: emit b
    else: expansion(L[e], e); expansion(R[e], e)
```

Recursion depth is bounded by `n` (≤ 255); an explicit stack is recommended.

The decoder was validated byte-for-byte against the original loader running in emulation on files 2, 3, 19, 21, 22, 40 and 171.

## 7. Music track selection (cross-reference)

When a level starts, the in-level music file is chosen from the level's password (doc 02 §6): take the **third** password letter as an index `k` (A = 0 … Z = 25); the music file is `3 + (k >> 1)` (i.e. tracks 1–13 → files 3–15).

## 8. Extractor checklist

1. Strip the LNX header (or accept a raw body); require body length 131 072.
2. Optionally verify the body CRC-32 (doc 09) and warn on mismatch (other dumps/revisions may differ).
3. Read 172 directory entries; decode each file; check consumed length == stored size; check decoded CRCs (doc 09).
4. Emit: levels (doc 02), sprites/palettes/font (doc 07), text (doc 06), audio data (doc 08).
