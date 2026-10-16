# With the brain (Profile B, TSK-I2f-14): `neuroedge build --brain neuroclaw` puts
# components/neuroclaw/ and components/ne_brain_bridge/ into the project; main then also
# builds brain.c, which starts NeuroClaw-ESP on the bridge (main/brain.h).
set(neuroedge_srcs "main.c" "memory_probe.c" "gate_selftest.c" "trace_vectors.c")
set(neuroedge_requires
    ne_agent
    ne_gate
    ne_trace
    ne_ota
    ne_boot
    ne_config
    ne_console
    esp_system
    esp_wifi
    esp_netif
    esp_event
    esp_http_client
    nvs_flash
    driver
    esp_timer
    heap
)
set(neuroedge_brain FALSE)
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/../components/neuroclaw/CMakeLists.txt")
    set(neuroedge_brain TRUE)
    list(APPEND neuroedge_srcs "brain.c")
    list(APPEND neuroedge_requires neuroclaw ne_brain_bridge ne_hal console joltwallet__littlefs)
endif()

idf_component_register(
    SRCS ${neuroedge_srcs}
    INCLUDE_DIRS "."
    REQUIRES ${neuroedge_requires}
)
if(neuroedge_brain)
    target_compile_definitions(${COMPONENT_LIB} PRIVATE NEUROEDGE_BRAIN=1)
endif()
if(neuroedge_brain)
    # NeuroClaw-ESP is pinned by SHA (DP-B-01) and not ours to edit. Built at -O2 here
    # (CONFIG_COMPILER_OPTIMIZATION_PERF), GCC 14 sees a possible truncation in one of its
    # snprintf calls (nc_brain.c, a bounded buffer): a warning in its code, never an error.
    idf_component_get_property(neuroclaw_lib neuroclaw COMPONENT_LIB)
    target_compile_options(${neuroclaw_lib} PRIVATE -Wno-error=format-truncation)
endif()
