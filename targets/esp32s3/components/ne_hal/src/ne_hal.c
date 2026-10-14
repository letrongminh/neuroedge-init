/* NeuroEdge device HAL, digital.out — see ne_hal.h. */
#include "ne_hal.h"

#include <stddef.h>

ne_hal_status ne_hal_on(const ne_hal *hal, const ne_token *token, uint32_t pin, uint32_t now_ms,
                        ne_token_reason *why)
{
    ne_token_reason reason = NE_TOKEN_NOT_A_TOKEN;
    if (why != NULL) *why = reason;
    if (hal == NULL || hal->writer.write == NULL || hal->ledger == NULL ||
        hal->pin_count > NE_MAX_PINS || pin >= hal->pin_count) {
        return NE_HAL_ARGUMENT;
    }
    if (token == NULL) return NE_HAL_REFUSED; /* no token, no action */
    reason = ne_token_authorize(hal->ledger, token, pin, now_ms);
    if (why != NULL) *why = reason;
    if (reason != NE_TOKEN_AUTHORIZED) return NE_HAL_REFUSED;
    return hal->writer.write(hal->writer.ctx, pin, 1u) == 0 ? NE_HAL_OK : NE_HAL_IO;
}

ne_hal_status ne_hal_off(const ne_hal *hal, uint32_t pin)
{
    if (hal == NULL || hal->writer.write == NULL || hal->pin_count > NE_MAX_PINS ||
        pin >= hal->pin_count) {
        return NE_HAL_ARGUMENT;
    }
    return hal->writer.write(hal->writer.ctx, pin, 0u) == 0 ? NE_HAL_OK : NE_HAL_IO;
}
