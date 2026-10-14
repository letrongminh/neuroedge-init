/*
 * Host harness of the brain bridge (TSK-I2f-12): python/tests/test_c_bridge.py builds it with
 * an agent's generated ne_agent component and drives it with a script, one command per line:
 *
 *   time <ms>                     the clock
 *   fact <criterion> <value|->    what the on-chip fact source reads, for every gate (- = none);
 *                                 <value>@<confidence> gives it a confidence
 *   reads                         -> reads<TAB>n: how often the fact source was read
 *   degraded none|unreachable|budget
 *   owner <id|->                  re-init the bridge with this owner (- = none)
 *   tools                         -> tool<TAB>name<TAB>description<TAB>schema, one per tool
 *   call <name> [<json>]          -> result<TAB>status<TAB>json
 *   answer <id> <0|1> <from|->    -> result<TAB>status<TAB>json
 *   button <0|1>                  -> result<TAB>status<TAB>json
 *   waiting                       -> waiting<TAB>n
 *
 * The device prints run<TAB>action<TAB>arg=value... and drive<TAB>pin<TAB>reason for every pin
 * of an action it runs, as ne_token_authorize decided it.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ne_brain_bridge.h"

#define MAX_FACTS 32

typedef struct {
    char name[64];
    char value[64];
    int present;
} fake_fact;

typedef struct {
    uint32_t now;
    ne_degraded degraded;
    fake_fact facts[MAX_FACTS];
    uint32_t fact_count;
    const ne_agent *agent;
    uint32_t reads;
} device;

static device dev;
static ne_ledger ledger;
static ne_bridge bridge;
static ne_bridge_result result;
static unsigned rng = 1u;

static void fill(void *buf, size_t len)
{
    unsigned char *p = buf;
    for (size_t i = 0; i < len; i++) {
        rng = rng * 1103515245u + 12345u;
        p[i] = (unsigned char)(rng >> 16);
    }
}

static uint32_t now_ms(void *ctx)
{
    return ((device *)ctx)->now;
}

static ne_degraded read_facts(void *ctx, const ne_tree *gate, uint32_t gate_index, ne_fact *facts,
                              uint32_t count, uint32_t now)
{
    device *d = ctx;
    (void)gate_index;
    (void)now;
    d->reads++;
    for (uint32_t i = 0; i < count; i++) {
        const char *name = ne_criterion_name(gate, i);
        for (uint32_t k = 0; name && k < d->fact_count; k++) {
            const fake_fact *f = &d->facts[k];
            if (strcmp(f->name, name) != 0 || !f->present) continue;
            facts[i].present = 1;
            char value[64];
            snprintf(value, sizeof value, "%s", f->value);
            char *at = strchr(value, '@');
            if (at) {
                *at = '\0';
                facts[i].has_confidence = 1;
                facts[i].confidence = strtod(at + 1, NULL);
            }
            if (ne_criterion_kind(gate, i) == NE_KIND_NUMERIC) {
                facts[i].value = strtod(value, NULL);
                facts[i].age_ms = 0;
                break;
            }
            for (uint32_t j = 0; j < NE_MAX_DOMAIN; j++) {
                const char *v = ne_domain_value(gate, i, j);
                if (v == NULL) break;
                if (strcmp(v, value) == 0) {
                    facts[i].in_domain = 1;
                    facts[i].index = (uint8_t)j;
                }
            }
            break;
        }
    }
    return d->degraded;
}

static void run(void *ctx, uint32_t action, const ne_arg_value *args, uint32_t arg_count,
                ne_ledger *l, const ne_token *token)
{
    device *d = ctx;
    const ne_agent_action *a = &d->agent->actions[action];
    const ne_tree *tree = NULL;
    ne_tree loaded;
    const ne_agent_gate *g = &d->agent->gates[a->gate];
    if (ne_tree_load(&loaded, g->tree, g->tree_size) == NE_OK) tree = &loaded;
    printf("run\t%s", a->name);
    for (uint32_t i = 0; tree && i < arg_count; i++) {
        const ne_arg_value *v = &args[i];
        printf("\t%s=", ne_argument_name(tree, i));
        if (!v->present) printf("-");
        else if (v->type == NE_ARG_STRING) printf("%.*s", (int)v->str_len, v->str);
        else printf("%g", v->number);
    }
    printf("\n");
    for (uint32_t pin = 0; pin < d->agent->pin_count; pin++) {
        if (!(a->pin_mask & (1u << pin))) continue;
        ne_token_reason why = ne_token_authorize(l, token, pin, d->now);
        printf("drive\t%s\t%s\n", d->agent->pins[pin], ne_token_reason_name(why));
    }
}

/* The next space-separated word of *rest (C99 has no strsep). */
static char *word(char **rest, const char *sep)
{
    char *start = *rest;
    if (start == NULL) return NULL;
    char *end = strpbrk(start, sep);
    if (end) {
        *end = '\0';
        *rest = end + 1;
    } else {
        *rest = NULL;
    }
    return start;
}

static const char *const STATUS[] = {"ALLOW", "BLOCK", "REJECTED"};

static void print_result(void)
{
    if (strlen(result.json) != result.len) {
        printf("error\tlength %u, string %zu\n", (unsigned)result.len, strlen(result.json));
    }
    printf("result\t%s\t%s\n", STATUS[result.status], result.json);
}

static void init(const char *owner)
{
    static const ne_fact_source source = {&dev, read_facts};
    static const ne_bridge_hal hal = {&dev, now_ms, fill, run};
    ne_ledger_init(&ledger, 0x2468u);
    if (ne_bridge_init(&bridge, dev.agent, &ledger, &source, &hal, owner) != 0) {
        printf("error\tinit\n");
    }
}

int main(int argc, char **argv)
{
    static char line[4096];
    FILE *script = argc > 1 ? fopen(argv[1], "r") : stdin;
    if (script == NULL) return 2;
    dev.agent = &ne_agent_linked;
    init(NULL);
    while (fgets(line, sizeof line, script)) {
        line[strcspn(line, "\n")] = '\0';
        char *rest = line;
        char *cmd = word(&rest, " ");
        if (cmd == NULL || *cmd == '\0' || *cmd == '#') continue;
        if (strcmp(cmd, "time") == 0) {
            dev.now = (uint32_t)strtoul(rest, NULL, 10);
        } else if (strcmp(cmd, "fact") == 0) {
            char *name = word(&rest, " ");
            fake_fact *f = NULL;
            for (uint32_t k = 0; k < dev.fact_count; k++) {
                if (strcmp(dev.facts[k].name, name) == 0) f = &dev.facts[k];
            }
            if (f == NULL && dev.fact_count < MAX_FACTS) f = &dev.facts[dev.fact_count++];
            if (f == NULL) return 3;
            snprintf(f->name, sizeof f->name, "%s", name);
            f->present = rest && strcmp(rest, "-") != 0;
            snprintf(f->value, sizeof f->value, "%s", rest ? rest : "");
        } else if (strcmp(cmd, "degraded") == 0) {
            dev.degraded = strcmp(rest, "unreachable") == 0 ? NE_DEGRADED_UNREACHABLE
                           : strcmp(rest, "budget") == 0    ? NE_DEGRADED_BUDGET
                                                            : NE_DEGRADED_NONE;
        } else if (strcmp(cmd, "owner") == 0) {
            init(strcmp(rest, "-") == 0 ? NULL : rest);
        } else if (strcmp(cmd, "tools") == 0) {
            for (uint32_t i = 0; i < ne_bridge_tool_count(&bridge); i++) {
                const char *name, *description, *schema;
                ne_bridge_tool(&bridge, i, &name, &description, &schema);
                printf("tool\t%s\t%s\t%s\n", name, description, schema);
            }
        } else if (strcmp(cmd, "call") == 0) {
            char *name = word(&rest, " ");
            ne_bridge_call(&bridge, name, rest, &result);
            print_result();
        } else if (strcmp(cmd, "answer") == 0) {
            char *id = word(&rest, " ");
            char *approve = word(&rest, " ");
            ne_bridge_answer(&bridge, id, atoi(approve), strcmp(rest, "-") == 0 ? NULL : rest,
                             &result);
            print_result();
        } else if (strcmp(cmd, "button") == 0) {
            ne_bridge_answer_button(&bridge, atoi(rest), &result);
            print_result();
        } else if (strcmp(cmd, "reads") == 0) {
            printf("reads\t%u\n", (unsigned)dev.reads);
        } else if (strcmp(cmd, "waiting") == 0) {
            printf("waiting\t%u\n", (unsigned)ne_bridge_waiting(&bridge));
        } else {
            printf("error\tunknown command %s\n", cmd);
        }
        fflush(stdout);
    }
    return 0;
}
