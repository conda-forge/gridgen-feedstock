/*
 * Build configuration for gridgen with clang targeting the MSVC ABI, used in
 * place of the config.h that upstream's configure script generates.
 *
 * gridgen does arithmetic on _Complex double, which clang supports natively.
 * The UCRT <complex.h> however only declares its functions for the struct
 * type _Dcomplex, so wrap the ones gridgen uses (cabs, carg, cexp, clog, conj,
 * creal, cimag) for _Complex double.
 */
#ifndef GRIDGEN_CONFIG_H
#define GRIDGEN_CONFIG_H

#define zdouble _Complex double
/* The UCRT provides tgamma */
#define HAVE_TGAMMA 1
#define HAVE_GRIDNODES_H 1

/* Include <math.h> first, so that a later include cannot redefine the names
 * below. */
#include <math.h>
#include <complex.h>

static inline _Dcomplex gridgen_to_dcomplex(double _Complex z)
{
    return _Cbuild(__real__ z, __imag__ z);
}

static inline double _Complex gridgen_from_dcomplex(_Dcomplex z)
{
    return __builtin_complex(z._Val[0], z._Val[1]);
}

static inline double gridgen_cabs(double _Complex z)
{
    return cabs(gridgen_to_dcomplex(z));
}

static inline double gridgen_carg(double _Complex z)
{
    return carg(gridgen_to_dcomplex(z));
}

static inline double _Complex gridgen_cexp(double _Complex z)
{
    return gridgen_from_dcomplex(cexp(gridgen_to_dcomplex(z)));
}

static inline double _Complex gridgen_clog(double _Complex z)
{
    return gridgen_from_dcomplex(clog(gridgen_to_dcomplex(z)));
}

#undef I
#undef cabs
#undef carg
#undef cexp
#undef clog
#undef conj
#undef creal
#undef cimag

#define I (__extension__ 1.0i)
#define cabs(z) gridgen_cabs(z)
#define carg(z) gridgen_carg(z)
#define cexp(z) gridgen_cexp(z)
#define clog(z) gridgen_clog(z)
#define conj(z) (~(z))
#define creal(z) (__real__(z))
#define cimag(z) (__imag__(z))

#endif /* GRIDGEN_CONFIG_H */
