@echo on

cmake %CMAKE_ARGS% -S "%RECIPE_DIR%" -B build -G Ninja ^
    -DGRIDGEN_SOURCE_DIR="%SRC_DIR%\gridgen" ^
    -DCMAKE_PREFIX_PATH="%LIBRARY_PREFIX%"
if errorlevel 1 exit /b 1

cmake --build build --parallel %CPU_COUNT%
if errorlevel 1 exit /b 1

cmake --install build
if errorlevel 1 exit /b 1
