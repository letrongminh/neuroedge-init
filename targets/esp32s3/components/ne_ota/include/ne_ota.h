/*
 * Firmware update on the ESP32-S3 — A/B, signed, with local rollback
 * (FR-OTA-01..04, TSK-S6-01/02/04).
 *
 * The device never evaluates trust: it runs the image the bootloader picked,
 * runs the same gate self-test it runs every boot, and only then tells the
 * bootloader the image may stay. An image that boots as PENDING_VERIFY is
 * marked valid here after the self-test passes; one whose self-test fails is
 * marked invalid and the device reboots into the previous app. An image that
 * panics or resets before this line, or that never gets there, is rolled back
 * by the bootloader on the next boot regardless (FR-OTA-02).
 *
 * Updates come from any HTTP(S) URL the user configures — no NeuroEdge
 * service, no account (FR-OTA-04). What the URL serves is verified with the
 * same RSA-3072 key that signed the running app before anything is switched;
 * a missing or wrong signature is refused and the running app stays
 * (FR-OTA-03, without Secure Boot). Plain HTTP is therefore acceptable for
 * integrity — the signature is the integrity — but it says nothing about
 * confidentiality; the documentation says so.
 *
 * The order main.c must use:
 *
 *     ne_ota_boot();                          // before the gate self-test
 *     ... run_gate_selftest() ...
 *     if (passed) ne_ota_boot_confirmed();    // pending: mark valid
 *     else        ne_ota_boot_rejected();     // pending: mark invalid, reboot
 *                                             // factory: returns; stop the runtime
 *     ... gate runtime up ...
 *     ne_ota_run();                           // no-op unless a URL is configured
 *
 * Everything the component says on the UART is one anchored marker line per
 * event (`NE_OTA …`), built by ne_ota_policy.c; credentials never appear.
 */
#ifndef NE_OTA_H
#define NE_OTA_H

#include <stdbool.h>

#include "ne_ota_policy.h"

#ifdef __cplusplus
extern "C" {
#endif

/* The running partition's state, the last rollback if there was one. */
void ne_ota_boot(void);

/*
 * The gate self-test passed. A pending image is marked valid, named, and its
 * version becomes the NVS high-water mark (no update at or below it is
 * installed). If the mark-valid call itself fails the choice is fail-closed:
 * when the bootloader could roll back, reboot and let it — an image whose
 * confirmation did not stick must not be the one that keeps running; when no
 * rollback exists (nothing else to boot), a self-test-passing image is better
 * than none, so it stays and only the VALID marker is withheld.
 */
void ne_ota_boot_confirmed(void);

/*
 * The gate self-test failed. A pending image is marked invalid and the device
 * reboots into the previous app; on success this does not return. On a factory
 * image there is nothing to mark: it returns, and the caller must stop the
 * gate runtime (as it does without OTA).
 */
void ne_ota_boot_rejected(void);

/* One update check: fetch, verify, switch, reboot — or refuse and stay. */
void ne_ota_run(void);

#ifdef __cplusplus
}
#endif

#endif /* NE_OTA_H */
