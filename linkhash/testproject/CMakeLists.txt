cmake_minimum_required(VERSION 3.5)
project(linkhash-test)

option(ENABLE_LINKCACHE
       "Enable link caching. NOTE: the helper program must also be installed"
       OFF)

find_package(linkhash)
if(linkhash_FOUND AND ENABLE_LINKCACHE)
  activate_linkcache(LOG_LEVEL debug)
endif()

add_library(foo SHARED foo.cc)
add_library(bar SHARED bar.cc)
target_link_libraries(bar foo)
add_executable(prog main.cc)
target_link_libraries(prog bar)
