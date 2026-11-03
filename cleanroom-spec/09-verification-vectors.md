# 09 — Verification Vectors

Use these to test an extractor against a user-supplied ROM without consulting the ROM's internals. All values were produced by an independent extractor written from docs 01–02 and match the original loader's output.

## 1. Cartridge

- Body length: 131 072 bytes (after the 64-byte LNX header).
- Body CRC-32 (IEEE, as used by zlib): **`6A5F53ED`**. A different value means a different dump or revision; the formats may still apply, but the vectors below may not.

## 2. Directory and decoded files

`mode` = raw (uncompressed, with load address) or bpe. `stored` = bytes in the cartridge; `decoded` = bytes after decompression; CRC-32 of the decoded bytes.

| File | Cart offset | Stored | Mode | Decoded | CRC-32 |
|---|---|---|---|---|---|
| 0 | `0x00760` | 3640 | raw @ $A7C0 | 3640 | `37509E02` |
| 1 | `0x01598` | 951 | raw @ $18B7 | 951 | `5B8453D4` |
| 2 | `0x0194F` | 21473 | bpe | 29577 | `5AB859A4` |
| 3 | `0x06D30` | 465 | bpe | 578 | `76E74FD7` |
| 4 | `0x06F01` | 692 | bpe | 1002 | `6A648D4C` |
| 5 | `0x071B5` | 1782 | bpe | 2411 | `C72FCF2D` |
| 6 | `0x078AB` | 851 | bpe | 1135 | `D9D96755` |
| 7 | `0x07BFE` | 637 | bpe | 751 | `49CD4ECE` |
| 8 | `0x07E7B` | 1396 | bpe | 2307 | `2DB9DB15` |
| 9 | `0x083EF` | 674 | bpe | 1039 | `C6050A58` |
| 10 | `0x08691` | 442 | bpe | 895 | `296FB16F` |
| 11 | `0x0884B` | 1345 | bpe | 1552 | `40B1DD9F` |
| 12 | `0x08D8C` | 263 | bpe | 313 | `7F408F0F` |
| 13 | `0x08E93` | 1297 | bpe | 1655 | `D28AA8A9` |
| 14 | `0x093A4` | 801 | bpe | 887 | `FDF786AB` |
| 15 | `0x096C5` | 1483 | bpe | 2426 | `9C63C5CA` |
| 16 | `0x09C90` | 1191 | bpe | 1520 | `55277EB7` |
| 17 | `0x0A137` | 828 | bpe | 933 | `42A4D779` |
| 18 | `0x0A473` | 5054 | bpe | 5781 | `F1CE4279` |
| 19 | `0x0B831` | 4495 | bpe | 5222 | `B861AE30` |
| 20 | `0x0C9C0` | 1780 | bpe | 2154 | `3BD8A052` |
| 21 | `0x0D0B4` | 4661 | bpe | 5544 | `1D89CAF1` |
| 22 | `0x0E2E9` | 258 | bpe | 1487 | `40B91E56` |
| 23 | `0x0E3EB` | 226 | bpe | 1481 | `902883A3` |
| 24 | `0x0E4CD` | 307 | bpe | 1507 | `E5496B0B` |
| 25 | `0x0E600` | 343 | bpe | 1529 | `1949A701` |
| 26 | `0x0E757` | 261 | bpe | 1493 | `F83282A1` |
| 27 | `0x0E85C` | 248 | bpe | 1505 | `35E27B3D` |
| 28 | `0x0E954` | 311 | bpe | 1510 | `1ECB3E0E` |
| 29 | `0x0EA8B` | 229 | bpe | 1461 | `8652B8E1` |
| 30 | `0x0EB70` | 548 | bpe | 1425 | `46495253` |
| 31 | `0x0ED94` | 373 | bpe | 1420 | `8B51D423` |
| 32 | `0x0EF09` | 427 | bpe | 1418 | `6A9B83AE` |
| 33 | `0x0F0B4` | 255 | bpe | 1415 | `D411CFDA` |
| 34 | `0x0F1B3` | 409 | bpe | 1454 | `C5A9B010` |
| 35 | `0x0F34C` | 296 | bpe | 1420 | `5D16E2B5` |
| 36 | `0x0F474` | 546 | bpe | 1421 | `D10B9593` |
| 37 | `0x0F696` | 247 | bpe | 1459 | `C4EC1F48` |
| 38 | `0x0F78D` | 344 | bpe | 1419 | `BA550BF0` |
| 39 | `0x0F8E5` | 477 | bpe | 1422 | `8A75AF96` |
| 40 | `0x0FAC2` | 369 | bpe | 1417 | `B745060E` |
| 41 | `0x0FC33` | 464 | bpe | 1423 | `D45A2619` |
| 42 | `0x0FE03` | 335 | bpe | 1418 | `196654D1` |
| 43 | `0x0FF52` | 538 | bpe | 1423 | `DEA20760` |
| 44 | `0x1016C` | 342 | bpe | 1418 | `83FBA993` |
| 45 | `0x102C2` | 450 | bpe | 1421 | `BA89ED76` |
| 46 | `0x10484` | 344 | bpe | 1416 | `0FE9B14A` |
| 47 | `0x105DC` | 325 | bpe | 1420 | `32E7CA8D` |
| 48 | `0x10721` | 290 | bpe | 1427 | `FE9B15F4` |
| 49 | `0x10843` | 298 | bpe | 1420 | `17CC9D00` |
| 50 | `0x1096D` | 517 | bpe | 1421 | `59B41918` |
| 51 | `0x10B72` | 381 | bpe | 1419 | `1BE28F1E` |
| 52 | `0x10CEF` | 239 | bpe | 1415 | `BFB60F01` |
| 53 | `0x10DDE` | 551 | bpe | 1425 | `15CE45D3` |
| 54 | `0x11005` | 365 | bpe | 1423 | `5F3C706F` |
| 55 | `0x11172` | 341 | bpe | 1417 | `09A10870` |
| 56 | `0x112C7` | 332 | bpe | 1419 | `41209D42` |
| 57 | `0x11413` | 393 | bpe | 1417 | `AAE16D92` |
| 58 | `0x1159C` | 449 | bpe | 1423 | `2C505650` |
| 59 | `0x1175D` | 273 | bpe | 1418 | `63C55BD7` |
| 60 | `0x1186E` | 249 | bpe | 1415 | `F7C5B789` |
| 61 | `0x11967` | 379 | bpe | 1423 | `69754633` |
| 62 | `0x11AE2` | 498 | bpe | 1466 | `32306A53` |
| 63 | `0x11CD4` | 265 | bpe | 1424 | `74F78E11` |
| 64 | `0x11DDD` | 396 | bpe | 1421 | `D7C14CE0` |
| 65 | `0x11F69` | 310 | bpe | 1421 | `940CDFFD` |
| 66 | `0x1209F` | 503 | bpe | 1422 | `00144887` |
| 67 | `0x12296` | 410 | bpe | 1422 | `D7433B10` |
| 68 | `0x12430` | 343 | bpe | 1421 | `74F97AAF` |
| 69 | `0x12587` | 448 | bpe | 1424 | `434566D6` |
| 70 | `0x12747` | 383 | bpe | 1419 | `408BAB30` |
| 71 | `0x128C6` | 219 | bpe | 1418 | `7F1A04FB` |
| 72 | `0x129A1` | 328 | bpe | 1418 | `CC6CC7BD` |
| 73 | `0x12AE9` | 316 | bpe | 1425 | `73DFE37E` |
| 74 | `0x12C25` | 415 | bpe | 1483 | `BD7FF0E7` |
| 75 | `0x12DC4` | 572 | bpe | 1416 | `0A5308D5` |
| 76 | `0x13000` | 418 | bpe | 1420 | `7C192288` |
| 77 | `0x131A2` | 438 | bpe | 1421 | `FA2C0D5A` |
| 78 | `0x13358` | 680 | bpe | 1423 | `2E930932` |
| 79 | `0x13600` | 514 | bpe | 1422 | `09664FA5` |
| 80 | `0x13802` | 439 | bpe | 1424 | `E7687146` |
| 81 | `0x139B9` | 479 | bpe | 1420 | `00A6BC08` |
| 82 | `0x13B98` | 305 | bpe | 1415 | `67DA3C01` |
| 83 | `0x13CC9` | 376 | bpe | 1417 | `32B30430` |
| 84 | `0x13E41` | 336 | bpe | 1424 | `910DC2F9` |
| 85 | `0x13F91` | 564 | bpe | 1417 | `6C32FB1C` |
| 86 | `0x141C5` | 550 | bpe | 1420 | `4A776C9A` |
| 87 | `0x143EB` | 311 | bpe | 1417 | `2E95E7F9` |
| 88 | `0x14522` | 343 | bpe | 1419 | `CCD6C2F6` |
| 89 | `0x14679` | 508 | bpe | 1424 | `C6339117` |
| 90 | `0x14875` | 450 | bpe | 1422 | `B341B678` |
| 91 | `0x14A37` | 603 | bpe | 1420 | `F5238596` |
| 92 | `0x14C92` | 384 | bpe | 1419 | `382847F9` |
| 93 | `0x14E12` | 464 | bpe | 1424 | `7807FA3C` |
| 94 | `0x14FE2` | 380 | bpe | 1417 | `9FA6934D` |
| 95 | `0x1515E` | 507 | bpe | 1419 | `8F81F9A8` |
| 96 | `0x15359` | 386 | bpe | 1416 | `A4103F60` |
| 97 | `0x154DB` | 639 | bpe | 1420 | `6B587D44` |
| 98 | `0x1575A` | 490 | bpe | 1430 | `839B02F3` |
| 99 | `0x15944` | 350 | bpe | 1423 | `9171F275` |
| 100 | `0x15AA2` | 302 | bpe | 1430 | `481E44A7` |
| 101 | `0x15BD0` | 414 | bpe | 1424 | `69144F7E` |
| 102 | `0x15D6E` | 333 | bpe | 1424 | `4A522786` |
| 103 | `0x15EBB` | 567 | bpe | 1427 | `E32C86BB` |
| 104 | `0x160F2` | 369 | bpe | 1423 | `44C68383` |
| 105 | `0x16263` | 362 | bpe | 1415 | `C0DB9407` |
| 106 | `0x163CD` | 339 | bpe | 1418 | `ECE85121` |
| 107 | `0x16520` | 260 | bpe | 1418 | `AFADB94A` |
| 108 | `0x16624` | 647 | bpe | 1420 | `7FED03BE` |
| 109 | `0x168AB` | 391 | bpe | 1418 | `AEDDE2C4` |
| 110 | `0x16A32` | 386 | bpe | 1423 | `DC0B587D` |
| 111 | `0x16BB4` | 569 | bpe | 1420 | `128F80B7` |
| 112 | `0x16DED` | 264 | bpe | 1424 | `6FAFF178` |
| 113 | `0x16EF5` | 595 | bpe | 1417 | `1EEAB92A` |
| 114 | `0x17148` | 445 | bpe | 1419 | `64A3C1A8` |
| 115 | `0x17305` | 513 | bpe | 1425 | `C801F295` |
| 116 | `0x17506` | 344 | bpe | 1422 | `FE0332CE` |
| 117 | `0x1765E` | 570 | bpe | 1480 | `905A8486` |
| 118 | `0x17898` | 354 | bpe | 1430 | `3DC4B7F1` |
| 119 | `0x179FA` | 675 | bpe | 1420 | `9583D599` |
| 120 | `0x17C9D` | 530 | bpe | 1420 | `FE7DD2B0` |
| 121 | `0x17EAF` | 368 | bpe | 1417 | `B8989938` |
| 122 | `0x1801F` | 302 | bpe | 1420 | `9429C6F9` |
| 123 | `0x1814D` | 447 | bpe | 1419 | `710A9269` |
| 124 | `0x1830C` | 496 | bpe | 1417 | `5A69EED9` |
| 125 | `0x184FC` | 323 | bpe | 1417 | `D95F315A` |
| 126 | `0x1863F` | 395 | bpe | 1424 | `773564AC` |
| 127 | `0x187CA` | 206 | bpe | 1417 | `BF8AD6C3` |
| 128 | `0x18898` | 671 | bpe | 1423 | `77BF03FA` |
| 129 | `0x18B37` | 532 | bpe | 1420 | `82240FA7` |
| 130 | `0x18D4B` | 248 | bpe | 1425 | `571D1758` |
| 131 | `0x18E43` | 394 | bpe | 1418 | `6A5AAD20` |
| 132 | `0x18FCD` | 449 | bpe | 1421 | `4742D410` |
| 133 | `0x1918E` | 214 | bpe | 1430 | `8A9A0BB8` |
| 134 | `0x19264` | 414 | bpe | 1450 | `DC3B28E5` |
| 135 | `0x19402` | 269 | bpe | 1420 | `8899D3B4` |
| 136 | `0x1950F` | 399 | bpe | 1485 | `561BDD93` |
| 137 | `0x1969E` | 352 | bpe | 1426 | `6483F460` |
| 138 | `0x197FE` | 618 | bpe | 1420 | `2B233349` |
| 139 | `0x19A68` | 487 | bpe | 1425 | `1A610C9E` |
| 140 | `0x19C4F` | 491 | bpe | 1421 | `2443F62A` |
| 141 | `0x19E3A` | 586 | bpe | 1424 | `073961D8` |
| 142 | `0x1A084` | 407 | bpe | 1474 | `6E21C6B0` |
| 143 | `0x1A21B` | 312 | bpe | 1423 | `ACF9C5A2` |
| 144 | `0x1A353` | 402 | bpe | 1423 | `21E150C9` |
| 145 | `0x1A4E5` | 524 | bpe | 1419 | `6425A709` |
| 146 | `0x1A6F1` | 550 | bpe | 1421 | `1BF7442F` |
| 147 | `0x1A917` | 625 | bpe | 1423 | `17CF010F` |
| 148 | `0x1AB88` | 352 | bpe | 1418 | `81198AEE` |
| 149 | `0x1ACE8` | 585 | bpe | 1419 | `14A9F4A8` |
| 150 | `0x1AF31` | 413 | bpe | 1423 | `D06708E3` |
| 151 | `0x1B0CE` | 469 | bpe | 1419 | `EAA33342` |
| 152 | `0x1B2A3` | 329 | bpe | 1440 | `2DF74AB5` |
| 153 | `0x1B3EC` | 622 | bpe | 1417 | `0ABC1AED` |
| 154 | `0x1B65A` | 478 | bpe | 1420 | `1E58E506` |
| 155 | `0x1B838` | 474 | bpe | 1415 | `A6E0DB6B` |
| 156 | `0x1BA12` | 636 | bpe | 1419 | `3FC12043` |
| 157 | `0x1BC8E` | 405 | bpe | 1421 | `4C683243` |
| 158 | `0x1BE23` | 563 | bpe | 1418 | `FFC1FFFF` |
| 159 | `0x1C056` | 237 | bpe | 1459 | `A5C82304` |
| 160 | `0x1C143` | 344 | bpe | 1420 | `C356236D` |
| 161 | `0x1C29B` | 341 | bpe | 1419 | `38ACB202` |
| 162 | `0x1C3F0` | 393 | bpe | 1422 | `D4C42873` |
| 163 | `0x1C579` | 408 | bpe | 1483 | `BC949447` |
| 164 | `0x1C711` | 340 | bpe | 1419 | `7FD95875` |
| 165 | `0x1C865` | 580 | bpe | 1420 | `5B9714E6` |
| 166 | `0x1CAA9` | 5 | bpe | 1 | `FF000000` |
| 167 | `0x1CAAE` | 648 | bpe | 1420 | `4F014B8E` |
| 168 | `0x1CD36` | 426 | bpe | 1422 | `0F3BDCF6` |
| 169 | `0x1CEE0` | 253 | bpe | 1421 | `3C8887E9` |
| 170 | `0x1CFDD` | 564 | bpe | 1451 | `62C51FF8` |
| 171 | `0x1D211` | 5 | bpe | 1 | `FF000000` |

## 3. Passwords (levels 1–150)

| Levels | Passwords |
|---|---|
| 1–10 | BDHP JXMJ ECBQ YMCJ TQKB WNLP FXQO NHAG KCRE VUWS |
| 11–20 | CNPE WVHI OCKS BTDY COZQ SKKK AJMG HMJL MRHR KGFP |
| 21–30 | UGRW WZIN HUVE UNIZ PQGV YVYJ IGGZ UJDD QGOL BQZP |
| 31–40 | RYMS PEFS BQSN NQFI VDTM NXIS VQNK BIFA ICXY YWFH |
| 41–50 | GKWD LMFU UJDP TXHL OVPZ HDQJ LXPP JYSF PPXI QBDH |
| 51–60 | IGGJ PPHT CGNX ZMGC SJES FCJE UBXU YBLT BLDM ZYVI |
| 61–70 | RMOW TIGW GOHX IJPQ UPUN ZIKZ GGJA RTDI NLLY GCCG |
| 71–80 | LAJM EKFT QCCR MKNH MJDV NMRH FHIC GRMO JINU EVUG |
| 81–90 | SCWF LLIO OVPJ UVEO LEBX FLHH YJYS WZYV VCZO OLLM |
| 91–100 | JPQG DTMI REKF EWCS BIFQ WVHY IOCS TKWD XUVU QJXR |
| 101–110 | RPIR VDDU PTAC KWNL YNEG NXYB ECRE LIOC KZQR XBAO |
| 111–120 | KRQJ NJLA PTAS JWNL EGRW HXMF FPZT OSCW PHTY FLXP |
| 121–130 | BPYS SJUM YKZE TASX MYRT QRLD JMWZ FTLA HEAN XHIZ |
| 131–140 | FIRD ZYFA TIGG XPPH LYWO LUZL HPPX LUJT VLHH SJUK |
| 141–150 | MCJE UCRY OKOR GVXQ YBLI JHEN COZA RGSK DIGW GNLP |

## 4. Level facts

Per level: time limit (0 = untimed), chips required (count of tile `0x23`), number of occupied object slots. Slots 145 and 150 are end markers.

| Level | Time | Chips | Objects | Level | Time | Chips | Objects | Level | Time | Chips | Objects |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 100 | 11 | 1 | 51 | 750 | 13 | 1 | 101 | 300 | 34 | 5 |
| 2 | 100 | 4 | 6 | 52 | 400 | 2 | 16 | 102 | 200 | 3 | 14 |
| 3 | 100 | 4 | 1 | 53 | 500 | 0 | 17 | 103 | 600 | 37 | 38 |
| 4 | 150 | 9 | 8 | 54 | 350 | 68 | 6 | 104 | 300 | 82 | 13 |
| 5 | 100 | 0 | 4 | 55 | 100 | 30 | 25 | 105 | 350 | 37 | 1 |
| 6 | 100 | 4 | 1 | 56 | 250 | 8 | 5 | 106 | 0 | 0 | 9 |
| 7 | 150 | 3 | 1 | 57 | 400 | 35 | 42 | 107 | 300 | 50 | 103 |
| 8 | 100 | 1 | 2 | 58 | 600 | 9 | 7 | 108 | 350 | 31 | 66 |
| 9 | 400 | 9 | 29 | 59 | 400 | 8 | 36 | 109 | 150 | 4 | 12 |
| 10 | 80 | 0 | 2 | 60 | 294 | 12 | 9 | 110 | 399 | 16 | 14 |
| 11 | 300 | 3 | 4 | 61 | 0 | 16 | 1 | 111 | 0 | 4 | 11 |
| 12 | 400 | 652 | 3 | 62 | 300 | 0 | 36 | 112 | 0 | 4 | 15 |
| 13 | 0 | 0 | 1 | 63 | 500 | 7 | 8 | 113 | 500 | 5 | 41 |
| 14 | 250 | 4 | 9 | 64 | 600 | 41 | 97 | 114 | 200 | 12 | 6 |
| 15 | 250 | 12 | 6 | 65 | 500 | 51 | 67 | 115 | 0 | 0 | 5 |
| 16 | 0 | 0 | 1 | 66 | 300 | 12 | 23 | 116 | 750 | 27 | 13 |
| 17 | 100 | 46 | 18 | 67 | 700 | 28 | 1 | 117 | 0 | 0 | 128 |
| 18 | 600 | 0 | 16 | 68 | 650 | 52 | 68 | 118 | 300 | 0 | 34 |
| 19 | 210 | 146 | 11 | 69 | 300 | 0 | 47 | 119 | 250 | 38 | 9 |
| 20 | 400 | 15 | 29 | 70 | 199 | 0 | 35 | 120 | 0 | 11 | 40 |
| 21 | 150 | 9 | 2 | 71 | 500 | 23 | 20 | 121 | 0 | 0 | 30 |
| 22 | 300 | 8 | 1 | 72 | 0 | 35 | 61 | 122 | 300 | 6 | 4 |
| 23 | 500 | 88 | 81 | 73 | 600 | 28 | 2 | 123 | 299 | 3 | 19 |
| 24 | 550 | 48 | 35 | 74 | 400 | 4 | 22 | 124 | 800 | 22 | 15 |
| 25 | 600 | 28 | 1 | 75 | 500 | 0 | 1 | 125 | 0 | 71 | 32 |
| 26 | 300 | 170 | 19 | 76 | 550 | 20 | 19 | 126 | 600 | 36 | 100 |
| 27 | 200 | 6 | 8 | 77 | 500 | 5 | 33 | 127 | 500 | 21 | 7 |
| 28 | 300 | 22 | 29 | 78 | 500 | 13 | 4 | 128 | 400 | 182 | 24 |
| 29 | 400 | 5 | 24 | 79 | 300 | 56 | 11 | 129 | 300 | 6 | 37 |
| 30 | 600 | 36 | 1 | 80 | 800 | 17 | 1 | 130 | 0 | 32 | 2 |
| 31 | 29 | 118 | 1 | 81 | 0 | 56 | 70 | 131 | 60 | 6 | 2 |
| 32 | 600 | 3 | 1 | 82 | 999 | 0 | 96 | 132 | 999 | 28 | 41 |
| 33 | 0 | 9 | 8 | 83 | 400 | 14 | 16 | 133 | 0 | 30 | 56 |
| 34 | 350 | 14 | 4 | 84 | 600 | 5 | 38 | 134 | 0 | 7 | 109 |
| 35 | 600 | 10 | 50 | 85 | 300 | 15 | 17 | 135 | 300 | 0 | 45 |
| 36 | 350 | 28 | 19 | 86 | 400 | 0 | 18 | 136 | 0 | 38 | 1 |
| 37 | 800 | 56 | 33 | 87 | 0 | 34 | 125 | 137 | 450 | 0 | 37 |
| 38 | 500 | 1 | 11 | 88 | 400 | 12 | 2 | 138 | 300 | 0 | 17 |
| 39 | 20 | 29 | 49 | 89 | 450 | 5 | 18 | 139 | 0 | 388 | 11 |
| 40 | 200 | 0 | 1 | 90 | 400 | 121 | 34 | 140 | 300 | 0 | 1 |
| 41 | 250 | 60 | 23 | 91 | 400 | 22 | 3 | 141 | 0 | 15 | 35 |
| 42 | 300 | 27 | 6 | 92 | 500 | 6 | 56 | 142 | 0 | 10 | 1 |
| 43 | 200 | 0 | 23 | 93 | 800 | 4 | 14 | 143 | 0 | 23 | 1 |
| 44 | 300 | 32 | 23 | 94 | 0 | 7 | 1 | 144 | 0 | 30 | 9 |
| 45 | 300 | 0 | 16 | 95 | 350 | 2 | 20 | 145 | end | – | – |
| 46 | 250 | 14 | 19 | 96 | 399 | 46 | 27 | 146 | 999 | 13 | 68 |
| 47 | 300 | 4 | 8 | 97 | 300 | 0 | 28 | 147 | 0 | 24 | 1 |
| 48 | 300 | 6 | 13 | 98 | 350 | 7 | 102 | 148 | 0 | 12 | 2 |
| 49 | 200 | 23 | 25 | 99 | 399 | 8 | 59 | 149 | 999 | 0 | 56 |
| 50 | 350 | 16 | 17 | 100 | 0 | 48 | 64 | 150 | end | – | – |

Text decoding checks: level 1 title decodes to `LESSON 1`; level 2 to `LESSON 2`. Level 1 has exactly one object (Chip, slot 0) at column 15, row 14, and a 5-line hint.

## 5. Engine spot checks (from emulation of the original)

- Level 1 at the start of play: HUD shows level `001`, time `100`, chips left `011`; the intro overlay shows the total score `0000000`, the title and `CODE:BDHP`.
- The game logic advances one tick per 3 video frames; the clock drops by 1 every 20 running ticks.
- Chip walks one tile in 4 ticks; on ice/force floors in 2 ticks.


## 6. Solution-replay oracle (Tile World solution file)

A Tile World solution file for this level set (`CC1.dac.tws`, Lynx ruleset) was replayed against the **original ROM** (in emulation) and against an engine written only from docs 03–05. **All 148 replays (levels 1–144 and the password-only bonus levels 146–149; slot 145 is an end marker and has no level) matched tick-for-tick to the end, with zero divergences** — including the replays that do not win (Tile World's Lynx emulation differs from the real cartridge in places, e.g. random-number behaviour, so 43 of its winning solutions end differently on the real game).

Summary on the original: 105 wins (101 main + all 4 bonus), 29 deaths, 1 time-out, 13 stalls. A Tile World file may also hold a solution numbered 145 (Tile World's own extra level); it has no counterpart on the cartridge and is skipped.

**Replay protocol** (use it to regression-test a reimplementation):
- Start each level as a fresh attempt (doc 02 §4). For exact agreement with this table use the global values the original had at the start of the replays: `tick = 0x05`, random-force-floor counter `R = 0`, sub-second clock counter = 0 ticks already elapsed, no previously held/preferred direction.
- Decode moves per the TWS specification. A move with time *t* means its direction(s) are held **during tick t only** ; diagonals hold two directions; every other tick has no input.
- **Initial random-force-floor direction.** For Lynx-ruleset solution files, set the cartridge's random-force-floor counter R (N=0, E=1, S=2, W=3) from the solution's slide value (low 3 bits of the per-solution byte; Tile World direction code 0 N, 1 W, 2 S, 3 E, so R = 0, 3, 2, 1). The stepping bits (bits 3–5) are 0 in every Lynx-ruleset file tested. MS-ruleset files carry a fixed slide value that does not apply. In CC1, CCLP1, CCLP5 and geo5 this changes 3 of the 94 solutions with a non-zero slide: CC1 54 and CCLP1 16 become wins; CCLP1 145 dies at tick 310 instead of 56.
- **The level starts at tick 0 even when the first move comes later.** Tile World runs monsters from tick 0, but the cartridge waits for the first input before anything moves. Start it with an A-button press on tick 0, which moves nothing. 74 solution files in the sets below start late (CC1 4, CCLP1 3, CCLP5 2, Joshie 28, Jacques 37); before this rule, those replays ran from the wrong start, and 63 of them end differently with it (5 become wins: CC1 100 and 102, CCLP1 17 and 48, CCLP5 85).
- Run until win, death (Chip's death effect finished + 4-tick grace), time-out, or 400 ticks after the last move ("stall").
- Outcome tick = tick index at which the result is detected. Winning replays win on tick `TWS ticks − 1`.

| Level | TWS ticks | Original outcome | Level | TWS ticks | Original outcome | Level | TWS ticks | Original outcome |
|---|---|---|---|---|---|---|---|---|
| 1 | 394 | win @393 | 49 | 2381 | win @2380 | 97 | 1490 | win @1489 |
| 2 | 267 | win @266 | 50 | 1348 | win @1347 | 98 | 3660 | death @2824 |
| 3 | 250 | win @249 | 51 | 4119 | win @4118 | 99 | 2845 | death @1368 |
| 4 | 750 | win @749 | 52 | 589 | death @144 | 100 | 2774 | win @2773 |
| 5 | 385 | win @384 | 53 | 1406 | win @1405 | 101 | 1872 | win @1871 |
| 6 | 184 | win @183 | 54 | 2637 | win @2572 | 102 | 947 | win @946 |
| 7 | 420 | win @419 | 55 | 1409 | stall | 103 | 6148 | death @4418 |
| 8 | 92 | win @91 | 56 | 2658 | win @2657 | 104 | 2707 | win @2706 |
| 9 | 2421 | death @436 | 57 | 3642 | win @3641 | 105 | 2494 | win @2493 |
| 10 | 963 | win @962 | 58 | 2119 | win @2118 | 106 | 2613 | win @2612 |
| 11 | 2965 | win @2964 | 59 | 760 | win @759 | 107 | 2017 | stall |
| 12 | 3019 | win @3018 | 60 | 2418 | stall | 108 | 3596 | win @3595 |
| 13 | 376 | win @375 | 61 | 16273 | win @16272 | 109 | 498 | win @497 |
| 14 | 1983 | win @1982 | 62 | 434 | death @274 | 110 | 4153 | death @3930 |
| 15 | 3599 | win @3598 | 63 | 2456 | win @2455 | 111 | 1763 | stall |
| 16 | 739 | win @738 | 64 | 2920 | win @2919 | 112 | 305 | win @304 |
| 17 | 449 | win @448 | 65 | 6537 | win @6536 | 113 | 2011 | win @2010 |
| 18 | 1087 | win @1086 | 66 | 268 | death @324 | 114 | 799 | death @468 |
| 19 | 1509 | win @1508 | 67 | 6262 | win @6261 | 115 | 4582 | win @4581 |
| 20 | 1503 | win @1502 | 68 | 4949 | stall | 116 | 3543 | win @3542 |
| 21 | 1619 | win @1618 | 69 | 2181 | win @2180 | 117 | 2155 | win @2154 |
| 22 | 3819 | win @3818 | 70 | 2694 | win @2693 | 118 | 1144 | win @1143 |
| 23 | 3676 | death @50 | 71 | 4823 | death @4056 | 119 | 2106 | win @2105 |
| 24 | 4555 | stall | 72 | 1179 | win @1178 | 120 | 2122 | death @356 |
| 25 | 6476 | win @6475 | 73 | 4929 | death @604 | 121 | 693 | death @547 |
| 26 | 1240 | death @1286 | 74 | 1658 | win @1657 | 122 | 1227 | stall |
| 27 | 2391 | win @2390 | 75 | 784 | win @783 | 123 | 1589 | win @1588 |
| 28 | 2240 | win @2239 | 76 | 6116 | win @6115 | 124 | 5016 | win @5015 |
| 29 | 3149 | win @3148 | 77 | 1396 | win @1395 | 125 | 5400 | death @3038 |
| 30 | 6300 | stall | 78 | 3023 | stall | 126 | 6069 | death @6066 |
| 31 | 556 | win @555 | 79 | 2311 | win @2310 | 127 | 2867 | death @2126 |
| 32 | 5698 | win @5697 | 80 | 2486 | win @2485 | 128 | 3951 | stall |
| 33 | 18497 | win @18496 | 81 | 16729 | win @16728 | 129 | 2184 | win @2183 |
| 34 | 1108 | win @1107 | 82 | 927 | death @366 | 130 | 3597 | win @3596 |
| 35 | 4093 | win @4092 | 83 | 3951 | stall | 131 | 1089 | time-out @1214 |
| 36 | 3484 | win @3483 | 84 | 657 | win @656 | 132 | 14306 | death @12748 |
| 37 | 6479 | death @4028 | 85 | 2450 | win @2449 | 133 | 5598 | death @70 |
| 38 | 2857 | death @742 | 86 | 1406 | win @1405 | 134 | 22767 | death @4320 |
| 39 | 127 | win @126 | 87 | 14359 | death @6282 | 135 | 1543 | win @1542 |
| 40 | 379 | win @378 | 88 | 2078 | stall | 136 | 12035 | win @12034 |
| 41 | 2937 | win @2936 | 89 | 3027 | death @2222 | 137 | 2629 | win @2628 |
| 42 | 2682 | win @2681 | 90 | 3723 | stall | 138 | 4239 | win @4238 |
| 43 | 2477 | death @630 | 91 | 1557 | death @530 | 139 | 2242 | win @2241 |
| 44 | 4790 | win @4789 | 92 | 1808 | win @1807 | 140 | 2528 | win @2527 |
| 45 | 395 | death @170 | 93 | 6752 | win @6751 | 141 | 5567 | win @5566 |
| 46 | 1238 | win @1237 | 94 | 8626 | win @8625 | 142 | 938 | win @937 |
| 47 | 2324 | win @2323 | 95 | 1144 | win @1143 | 143 | 9538 | win @9537 |
| 48 | 1120 | win @1119 | 96 | 2615 | win @2614 | 144 | 5058 | win @5057 |

Bonus levels (reached by password only; doc 02):

| Level | TWS ticks | Original outcome |
|---|---|---|
| 146 | 9600 | win @9599 |
| 147 | 10911 | win @10910 |
| 148 | 12135 | win @12134 |
| 149 | 1358 | win @1357 |

The bonus levels use no tiles or object types beyond those of levels 1–144, and the lockstep comparison (full object/map state each tick) found nothing unusual in them.

## 7. Imported levels (CCLP1) on the original

The community set CCLP1 (`CCLP1.dat`, 149 levels) with its Tile World Lynx solutions (`CCLP1-Lynx.dac.tws`), each level converted to the cartridge format and injected into the original in place of level 1 (doc 10 §2 D). Replay protocol as in §6. Conversion (strict): ice corners by their walls (MS `1A`/`1B`/`1C`/`1D`, named by their open sides SE/SW/NW/NE, become the corners walled NW/NE/SE/SW); MSCC-only tiles → wall (`36`/`37` → invisible wall); buttons wired by the cartridge rule; north/west thin walls become the neighbour's south/east edge where that tile is floor or a thin wall, and are dropped next to a solid wall or elsewhere; objects in reading order with Chip swapped into slot 0, at most 128; surplus chips beyond the DAT's chips-required become `31`; titles and hint lines cut to 19 characters, at most 7 hint lines.

Summary on the original: 59 wins, 61 deaths, 1 time-out, 27 stalls, 1 crash (level 140 at tick 652). A few spot values:

| Level | Original outcome | Note |
|---|---|---|
| 1 | stall | Tile World wins; the original ignores the input of the tick after a blocked move |
| 84 | stall | blocks start on blue keys and destroy them on the first tick |
| 85 | stall | monsters leave the map at the bottom and overwrite object state bytes, including Chip's |
| 87 | death @2960 | monsters leave the map at the top |
| 140 | crash @652 | a ball ends up standing on a stray state byte (tile code `0x49`) |


## 8. More imported sets (CCLP5, geo5-1, geo5-2, geo5-5)

*Naming note:* the set labelled "CCLP5" throughout these docs is **Chipster1059's submission file for CCLP5** (`CCLP5.dat` with `C1059-CCLP5-Lynx.dac.tws`), not the released CCLP5 pack, which is still the latest set and has no published solution file.

Same conversion and protocol as §7. Outcomes on the original:

| Set | Levels | Wins | Deaths | Time-outs | Stalls | Crashes / hangs |
|---|---|---|---|---|---|---|
| CCLP5 | 100 | 23 | 48 | 1 | 14 | 14 |
| geo5-1 | 9 | 1 | 4 | 0 | 3 | 1 |
| geo5-2 | 9 | 2 | 7 | 0 | 0 | 0 |
| geo5-5 | 10 | 3 | 6 | 0 | 1 | 0 |

Crashes and hangs (tick): CCLP5 2 @9, 10 @92, 11 @1303, 20 @17, **22 @0**, 28 @430, 31 @284, 34 @221, **51 @0**, **63 @0**, 72 @23, 87 @287, 95 @29, 97 @321; geo5-1 9 @986. The three at tick 0 are buttons without a target (doc 02 §5); the others follow objects leaving the map (doc 04 §4.2–4.3). CCLP5 level 5 stalls on the original although its objects also reach the RAM below the map (Chip ends up standing on an object reference used as a tile). An engine following doc 04 §4.4 reproduces all of these outcomes, including every crash tick, without any cartridge data.

## 9. Large imported sets with MS solutions (Joshie, Jacques)

Two large community sets, `Joshie.dat` (1325 levels) and `Jacques.dat` (986 levels), with Tile World solutions recorded under the **MS ruleset**. Under Lynx rules most of those inputs fail early, but they drive the levels in every direction, so they serve as input for comparing the original with a reimplementation. Same conversion and protocol as §7.

| Set | Levels | Wins | Deaths | Time-outs | Stalls | Crashes / hangs |
|---|---|---|---|---|---|---|
| Joshie | 1325 | 101 | 830 | 4 | 372 | 18 |
| Jacques | 986 | 62 | 545 | 6 | 149 | 224 |

An engine following docs 03–05 (with doc 04 §4.4) reproduces **all 2311** outcomes on the same tick (Jacques 799 with the link-table start state below). The last five to be resolved (Joshie 511, 938, 1097, Jacques 924, 964) all involve the original drawing a junk object on screen: four times Chip himself in a stray state (doc 04 §4.4, Chip drawn in a junk state), and in Joshie 511 a stray object in state `F5` whose drawing overwrites the cell lookup's row table (doc 04 §4.4, row table).

Protocol notes:
- **Link-table start state.** The original never clears its link table (doc 04 §4.4); when the level starts it holds whatever the title screen left in that RAM. One replay (Jacques 799) reads such a leftover entry. A reimplementation starting from an empty table matches all other replays; to reproduce that one too, start from the same leftover bytes.
- **Chips required.** Jacques 4 asks for 97 chips but has one (the others are hidden in the MS lower layer, which the cartridge cannot store); on the cartridge the level needs the one chip it holds (doc 02 §4).
- **Solution files.** In these files the 4-byte move form carries a set top byte (`90`), which is not part of the time field: time = bits 5–23.

## 10. Ice collision batteries

Two lock-step batteries aimed at timing on ice (`tools/measure/icetest.py`, `iceblock.py`; `ice4.py` runs both in all four directions), run against the original. Counts below are per direction; all four directions (E, W, S, N) were run, 33 408 scenarios in total, and all match:

- **Two actors meeting on an ice corridor**: Chip, a pushed block and every monster type against each other, head-on (the second one moving or waiting), gaps 2–9 and Chip's start tick 0–3, so the meeting falls on every sub-step. 7008 scenarios, all match.
- **Chip sliding into a block**: block 1–7 cells ahead, on ice or on floor, free, wedged against a wall, against a second block or against a monster (tank, teeth, ball); with and without skates, with the direction tapped once or held. 1344 scenarios, all match.

Observed on the original (no skates, Chip arriving by sliding): a free block is pushed and Chip stops behind it; a block **on floor** that cannot move makes Chip bounce back along the ice; a block **on ice** that cannot move kills Chip every time (the pushed block bounces back off the obstacle into him). Unlike some other versions, no timing makes him survive the wedged block on ice.

**Ice corners in the path** (small sample, `tools/measure/icecorner.py`): an L-shaped ice run, a row heading into an ice corner that turns it into a column, in both mirror images. Two actors meeting around the corner (every pairing of Chip, block and the nine monster types, five gaps, random start tick): 1200 scenarios, all match. Chip sliding round the corner into a block (distance 1–5, block on ice or floor, free / wedged by a wall / by a second block / by a tank, with and without skates): 480 scenarios, all match. One example of what the original does there: Chip turned south by the corner meets a block on ice wedged against a wall, bounces back up the column, is turned west by the corner, and the block — knocked loose — follows him round and crushes him a few cells later.

**Ice-corner run** (`tests/icecorners/icecorners.dat`, built by `tools/measure/cornermaze.py`): a 32×32 level with walls round the edge and an interior of ice corners laid so that one push west from the start (top right) sends Chip, without skates, over every one of the 870 corners in turn and onto the exit in the middle. On the original he reaches the exit at tick 1743 having touched all 870 corners; the remake matches it tick for tick over 2200 ticks.

## 11. Glitch showcase pack

`tests/glitchpack/lynx-glitches.dat` (built by `tools/measure/glitchpack.py`, Lynx ruleset, no time limit): three small levels whose point is a non-crash glitch of the cartridge, each with a hint. Each was checked on the original after converting the DAT back to cartridge form, and the remake matches it tick for tick.

| # | Title (password) | Glitch | Original |
|---|---|---|---|
| 1 | Over the Edge (EDGE) | No bounds check at the map's top edge: Chip walks north out of a sealed room, his y wraps to row 31, and he arrives at an exit walled off from the start | exit reached at tick 19 |
| 2 | Wrap Around (WRAP) | Same at the left edge: the move goes to the linearly previous cell (31, row − 1), x wraps to 31, and Chip walks into a sealed corridor on the right edge | exit reached at tick 19 |
| 3 | Vanishing Ball (POOF) | A ball bouncing in a shaft open to the top edge slips off the map, bounces in a pocket at the bottom of the map, and comes back through the bottom edge | finishes when Chip crosses while the ball is away (several start ticks tried, including two that die) |

## 12. Clone machine with Chip on it

Small lock-step tests (`tools/measure/clonestay.py` and inline runs), checked on the original; the remake matches every tick.

- **Chip starting on a clone machine, no button anywhere**: he cannot leave it. All four facings × all four joystick directions × tap or hold × four start ticks (128 runs): Chip never moves. Control: the same inputs on plain floor walk him away normally.
- **A ball presses the clone machine's red button while Chip is on it**: Chip is pushed off in the direction he faces, and a Chip-type template appears on the machine in a new slot. 30/30 and 30/30 (two facings) and 60/60 (repeated presses) match.
- **Long run** (ball pressing the button about every 112 ticks, Chip walking to a pocket): each press releases the template, which takes one forced step in its facing direction and then never acts again — it ignores the joystick and only the real Chip (slot 0) answers it — and leaves a new template. A released copy standing in front of the machine jams it: further presses do nothing. Chip can share a cell with a released copy safely; a copy released into him kills him (both become death effects). 419/419 ticks match.

## 13. Every crash traced

All 258 crashes and hangs in the real replays (§7–§9, with the tick-0 start of §6: CCLP1 1, CCLP5 14, geo5-1 1, Joshie 18, Jacques 224) have a traced cause, and the remake reaches each on the same tick. 26 hang at tick 0 because a brown or red button has no target (doc 02 §5: CCLP5 22, 51, 63; Joshie 92, 179, 435, 932; Jacques 88, 167, 310, 352, 355, 360, 362, 443, 493, 611, 627, 628, 657, 693, 717, 761, 819, 905, 910). 224 follow an object crossing the map edge that the edge detector saw: 219 with the old start and 7 new with the tick-0 start (Joshie 1304; Jacques 129, 236, 363, 672, 715, 842), less 2 that no longer crash (Jacques 442 now stalls, 964 times out). Culling monsters about to leave the map turns 9 of the 219 into wins (CCLP5 72; Jacques 10, 252, 489, 542, 685, 686, 793, 863, all still in sync). The last eight looked edge-free because the detector compared positions only after a tick finished, while seven of them crash during the crossing tick itself:

| Replay | Crash tick | Cause |
|---|---|---|
| CCLP5 2 | 9 | a monster steps south off (2,31) onto object state bytes; the "tile" it reads is another slot's death-effect frame (`42`); arriving on it crashes |
| CCLP5 28 | 430 | same at (3,31); the step also overwrites slot 3's effect state, turning it into stray type 12, whose dispatch crashes |
| Jacques 295 | 64 | a monster steps east off (31,31) into the same RAM, effect frame `49` |
| Jacques 644 | 25 | south off (23,31), effect frame `48` |
| Jacques 963 | 81 | south off (17,31), effect frame `4A` |
| Jacques 516 | 35 | Chip presses south on row 31; the byte below (slot 4's state) is taken as a reference to slot 47 (empty), so Chip "dies" touching it; slot 47's effect has no map reference and its removal probe hangs (doc 04 §8) |
| Jacques 258 | 271 | the level is all water with no Chip; the original still has a slot-0 Chip at (0,0) with no map reference; the 13-second time-out kills him and removing his effect hangs |
| CCLP5 11 | 1303 | the only one not tied to the edge: a monster kills Chip standing on a teleport; another monster then teleports and the plain teleport tile is written over the dying monster's map reference; when its effect ends the removal probe hangs |

Totals: 26 + 224 + 8 = 258. Scripts: `tools/measure/crashall.py` (classification), `tools/measure/crash8.py` (the eight traces).

## 14. Block kick

The "block kick", found in a recording of CC1 level 45 on the original (Lynx emulation): Chip pushes a block that stands on fire toward a lane of walkers cloned at its east end; the block slides into the lane while Chip stays on his square instead of following it into the fire.

**Rule (traced on the original, level 45 column 5):** Chip pushes a block in the same tick a monster enters the cell beyond it. The push fails and Chip does not move, but the block is left in its moving state (e.g. `9E`) and keeps trying to move every tick. When the monster starts to leave the cell (its map reference moves at the start of its move), the block moves into it on its own. If Chip is not pressing that direction in that tick he stays behind; if he is still holding it, he follows as in an ordinary push. A monster that has already started to leave when Chip pushes frees the cell at once, so that push simply succeeds.

Tested in lock-step (`tools/measure/blockkick*.py`, all with the A-button start of §6; without it the monsters wait for the push and the kick timing is never reached):

| Test | Scenarios | Kicks on the original | Remake matches |
|---|---|---|---|
| Level 45 itself, Chip and block placed as in the recording, live walker lane, push then one short press at many times | 2304 | 540 (columns 5 and 6) | all |
| Monster leaving the cell beyond the block (straight on or to a side) | 1008 | 0 | all |
| Monster crossing the cell beyond the block | 3456 | 53 | all |
| Lane below a block, monster entering from the east, block on fire or floor | 3456 | 62 | all |

Every kick needs a tap: the direction pressed for the push and released before the monster leaves. Every monster type kicks except teeth (they turn toward Chip instead of passing). Fire under the block makes no difference.

## 15. Diagonal block push without moving

Community report: "push against a wall, then push diagonally against a neighbouring block very briefly; the block is pushed but Chip doesn't follow" (impossible in Tile World). Confirmed on the original in lock-step (`tools/measure/diagpush.py`, A-button start): Chip with a wall on one side and a block on a perpendicular side, all 8 orientations, 0–6 ticks pushing the wall, then the diagonal (wall + block direction) held 1–4 ticks, then released: 640 scenarios, all match the remake tick for tick.

| Diagonal held | Block moves, Chip stays |
|---|---|
| 1 tick | 80 of 96 (every case after ≥ 1–2 ticks against the wall; about half the timings with no wall push first) |
| 2–4 ticks | 0 of 288 (Chip follows the block) |

Mechanism: the block slap (doc 04 §3, doc 10 §3 item 1). On the diagonal tick Chip's decision probe tries the block side and launches the block; Chip then chooses the wall side, which is blocked, and stays. If the diagonal is still held on the next tick he steps after the block.

## 16. Clone machine with a full object table

`tools/measure/clonefull.py`: slots pre-filled with parked blocks (120–128 objects at the start), a ball bouncing over a red button wired to a clone machine holding a tank that drives down an open column; 400 ticks, 17 button presses. On the original the object count rises to exactly 128 (all slots, Chip's included) and stops. At the limit a press still releases the copy waiting on the machine, but no new copy is made, so the machine is left empty and later presses do nothing. No crash or hang. The remake matches all six runs tick for tick.

## 17. Fake-Chip pickup and objects starting on ice corners

`tools/measure/fakechip.py`: a stray Chip-type object (slot 1) arrives on a counted chip while the real Chip stands on or slides over each of 25 tile kinds (floor, ice, the five force floors, the four ice corners, dirt, gravel, trap, buttons, teleport, fire, water, exit, hint, blue key, thin walls, popup wall): 300 lock-step scenarios, all match after two fixes found here and in the edge-protection run (Jacques 292): the pickup also writes floor as the tile under slot 0 (doc 03 §3.8), and an object standing still on an ice corner is only turned, not set moving (doc 03 §3.3). Controls for the second rule: Chip, every monster type and blocks starting on each corner, still or moving, with Chip held in each direction: 1280 runs, all match.

**Fake Chip on every other tile** (`tools/measure/fakechip2.py`): the fake Chip moves one cell and then stops for good (its own decision runs Chip's decision code, which acts on slot 0), so each target is placed right next to it, or it rides an east force floor into the target. 49 tile kinds (keys, boots, uncounted chip, exit, socket, doors, hint, thief, all buttons with their targets, teleports, trap, clone machine, fire, water, bomb, dirt, blue walls, popup and toggle walls, hidden and invisible walls, gravel, ice, ice corners, force floors, thin walls), with the real Chip on floor, ice, a force floor or an ice corner and random input, sometimes holding a key: 784 lock-step runs comparing objects, map, boots, keys, chips left and the clock every tick — all match. The fake Chip cannot enter doors (even when the real Chip holds the key), the real blue wall, closed toggle walls, hidden or invisible walls; those runs exercise the bump path instead.

## 18. More imported sets: CCLP3, CCLP4, CCLXP2 (Lynx-ruleset solutions)

Same conversion and protocol as §7 (tick-0 start, slide rule of §6). Tables: `tests/oracle_cclp3.tsv`, `oracle_cclp4.tsv`, `oracle_cclxp2.tsv`.

| Set | Levels | Wins | Deaths | Time-outs | Stalls | Crashes / hangs | Remake |
|---|---|---|---|---|---|---|---|
| CCLP3 | 149 | 51 | 63 | 1 | 28 | 6 | 149 / 149 |
| CCLP4 | 149 | 56 | 60 | 0 | 32 | 1 | 149 / 149 |
| CCLXP2 | 149 | 56 | 57 | 0 | 17 | 19 | 149 / 149 |

All 26 crashes have known causes: 3 hang at level start, as with a button that has no target (CCLP3 117, CCLP4 91, CCLXP2 91), and 23 follow an object crossing the map edge (in 13 of them Chip himself walks off the map along the solution's path). **Edge protection** (border floor cells turned into thin walls facing out, as in doc 10 §2 / `remake/ideas.md`) on those 23: with south/east walls only, run on the original, 14 still crash, 7 die, 1 stalls and **CCLXP2 64 wins**; the remake stays in sync in all 23. With all four edges (fake north/west walls, remake only): 9 crash, 12 die, 1 stalls, CCLXP2 64 wins.

**Blobs and walkers removed, and edge culling** (`tools/measure/bwcull.py CCLP3 CCLP4 CCLXP2`; only replays that do not win on the original). With blobs and walkers taken out of the level (69 levels that have them): **7 new wins** (CCLP4 44, 71, 109, 117; CCLXP2 3, 24, 77), 48 deaths, 18 stalls, 6 crashes; CCLP3 none. With monsters about to step off the map removed before each tick (26 crashing replays): 1 win (CCLXP2 64, the same level edge protection wins), 11 crashes, 8 deaths, 3 stalls, 3 hang at the start; both together (6 levels): no win. The remake matches all 8 wins tick for tick.

## 19. CC1telewalls (all walls turned into teleports)

A community "meme" set: the CC1 levels with every wall replaced by a teleport. No solution file, so `tools/measure/survive.py` drives Chip: on each cell he takes a random direction whose target is not next to a monster (one cell), else waits; inputs are decided from the original's own state and replayed into the remake in lock-step. 149 levels × 2 seeds, up to 600 ticks.

| Version | Runs | In sync | Alive at 600 | Deaths | Wins | Crashes | Not starting |
|---|---|---|---|---|---|---|---|
| As published (border cells are teleports too) | 298 | 298 | 49 | 126 | 11 | 112 | 0 |
| Border turned into walls (Chip moved one cell inward in 1 level, 3 monsters/blocks in others) | 296 | 296 | 99 | 178 | 14 | 5 | 2 |

The published version crashes mostly through objects teleporting or walking off the open border. With the border walled, the 5 remaining crashes are all the removal hang of doc 04 §8 (a finished death effect whose map reference was overwritten — here by objects teleporting onto it, cf. doc 10 §3 item 7), and level 88 (Spirals) hangs at start because walling the border removed its only clone machine, leaving the red button without a target (doc 02 §5). The remake reproduces every one of these on the same tick. **Level 88 with its clone machine kept** (border walled except the clone machine at (0,30); a second variant also keeps the exit at (31,15)): the level starts, and 20 survival seeds per variant all end in Chip's death within 27–85 ticks, all 40 in sync. Chip starts in the one-cell corridor of row 30 with a monster (slot 1) coming east from beside the clone machine, and the survival driver has no way past it in that corridor.

## 20. Edge protection over the whole border

All 255 replays that crash after an edge crossing (CCLP1, CCLP5, geo5-1, Joshie, Jacques, CCLP3, CCLP4, CCLXP2) with **every** border cell turned into a thin wall facing out, whatever it held (south row / east column with the cartridge's own walls, the south-east corner with its corner wall; north row / west column with the remake's fake walls for the remake-only run). Floor-only protection (`remake/ideas.md`) left 80 four-edge runs still crashing through other border tiles.

| Version | Not starting | Death | Crash | Stall | Time-out | Win |
|---|---|---|---|---|---|---|
| South/east, on the original | 8 | 131 | 71 | 41 | 3 | 1 (Jacques 252) |
| All four edges, remake only | 8 | 179 | 32 | 30 | 3 | 3 (Jacques 537, 680, 683) |

The remake stays in sync with the original in all 255 south/east runs. The 8 levels that no longer start had a trap or clone machine on the border, now walled over, so a button lost its target (doc 02 §5). **The 32 four-edge crashes, traced** (crash rule and first edge crossing logged per replay):

| Cause | Count |
|---|---|
| Hang at level start: walling covered a border trap or clone machine, so a button has no target (CCLP3 76, CCLXP2 59, Jacques 230, 259, 306, 313, 339, 489, 799, 950, 953) | 11 |
| Crossing out of the top-right corner (31,0), which got only its east wall: then an odd-tile arrival (8), a stray type 12/14/15 (5), the junk-Chip draw or display hang (3), the removal hang (2) | 18 |
| Removal hang with no crossing, as unprotected (CCLP5 11, Jacques 258, 728; §13) | 3 |

**Second version:** the three corners that need two outward walls (top-left, top-right, bottom-left; only south-east exists as one tile) become solid walls, and border traps and clone machines are left unwalled. All 255, remake only:

| Version | Not starting | Death | Crash | Stall | Time-out | Win |
|---|---|---|---|---|---|---|
| All four edges, corners solid, traps/clone machines kept | 0 | 204 | 7 | 41 | 2 | 1 (Jacques 677) |

Jacques 537, 680 and 683 lose their wins; traced, all three were artifacts of the first walling, not real wins. In 680 and 683 the cell (31, 0) is a wall in the level, and the first walling replaced it with an east thin wall, opening it; with only that corner made solid again both stall, with the other corners changed they still win. In 537 the top row holds two clone machines (teeth and blob templates) with their red buttons; the first walling covered them and their buttons, leaving the templates (moving flag set) on plain wall tiles, where they most likely move off as ordinary monsters; keeping the machines alone already loses the win (death at 324), and so does making all three open corners solid at once (any two still win). Of the 7 crashes, 3 are the edge-free removal hangs above. The other 4 (CCLP5 31, Jacques 313, 655, 904) come from **objects that start on a border cell**: the wall written there becomes the tile under the object, which does not stop it leaving, and once it has gone the cell holds what it left behind (floor for Chip), not the wall. In Jacques 904 Chip starts on the top-left corner, leaves west on tick 0 and arrives on the top-right corner. Moving every border-start object inward to the first free non-border cell clears all 4 (each ends in a death instead: CCLP5 31 @630, Jacques 313 @200, 655 @87, 904 @14), but it reshapes those levels heavily (CCLP5 31 has a full row of objects on the top edge; Chip lands on a bomb in 904; some objects land on walls in 655), so the results say nothing about winning. **Over all 255** (remake only, with the corners solid and edge traps and clone machines kept): 228 of the levels have objects starting on the border.

| Version | Death | Crash | Stall | Time-out | Win |
|---|---|---|---|---|---|
| Corners solid, traps / clone machines kept | 204 | 7 | 41 | 2 | 1 (Jacques 677) |
| … and border-start objects moved inward | 199 | **2** | 47 | 3 | **4** (Jacques 677, 537, 685; CCLXP2 109) |

The 2 crashes left are the edge-free removal hangs (CCLP5 11, Jacques 258); the third one, Jacques 728, now times out because one object moved. 24 outcomes change in all, most of them death ↔ stall. Moving objects changes the levels, so these wins are no more than hints, like the others in this section.

Conclusion: with full-border protection, every remaining crash is either an object that started on the border or the edge-free removal hang of doc 04 §8.

## 21. Object pass with a shifted row table

Random lock-step tests with stray objects in the four states whose drawing writes game data (68/E8 slot states, 75/F5 the cell lookup's row table; `tools/measure/objdrawtest.py 1000 SEED`, seeds 1–4, 48 ticks each). The rule of doc 04 §4.4 (the window scanned relative to the last row's entry) replaces an earlier low-5-bit rule.

| Rule | Runs | Match | Differ |
|---|---|---|---|
| Earlier (low 5 bits of the last row's entry) | 3950 | 3934 | 16 (all but one announced in time; seed 4 #255 one tick late) |
| Scan relative to the last row | 3950 | 3948 | 2 (seed 2 #262, state E8; seed 4 #939, F5) |
| … and addresses outside the map skipped | 3950 | 3949 | 1 (seed 2 #262) |

The two cases left over from the earlier notes (seed 1 #203 and #879) are both mid-scroll: the last row's entry is `00` (the writer's x or y high byte) where `60` or `20` belongs, which moves the scan up by whole rows so the writer itself is no longer visited. Seed 4 #939: Chip, carried across the top edge, puts the camera at the bottom, where the window's last row is row 32; the scan then reaches past the map into the object table, and Chip's own state `84` looked like a reference to the writer in slot 4; the original skips addresses outside the map. Seed 2 #262 is the state-`7B` likely-crash case (doc 04 §4.4): the E8 writer puts Chip's screen position into slot 69's state, which becomes `7B`; the original crashes on the next tick; the remake shows the likely-crash notice a tick ahead and plays on. All real replays still match (§6–§9, §18) and none shows the desync notice any more.

## 22. Survey: Chip on skates among the redirect codes `4A` / `71`

Random 13 × 13 rooms (`tools/measure/redirectsurvey.py SEED 150`; 4 seeds × 150, tick-0 A start, 120 ticks): ice, ice corners, force floors, walls, water, dirt and many `4A` / `71` cells (often right next to Chip), Chip with skates (sometimes suction boots too), random input, 0–4 other objects (monsters, blocks, and type-1 objects, i.e. fake Chips). Lock-step against the original.

| Stage | Unexplained differences (no notice) |
|---|---|
| Before (same with or without the 2026-11-02 drawing fixes) | about 90 of 600 |
| Harness fix: a crash on the very first tick was replayed into the remake without the A press | — |
| Chip on skates arriving on `71`; objects standing on `71` (doc 04 §4.4: sound-driver byte `795B`), flagged | 6 |
| Any object boxed in on a re-move code, flagged (the original usually but not always crashes) | 2 |
| A move blocked while on `71`, flagged (doc 04 §4.4 case 3) | 0 |

Chip alone (no monsters, 150 rooms): every difference is the `71` / sound-byte case and carries the notice. `4A` with skates holds as documented (moved on at once; a blocked re-move crashes). The last two were traced: seed 3 #146 is a blob on `71` that tries to step onto the `71` beside it (the blocked move gives the ball in the next slot one extra step, by the sound byte); seed 1 #125 is a fake Chip carried by a force floor over `4A` into `71` moving S, which the original lets wait a tick. Both now carry the notice from the divergence tick; a sweep of 160 monster / direction / neighbour combinations around a second `71` has 31 differences, all flagged. Now 0 of 600 rooms differ without the notice. All real replays still match; five Jacques replays that crash in both now show the notice (Jacques 69, 186, 542, 963, 965).

## 23. Cloning off the map edge (the MS "Insanity" idea)

`tools/measure/edgeclone.py`: a clone machine on row 0 facing N, or on row 31 facing S, in each of the 32 columns, with a wall behind it; the template is a block or a fake Chip (type 1); a ball bounces over the red button and presses it about every 24 ticks. Three Chip set-ups: sliding back and forth for good on an ice lane fed by a force floor (500 ticks), standing still, and walking at random (300 ticks). 384 lock-step runs, **all 384 in sync** (5 of them crash, on the same tick in both).

What the original does: the released copy steps into the RAM beyond the edge and stops there; it then blocks the machine, so each machine makes one off-map write. North of row 0 is the link table's high half for row 31 (only teleports and buttons on row 31 notice). South of row 31 is the slot state table: the release succeeds only if that slot's state byte reads as an enterable tile (an empty slot, or an object standing still); a moving object there blocks it. With Chip standing still, the machine in column 0 writes `81` into Chip's own state: he becomes a stray type-0 object, slides one cell east and stays put for good. A sliding Chip always has his moving bit set, so this cannot stop him mid-slide as in the MS level; in all sliding runs he kept sliding.

**East and west.** Moving off the west or east edge goes to the linearly previous or next cell (doc 09 §11), so a machine anywhere but the two corners just clones into the row above or below. The two corners that leave the map: (0, 0) facing W writes into the last link-table byte, with no visible effect; (31, 31) facing E reaches Chip's own state byte, the same as the bottom-row machine in column 0 (Chip sliding: the release is blocked; Chip caught standing still: he becomes a stray type-0 object). Block and fake-Chip templates, Chip sliding / standing / walking at random: 12 runs, all in sync.

**Several machines on one edge, and re-aimed row-31 links** (`tools/measure/multiclone.py SEED 25`, seeds 1–4). Up to 16 machines on row 0 (facing N) or row 31 (facing S), each with its own red button in the column before it; templates mostly blocks, some fake Chips, tanks and balls. Chip walks along the next row and presses every button twice in random order (up to about 2300 ticks, up to 34 objects). On the north edge, row 31 also holds two teleports and a brown button wired to a trap, below machine columns. A clone can only overwrite such a link entry if the byte there reads as an enterable tile, so the partner teleport sits on row 1 (link high byte `08`) and the trap on row 20 (`0E`). After the cloning, Chip walks into them. In 48 of the 52 north runs at least one of those links was re-aimed by a clone. 100 runs, **all 100 in sync**, 31 of them crashing on the same tick in both (mostly Chip taking a re-aimed teleport). A teleport whose partner is on row 16 or below has a link high byte of `80` or more, which reads as an object, so the clone cannot leave there.

**Monster templates** (`tools/measure/edgeclone.py`, `TYPES=2,3,4,5,6,8,9,10,11`, with `IDLE=1` and without): every monster type cloned off row 0 (N) and row 31 (S) in all 32 columns, Chip sliding or standing: 1152 runs; plus the two side corners (0, 0) W and (31, 31) E: 36 runs. **All 1188 in sync**, none crashing. Unlike a block, a cloned monster keeps going: past the top it comes back in at the bottom (its y wraps to row 31 and it carries on through the map), past the bottom it wanders the object table's rows and re-enters at the top, so the machine is free again: most runs reach two released copies plus the template within 300 ticks (at most 5 objects in all).

## 24. A monster in slot 0

`tools/measure/slot0mon.py SEED 100` (seeds 1–4): slot 0, the slot the game treats as Chip, holds a real monster type or a block (each of the ten types 40 times), standing or moving, in a random 15 × 15 room of floor, walls, ice, ice corners, force floors, fire, water, dirt, gravel, chips, keys, doors, boots, buttons, thief, popup walls, teleports, bombs and an exit, with up to three other monsters, random boots and random joystick input, 200 ticks. **400 runs, all 400 in sync**, none crashing. The joystick has no effect: slot 0 runs its own type's decision (a monster its AI, a block nothing), while the slot-0 rules of doc 03 (fire and water kill whatever stands in slot 0) still apply.

**Items and hazards** (`tools/measure/slot0inv.py`, plus a fixed table: tank, glider, bug, fireball and a force-carried block, each in slot 0 and, as a control, in slot 1, run down a column over each of 25 tile kinds; boots, keys, chips left and the clock compared every tick): all in sync. Note that the level start turns slot 0 to face south, whatever its type. What slot 0 does as a non-Chip type:

| Tile | Slot 0 (any type) | Same object in slot 1 |
|---|---|---|
| Red / blue key | picked up: the key is added to the inventory, tile becomes floor | red key: walked over; blue key: destroyed |
| Fire | dies (fireballs and blocks too) | fireball and block unharmed |
| Water | drowns (gliders too; a block drowns instead of turning into dirt) | glider swims; block becomes dirt |
| Chips, boots, yellow / green keys, doors, exit, socket, thief, hint, dirt, popup and blue walls | not reachable: entering them depends on the type (only Chip's class may enter), so a slot-0 monster is blocked like any monster | same |
| Bomb | explodes, as for any mover | same |

So a monster in slot 0 cannot collect chips or boots, or walk onto the exit; it does collect the keys it can walk onto. Starting on the exit is different: whatever is in slot 0 wins on the first tick if it is still standing there (a block; a tank walled in), while a free monster has already moved off (tank, glider, bug, fireball, teeth: no win). All in sync with the remake.

## 25. Ghost references (an object reference with no object there)

`tools/measure/ghost.py SEED 100` (seeds 1–4): one map cell of the level data holds `80 | k`, where slot k is empty, a live object elsewhere (any type), a dying effect elsewhere, Chip (elsewhere), or the mover itself. Movers heading into it: Chip with random input, every monster type, a block Chip pushes, objects sliding on ice or carried by a force floor; 80 ticks, A start. 400 runs.

| Remake | In sync |
|---|---|
| Before: the loader kept such a byte as a *tile* code (`80`–`FF`) | 111 of 400 |
| After: the loader reads it as an object reference (`80 | k` → object k), as the original does | **400 of 400** |

What the original does with a ghost, by the rules of doc 04 §3 applied to slot k: a monster or block treats it as an object in the way (blocked); one that "bumps into" a dying slot k erases it; Chip walking into it is handled as touching object k: most of those runs end in a crash (49 of 80, on the same tick in both; none when k is a live object elsewhere), as in the Jacques 516 trace of §13, where Chip touches a reference to an empty slot. Real levels never hold such bytes, so no replay changed (all still match).

**Objects starting on a ghost** (`tools/measure/ghost2.py`): the same five ghost kinds, now with an object placed on the ghost cell at the start, so its under-tile is the reference: Chip with random input, a monster, a block Chip pushes off, a monster sliding on ice, and a tank that drives off before Chip walks into the cell it left (where the ghost is back on the map). 50 runs, **all 50 in sync**, 20 of them crashing on the same tick in both.

**Fake Chip on `71`** (`tools/measure/fakechip71.py`): a fake Chip carried by force floors onto `71`, `4A` and `43` from all four directions, real Chip with and without skates: all 24 in sync once the remake stops re-moving a fake Chip on arrival at `71`. That turned out to be timing: with writes to the sound-driver byte blocked, every Chip-type arrival on `71` follows the byte (doc 04 §4.4), so the remake now flags them all. A wider survey with 2–6 fake Chips per room among the redirect codes (`tools/measure/fakechipsurvey.py`, 600 rooms) had 14 differences without the notice; all 14 were such arrivals and now carry the notice (0 left). The redirect survey above is also still at 0, and all real replays still match.

## 26. Deterministic variants of the MS sets (Joshie, Jacques)

`tools/measure/msvariants.py`: the MS-ruleset solution files on changed levels, current protocol (A on tick 0). Only replays that do not win on the original and whose level has blobs, walkers or random force floors (`09`). Three variants: **none** (blobs and walkers removed, random force floors made plain floor); **override** (blobs and walkers removed, random force floors kept, and before every tick R is set so the next use gives the direction MSCC gave, in order, from Tile World's MS-mode log of the same solution); **override + blobs/walkers** (only the force floors overridden).

| Variant | Jacques levels | Jacques wins | Joshie levels | Joshie wins |
|---|---|---|---|---|
| none | 485 | **12** (68, 74, 182, 252, 289, 410, 537, 615, 617, 635, 785, 844) | 475 | **7** (53, 151, 225, 421, 432, 623, 979) |
| override | 81 | 0 | 130 | 0 |
| override + blobs/walkers | 49 | 0 | 79 | 0 |

The remake matches all 19 wins tick for tick. Overriding the random floors with MSCC's own directions wins nothing: the MS solutions part from the Lynx game for movement reasons long before the floors matter (as found with the earlier static-floor attempt, `remake/ideas.md`), and the order in which objects use the floors also differs between the two games. Two of the wins need a random floor gone (Jacques 617, Joshie 151); the other 17 only need blobs and walkers gone.

## 27. Chip starting on a tile

Chip placed on each of 25 tile kinds at the start, no input, A on tick 0; objects, map, boots, keys, chips left, finished flag and clock compared every tick: all in sync. The start tile's handler runs on the first tick (as STAY), so Chip picks up keys and boots he starts on, wins at once on the exit, drowns in water, is pushed by a force floor, opens a socket (becomes floor, chips left or not), turns dirt and the fake blue wall to floor and a popup wall to wall (with him inside). Not affected: a counted chip (not picked up, chips left unchanged), fire and bombs (he survives), ice, hint, buttons, teleport, trap, thief. This is Tile World's "pedantic Lynx" start-tile behaviour. It needs Chip still on the tile on that tick: a level started with A or B shows it, one started with a direction does not (he walks off first and collects nothing); only the exit wins either way (checked with a key-and-door demo level).

*Not matched, by choice:* after any win the original's finished flag goes from 1 to 2 on the next tick; the remake leaves it at 1. Nothing reads it after a win, since the attempt ends there.

## 28. Tile World's lxbugs.txt (known Lynx-only behaviours)

Brian Raiter's `lxbugs.txt` (the c4 text format, read with c4's built-in tile characters plus each level's own `tiles` list; `tools/measure/lxbugs.py`, `lxbugs_check.py`) describes seven Lynx behaviours Tile World did not reproduce at the time. Each level was built as a cartridge level and run on the original and the remake in lock-step with the described action, with the level started the cartridge's usual way (the first press starts everything). All runs are in sync, and the original shows every behaviour described:

| Level | Action | Original (and remake) |
|---|---|---|
| Stuck Teleport I | move W | Chip alternates between the two teleports (39 changes); dies at tick 45 on the top teleport |
| Stuck Teleport II, III | move W | Chip alternates teleports; after the green button both blocks are pushed W, at once |
| Ghost Block | none / walk to a teleport | the block alternates between the teleports every tick; Chip arriving pushes it off (here to the north) |
| Mag-Lev | push the block onto the force floor, then N | without suction boots it stays; after picking them up it goes N into the water (water becomes dirt) |
| Pushback | move and hold S | Chip holds the cloned block back as long as he pushes S; he is killed the tick after letting go |
| Pass Through | walk N | the glider cannot teleport (Chip is on the far teleport), they collide, and the game hangs (tick 16) |

Pushback depends on the start: with the A-button start of the replay protocol (§6) the monsters move from tick 0, the block comes up the force floors before Chip gets there, and he is killed at once; with the level started by Chip's first press he reaches the cell above the force floors in time.

