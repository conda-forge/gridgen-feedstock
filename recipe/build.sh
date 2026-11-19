#!/bin/bash

# triangle.c uses K&R-style function definitions, which are invalid in C23
# (the default since GCC 15), so pin an older C standard
export CFLAGS="-std=gnu17 -I$PREFIX/include $CFLAGS"
export LDFLAGS="-L$PREFIX/lib"
export CPPFLAGS="-I/$PREFIX/include $CPPFLAGS"

pushd gridgen

./configure --prefix=$PREFIX

make
make lib
make shlib
make tests
make install

popd
