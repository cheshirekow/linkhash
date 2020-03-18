@PACKAGE_INIT@
set(linkhash_BINDIR @PACKAGE_CMAKE_INSTALL_BINDIR@)

include(${CMAKE_CURRENT_LIST_DIR}/linkhash-targets.cmake)
check_required_components(linkhash)

function(_error)
  message(FATAL_ERROR " activate_linkcache(): " ${ARGN})
endfunction()

function(activate_linkcache)
  set(_args_VERBOSITY "info")
  cmake_parse_arguments(_args "" "LOG_LEVEL" "" ${ARGN})

  set(_linkcache_path "${linkhash_BINDIR}/linkcache")
  if(NOT EXISTS ${_linkcache_path})
    _error("linkcache not found at expected location: ${linkhash_BINDIR}")
  endif()

  if(_args_UNPARSED_ARGUMENTS)
    _error("too-many arguments to activate_linkcache():"
           " ${_args_UNPARSED_ARGUMENTS}")
  endif()

  set(_suffix)
  if(_args_LOG_LEVEL)
    set(_valid_LOG_LEVEL debug;info;warning;error)
    list(FIND _valid_LOG_LEVEL "${_args_LOG_LEVEL}" _found_LOG_LEVEL)
    if("${_found_LOG_LEVEL}" EQUAL "-1")
      _error("Invalid LOG_LEVEL: ${_args_LOG_LEVEL}")
    endif()
    set(_suffix " --log-level ${_args_LOG_LEVEL}")
  endif()

  set(_prefix)
  get_property(_preexisting_launcher GLOBAL PROPERTY RULE_LAUNCH_LINK)
  if(_preexisting_launcher)
    set(_prefix "${_preexisting_launcher} ")
  endif()

  if("${_args_LOG_LEVEL}" STREQUAL "debug")
    message(STATUS " linkcache enabled from ${_linkcache_path}")
  endif()

  set(_cmd "${_prefix}${_linkcache_path}${_suffix}")
  set_property(GLOBAL PROPERTY RULE_LAUNCH_LINK "${_cmd}")
endfunction()
