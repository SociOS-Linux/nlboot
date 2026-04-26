# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation.

It is intentionally small and safe-by-default:

- validates signed-boot-manifest-shaped objects before planning boot/recovery
- validates one-time enrollment token intent and audience
- produces a boot plan as JSON
- never downloads artifacts, writes disks, kexecs, or mutates a host in this reference slice

This repository starts as a protocol implementation home, not a full bootloader.
