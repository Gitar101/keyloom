# Supported device protocol

Scope: the wired Apex100/GZS68 device, USB VID/PID `28E9:31A3`, interface 1, vendor usage page `FF87`, usage `0020`. Input and output reports must both be 64 bytes. Keyboard-input collections and wireless dongles are not targets.

The implementation is independent of the vendor application. Protocol behavior and native factory signatures were checked against its device-management routines. No vendor application binary is required or distributed.

## Report format

| Bytes | Meaning |
| --- | --- |
| 0 | Report ID `06` |
| 1 | Command |
| 2–3 | Little-endian byte offset |
| 4 | Payload/query length, at most 56 |
| 5–6 | Little-endian additive checksum |
| 7 | Zero on transmission; response status on receipt |
| 8–63 | Payload, zero-padded on transmission |

The checksum is the sum of bytes 1–63 with checksum bytes zeroed. Every outgoing report is initialized independently, including the unused tail of the final chunk.

## Allowlisted commands

- `12`: read 57 bytes of basic information. Byte 4 of the assembled payload gives the buffer slot count.
- `16`: read the factory key matrix, three bytes per buffer slot.
- `1D`: stream physical RGB, three bytes per buffer slot.

No other command is implemented. In particular there are no reset, bootloader, firmware, profile, macro, function-settings, or key-mapping writes.

The factory matrix is matched against native key signatures. These are not assumed to be ordinary USB usage bytes: modifiers and Fn have device-specific three-byte signatures. XML key-code labels alone are insufficient. All 68 physical keys must match uniquely before streaming begins. The tested device reports 128 slots; inactive/unmapped slots are zeroed. The serializer rejects counts beyond its 512-byte staging-buffer limit.

Each RGB report must receive a matching 64-byte acknowledgement. Response status `0F` or `FE` stops the session. Reads use a 150 ms timeout; an uncertain transaction is not retried because a late reply could be mistaken for a later chunk's acknowledgement. Stop is checked before each new report.

Complete frames continue while the picture is static. The first prototype suppressed identical colors for one second, which was consistent with firmware returning to an onboard animation between updates. The current implementation does not suppress them or send an unverified persistent mode switch. Acknowledgements demonstrate transport, not visual correctness on every firmware revision.
