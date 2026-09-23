# Host build of the gate walker (TSK-S4-07): runs on every PR through
# python/tests/test_c_walker.py, which also generates the case files.
#
#   make                 build the sanitised conformance runner
#   make check-static    no .data/.bss, stack frames from -fstack-usage
#   make clean
CC ?= cc
STRICT = -std=c99 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror
SAN = -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer

all: build/test_walker_host

build:
	mkdir -p build

build/test_walker_host: src/ne_walker.c test/test_walker_host.c include/ne_walker.h | build
	$(CC) -std=c99 -Wall -Wextra -Wpedantic -Wshadow -O1 -g $(SAN) -Iinclude src/ne_walker.c test/test_walker_host.c -o $@

build/ne_walker.o: src/ne_walker.c include/ne_walker.h | build
	cd build && $(CC) $(STRICT) -O2 -fstack-usage -I../include -c ../src/ne_walker.c -o ne_walker.o

check-static: build/ne_walker.o
	@! nm build/ne_walker.o | grep -E ' [bBdDC] ' || (echo "walker holds writable state" && false)
	@cat build/ne_walker.su

clean:
	rm -rf build

.PHONY: all check-static clean
