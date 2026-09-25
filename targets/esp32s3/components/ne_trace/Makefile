# Host build of the trace formatter (TSK-S4-09): python/tests/test_c_trace.py
# compiles and runs it on every PR; this Makefile is for working on it by hand.
#
#   make check-static    no .data/.bss in the object, stack frames from -fstack-usage
#   make clean
CC ?= cc
STRICT = -std=c99 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror
GATE = ../ne_gate/include
OBJECTS = build/ne_trace.o

build:
	mkdir -p build

build/%.o: src/%.c include/ne_trace.h $(GATE)/ne_walker.h $(GATE)/ne_token.h | build
	cd build && $(CC) $(STRICT) -O2 -fstack-usage -I../include -I../$(GATE) -c ../src/$*.c -o $*.o

check-static: $(OBJECTS)
	@! nm $(OBJECTS) | grep -E ' [bBdDC] ' || (echo "the trace component holds writable state" && false)
	@cat build/ne_trace.su

clean:
	rm -rf build

.PHONY: check-static clean
