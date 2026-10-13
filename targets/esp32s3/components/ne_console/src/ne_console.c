/*
 * Serial console (ne_console.h). The REPL setup follows MimiClaw
 * main/cli/serial_cli.c (https://github.com/memovai/mimiclaw, commit dcc1c8c, MIT,
 * Copyright (c) 2026 Ziboyan Wang) and the ESP-IDF console example; the loop is
 * written out here instead of esp_console_new_repl_uart so a line that sets a
 * value is never kept in the history.
 */
#include "ne_console.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "esp_console.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "linenoise/linenoise.h"
#include "nvs.h"
#include "ne_boot_guard.h"
#include "ne_config.h"
#include "sdkconfig.h"

#define NE_CONSOLE_LINE_MAX 320

static const char *TAG = "ne_console";
static bool s_safe_mode;

/* --- reading a secret ------------------------------------------------------------------------ */

/*
 * One line from stdin with no echo. Returns the length, or -1 when the line did
 * not fit (the rest of it is still read and dropped, so it never reaches the
 * next prompt).
 */
static int read_hidden_line(char *out, size_t cap)
{
    size_t len = 0;
    bool overflow = false;
    while (true) {
        const int c = fgetc(stdin);
        if (c == EOF) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }
        if (c == '\n' || c == '\r') {
            if (len == 0 && !overflow) continue; /* the rest of a CR LF, or an empty Enter */
            break;
        }
        if (c == 0x08 || c == 0x7f) { /* backspace */
            if (len > 0) len--;
            continue;
        }
        if (len + 1 < cap) {
            out[len++] = (char)c;
        } else {
            overflow = true;
        }
    }
    out[len] = '\0';
    printf("\n");
    return overflow ? -1 : (int)len;
}

/* --- config ---------------------------------------------------------------------------------- */

static void print_value(const ne_config_key *key)
{
    char value[NE_CONFIG_VALUE_MAX + 1];
    char shown[NE_CONFIG_VALUE_MAX + 1];
    const esp_err_t err = ne_config_get(key->name, value, sizeof value);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        printf("%s = <error %s>\n", key->name, esp_err_to_name(err));
        return;
    }
    ne_config_display(key, err == ESP_OK ? value : NULL, shown, sizeof shown);
    memset(value, 0, sizeof value);
    printf("%s = %s\n", key->name, shown);
}

static void print_refused(const char *name, const char *reason)
{
    printf("NE_CONFIG REFUSED key=%s reason=%s\n", name, reason);
}

static int config_set(const ne_config_key *key, int argc, char **argv)
{
    char value[NE_CONFIG_VALUE_MAX + 1];
    if (key->secret) {
        if (argc > 3) {
            print_refused(key->name, "inline_secret");
            printf("Type `config set %s` and enter the value at the hidden prompt.\n", key->name);
            return 1;
        }
        printf("%s (hidden, Enter to finish): ", key->name);
        fflush(stdout);
        if (read_hidden_line(value, sizeof value) < 0) {
            memset(value, 0, sizeof value);
            print_refused(key->name, "too_long");
            return 1;
        }
    } else {
        if (argc != 4) {
            print_refused(key->name, argc < 4 ? "empty" : "format");
            printf("Usage: config set %s <value>   (%s)\n", key->name, key->help);
            return 1;
        }
        strlcpy(value, argv[3], sizeof value);
    }

    ne_config_verdict verdict = NE_CONFIG_OK;
    const esp_err_t err = ne_config_set(key->name, value, &verdict);
    const char *risk = ne_config_value_risk(key, value);
    memset(value, 0, sizeof value);
    if (verdict != NE_CONFIG_OK) {
        print_refused(key->name, ne_config_verdict_name(verdict));
        return 1;
    }
    if (err != ESP_OK) {
        printf("NE_CONFIG FAILED key=%s error=%s\n", key->name, esp_err_to_name(err));
        return 1;
    }
    printf("NE_CONFIG SET key=%s storage=%s", key->name,
           ne_config_storage_name(ne_config_storage_mode()));
    if (key->secret && ne_config_storage_risk() != NULL) {
        printf(" risk=%s", ne_config_storage_risk());
    }
    if (risk != NULL) printf(" risk=%s", risk);
    printf("\n");
    return 0;
}

static int cmd_config(int argc, char **argv)
{
    const char *sub = argc > 1 ? argv[1] : "list";
    if (strcmp(sub, "list") == 0) {
        size_t count = 0;
        const ne_config_key *keys = ne_config_keys(&count);
        for (size_t i = 0; i < count; i++) print_value(&keys[i]);
        return 0;
    }
    if (argc < 3) {
        printf("Usage: config list | get <key> | set <key> [value] | unset <key>\n");
        return 1;
    }
    const ne_config_key *key = ne_config_key_find(argv[2]);
    if (key == NULL) {
        print_refused(argv[2], "unknown_key");
        return 1;
    }
    if (strcmp(sub, "get") == 0) {
        print_value(key);
        return 0;
    }
    if (strcmp(sub, "set") == 0) return config_set(key, argc, argv);
    if (strcmp(sub, "unset") == 0) {
        const esp_err_t err = ne_config_unset(key->name);
        if (err != ESP_OK) {
            printf("NE_CONFIG FAILED key=%s error=%s\n", key->name, esp_err_to_name(err));
            return 1;
        }
        printf("NE_CONFIG UNSET key=%s\n", key->name);
        return 0;
    }
    printf("Usage: config list | get <key> | set <key> [value] | unset <key>\n");
    return 1;
}

/* --- the rest -------------------------------------------------------------------------------- */

static int cmd_status(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    const ne_boot_decision boot = ne_boot_guard_current();
    const char *risk = ne_config_storage_risk();
    /* stack_free: the console task's lowest free stack so far, in bytes (the
     * stack guard reads it after the deepest command, `config set`). */
    printf("NE_STATUS mode=%s boot=%lu/%lu storage=%s%s%s heap=%lu stack_free=%u stack=%u\n",
           s_safe_mode ? "safe" : "normal", (unsigned long)boot.count, (unsigned long)boot.max,
           ne_config_storage_name(ne_config_storage_mode()), risk ? " risk=" : "",
           risk ? risk : "", (unsigned long)esp_get_free_heap_size(),
           (unsigned)uxTaskGetStackHighWaterMark(NULL), (unsigned)CONFIG_NEUROEDGE_CONSOLE_STACK);
    return 0;
}

static int cmd_bootguard(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "clear") == 0) return ne_boot_guard_clear() == ESP_OK ? 0 : 1;
    const ne_boot_decision boot = ne_boot_guard_current();
    printf("boot %lu of %lu before safe mode; this boot: %s\n", (unsigned long)boot.count,
           (unsigned long)boot.max, s_safe_mode ? "safe mode" : "normal");
    printf("`bootguard clear` then `reboot` leaves safe mode.\n");
    return 0;
}

static int cmd_reboot(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    printf("NE_CONSOLE REBOOT\n");
    fflush(stdout);
    vTaskDelay(pdMS_TO_TICKS(100));
    esp_restart();
    return 0;
}

static int cmd_factory_reset(int argc, char **argv)
{
    if (argc != 2 || strcmp(argv[1], "confirm") != 0) {
        printf("Erases every setting and secret on this chip, then reboots.\n");
        printf("Type `factory-reset confirm` to go ahead.\n");
        return 1;
    }
    const esp_err_t err = ne_config_erase_all();
    if (err != ESP_OK) {
        printf("NE_CONFIG FAILED key=* error=%s\n", esp_err_to_name(err));
        return 1;
    }
    ne_boot_guard_clear();
    printf("NE_CONSOLE FACTORY_RESET\n");
    fflush(stdout);
    vTaskDelay(pdMS_TO_TICKS(100));
    esp_restart();
    return 0;
}

static void register_commands(void)
{
    const esp_console_cmd_t commands[] = {
        {.command = "status", .help = "Mode, boot count, storage, free heap", .func = cmd_status},
        {.command = "config",
         .help = "config list | get <key> | set <key> [value] | unset <key>. A secret is "
                 "typed at a hidden prompt.",
         .hint = "list|get|set|unset",
         .func = cmd_config},
        {.command = "bootguard",
         .help = "Show the boot count; `bootguard clear` resets it (then `reboot`)",
         .func = cmd_bootguard},
        {.command = "reboot", .help = "Restart the chip", .func = cmd_reboot},
        {.command = "factory-reset",
         .help = "`factory-reset confirm` erases every setting and secret, then reboots",
         .func = cmd_factory_reset},
    };
    for (size_t i = 0; i < sizeof commands / sizeof commands[0]; i++) {
        ESP_ERROR_CHECK(esp_console_cmd_register(&commands[i]));
    }
    ESP_ERROR_CHECK(esp_console_register_help_command());
}

/* --- the loop -------------------------------------------------------------------------------- */

static bool keep_in_history(const char *line)
{
    /* `config set` lines may carry a value; refused inline secrets too. */
    return strncmp(line, "config set", 10) != 0;
}

static void console_task(void *arg)
{
    (void)arg;
    const char *prompt = s_safe_mode ? "neuroedge(safe)> " : "neuroedge> ";
    /* READY before the terminal probe: the probe's escape sequence is not a line. */
    printf("NE_CONSOLE READY mode=%s\n", s_safe_mode ? "safe" : "normal");
    if (s_safe_mode) {
        printf("SAFE MODE: too many boots in a row did not stay up. Network and the gate runtime\n"
               "are off. `status`, `config list`, `bootguard clear` then `reboot`.\n");
    }
    fflush(stdout);
    if (linenoiseProbe() != 0) linenoiseSetDumbMode(1); /* a log file or a plain pipe */
    while (true) {
        char *line = linenoise(prompt);
        if (line == NULL) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }
        if (line[0] != '\0' && keep_in_history(line)) linenoiseHistoryAdd(line);
        int ret = 0;
        const esp_err_t err = esp_console_run(line, &ret);
        if (err == ESP_ERR_NOT_FOUND) {
            printf("Unknown command. `help` lists them.\n");
        } else if (err == ESP_ERR_INVALID_ARG) {
            /* an empty line */
        } else if (err != ESP_OK) {
            printf("Error: %s\n", esp_err_to_name(err));
        }
        memset(line, 0, strlen(line));
        linenoiseFree(line);
        fflush(stdout);
    }
}

esp_err_t ne_console_start(bool safe_mode)
{
    s_safe_mode = safe_mode;
#if !CONFIG_ESP_CONSOLE_UART
    /* A USB-Serial-JTAG console (the BOX-3 over its USB-C port) is not wired yet. */
    ESP_LOGW(TAG, "the serial console needs the console on a UART (CONFIG_ESP_CONSOLE_UART)");
    printf("NE_CONSOLE OFF reason=no_uart_console\n");
    return ESP_ERR_NOT_SUPPORTED;
#else
    const int port = CONFIG_ESP_CONSOLE_UART_NUM;

    fflush(stdout);
    fsync(fileno(stdout));
    setvbuf(stdin, NULL, _IONBF, 0);
    uart_vfs_dev_port_set_rx_line_endings(port, ESP_LINE_ENDINGS_CR);
    uart_vfs_dev_port_set_tx_line_endings(port, ESP_LINE_ENDINGS_CRLF);

    const uart_config_t uart = {
        .baud_rate = CONFIG_ESP_CONSOLE_UART_BAUDRATE,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .source_clk = UART_SCLK_DEFAULT,
    };
    esp_err_t err = uart_driver_install(port, 256, 0, 0, NULL, 0);
    if (err == ESP_OK) err = uart_param_config(port, &uart);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "cannot take the console UART: %s", esp_err_to_name(err));
        return err;
    }
    uart_vfs_dev_use_driver(port);

    const esp_console_config_t console = {
        .max_cmdline_args = 8,
        .max_cmdline_length = NE_CONSOLE_LINE_MAX,
        .hint_color = 37,
    };
    err = esp_console_init(&console);
    if (err != ESP_OK) return err;
    linenoiseSetMultiLine(1);
    linenoiseSetCompletionCallback(&esp_console_get_completion);
    linenoiseSetHintsCallback((linenoiseHintsCallback *)&esp_console_get_hint);
    linenoiseHistorySetMaxLen(16);
    linenoiseSetMaxLineLen(NE_CONSOLE_LINE_MAX);
    linenoiseAllowEmpty(false);
    register_commands();

    if (xTaskCreate(console_task, "ne_console", CONFIG_NEUROEDGE_CONSOLE_STACK, NULL, 2, NULL) !=
        pdPASS) {
        return ESP_ERR_NO_MEM;
    }
    return ESP_OK;
#endif
}
