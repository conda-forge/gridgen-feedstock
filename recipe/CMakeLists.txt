cmake_minimum_required(VERSION 3.20)
project(gridgen VERSION 1.51.5 LANGUAGES C)

if(NOT MINGW)
    message(FATAL_ERROR "This build requires MinGW-w64 for upstream's C complex arithmetic.")
endif()

set(GRIDGEN_SOURCE_DIR "" CACHE PATH "Path to the upstream gridgen source directory")
if(NOT EXISTS "${GRIDGEN_SOURCE_DIR}/gridgen.c")
    message(FATAL_ERROR "Set GRIDGEN_SOURCE_DIR to the upstream gridgen directory.")
endif()

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)
include(GNUInstallDirs)
include(CheckCSourceCompiles)
include(CheckSymbolExists)

set(CMAKE_REQUIRED_LIBRARIES m)
check_c_source_compiles("
    #include <complex.h>
    int main(void) {
        volatile double complex z = 1.0 + I;
        return (int)creal(clog(z) + cexp(z) + csqrt(z));
    }" HAVE_C99_COMPLEX)
if(NOT HAVE_C99_COMPLEX)
    message(FATAL_ERROR "Working C99 complex arithmetic and math functions are required.")
endif()
check_symbol_exists(tgamma "math.h" HAVE_TGAMMA)
check_symbol_exists(lgamma "math.h" HAVE_LGAMMA)
unset(CMAKE_REQUIRED_LIBRARIES)
if(NOT HAVE_TGAMMA AND NOT HAVE_LGAMMA)
    message(FATAL_ERROR "Either tgamma or lgamma is required.")
endif()

# Do not allow a successful build with gridgen_generategrid2 silently disabled.
find_path(GRIDUTILS_INCLUDE_DIR NAMES gridnodes.h REQUIRED)
find_library(GRIDUTILS_LIBRARY NAMES gu gridutils REQUIRED)

file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/config.h"
    "#ifndef GRIDGEN_BUILD_CONFIG_H\n#define GRIDGEN_BUILD_CONFIG_H\n"
    "#include <complex.h>\n#define zdouble _Complex double\n"
    "#define HAVE_COMPLEX 1\n#define HAVE_GRIDNODES_H 1\n")
foreach(feature HAVE_TGAMMA HAVE_LGAMMA)
    if(${feature})
        file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/config.h" "#define ${feature} 1\n")
    endif()
endforeach()
file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/config.h" "#endif\n")

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
    COMPILE_DEFINITIONS TRILIBRARY
    # Preserve Triangle's robust predicates; do not contract multiply/add.
    COMPILE_OPTIONS "-w;-ffloat-store;-ffp-contract=off"
)

add_library(gridgen_shared SHARED ${GRIDGEN_SOURCES})
set_target_properties(gridgen_shared PROPERTIES
    OUTPUT_NAME gridgen
    PREFIX ""
    IMPORT_PREFIX "lib"
)
# Export only the public API, not Triangle and other bundled implementation symbols.
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/gridgen.def"
    "EXPORTS\n"
    "gridgen_setverbose\n"
    "gridgen_printversion\n"
    "gridgen_printhelpalg\n"
    "gridgen_printhelpprm\n"
    "gridgen_generategrid\n"
    "gridgen_generategrid2\n")
target_sources(gridgen_shared PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/gridgen.def")

add_library(gridgen_static STATIC ${GRIDGEN_SOURCES})
set_target_properties(gridgen_static PROPERTIES OUTPUT_NAME gridgen)

# Match upstream: the executable compiles out the gridutils-dependent API.
add_executable(gridgen "${GRIDGEN_SOURCE_DIR}/main.c" ${GRIDGEN_SOURCES})
target_compile_definitions(gridgen PRIVATE GRIDGEN_STANDALONE)
foreach(target gridgen_shared gridgen_static gridgen)
    target_include_directories(${target} PRIVATE
        "${CMAKE_CURRENT_BINARY_DIR}"
        "${GRIDGEN_SOURCE_DIR}"
        "${GRIDUTILS_INCLUDE_DIR}"
    )
    target_compile_definitions(${target} PRIVATE ANSI_DECLARATORS)
    target_link_libraries(${target} PRIVATE m)
endforeach()
target_link_libraries(gridgen_shared PRIVATE "${GRIDUTILS_LIBRARY}")

enable_testing()
add_test(NAME gridgen_help COMMAND gridgen -h)

# The public API does not expose complex numbers. Keep the installed header
# usable by non-GNU consumers and avoid installing a generic "config.h".
file(READ "${GRIDGEN_SOURCE_DIR}/gridgen.h" GRIDGEN_PUBLIC_HEADER)
string(REPLACE "#include \"config.h\"" "#include \"gridgen_config.h\""
    GRIDGEN_PUBLIC_HEADER "${GRIDGEN_PUBLIC_HEADER}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/gridgen.h" "${GRIDGEN_PUBLIC_HEADER}")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/gridgen_config.h"
    "#ifndef GRIDGEN_PUBLIC_CONFIG_H\n#define GRIDGEN_PUBLIC_CONFIG_H\n"
    "#define HAVE_GRIDNODES_H 1\n#endif\n")

install(TARGETS gridgen gridgen_shared gridgen_static
    RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
    LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
)
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/gridgen.h"
    "${CMAKE_CURRENT_BINARY_DIR}/gridgen_config.h"
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
)
