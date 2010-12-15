PKGNAME=simple-image-reducer
VERSION=1.0.1

SUBDIRS=po

PREFIX=/usr

BINDIR=${PREFIX}/bin
DATADIR=${PREFIX}/share

all:	simple-image-reducer $(PKGNAME).desktop

po/$(PKGNAME).pot:: subdirs

subdirs:	$(PKGNAME).desktop.in.h
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1; done

simple-image-reducer: simple-image-reducer.py
	sed "s/@VERSION@/$(VERSION)/g" $< >$@

%.desktop.in.h:	%.desktop.in
	intltool-extract --type=gettext/ini $<

%.desktop: %.desktop.in po/$(PKGNAME).pot po/*.po
	intltool-merge -u -d po/ $< $@

%.spec: %.spec.in
	sed "s/@VERSION@/$(VERSION)/g" $< >$@

install:	all
	mkdir -p $(DESTDIR)$(BINDIR)
	mkdir -p $(DESTDIR)$(DATADIR)/pixmaps
	mkdir -p $(DESTDIR)$(DATADIR)/applications
	mkdir -p $(DESTDIR)$(DATADIR)/icons/hicolor/48x48/apps
	mkdir -p $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps
	install -m 0755 simple-image-reducer $(DESTDIR)$(BINDIR)
	install -m 0644 ${PKGNAME}.desktop $(DESTDIR)$(DATADIR)/applications/${PKGNAME}.desktop
	install -m 0644 ${PKGNAME}.png $(DESTDIR)$(DATADIR)/pixmaps
	install -m 0644 ${PKGNAME}.png $(DESTDIR)$(DATADIR)/icons/hicolor/48x48/apps
	install -m 0644 ${PKGNAME}.svg $(DESTDIR)$(DATADIR)/icons/hicolor/scalable/apps
	for d in $(SUBDIRS); do \
	(cd $$d; $(MAKE) DESTDIR=$(DESTDIR) install) \
		|| case "$(MFLAGS)" in *k*) fail=yes;; *) exit 1;; esac; \
	done && test -z "$$fail"

dist: $(PKGNAME).spec
	mkdir -p .dist/${PKGNAME}-${VERSION}
	cp -a Makefile \
	    AUTHORS COPYING README \
	    ${PKGNAME}.py \
	    ${PKGNAME}.desktop.in \
	    ${PKGNAME}.png \
	    ${PKGNAME}.svg \
	    ${PKGNAME}.spec \
	    ${PKGNAME}.spec.in \
	    .dist/${PKGNAME}-${VERSION}
	mkdir -p .dist/${PKGNAME}-${VERSION}/po
	cp -a po/Makefile \
	    po/${PKGNAME}.pot \
	    po/*.po po/*.mo \
	    .dist/${PKGNAME}-${VERSION}/po
	cd .dist && tar cjf ../${PKGNAME}-${VERSION}.tar.bz2 ${PKGNAME}-${VERSION}
	rm -rf .dist

clean:
	@rm -fv *~
	@rm -fv *.pyc
	@rm -fv simple-image-reducer
	@rm -fv simple-image-reducer.desktop simple-image-reducer.desktop.in.h
