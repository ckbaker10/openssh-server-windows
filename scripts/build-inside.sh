#!/usr/bin/env bash
set -euo pipefail
cd /project

target=x86_64-pc-cygwin
sysroot=$($target-gcc -print-sysroot)
case "$sysroot" in
    /usr/x86_64-pc-cygwin/sys-root) ;;
    *) echo "Unexpected compiler sysroot: $sysroot" >&2; exit 1 ;;
esac

# Only project-owned generated directories are replaced on a rebuild.
rm -rf work/sysroot work/runtime work/openssh-portable work/obj work/package
python3 scripts/inputs.py stage
cp -a work/sysroot/. "$sysroot/"
export CYGWIN_SYSROOT="$sysroot"
export SOURCE_DATE_EPOCH=1791244800
tar --no-same-owner -xf work/source-package/openssh-10.6p1-1.src/openssh-portable-10.6p1.tar.bz2 -C work
patch -d work/openssh-portable -p1 < patches/cygwin-cross-textreadmode.patch

mkdir -p work/obj work/package
cd work/obj
export CC="$target-gcc" AR="$target-ar" RANLIB="$target-ranlib"
export CFLAGS='-O2 -g -fstack-protector-strong'
export CPPFLAGS="-I$sysroot/usr/include"
export LDFLAGS="-B$sysroot/usr/lib/ -L$sysroot/usr/lib"
../../work/openssh-portable/configure \
    --build="$(gcc -dumpmachine)" --host="$target" \
    --prefix=/usr --sysconfdir=/etc --libexecdir=/usr/sbin \
    --with-privsep-path=/var/empty --with-pid-dir=/var/run \
    --without-pam --without-kerberos5 --without-libedit \
    --without-security-key-builtin --without-selinux --without-audit \
    --disable-strip
make -j"${BUILD_JOBS:-4}"
make install-nokeys DESTDIR=/project/work/package
make -C ../openssh-portable/contrib/cygwin install-scripts install-cygwindoc DESTDIR=/project/work/package
install -D -m 644 ../openssh-portable/LICENCE /project/work/package/usr/share/doc/openssh/LICENCE
cd /project
python3 scripts/package.py
