# Host build of the gate walker and token ledger (TSK-S4-02, TSK-S4-07): runs on
# every PR through python/tests/test_c_walker.py and python/tests/test_c_token.py,
# which also generate the case files and scripts.
#
#   make                 build the sanitised runners
#   make check-static    no .data/.bss in either object, stack frames from -fstack-usage
#   make clean
CC ?= cc
STRICT = -std=c99 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Werror
SAN = -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer
OBJECTS = build/ne_walker.o build/ne_token.o

all: build/test_walker_host build/test_token_host

build:
	mkdir -p build

build/test_walker_host: src/ne_walker.c test/test_walker_host.c include/ne_walker.h | build
	$(CC) -std=c99 -Wall -Wextra -Wpedantic -Wshadow -O1 -g $(SAN) -Iinclude src/ne_walker.c test/test_walker_host.c -o $@

build/test_token_host: src/ne_token.c test/test_token_host.c include/ne_token.h include/ne_walker.h | build
	$(CC) -std=c99 -Wall -Wextra -Wpedantic -Wshadow -O1 -g $(SAN) -Iinclude src/ne_token.c test/test_token_host.c -o $@

build/%.o: src/%.c include/ne_walker.h include/ne_token.h | build
	cd build && $(CC) $(STRICT) -O2 -fstack-usage -I../include -c ../src/$*.c -o $*.o

check-static: $(OBJECTS)
	@! nm $(OBJECTS) | grep -E ' [bBdDC] ' || (echo "the gate component holds writable state" && false)
	@cat build/ne_walker.su build/ne_token.su

clean:
	rm -rf build

.PHONY: all check-static clean
