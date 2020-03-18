get_version_from_header(linkhash.cc LINKHASH_VERSION)

cc_binary(
  linkhash
  SRCS linkhash.cc
  DEPS argue::static fmt::fmt loki
  PKGDEPS openssl)

add_custom_command(
  TARGET linkhash
  POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:linkhash>
          ${CMAKE_BINARY_DIR}/linkhash.debug
  COMMAND ${CMAKE_STRIP} -g $<TARGET_FILE:linkhash>)

# NOTE(josh): If CMAKE_LIBRARY_ARCHITECTURE is defined (it is on debian) then
# ${CMAKE_INSTALL_LIBDIR} will end with it's value. We don't want to install
# there because linkhash is a cmake utility package, not a package of software
# to be built into the project.
set(_package_location lib/cmake/linkhash)

write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/linkhash-config-version.cmake"
  VERSION "${LINKHASH_VERSION}"
  COMPATIBILITY AnyNewerVersion)

configure_package_config_file(
  linkhash-config.cmake ${CMAKE_CURRENT_BINARY_DIR}/linkhash-config.cmake
  PATH_VARS CMAKE_INSTALL_BINDIR INSTALL_DESTINATION ${_package_location})

install(
  TARGETS linkhash
  EXPORT linkhash-targets
  RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")

export(
  EXPORT linkhash-targets
  FILE "${CMAKE_CURRENT_BINARY_DIR}/linkhash-targets.cmake"
  NAMESPACE "linkhash::")

install(
  PROGRAMS linkcache.py
  DESTINATION "${CMAKE_INSTALL_BINDIR}"
  RENAME linkcache)

install(
  EXPORT linkhash-targets
  FILE linkhash-targets.cmake
  NAMESPACE "linkhash::"
  DESTINATION ${_package_location})

install(FILES "${CMAKE_CURRENT_BINARY_DIR}/linkhash-config.cmake"
              "${CMAKE_CURRENT_BINARY_DIR}/linkhash-config-version.cmake"
        DESTINATION ${_package_location})

# cmake-format: off
set(_code
    "execute_process("
    "  COMMAND python -Bm tangent.tooling.install_debug_symbols "
    "    --bin-path ${CMAKE_BINARY_DIR}/linkhash.debug"
    "    --lib-dir ${CMAKE_INSTALL_PREFIX}/lib"
    "  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}"
    ")")
# cmake-format: on
string(REPLACE ";" "\n" _code "${_code}")
install(CODE ${_code})

set(_config "noconfig")
if(CMAKE_BUILD_TYPE)
  string(TOLOWER "${CMAKE_BUILD_TYPE}" _config)
endif()

set(_exportdir
    "${CMAKE_CURRENT_BINARY_DIR}/CMakeFiles/Export/${_package_location}")

add_custom_target(
  linkhash-testproject
  COMMAND
    python -Bm linkhash.test_linkcache #
    --linkhash $<TARGET_FILE:linkhash> #
    --linkcache ${CMAKE_CURRENT_SOURCE_DIR}/linkcache.py #
    --project-template ${CMAKE_CURRENT_SOURCE_DIR}/testproject #
    --pkgdir ${_package_location} #
    --bindir ${CMAKE_CURRENT_BINARY_DIR}
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/linkhash-config.cmake"
          "${CMAKE_CURRENT_BINARY_DIR}/linkhash-config-version.cmake"
          "${_exportdir}/linkhash-targets.cmake"
          "${_exportdir}/linkhash-targets-${_config}.cmake"
          "$<TARGET_FILE:linkhash>"
          "linkcache.py")

add_test(
  NAME linkhash-testproject
  COMMAND
    python -Bm linkhash.test_linkcache #
    --linkhash $<TARGET_FILE:linkhash> #
    --linkcache ${CMAKE_CURRENT_SOURCE_DIR}/linkcache.py #
    --project-template ${CMAKE_CURRENT_SOURCE_DIR}/testproject #
    --pkgdir ${_package_location} #
    --bindir ${CMAKE_CURRENT_BINARY_DIR}
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
