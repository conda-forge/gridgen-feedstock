@echo on

cmake -S "%RECIPE_DIR%" -B build -G Ninja ^
    -DGRIDGEN_SOURCE_DIR="%SRC_DIR%\gridgen" ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_INSTALL_PREFIX="%LIBRARY_PREFIX%" ^
    -DCMAKE_PREFIX_PATH="%LIBRARY_PREFIX%" ^
    -DCMAKE_INSTALL_LIBDIR=lib
if errorlevel 1 exit /b 1

cmake --build build --parallel %CPU_COUNT%
if errorlevel 1 exit /b 1

ctest --test-dir build --output-on-failure
if errorlevel 1 exit /b 1

cmake --install build
if errorlevel 1 exit /b 1
