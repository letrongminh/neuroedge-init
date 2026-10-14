/*
 * The brain in the image: NeuroClaw-ESP on the bridge (Q-79, Q-83 Profile B, TSK-I2f-14).
 * Compiled only when `neuroedge build --brain neuroclaw` put components/neuroclaw/ into the
 * project (main/CMakeLists.txt defines NEUROEDGE_BRAIN); docs/spec/deployment_profiles.md:
 *
 *   DP-B-02  brain and box talk through `nc_gate`: function calls, no MCP, no TLS server;
 *   DP-B-06  `ne_bridge_result` → `nc_tool_result`, field by field (ne_bridge_result_field);
 *   DP-B-07  an owner's answer reaches the bridge from NeuroClaw's Telegram callback, which
 *            already drops presses from anyone else (nc_core.c), so the glue names the owner
 *            it was configured with: the brain is trusted with that much under
 *            `risk=single_chip`; `brain_button` is the board's own way;
 *   DP-B-10  every setting comes from ne_config, read here and handed over once;
 *   DP-B-11  this image owns Wi-Fi (brain_network) and one console (ne_console), on which the
 *            brain registers its commands;
 *   DP-B-14  `risk=single_chip` at boot and in `status`;
 *   DP-B-15  brain_selftest: the bridge answers a tool list and a call before an update is kept.
 *
 * The bridge is one caller at a time: every call takes s_lock. Pins move only through
 * ne_hal_on on the call's own token; until the board HAL (TSK-S4-01) maps them to GPIOs the
 * writer prints `NE_PIN` lines, which is also what QEMU checks. Facts come from the fact
 * source below and never from the call's arguments (DP-B-05): on QEMU the console's
 * `fact` command stands in for sensors, on a board a fact the HAL does not read is absent
 * (the gate decides on absence, fail closed).
 */
#include "brain.h"

#if NEUROEDGE_BRAIN

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "esp_console.h"
#include "esp_event.h"
#include "esp_littlefs.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "ne_agent.h"
#include "ne_brain_bridge.h"
#include "ne_config.h"
#include "ne_console.h"
#include "ne_hal.h"
#include "neuroclaw.h"

static const char *TAG = "brain";

/* Statics of the application, never of the components (the bridge's own rule). */
static ne_bridge s_bridge;
static ne_ledger s_ledger;
static ne_bridge_result s_result;
static SemaphoreHandle_t s_lock;
static nc_tool s_tools[32];
static size_t s_tool_count;
static char s_owner[24];
static bool s_network;

static void wipe(void *p, size_t n);

/* --- facts (DP-B-05) ------------------------------------------------------------------------ */

#define BRAIN_FACTS 16u
/* NeuroClaw-ESP's start (LittleFS mount, session, system prompt) needs more than app_main's
 * 3.5 KB: it runs in a task of its own, whose stack goes back to the heap when it is done. */
#define BRAIN_START_STACK 8192u
typedef struct {
    char name[32];
    char value[32];
} brain_fact;
static brain_fact s_facts[BRAIN_FACTS];
static uint32_t s_fact_count;

#ifdef CONFIG_NEUROEDGE_QEMU /* the console's `fact`: sensors stand-in on QEMU only */
static void set_fact(const char *name, const char *value)
{
    for (uint32_t i = 0; i < s_fact_count; i++) {
        if (strcmp(s_facts[i].name, name) == 0) {
            snprintf(s_facts[i].value, sizeof s_facts[i].value, "%s", value);
            return;
        }
    }
    if (s_fact_count < BRAIN_FACTS) {
        snprintf(s_facts[s_fact_count].name, sizeof s_facts[0].name, "%s", name);
        snprintf(s_facts[s_fact_count].value, sizeof s_facts[0].value, "%s", value);
        s_fact_count++;
    }
}
#endif

static const brain_fact *find_fact(const char *name)
{
    for (uint32_t i = 0; i < s_fact_count; i++) {
        if (strcmp(s_facts[i].name, name) == 0) return &s_facts[i];
    }
    return NULL;
}

static ne_degraded read_facts(void *ctx, const ne_tree *gate, uint32_t gate_index, ne_fact *facts,
                              uint32_t count, uint32_t now)
{
    (void)ctx;
    (void)gate_index;
    (void)now;
    for (uint32_t i = 0; i < count; i++) {
        const char *name = ne_criterion_name(gate, i);
        const brain_fact *known = name ? find_fact(name) : NULL;
        if (known == NULL || strcmp(known->value, "-") == 0) continue; /* absent: present 0 */
        facts[i].present = 1;
        if (ne_criterion_kind(gate, i) == NE_KIND_NUMERIC) {
            facts[i].value = strtod(known->value, NULL);
            facts[i].age_ms = 0;
            continue;
        }
        for (uint32_t j = 0; j < NE_MAX_DOMAIN; j++) {
            const char *v = ne_domain_value(gate, i, j);
            if (v == NULL) break;
            if (strcmp(v, known->value) == 0) {
                facts[i].in_domain = 1;
                facts[i].index = (uint8_t)j;
            }
        }
    }
    return NE_DEGRADED_NONE;
}

/* --- pins, clock, randomness ---------------------------------------------------------------- */

static uint32_t now_ms(void *ctx)
{
    (void)ctx;
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static int write_pin(void *ctx, uint32_t pin, uint8_t level)
{
    (void)ctx;
#ifdef CONFIG_NEUROEDGE_QEMU
    /* The emulator's pins are these lines: what QEMU checks, and what the trace says moved. */
    printf("NE_PIN pin=%s level=%u\n", ne_agent_linked.pins[pin], (unsigned)level);
    return 0;
#else
    /* No GPIO number for this pin until the board HAL (TSK-S4-01): nothing moved, and the
     * trace must not say it did. */
    (void)level;
    printf("NE_PIN pin=%s unmapped\n", ne_agent_linked.pins[pin]);
    return -1;
#endif
}

/* A pulse ends on a one-shot timer: the pin goes back to its safe state (ne_hal_off). */
static esp_timer_handle_t s_pulse[NE_MAX_PINS];

static void pulse_over(void *arg)
{
    const uint32_t pin = (uint32_t)(uintptr_t)arg;
    const ne_hal hal = {{NULL, write_pin}, &s_ledger, ne_agent_linked.pin_count};
    ne_hal_off(&hal, pin);
}

static void schedule_off(uint32_t pin, uint32_t ms)
{
    if (s_pulse[pin] == NULL) {
        const esp_timer_create_args_t timer = {
            .callback = pulse_over,
            .arg = (void *)(uintptr_t)pin,
            .name = "ne_pulse",
        };
        if (esp_timer_create(&timer, &s_pulse[pin]) != ESP_OK) {
            pulse_over((void *)(uintptr_t)pin); /* no timer, no pulse: back to safe now */
            return;
        }
    }
    esp_timer_stop(s_pulse[pin]); /* a new pulse restarts the count */
    esp_timer_start_once(s_pulse[pin], (uint64_t)ms * 1000u);
}

static void run(void *ctx, uint32_t action, const ne_arg_value *args, uint32_t arg_count,
                ne_ledger *ledger, const ne_token *token)
{
    /* What the action's body does (ne_agent_pin_op, recorded at build time), through the one
     * door to a pin (DP-B-08): `on` and a pulse need the token; `off` is the safe state. */
    (void)ctx;
    const ne_agent_action *a = &ne_agent_linked.actions[action];
    const ne_hal hal = {{NULL, write_pin}, ledger, ne_agent_linked.pin_count};
    for (uint32_t k = 0; k < a->op_count; k++) {
        const ne_agent_pin_op *op = &a->ops[k];
        ne_token_reason why = NE_TOKEN_AUTHORIZED;
        if (op->pin >= ne_agent_linked.pin_count || op->pin >= 32u) {
            printf("NE_PIN index=%u refused=no_such_pin\n", (unsigned)op->pin);
            continue;
        }
        if (!(a->pin_mask & (1u << op->pin)) || op->op == NE_AGENT_OP_UNSUPPORTED) {
            printf("NE_PIN pin=%s refused=unsupported\n", ne_agent_linked.pins[op->pin]);
            continue;
        }
        if (op->op == NE_AGENT_OP_OFF) {
            const int driven = ne_hal_off(&hal, op->pin) == NE_HAL_OK;
            ne_bridge_trace_pin(&s_bridge, op->pin, driven, "off", 0u, why);
            continue;
        }
        const uint32_t ms = ne_bridge_pulse_ms(&s_bridge, action, op, args, arg_count);
        if (op->op == NE_AGENT_OP_PULSE && ms == 0u) {
            printf("NE_PIN pin=%s refused=no_duration\n", ne_agent_linked.pins[op->pin]);
            continue;
        }
        const int driven = ne_hal_on(&hal, token, op->pin, now_ms(NULL), &why) == NE_HAL_OK;
        if (!driven) {
            printf("NE_PIN pin=%s refused=%s\n", ne_agent_linked.pins[op->pin],
                   ne_token_reason_name(why));
        } else if (op->op == NE_AGENT_OP_PULSE) {
            schedule_off(op->pin, ms);
        }
        ne_bridge_trace_pin(&s_bridge, op->pin, driven, op->op == NE_AGENT_OP_PULSE ? "pulse" : "on",
                            ms, why);
    }
    printf("NE_ACTION %s\n", a->name);
}

/* --- ne_bridge_result → nc_tool_result (DP-B-06) -------------------------------------------- */

static void field(const char *object, const char *name, char *out, size_t cap)
{
    ne_bridge_result_field(&s_result, object, name, out, (uint32_t)cap);
}

static void to_nc(nc_tool_result *out)
{
    memset(out, 0, sizeof *out);
    out->status = s_result.status == NE_BRIDGE_ALLOW   ? NC_ALLOW
                  : s_result.status == NE_BRIDGE_BLOCK ? NC_BLOCK
                                                       : NC_REJECTED;
    field(NULL, "reason", out->reason, sizeof out->reason);
    field(NULL, "failed_criterion", out->failed_criterion, sizeof out->failed_criterion);
    field(NULL, "message", out->message, sizeof out->message);
    if (out->message[0] == '\0') field(NULL, "problems", out->message, sizeof out->message);
    if (out->message[0] == '\0') {
        char to[48];
        field(NULL, "escalated_to", to, sizeof to);
        if (to[0] != '\0') snprintf(out->message, sizeof out->message, "passed to %s", to);
    }
    field("confirmation", "id", out->confirmation_id, sizeof out->confirmation_id);
    out->asks_owner = out->confirmation_id[0] != '\0';
    if (out->asks_owner) {
        char ttl[16];
        field("confirmation", "message", out->confirmation_message,
              sizeof out->confirmation_message);
        field("confirmation", "expires_in_ms", ttl, sizeof ttl);
        out->expires_in_ms = (uint32_t)strtoul(ttl, NULL, 10);
    }
}

/* --- nc_gate ------------------------------------------------------------------------------- */

static size_t gate_tools(void *ctx, const nc_tool **out)
{
    (void)ctx;
    *out = s_tools;
    return s_tool_count;
}

static void gate_call(void *ctx, const char *name, const char *arguments_json, nc_tool_result *out)
{
    (void)ctx;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    ne_bridge_call(&s_bridge, name, arguments_json, &s_result);
    to_nc(out);
    xSemaphoreGive(s_lock);
}

static void gate_answer(void *ctx, const char *confirmation_id, bool approve, nc_tool_result *out)
{
    (void)ctx;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    ne_bridge_answer(&s_bridge, confirmation_id, approve ? 1 : 0, s_owner, &s_result);
    to_nc(out);
    xSemaphoreGive(s_lock);
}

static const nc_gate s_gate = {NULL, gate_tools, gate_call, gate_answer};

/* --- the console: QEMU's sensor stand-in and the board button ------------------------------- */

#ifdef CONFIG_NEUROEDGE_QEMU
static int cmd_fact(int argc, char **argv)
{
    if (argc != 3) {
        printf("Usage: fact <name> <value|->  (QEMU only: stands in for the board's sensors)\n");
        return 1;
    }
    set_fact(argv[1], argv[2]);
    printf("NE_FACT %s=%s\n", argv[1], argv[2]);
    return 0;
}
#endif

/* `key=value` words → a JSON object: a number stays a number, anything else is a string. */
static int button_arguments(int argc, char **argv, char *out, size_t cap)
{
    size_t n = (size_t)snprintf(out, cap, "{");
    for (int i = 2; i < argc && n < cap; i++) {
        char *eq = strchr(argv[i], '=');
        if (eq == NULL || eq == argv[i] || strpbrk(argv[i], "\"\\") != NULL) return -1;
        *eq = '\0';
        char *end = NULL;
        strtod(eq + 1, &end);
        const bool number = end != eq + 1 && *end == '\0';
        n += (size_t)snprintf(out + n, cap - n, number ? "%s\"%s\":%s" : "%s\"%s\":\"%s\"",
                              i > 2 ? "," : "", argv[i], eq + 1);
    }
    if (n + 2 > cap) return -1;
    out[n++] = '}';
    out[n] = '\0';
    return 0;
}

static int cmd_button(int argc, char **argv)
{
    /* button <action> [key=value ...]: a board button bound to an action, decided by the gate
     * like any call, with or without the network (DP-B-16);
     * button <confirm_N> yes|no: the board's answer to a question it shows (DP-B-07). */
    static char args[NE_BRIDGE_ARGS_MAX];
    if (argc == 3 && strncmp(argv[1], "confirm_", 8) == 0) {
        xSemaphoreTake(s_lock, portMAX_DELAY);
        ne_bridge_answer_button(&s_bridge, argv[1], strcmp(argv[2], "yes") == 0, &s_result);
        printf("NE_BUTTON %s\n", s_result.json);
        xSemaphoreGive(s_lock);
        return 0;
    }
    if (argc >= 2 && button_arguments(argc, argv, args, sizeof args) == 0) {
        xSemaphoreTake(s_lock, portMAX_DELAY);
        ne_bridge_call(&s_bridge, argv[1], args, &s_result);
        printf("NE_BUTTON %s\n", s_result.json);
        xSemaphoreGive(s_lock);
        return 0;
    }
    printf("Usage: button <action> [key=value ...] | button <confirm_N> yes|no\n");
    return 1;
}

static int cmd_tasks(int argc, char **argv)
{
    /* DP-B-13: each task's lowest free stack so far (`main` reports once, before NE_TRACE DONE) */
    (void)argc;
    (void)argv;
    static const struct {
        const char *name;
        unsigned size;
    } TASKS[] = {
        {"neuroclaw", CONFIG_NEUROCLAW_TASK_STACK},
        {"ne_console", CONFIG_NEUROEDGE_CONSOLE_STACK},
    };
    for (size_t i = 0; i < sizeof TASKS / sizeof TASKS[0]; i++) {
        TaskHandle_t task = xTaskGetHandle(TASKS[i].name);
        if (task == NULL) {
            printf("NE_STACK task=%s absent\n", TASKS[i].name);
            continue;
        }
        printf("NE_STACK task=%s free_min=%u size=%u\n", TASKS[i].name,
               (unsigned)uxTaskGetStackHighWaterMark(task), TASKS[i].size);
    }
    return 0;
}

static esp_err_t register_commands(void)
{
    const esp_console_cmd_t button = {
        .command = "button",
        .help = "A board button: `button <action>`, or `button <confirm_N> yes|no`",
        .func = cmd_button,
    };
    esp_err_t err = esp_console_cmd_register(&button);
    const esp_console_cmd_t tasks = {
        .command = "tasks",
        .help = "Each task's lowest free stack so far (NE_STACK lines)",
        .func = cmd_tasks,
    };
    if (err == ESP_OK) err = esp_console_cmd_register(&tasks);
#ifdef CONFIG_NEUROEDGE_QEMU
    const esp_console_cmd_t fact = {
        .command = "fact",
        .help = "QEMU only: set a fact the sensors would read (`fact daytime false`)",
        .func = cmd_fact,
    };
    if (err == ESP_OK) err = esp_console_cmd_register(&fact);
#endif
    if (err == ESP_OK) err = neuroclaw_console_register();
    return err;
}

/* --- the run-time trace (DP-B-12) ----------------------------------------------------------- */

static void trace_line(void *ctx, const char *line)
{
    (void)ctx;
    printf("%s\n", line); /* one call per line: nothing else can split it */
}

static char s_trace_buf[NE_TRACE_LINE_MAX + 1];
static ne_trace_sink s_trace = {trace_line, NULL, NULL, s_trace_buf, sizeof s_trace_buf, 0, 0, 0};
static char s_device[24];
static ne_device_info s_info;

void brain_trace(const ne_device_info *info)
{
    snprintf(s_device, sizeof s_device, "%s", info->device_id);
    s_info = *info;
    s_info.device_id = s_device;
    s_info.replay_of = NULL;
    s_info.trace_digest = NULL;
    s_trace.now_ms = now_ms;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    ne_bridge_trace(&s_bridge, &s_trace, &s_info);
    xSemaphoreGive(s_lock);
}

/* --- start-up ------------------------------------------------------------------------------- */

void brain_prepare(void)
{
    s_lock = xSemaphoreCreateMutex();
    ne_ledger_init(&s_ledger, esp_random());
    static const ne_fact_source source = {NULL, read_facts};
    static const ne_bridge_hal hal = {NULL, now_ms, esp_fill_random, run};
    if (ne_config_get("telegram.owner", s_owner, sizeof s_owner) != ESP_OK) s_owner[0] = '\0';
    if (ne_bridge_init(&s_bridge, &ne_agent_linked, &s_ledger, &source, &hal,
                       s_owner[0] ? s_owner : NULL) != 0) {
        ESP_LOGE(TAG, "the bridge did not start");
    }
    s_tool_count = 0;
    for (uint32_t i = 0; i < ne_bridge_tool_count(&s_bridge) && s_tool_count < 32u; i++) {
        nc_tool *t = &s_tools[s_tool_count];
        if (ne_bridge_tool(&s_bridge, i, &t->name, &t->description, &t->parameters) == 0) {
            s_tool_count++;
        }
    }
    printf("NE_RISK risk=single_chip\n"); /* DP-B-14: brain and box share this chip */
    ne_console_add_risk("single_chip");
    ne_console_add_commands(register_commands);
}

int brain_selftest(void)
{
#if CONFIG_NEUROEDGE_OTA_TEST_FAIL_BRAIN
    printf("NE_BRAIN SELFTEST FAIL test image NEUROEDGE_OTA_TEST_FAIL_BRAIN\n");
    return -1;
#endif
    /* DP-B-15: the tools are listed and an unknown tool is refused, through the bridge. */
    if (s_tool_count == 0u || s_tool_count != ne_agent_linked.action_count) return -1;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    ne_bridge_call(&s_bridge, "__brain_selftest__", "{}", &s_result);
    const int ok = s_result.status == NE_BRIDGE_REJECTED;
    xSemaphoreGive(s_lock);
    printf("NE_BRAIN SELFTEST %s tools=%u\n", ok ? "PASS" : "FAIL", (unsigned)s_tool_count);
    return ok ? 0 : -1;
}

static void on_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    (void)data;
    if (base == WIFI_EVENT && (id == WIFI_EVENT_STA_START || id == WIFI_EVENT_STA_DISCONNECTED)) {
        esp_wifi_connect();
    }
}

bool brain_network(void)
{
    /* DP-B-11: the only Wi-Fi start in the image (NeuroClaw-ESP never starts it). */
    wifi_config_t config = {0};
    char ssid[33] = "";
    char pass[65] = "";
    ne_config_get("wifi.ssid", ssid, sizeof ssid);
    ne_config_get("wifi.pass", pass, sizeof pass);
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    const wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_event, NULL));
    memcpy(config.sta.ssid, ssid, strlen(ssid));
    memcpy(config.sta.password, pass, strlen(pass));
    wipe(pass, sizeof pass);
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &config));
    wipe(&config, sizeof config);
    ESP_ERROR_CHECK(esp_wifi_start());
    printf("NE_WIFI START owner=neuroedge ssid_set=%s\n", ssid[0] ? "yes" : "no");
    s_network = ssid[0] != '\0';
    return s_network;
}

void brain_offline(void)
{
    /* No Wi-Fi (QEMU, or a board with none set): TCP/IP still comes up, so the brain's sockets
     * fail as without a route instead of asserting; the board's buttons work as ever (DP-B-16). */
    esp_err_t err = esp_netif_init();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) ESP_LOGE(TAG, "esp_netif_init: %s", esp_err_to_name(err));
    err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "esp_event_loop_create_default: %s", esp_err_to_name(err));
    }
    printf("NE_WIFI OFF\n");
}

static bool wifi_rssi(int *dbm)
{
    wifi_ap_record_t ap;
    if (!s_network || esp_wifi_sta_get_ap_info(&ap) != ESP_OK) return false;
    *dbm = ap.rssi;
    return true;
}

/* A setting for the brain: heap, kept for the brain's lifetime (it strdups what it keeps). */
static char *setting(const char *name)
{
    char value[NE_CONFIG_VALUE_MAX + 1];
    if (ne_config_get(name, value, sizeof value) != ESP_OK || value[0] == '\0') return NULL;
    char *copy = strdup(value);
    wipe(value, sizeof value);
    return copy;
}

/* A wipe the compiler may not drop as a dead store before free() or a return. */
static void wipe(void *p, size_t n)
{
    volatile unsigned char *v = p;
    while (n--) *v++ = 0;
}

static void forget(char *secret)
{
    if (secret != NULL) {
        wipe(secret, strlen(secret));
        free(secret);
    }
}

static void start_brain(void)
{
    const esp_vfs_littlefs_conf_t fs = {
        .base_path = "/ws",
        .partition_label = "ws",
        .format_if_mount_failed = true,
    };
    if (esp_vfs_littlefs_register(&fs) != ESP_OK) {
        printf("NC_OFF missing=ws\n");
        return;
    }
    char *token = setting("telegram.token");
    char *llm_url = setting("llm.url");
    char *llm_key = setting("llm.key");
    char *llm_model = setting("llm.model");
    char *fb_url = setting("llm.fallback_url");
    char *fb_key = setting("llm.fallback_key");
    char *fb_model = setting("llm.fallback_model");
    char *search_key = setting("search.key");
    char *tz = setting("tz");
    const nc_config config = {
        .telegram_token = token,
        .owner_id = s_owner[0] ? s_owner : NULL,
        .llm_url = llm_url,
        .llm_key = llm_key,
        .llm_model = llm_model,
        .workspace = "/ws",
        .tz = tz,
        .search_provider = search_key ? "tavily" : NULL,
        .search_key = search_key,
        .llm_fallback_url = fb_url,
        .llm_fallback_key = fb_key,
        .llm_fallback_model = fb_model,
        .wifi_rssi = wifi_rssi,
    };
    /* NeuroClaw prints `NC_OFF missing=<key>` itself when a setting it needs is absent. */
    const int started = neuroclaw_start(&config, &s_gate);
    printf("NE_BRAIN %s\n", started == 0 ? "STARTED" : "OFF");
    /* neuroclaw_start copied the settings: none stays in this image's heap. */
    forget(token);
    forget(llm_url);
    forget(llm_key);
    forget(llm_model);
    forget(fb_url);
    forget(fb_key);
    forget(fb_model);
    forget(search_key);
    forget(tz);
}

static void start_task(void *waiting)
{
    start_brain();
    xTaskNotifyGive((TaskHandle_t)waiting);
    vTaskDelete(NULL);
}

void brain_start(void)
{
    if (xTaskCreate(start_task, "nc_start", BRAIN_START_STACK, xTaskGetCurrentTaskHandle(), 5,
                    NULL) != pdPASS) {
        printf("NE_BRAIN OFF\n");
        return;
    }
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY); /* main goes on once the brain has started, as before */
}

#endif /* NEUROEDGE_BRAIN */
