/*
 * NeuroEdge device HAL, digital.out — C99, no allocation, no globals, no recursion.
 *
 * The one door from firmware to a pin (TSK-S4-01, DP-B-08 of docs/spec/deployment_profiles.md):
 * driving a pin active needs a token this boot's ledger issued for an ALLOW, for that pin, once,
 * within its TTL (`ne_token_authorize`); a refusal leaves the pin as it is and says why. Driving
 * a pin inactive is the safe state and is never refused, as on the host (`digital.out().off()`,
 * the end of an on-time, `hal.close()`: python/neuroedge/mcp_server.py, RFC-0011 section 3d).
 *
 * The platform part is `ne_pin_writer`: gpio_set_level on ESP-IDF, a fake in the host tests
 * (python/tests/test_c_hal.py). Nothing else in the image writes a pin.
 */
#ifndef NE_HAL_H
#define NE_HAL_H

#include <stdint.h>

#include "ne_token.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Writes one level to one pin; 0 on success. */
typedef struct {
    void *ctx;
    int (*write)(void *ctx, uint32_t pin, uint8_t level);
} ne_pin_writer;

typedef struct {
    ne_pin_writer writer;
    ne_ledger *ledger;
    uint32_t pin_count; /* pins 0 .. pin_count-1, at most NE_MAX_PINS */
} ne_hal;

typedef enum {
    NE_HAL_OK = 0,
    NE_HAL_REFUSED = 1,  /* the token does not allow it: `why` says which way */
    NE_HAL_ARGUMENT = 2, /* NULL, or a pin the board does not have */
    NE_HAL_IO = 3        /* the writer failed */
} ne_hal_status;

/* `pin` active, on `token`, at `now_ms`. Anything but NE_HAL_OK: the pin did not move. */
ne_hal_status ne_hal_on(const ne_hal *hal, const ne_token *token, uint32_t pin, uint32_t now_ms,
                        ne_token_reason *why);

/* `pin` inactive: the safe state, never refused for want of a token. */
ne_hal_status ne_hal_off(const ne_hal *hal, uint32_t pin);

#ifdef __cplusplus
}
#endif

#endif /* NE_HAL_H */
