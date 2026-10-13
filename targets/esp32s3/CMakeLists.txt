cmake_minimum_required(VERSION 3.16)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
# A .su file per object, read by scripts/check_stack_usage.py (Q-79 stack guard).
idf_build_set_property(COMPILE_OPTIONS "-fstack-usage" APPEND)
project(neuroedge-esp32s3-box3)
