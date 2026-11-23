# Use the policies of CMake versions up to 4.5 when available.
cmake_minimum_required(VERSION 3.20...4.5)
# The version is defined in recipe.yaml; this build does not use it.
project(gridgen LANGUAGES C)

# Upstream does arithmetic on C99 _Complex double, which MSVC's cl does not
# support. clang targeting the MSVC ABI does, and stays link-compatible with
# the MSVC-built gridutils (gu.lib).
if(NOT CMAKE_C_COMPILER_ID STREQUAL "Clang" OR NOT CMAKE_C_SIMULATE_ID STREQUAL "MSVC")
    message(FATAL_ERROR "This build requires clang targeting the MSVC ABI.")
endif()

set(GRIDGEN_SOURCE_DIR "" CACHE PATH "Path to the upstream gridgen source directory")
if(NOT EXISTS "${GRIDGEN_SOURCE_DIR}/gridgen.c")
    message(FATAL_ERROR "Set GRIDGEN_SOURCE_DIR to the upstream gridgen directory.")
endif()

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# Do not allow a successful build with gridgen_generategrid2 silently disabled.
find_path(GRIDUTILS_INCLUDE_DIR NAMES gridnodes.h REQUIRED)
find_library(GRIDUTILS_LIBRARY NAMES gu gridutils REQUIRED)

# Mirrors SRC in upstream's makefile.in; check it on every version update.
set(GRIDGEN_SOURCES
    broyden.c
    delaunay.c
    geom.c
    gridgen.c
    hash.c
    issimplepoly.c
    istack.c
    ode.c
    swcr.c
    vertlist.c
    zode.c
    triangle.c
)
list(TRANSFORM GRIDGEN_SOURCES PREPEND "${GRIDGEN_SOURCE_DIR}/")
set_source_files_properties("${GRIDGEN_SOURCE_DIR}/triangle.c" PROPERTIES
    # NO_TIMER: Triangle's timing code needs <sys/time.h>, which MSVC lacks.
    COMPILE_DEFINITIONS "TRILIBRARY;NO_TIMER"
    # Preserve Triangle's robust predicates; do not contract multiply/add.
    COMPILE_OPTIONS "-w;-ffp-contract=off"
)

add_library(gridgen_shared SHARED ${GRIDGEN_SOURCES})
set_target_properties(gridgen_shared PROPERTIES OUTPUT_NAME gridgen)
# Export only the public API, not Triangle and other bundled implementation
# symbols. The gridutils functions are exported as well, because gridutils
# only provides a static library on Windows, and consumers such as pygridgen
# call them through gridgen's library to read and free the gridnodes returned
# by gridgen_generategrid2. Drop them once gridutils ships a DLL.
# Keep this list in sync with the exports checked in test_library.py.
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/gridgen.def"
    "EXPORTS\n"
    "gridgen_setverbose\n"
    "gridgen_printversion\n"
    "gridgen_printhelpalg\n"
    "gridgen_printhelpprm\n"
    "gridgen_generategrid\n"
    "gridgen_generategrid2\n"
    "gridnodes_getx\n"
    "gridnodes_gety\n"
    "gridnodes_getnce1\n"
    "gridnodes_getnce2\n"
    "gridnodes_destroy\n"
    "gridmap_build\n")
target_sources(gridgen_shared PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/gridgen.def")

# Match upstream: the executable compiles out the gridutils-dependent API.
add_executable(gridgen "${GRIDGEN_SOURCE_DIR}/main.c" ${GRIDGEN_SOURCES})
target_compile_definitions(gridgen PRIVATE GRIDGEN_STANDALONE)
foreach(target gridgen_shared gridgen)
    target_include_directories(${target} PRIVATE
        # for config.h, which upstream does not ship
        "${CMAKE_CURRENT_SOURCE_DIR}"
        "${GRIDGEN_SOURCE_DIR}"
        "${GRIDUTILS_INCLUDE_DIR}"
    )
    target_compile_definitions(${target} PRIVATE
        ANSI_DECLARATORS
        # M_PI is only defined by the UCRT <math.h> with _USE_MATH_DEFINES
        _USE_MATH_DEFINES
        _CRT_SECURE_NO_WARNINGS
        _CRT_NONSTDC_NO_WARNINGS
    )
endforeach()
# Complex multiplication and division compile to calls to __muldc3 and
# __divdc3 from compiler-rt's builtins library, which conda-forge's clang
# activation adds to LDFLAGS.
target_link_libraries(gridgen_shared PRIVATE "${GRIDUTILS_LIBRARY}")
# gu.lib is built with the static CRT (/MT) and so requests LIBCMT, while
# conda-forge builds use the dynamic CRT (-fms-runtime-lib=dll). Do not link
# LIBCMT, so that gridgen.dll uses only the dynamic CRT. Remove this once
# gridutils builds gu.lib with /MD.
target_link_options(gridgen_shared PRIVATE "LINKER:/NODEFAULTLIB:LIBCMT")

# The public API does not expose complex numbers. Keep the installed header
# usable by other consumers and avoid installing a generic "config.h".
file(READ "${GRIDGEN_SOURCE_DIR}/gridgen.h" GRIDGEN_PUBLIC_HEADER)
string(REPLACE "#include \"config.h\"" "#include \"gridgen_config.h\""
    GRIDGEN_PUBLIC_HEADER "${GRIDGEN_PUBLIC_HEADER}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/gridgen.h" "${GRIDGEN_PUBLIC_HEADER}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/gridgen_config.h"
    "#ifndef GRIDGEN_PUBLIC_CONFIG_H\n#define GRIDGEN_PUBLIC_CONFIG_H\n"
    "#define HAVE_GRIDNODES_H 1\n#endif\n")

install(TARGETS gridgen gridgen_shared)
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/gridgen.h"
    "${CMAKE_CURRENT_BINARY_DIR}/gridgen_config.h"
    TYPE INCLUDE
)
