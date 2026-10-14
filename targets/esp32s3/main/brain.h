/*
 * The brain in the image (Profile B, TSK-I2f-14): brain.c. NEUROEDGE_BRAIN is 1 when
 * `neuroedge build --brain neuroclaw` put NeuroClaw-ESP into the project (main/CMakeLists.txt).
 */
#ifndef NEUROEDGE_MAIN_BRAIN_H
#define NEUROEDGE_MAIN_BRAIN_H

#include <stdbool.h>

#include "ne_trace.h"

#ifndef NEUROEDGE_BRAIN
#define NEUROEDGE_BRAIN 0
#endif

#if NEUROEDGE_BRAIN
/* The bridge, `risk=single_chip`, the brain's console commands: before the console starts. */
void brain_prepare(void);
/* DP-B-12: every decision from now on is an NE1 session with this device_info. */
void brain_trace(const ne_device_info *info);
/* DP-B-15: 0 when the bridge lists the tools and refuses an unknown one. */
int brain_selftest(void);
/* DP-B-11: the image's one Wi-Fi start, from ne_config; true when an SSID is set. */
bool brain_network(void);
/* No network in this image's run (QEMU): TCP/IP only, so the brain fails as offline. */
void brain_offline(void);
/* NeuroClaw-ESP on the bridge, its workspace on `ws`, its settings from ne_config. */
void brain_start(void);
#endif

#endif /* NEUROEDGE_MAIN_BRAIN_H */
