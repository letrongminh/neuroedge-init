/*
 * Host runner for the version rule (TSK-S6-01/02).
 *
 * One argument per version; one line per argument, `1` when
 * `ne_ota_parse_version` accepts it, `0` otherwise.
 * python/tests/test_ota_version_rule.py compiles this with ne_ota_policy.c
 * and compares every answer with `_RELEASE` in
 * python/neuroedge/engine/firmware.py — the build and the device must agree
 * on what a version is, or one side lets through what the other refuses.
 */
#include <stdio.h>

#include "ne_ota_policy.h"

int main(int argc, char **argv) {
    for (int i = 1; i < argc; i++) {
        uint32_t parts[3];
        printf("%d\n", ne_ota_parse_version(argv[i], parts) ? 1 : 0);
    }
    return 0;
}
