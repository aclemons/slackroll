# syntax=docker/dockerfile:1.23.0@sha256:2780b5c3bab67f1f76c781860de469442999ed1a0d7992a5efdf2cffc0e3d769

FROM aclemons/slackware:15.0@sha256:e7512065b6ad9c63d212bdbb9a0e85fdb587478c8b44d29e6a09cbedf1294c94 AS base

# install python2
RUN export TERSE=0 && \
    sed -i '/^WGETFLAGS/s/"$/ -q"/' /etc/slackpkg/slackpkg.conf && \
    slackpkg -default_answer=yes -batch=on update && \
    EXIT_CODE=0 && { slackpkg -default_answer=yes -batch=on upgrade-all || EXIT_CODE=$? ; } && \
    if [ "$EXIT_CODE" -ne 0 ] && [ "$EXIT_CODE" -ne 20 ] ; then exit "$EXIT_CODE" ; fi && \
    EXIT_CODE=0 && { slackpkg -default_answer=yes -batch=on install aaa_libraries brotli bzip2 db48 e2fsprogs expat gcc-11 gcc-g++-11 gdbm glib2 icu4c keyutils krb5-1 libedit libffi libnsl libpng libtirpc ncurses openssl openssl-solibs pcre python2 readline sqlite xz zlib || EXIT_CODE=$? ; } && \
    if [ "$EXIT_CODE" -ne 0 ] && [ "$EXIT_CODE" -ne 20 ] ; then exit "$EXIT_CODE" ; fi && \
    EXIT_CODE=0 && { slackpkg -default_answer=yes -batch=on install ca-certificates dcron perl || EXIT_CODE=$? ; } && \
    if [ "$EXIT_CODE" -ne 0 ] && [ "$EXIT_CODE" -ne 20 ] ; then exit "$EXIT_CODE" ; fi && \
    c_rehash && update-ca-certificates && \
    rm -rf /var/cache/packages/* && rm -rf /var/lib/slackpkg/*

# setup running tests
RUN pip2 --no-cache-dir install mock==3.0.5 pytest==4.6.11 pytest_cov==2.12.1 && rm -rf /root/.cache
